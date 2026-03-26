import asyncio
import os
import sys
import time
import json
from pathlib import Path
from dotenv import load_dotenv

# Setup paths
PROJECT_ROOT = Path(__file__).parents[1]
BACKEND_ROOT = PROJECT_ROOT / "nexus_backend"
BENCH_ROOT = PROJECT_ROOT / "test_memory_bench"
sys.path.append(str(PROJECT_ROOT))
sys.path.append(str(BACKEND_ROOT))
sys.path.append(str(BENCH_ROOT / "src"))

# Force override to ensure settings from .env are picked up
load_dotenv(dotenv_path=BACKEND_ROOT / ".env", override=True)

# FORCE FIX AI_BASE_URL
os.environ["AI_BASE_URL"] = "https://api.apiyi.com/v1"
os.environ["OPENAI_BASE_URL"] = "https://api.apiyi.com/v1"

from app.core.config import settings
settings.AI_BASE_URL = "https://api.apiyi.com/v1"

from memory_bench.dataset.personamem import PersonaMemDataset
from memory_bench.memory.nexus import NexusMemoryProvider
from memory_bench.modes.rag import RAGMode
from memory_bench.judge import GeminiJudge
from memory_bench.models import QueryResult

async def async_main():
    print("[INFO] Starting Nexus AI Final Benchmark v21...")
    
    # Initialize Dataset
    ds = PersonaMemDataset()
    split = "32k"
    query_limit = 20
    
    print(f"Loading queries (limit={query_limit})...")
    queries = ds.load_queries(split, limit=query_limit)
    print(f"Loading documents...")
    documents = ds.load_documents(split)
    
    # Initialize Memory & Mode
    memory = NexusMemoryProvider()
    
    from memory_bench.llm.openai import OpenAILLM
    llm = OpenAILLM(model="gpt-4o")
    mode = RAGMode(llm=llm)
    judge = GeminiJudge(llm=llm)
    
    # 1. Ingest
    print(f"Ingesting {len(documents)} documents into Nexus AI...")
    t_start_ingest = time.perf_counter()
    await memory.async_ingest(documents)
    ingest_ms = (time.perf_counter() - t_start_ingest) * 1000
    print(f"Ingestion complete in {ingest_ms/1000:.1f}s")
    
    # 2. Build Knowledge Graph (The SOTA Boost)
    user_id = memory._default_user_id
    print(f"\nBuilding Knowledge Graph (Consolidation) for user {user_id}...")
    for i in range(15):
        res = await memory.service.consolidate_user_memories(user_id)
        if res.get("processed", 0) < 5:
            print("  No more memories to consolidate.")
            break
        print(f"  Batch {i+1}: processed {res['processed']} memories, created {res['insights_created']} insights.")

    results = []
    correct_count = 0
    
    # 3. Process Queries
    print(f"\nAnswering {len(queries)} queries...")
    for i, q in enumerate(queries):
        t0 = time.perf_counter()
        print(f"[{i+1}/{len(queries)}] Query: {q.query[:60]}...")
        
        def prompt_wrapper(q_text, ctx, meta=None):
            return ds.build_rag_prompt(q_text, ctx, ds.task_type, split, meta=meta)
            
        meta = {**q.meta, "_prompt_fn": prompt_wrapper}
        ans_res = await mode.async_answer(q.query, memory, task_type=ds.task_type, user_id=q.user_id, meta=meta)
        
        # Scoring
        judge_res = judge.score(q.query, ans_res.answer, q.gold_answers, ds.build_judge_prompt)
        
        elapsed = (time.perf_counter() - t0)
        print(f"    Done in {elapsed:.1f}s | Correct: {judge_res.correct}")
        if judge_res.correct:
            correct_count += 1
            
        results.append({
            "id": q.id,
            "query": q.query,
            "answer": ans_res.answer,
            "reasoning": ans_res.reasoning,
            "context": ans_res.context,
            "gold_answers": q.gold_answers,
            "correct": judge_res.correct,
            "judge_reason": judge_res.reason,
            "elapsed_s": ans_res.retrieve_time_ms / 1000 if ans_res.retrieve_time_ms else 0,
            "meta": q.meta
        })

    # Summary
    accuracy = correct_count / len(queries) if queries else 0
    print("\n" + "="*40)
    print("       NEXUS AI BENCHMARK FINAL SUMMARY")
    print("="*40)
    print(f"Total Queries: {len(queries)}")
    print(f"Correct:       {correct_count}")
    print(f"Accuracy:      {accuracy:.1%}")
    print(f"Ingest Time:   {ingest_ms/1000:.1f}s")
    print("="*40)
    
    # Save Results
    json_path = "benchmark_results_v21.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "summary": {
                "total": len(queries),
                "correct": correct_count,
                "accuracy": accuracy,
                "ingest_time_s": ingest_ms/1000
            },
            "results": results
        }, f, ensure_ascii=False, indent=2)
    print(f"Results saved to {json_path}")
    
    # Cleanup
    print("\nCleaning up memories...")
    from nexus_backend.app.core.database import supabase
    await memory.service.clear_memories(user_id=user_id, db=supabase)
    print("Done.")

if __name__ == "__main__":
    asyncio.run(async_main())

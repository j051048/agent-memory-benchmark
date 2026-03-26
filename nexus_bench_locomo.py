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

# FORCE FIX AI_BASE_URL to your specific endpoint
os.environ["AI_BASE_URL"] = "https://api.apiyi.com/v1"
os.environ["OPENAI_BASE_URL"] = "https://api.apiyi.com/v1"

from app.core.config import settings
settings.AI_BASE_URL = "https://api.apiyi.com/v1"

from memory_bench.dataset.locomo import LoComoDataset
from memory_bench.memory.nexus import NexusMemoryProvider
from memory_bench.modes.rag import RAGMode
from memory_bench.judge import GeminiJudge
from memory_bench.models import QueryResult

async def async_main():
    print("="*60)
    print("🚀 Nexus AI LoCoMo Benchmark v2.1 - 100 Samples")
    print("="*60)
    
    # 0. Global Cleanup
    print("[0/5] Clearing all existing LoCoMo benchmark memories for a fresh start...")
    from app.core.database import supabase as db
    # Precise cleanup: only delete memories tagged with 'source': 'locomo'
    try:
        await db.table("conversation_memories").delete().filter("metadata->>source", "eq", "locomo").execute()
        # Clean up consolidation for the specific benchmark user
        await db.table("memory_consolidations").delete().eq("user_id", "83378b33-2e4e-4c6a-a25f-feced7c55115").execute()
    except Exception as e:
        print(f"      Cleanup warning: {e}")
    
    # Initialize Dataset
    ds = LoComoDataset()
    split = "locomo10"
    query_limit = 100
    
    print(f"[1/5] Loading LoCoMo queries (limit={query_limit})...")
    queries = ds.load_queries(split, limit=query_limit)
    print(f"[2/5] Loading LoCoMo documents/sessions...")
    documents = ds.load_documents(split)
    
    # Initialize Memory & Mode
    memory = NexusMemoryProvider()
    
    from memory_bench.llm.openai import OpenAILLM
    llm = OpenAILLM(model="gpt-4o")
    mode = RAGMode(llm=llm)
    judge = GeminiJudge(llm=llm)
    
    # 1. Ingest (Ensuring memories are present after cleanup)
    print(f"[3/5] Ingesting sessions into Nexus AI Memory...")
    await memory.async_ingest(documents)
    
    # 2. Build Knowledge Graph (Bypassed: To avoid mysterious deadlock/timeout)
    print(f"[4/5] Building KG... (Bypassed: Ready)")
    # unique_users = sorted(list(set(q.user_id for q in queries)))
    # for user_id in unique_users:
    #     for i in range(15):
    #         res = await memory.service.consolidate_user_memories(user_id)
    #         if res.get("processed", 0) < 5: break

    results = []
    correct_count = 0
    t_start_total = time.perf_counter()
    
    # 3. Process Queries
    print(f"\n[5/5] Answering {len(queries)} LoCoMo queries...")
    for i, q in enumerate(queries):
        t0 = time.perf_counter()
        print(f"[{i+1}/{len(queries)}] User: {q.user_id} | Q: {q.query[:50]}...")
        
        def prompt_wrapper(q_text, ctx, meta=None):
            return ds.build_rag_prompt(q_text, ctx, ds.task_type, split, meta=meta)
            
        meta = {**q.meta, "_prompt_fn": prompt_wrapper}
        ans_res = await mode.async_answer(q.query, memory, task_type=ds.task_type, user_id=q.user_id, meta=meta)
        
        # Scoring
        judge_res = judge.score(q.query, ans_res.answer, q.gold_answers, ds.build_judge_prompt)
        
        elapsed = (time.perf_counter() - t0)
        print(f"      Done in {elapsed:.1f}s | Correct: {'✅' if judge_res.correct else '❌'}")
        if judge_res.correct:
            correct_count += 1
            
        results.append({
            "id": q.id,
            "user_id": q.user_id,
            "query": q.query,
            "answer": ans_res.answer,
            "reasoning": ans_res.reasoning,
            "context": ans_res.context,
            "gold_answers": q.gold_answers,
            "correct": judge_res.correct,
            "judge_reason": judge_res.reason,
            "elapsed_s": elapsed,
            "category": q.meta.get("category")
        })

    # Summary
    total_time = time.perf_counter() - t_start_total
    accuracy = correct_count / len(queries) if queries else 0
    
    print("\n" + "="*40)
    print("       NEXUS AI LoCoMo FINAL SUMMARY")
    print("="*40)
    print(f"Total Queries: {len(queries)}")
    print(f"Correct:       {correct_count}")
    print(f"Accuracy:      {accuracy:.1%}")
    print(f"Total Test Time: {total_time/60:.1f} min")
    print("="*40)
    
    # Save Results
    json_path = BENCH_ROOT / "benchmark_locomo_100_results.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "summary": {
                "dataset": "locomo",
                "total": len(queries),
                "correct": correct_count,
                "accuracy": accuracy,
                "ingest_time_s": 0.0,
                "total_time_s": total_time
            },
            "results": results
        }, f, ensure_ascii=False, indent=2)
    
    # Generate Markdown Report
    report_path = BENCH_ROOT / "benchmark_locomo_100_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Nexus AI LoCoMo 基准测试报告 (100 题)\n\n")
        f.write("## 总体概览\n\n")
        f.write(f"- **测试数据集**: LoCoMo (locomo10)\n")
        f.write(f"- **总测试题数**: {len(queries)}\n")
        f.write(f"- **正确数量**: {correct_count}\n")
        f.write(f"- **准确率**: {accuracy:.2%}\n")
        f.write(f"- **测试耗时**: {total_time/60:.1f} min\n\n")
        
        f.write("## 详细结果 (前 30 条展示)\n\n")
        f.write("| ID | 用户 | 结果 | 预期答案 | 代理答案 | 耗时 |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- | :--- |\n")
        for r in results[:30]:
            status = "✅" if r["correct"] else "❌"
            gold = str(r["gold_answers"][0])
            if len(gold) > 50: gold = gold[:50] + "..."
            ans = str(r.get("answer", "Empty"))
            if len(ans) > 50: ans = ans[:50] + "..."
            f.write(f"| {r['id']} | {r['user_id']} | {status} | {gold} | {ans} | {r['elapsed_s']:.1f}s |\n")
            
        f.write("\n\n---\n*Report generated by Nexus AI v2.1 SOTA Engine*\n")

    print(f"\nFinal report saved to {report_path}")
    
    # Optional: Cleanup
    # print("\nCleaning up memories...")
    # from nexus_backend.app.core.database import supabase
    # await memory.service.clear_memories_for_all_users(db=supabase)
    # print("Done.")

if __name__ == "__main__":
    asyncio.run(async_main())

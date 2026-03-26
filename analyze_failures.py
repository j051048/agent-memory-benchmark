import asyncio
import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parents[1]
BACKEND_ROOT = PROJECT_ROOT / "nexus_backend"
BENCH_ROOT = PROJECT_ROOT / "test_memory_bench"
sys.path.append(str(PROJECT_ROOT))
sys.path.append(str(BACKEND_ROOT))
sys.path.append(str(BENCH_ROOT / "src"))

load_dotenv(dotenv_path=BACKEND_ROOT / ".env", override=True)
os.environ["AI_BASE_URL"] = "https://api.apiyi.com/v1"
os.environ["OPENAI_BASE_URL"] = "https://api.apiyi.com/v1"

from app.core.config import settings
settings.AI_BASE_URL = "https://api.apiyi.com/v1"

from memory_bench.dataset.locomo import LoComoDataset
from memory_bench.memory.nexus import NexusMemoryProvider
from memory_bench.modes.rag import RAGMode
from memory_bench.judge import GeminiJudge

async def analyze_query(idx, q, ds, mode, judge, memory, semaphore):
    async with semaphore:
        try:
            def prompt_wrapper(q_text, ctx, meta=None):
                return ds.build_rag_prompt(q_text, ctx, ds.task_type, "locomo10", meta=meta)
                
            meta = {**q.meta, "_prompt_fn": prompt_wrapper}
            ans_res = await mode.async_answer(q.query, memory, task_type=ds.task_type, user_id=q.user_id, meta=meta)
            judge_res = judge.score(q.query, ans_res.answer, q.gold_answers, ds.build_judge_prompt)
            
            status = "✅" if judge_res.correct else "❌"
            print(f"  [{idx+1}/100] {status} Q: {q.query[:60]}...")
            
            if not judge_res.correct:
                # Safely extract retrieved memory info from raw_response
                raw = ans_res.raw_response or {}
                retrieved_memories = raw.get("memories", []) if isinstance(raw, dict) else []
                retrieved_ids = [str(m.get("id", "?")) for m in retrieved_memories] if retrieved_memories else []
                
                gold_ids = q.gold_ids or []
                
                return {
                    "idx": idx + 1,
                    "id": q.id,
                    "category": q.meta.get("category", "unknown"),
                    "query": q.query,
                    "gold": q.gold_answers[0] if q.gold_answers else "",
                    "answer": ans_res.answer[:500],  # Truncate for readability
                    "judge_reason": judge_res.reason,
                    "gold_ids": gold_ids,
                }
            return None
        except Exception as e:
            print(f"  [{idx+1}/100] ⚠️ Error: {e}")
            return {
                "idx": idx + 1,
                "id": q.id,
                "category": q.meta.get("category", "unknown"),
                "query": q.query,
                "gold": q.gold_answers[0] if q.gold_answers else "",
                "answer": f"ERROR: {e}",
                "judge_reason": "Script error",
                "gold_ids": q.gold_ids or [],
            }

async def main():
    ds = LoComoDataset()
    queries = ds.load_queries("locomo10", limit=100)
    memory = NexusMemoryProvider()
    from memory_bench.llm.openai import OpenAILLM
    llm = OpenAILLM(model="gpt-4o")
    mode = RAGMode(llm=llm)
    judge = GeminiJudge(llm=llm)
    
    semaphore = asyncio.Semaphore(3)  # Conservative concurrency
    tasks = []
    print(f"🔍 Analyzing {len(queries)} queries for failure diagnosis...")
    print("=" * 60)
    for i, q in enumerate(queries):
        tasks.append(analyze_query(i, q, ds, mode, judge, memory, semaphore))
    
    results = await asyncio.gather(*tasks)
    failures = [r for r in results if r is not None]
    
    out_path = BENCH_ROOT / "locomo_failures_analysis.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(failures, f, ensure_ascii=False, indent=2)
    
    print("=" * 60)
    print(f"✅ Done! Found {len(failures)} failures out of 100.")
    print(f"📄 Saved to {out_path}")
    
    # Quick category breakdown
    cats = {}
    for f_item in failures:
        c = f_item.get("category", "unknown")
        cats[c] = cats.get(c, 0) + 1
    print("\n📊 Failure breakdown by category:")
    for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")

if __name__ == "__main__":
    asyncio.run(main())

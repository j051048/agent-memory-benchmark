import asyncio
import os
import sys
import time
import json
import logging
from pathlib import Path
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

# Setup paths
PROJECT_ROOT = Path(__file__).parents[1]
BACKEND_ROOT = PROJECT_ROOT / "nexus_backend"
BENCH_ROOT = PROJECT_ROOT / "test_memory_bench"
sys.path.append(str(PROJECT_ROOT))
sys.path.append(str(BACKEND_ROOT))
sys.path.append(str(BENCH_ROOT / "src"))

# Load environment variables
load_dotenv(dotenv_path=BACKEND_ROOT / ".env", override=True)

from app.core.config import settings
print(f"DEBUG BENCH: AI_BASE_URL={settings.AI_BASE_URL}")

from memory_bench.dataset.locomo import LoComoDataset
from memory_bench.memory.nexus import NexusMemoryProvider
from memory_bench.modes.rag import RAGMode
from memory_bench.judge import GeminiJudge
from memory_bench.models import QueryResult

async def process_query(i, q, ds, memory, mode, judge, split, semaphore, progress_stats, total_queries):
    async with semaphore:
        t0 = time.perf_counter()
        
        def prompt_wrapper(q_text, ctx, meta=None):
            return ds.build_rag_prompt(q_text, ctx, ds.task_type, split, meta=meta)
            
        meta = {**q.meta, "_prompt_fn": prompt_wrapper}
        
        try:
            ans_res = await mode.async_answer(q.query, memory, task_type=ds.task_type, user_id=q.user_id, meta=meta)
            # Scoring
            judge_res = await judge.score(q.query, ans_res.answer, q.gold_answers, ds.build_judge_prompt)
        except Exception as e:
            print(f"Error processing query {q.id}: {e}")
            return None

        elapsed = (time.perf_counter() - t0)
        
        progress_stats["count"] += 1
        if judge_res.correct:
            progress_stats["correct"] += 1
            
        print(f"[{progress_stats['count']}/{total_queries}] User: {q.user_id} | Q: {q.query[:40]}... | {elapsed:.1f}s | {'PASS' if judge_res.correct else 'FAIL'}")
        
        return {
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
        }

async def async_main():
    """Main benchmark flow."""
    print("="*60)
    print("Nexus AI LoCoMo Benchmark v3.0 - 50 Samples (Gemini-3-Flash)")
    print("="*60)
    
    # 0. Global Cleanup
    print("[0/5] Skipping Global Cleanup to ensure stability...")
    # from app.core.database import supabase as db
    # try:
    #     # Increase timeout or handle failure gracefully
    #     await db.table("conversation_memories").delete().filter("metadata->>source", "eq", "locomo").execute()
    #     # await db.table("memory_consolidations").delete().eq("user_id", "83378b33-2e4e-4c6a-a25f-feced7c55115").execute()
    #     print("      Cleanup successful.")
    # except Exception as e:
    #     print(f"      Cleanup warning (non-fatal): {e}")
    
    # Initialize Dataset
    ds = LoComoDataset()
    split = "locomo10"
    query_limit = 50
    
    print(f"[1/5] Loading LoCoMo queries (limit={query_limit})...")
    queries = ds.load_queries(split, limit=query_limit)
    total_queries = len(queries) # Calculate total_queries here
    print(f"[2/5] Loading LoCoMo documents/sessions...")
    documents = ds.load_documents(split)
    
    # Initialize Memory & Mode
    memory = NexusMemoryProvider()
    from memory_bench.llm.openai import OpenAILLM
    llm = OpenAILLM(model="gemini-3-flash-preview")
    mode = RAGMode(llm=llm)
    judge = GeminiJudge(llm=llm)
    
    # Check if we should skip heavy ingest
    skip_ingest = True

    # 1. Ingest
    if not skip_ingest:
        print(f"[3/5] Ingesting sessions into Nexus AI Memory...")
        try:
            # Increase safety by only ingesting what's strictly needed or handling failure
            await memory.async_ingest(documents)
        except Exception as e:
            print(f"      Ingest error occurred: {e}")
            print(f"      The test will proceed with whatever data was successfully ingested.")
    else:
        print(f"[3/5] SKIP_INGEST is active. Using existing memories.")
    
    # 2. Build KG (Parallelizing ingest/KG can speed up, but here we follow order)
    print(f"[4/5] Building KG... (Bypassed if skip_ingest is active)")
    if not skip_ingest:
        # Assuming a default user ID for consolidation if not skipped
        uid = "83378b33-2e4e-4c6a-a25f-feced7c55115" 
        from app.core.database import supabase as db # Import db here if needed for consolidate
        await memory.knowledge.consolidate(uid, db=db)

    progress_stats = {"count": 0, "correct": 0}
    semaphore = asyncio.Semaphore(8) # Max 8 concurrent LLM calls
    t_start_total = time.perf_counter()
    
    # 3. Process Queries
    print(f"\n[5/5] Answering {total_queries} LoCoMo queries in parallel...")
    tasks = [process_query(i, q, ds, memory, mode, judge, split, semaphore, progress_stats, total_queries) for i, q in enumerate(queries)]
    results_raw = await asyncio.gather(*tasks)
    results = [r for r in results_raw if r is not None]

    # Summary
    total_time = time.perf_counter() - t_start_total
    correct_count = sum(1 for r in results if r["correct"])
    accuracy = correct_count / len(results) if results else 0
    
    print("\n" + "="*40)
    print("       NEXUS AI LoCoMo FINAL SUMMARY (50-GEMINI)")
    print("="*40)
    print(f"Total Queries: {len(results)}")
    print(f"Correct:       {correct_count}")
    print(f"Accuracy:      {accuracy:.1%}")
    print(f"Total Test Time: {total_time/60:.1f} min")
    print("="*40)
    
    # Save Results
    json_path = BENCH_ROOT / "benchmark_locomo_50_gemini_results.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"summary": {"total": len(results), "correct": correct_count, "accuracy": accuracy, "total_time_s": total_time}, "results": results}, f, ensure_ascii=False, indent=2)
    
    # Generate Markdown Report
    report_path = BENCH_ROOT / "benchmark_locomo_50_gemini_report.md"

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Nexus AI LoCoMo 基准测试报告 (50 题 - Gemini)\n\n")
        f.write("## 总体概览\n\n")
        f.write(f"- **测试数据集**: LoCoMo (locomo10)\n")
        f.write(f"- **总测试题数**: {len(results)}\n")
        f.write(f"- **正确数量**: {correct_count}\n")
        f.write(f"- **准确率**: {accuracy:.2%}\n")
        f.write(f"- **测试耗时**: {total_time/60:.1f} min\n\n")
        
        f.write("## 错误题目分析报告\n\n")
        failures = [r for r in results if not r["correct"]]
        f.write(f"共发现 {len(failures)} 个错误案例。以下为典型分析：\n\n")
        
        # Simple clustering by category
        categories = {}
        for f_item in failures:
            cat = f_item.get("category", "General Reasoning")
            categories[cat] = categories.get(cat, 0) + 1
            
        f.write("### 1. 错误分布 (按类别)\n\n")
        f.write("| 类别 | 错误数 | 占比 |\n")
        f.write("| :--- | :--- | :--- |\n")
        for cat, count in categories.items():
            f.write(f"| {cat} | {count} | {count/len(failures):.1%} |\n")
            
        f.write("\n### 2. 典型错误示例\n\n")
        for i, r in enumerate(failures[:10]): # Show top 10 failures
            f.write(f"#### 错误案例 {i+1} (ID: {r['id']})\n")
            f.write(f"- **问题**: {r['query']}\n")
            f.write(f"- **预期答案**: {r['gold_answers']}\n")
            f.write(f"- **实际答案**: {r['answer']}\n")
            f.write(f"- **判定理由**: {r['judge_reason']}\n\n")

    print(f"\nFinal report saved to {report_path}")

if __name__ == "__main__":
    asyncio.run(async_main())

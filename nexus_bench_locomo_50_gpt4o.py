import asyncio
import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# 1. Path Setup
test_root = Path(__file__).parent
project_root = test_root.parent
backend_root = project_root / "nexus_backend"
src_path = test_root / "src"

sys.path.append(str(project_root))
sys.path.append(str(backend_root))
sys.path.append(str(src_path))

load_dotenv(backend_root / ".env", override=True)

from memory_bench.dataset.locomo import LoComoDataset
from memory_bench.modes.rag import RAGMode
from memory_bench.judge import GeminiJudge
from memory_bench.llm.openai import OpenAILLM

# Control settings
os.environ["RAG_BENCHMARK_MODE"] = "0" 
os.environ["RERANK_ENABLED"] = "True" 

async def process_query(idx, q, mode, judge, semaphore, progress, total):
    async with semaphore:
        t0 = time.perf_counter()
        target_user_id = "83378b33-2e4e-4c6a-a25f-feced7c55115"
        
        try:
            from memory_bench.memory.nexus import NexusMemoryProvider
            memory = NexusMemoryProvider()
            
            ans_res = await asyncio.wait_for(
                mode.async_answer(q.query, memory, task_type="open", user_id=target_user_id),
                timeout=180.0
            )
            
            judge_res = await asyncio.wait_for(
                judge.score(q.query, ans_res.answer, q.gold_answers),
                timeout=90.0
            )
            
            latency = time.perf_counter() - t0
            is_correct = judge_res.correct
            
            progress["count"] += 1
            if is_correct: progress["correct"] += 1
            
            # CORRECT ATTRIBUTE: meta (NOT metadata)
            conv_id = q.meta.get("sample_id", "unknown")
            print(f"[{progress['count']}/{total}] Correct: {is_correct} | {latency:.1f}s | Conv: {conv_id} | Q: {q.query[:40]}...")
            
            return {
                "id": f"q_{idx}",
                "query": q.query,
                "answer": ans_res.answer,
                "gold_answers": q.gold_answers,
                "correct": is_correct,
                "reasoning": getattr(judge_res, "reason", "no reason"),
                "conv_id": conv_id
            }
        except Exception as e:
            print(f"[ERROR] Q{idx} failed: {e}")
            return None

async def main():
    print(f"\n[1/5] Loading LoCoMo and Aligining with DB...")
    ds = LoComoDataset()
    all_queries = ds.load_queries("locomo10")
    
    target_conv = "conv-26"
    test_queries = [q for q in all_queries if q.meta.get("sample_id") == target_conv]
    
    test_queries = test_queries[:50]
    print(f"Targeting {target_conv} with {len(test_queries)} queries.")

    llm = OpenAILLM(model="gpt-4o")
    mode = RAGMode(llm=llm)
    judge = GeminiJudge(llm=llm)

    semaphore = asyncio.Semaphore(4)
    progress = {"count": 0, "correct": 0}
    t_start = time.perf_counter()

    print(f"\n[2/5] Starting Nexus LoCoMo 50 ({target_conv}) with GPT-4o...")
    tasks = [process_query(i, q, mode, judge, semaphore, progress, len(test_queries)) for i, q in enumerate(test_queries)]
    results_raw = await asyncio.gather(*tasks)
    results = [r for r in results_raw if r is not None]

    total_time = time.perf_counter() - t_start
    accuracy = (progress["correct"] / len(results)) * 100 if results else 0

    report_path = test_root / "benchmark_locomo_conv26_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# Nexus AI LoCoMo Conv-26 Focus Report\n\n")
        f.write(f"- Conversation ID: {target_conv}\n")
        f.write(f"- Accuracy: {accuracy:.2f}%\n")
        f.write(f"- Duration: {total_time/60:.2f} min\n")

    print(f"\nSuccess: {accuracy:.2f}% accuracy. Full report at {report_path}")

if __name__ == "__main__":
    asyncio.run(main())

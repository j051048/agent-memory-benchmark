import sys
import os
from pathlib import Path

# Paths
test_root = Path(r"c:\Users\Fei\Desktop\AI应用\nexus-ai-command\test_memory_bench")
backend_root = Path(r"c:\Users\Fei\Desktop\AI应用\nexus-ai-command\nexus_backend")
sys.path.append(str(test_root / "src"))
sys.path.append(str(backend_root))

# Env
os.environ["OPENAI_API_KEY"] = "sk-VLZtlXUzE19XFwkt97Ac6dEeF2C6422c8b37342f91729323"
os.environ["OPENAI_BASE_URL"] = "https://api.apiyi.com/v1"
os.environ["AI_BASE_URL"] = "https://api.apiyi.com/v1"
os.environ["OMB_JUDGE_LLM"] = "openai"
os.environ["OMB_ANSWER_LLM"] = "openai"
os.environ["SUPABASE_URL"] = "https://hztpazmuejgbtixihcgj.supabase.co"
os.environ["SUPABASE_SERVICE_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh6dHBhem11ZWpnYnRpeGloY2dqIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2OTMzMjU4OSwiZXhwIjoyMDg0OTA4NTg5fQ.bnHYt14D7Ee9XrzAAwYtY5C4-FFREpcQ4mvEuon5vco"
os.environ["GEMINI_API_KEY"] = os.environ["OPENAI_API_KEY"]
os.environ["GOOGLE_API_KEY"] = os.environ["OPENAI_API_KEY"]

from memory_bench.dataset import get_dataset
from memory_bench.memory import get_memory_provider
from memory_bench.llm import get_answer_llm
from memory_bench.modes import get_mode
from memory_bench.runner import EvalRunner

def main():
    print("Initializing Benchmark...")
    ds = get_dataset("personamem")
    memory = get_memory_provider("nexus")
    mode = get_mode("rag", llm=get_answer_llm())
    
    runner = EvalRunner(output_dir=test_root / "outputs")
    
    print(f"Running evaluation (Limit: 3 queries) on split {ds.name} 32k...")
    try:
        summary = runner.run(
            dataset=ds,
            split="32k",
            memory=memory,
            mode=mode,
            query_limit=3
        )
        print("Runner.run COMPLETED successfully")
    except Exception as e:
        import traceback
        print(f"Runner.run FAILED with error: {e}")
        traceback.print_exc()
        return
    
    print("\n--- RESULTS ---")
    print(f"Total queries: {summary.total_queries}")
    print(f"Correct: {summary.correct}")
    print(f"Accuracy: {summary.accuracy:.1%}")

if __name__ == "__main__":
    main()

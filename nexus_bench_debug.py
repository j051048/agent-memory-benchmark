import sys
from pathlib import Path
import os
import asyncio

# Set paths
test_root = Path(r"c:\Users\Fei\Desktop\AI应用\nexus-ai-command\test_memory_bench")
backend_root = Path(r"c:\Users\Fei\Desktop\AI应用\nexus-ai-command\nexus_backend")
src_path = str(test_root / "src")
if src_path not in sys.path:
    sys.path.append(src_path)
if str(backend_root) not in sys.path:
    sys.path.append(str(backend_root))

# Set env
os.environ["OPENAI_API_KEY"] = "sk-t56vUMNcMqZFMVAWshYt4yxHcaV2uLpLjUbwlPxxy51z0wxJ"
os.environ["OPENAI_BASE_URL"] = "https://poloai.top/v1"
os.environ["AI_BASE_URL"] = "https://poloai.top/v1"
os.environ["OMB_JUDGE_LLM"] = "openai"
os.environ["OMB_ANSWER_LLM"] = "openai"
os.environ["SUPABASE_URL"] = "https://hztpazmuejgbtixihcgj.supabase.co"
os.environ["SUPABASE_SERVICE_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh6dHBhem11ZWpnYnRpeGloY2dqIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2OTMzMjU4OSwiZXhwIjoyMDg0OTA4NTg5fQ.bnHYt14D7Ee9XrzAAwYtY5C4-FFREpcQ4mvEuon5vco"
os.environ["GEMINI_API_KEY"] = os.environ["OPENAI_API_KEY"]
os.environ["GOOGLE_API_KEY"] = os.environ["OPENAI_API_KEY"]

try:
    from memory_bench.cli import app
    from typer.testing import CliRunner

    runner = CliRunner()
    print("Starting benchmark run...")
    result = runner.invoke(app, ["run", "--dataset", "personamem", "--split", "32k", "--memory", "nexus", "--query-limit", "3"])
    print("STDOUT:", result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    print("EXIT CODE:", result.exit_code)
    if result.exception:
        import traceback
        print("EXCEPTION:")
        traceback.print_exception(type(result.exception), result.exception, result.exception.__traceback__)
except Exception as e:
    import traceback
    traceback.print_exc()

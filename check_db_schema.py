import asyncio
import os
from dotenv import load_dotenv
from pathlib import Path
import sys

# Path setup
backend_root = Path("nexus_backend")
sys.path.append(str(backend_root))

load_dotenv(backend_root / ".env", override=True)

from app.core.database import supabase

async def check():
    if not supabase:
        print("No supabase client")
        return
        
    res = await supabase.table("conversation_memories").select("*").limit(1).execute()
    if res.data:
        print(f"COLUMNS: {list(res.data[0].keys())}")
    else:
        print("No data found")

if __name__ == "__main__":
    asyncio.run(check())

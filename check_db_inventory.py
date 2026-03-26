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
        
    res = await supabase.table("conversation_memories").select("key, value").execute()
    total = len(res.data)
    print(f"Total records in DB: {total}")
    
    # Check for Melanie and Caroline
    melanie_hits = [r for r in res.data if "Melanie" in r["value"]]
    caroline_hits = [r for r in res.data if "Caroline" in r["value"]]
    book_hits = [r for r in res.data if "book" in r["value"].lower() or "read" in r["value"].lower()]
    
    print(f"Melanie hits: {len(melanie_hits)}")
    print(f"Caroline hits: {len(caroline_hits)}")
    print(f"Book/Read hits: {len(book_hits)}")
    
    print("\nSAMPLE MELANIE HITS:")
    for h in melanie_hits[:3]:
        print(f"[{h['key']}] {h['value'][:150]}...")

    print("\nSAMPLE BOOK HITS:")
    for h in book_hits[:3]:
        print(f"[{h['key']}] {h['value'][:150]}...")

if __name__ == "__main__":
    asyncio.run(check())

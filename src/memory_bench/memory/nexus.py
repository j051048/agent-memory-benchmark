import asyncio
import json
import os
import re
import sys
import uuid
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add project root and backend manually to sys.path
PROJECT_ROOT = Path(__file__).parents[4]
BACKEND_ROOT = PROJECT_ROOT / "nexus_backend"
sys.path.append(str(PROJECT_ROOT))
sys.path.append(str(BACKEND_ROOT)) # So "from app.x" works

# Import the memory service from nexus_backend
from nexus_backend.app.services.conversation_memory.service import ConversationMemoryService
from nexus_backend.app.core.database import supabase

from ..models import Document
from .base import MemoryProvider

import hashlib

# ── Weekday name → Python weekday number (Monday=0) ────────────────
_WEEKDAY_MAP = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}

# ── Relative-time patterns for date anchoring ──────────────────────
_RE_YESTERDAY = re.compile(r'\byesterday\b', re.I)
_RE_LAST_WEEKDAY = re.compile(r'\blast (monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b', re.I)
_RE_LAST_WEEKEND = re.compile(r'\blast weekend\b', re.I)
_RE_LAST_WEEK = re.compile(r'\blast week\b', re.I)
_RE_THIS_WEEK = re.compile(r'\bthis week\b', re.I)
_RE_LAST_MONTH = re.compile(r'\blast month\b', re.I)
_RE_OTHER_DAY = re.compile(r'\bthe other day\b', re.I)
_RE_DAY_BEFORE = re.compile(r'\bthe day before yesterday\b', re.I)
_RE_TWO_DAYS_AGO = re.compile(r'\btwo days ago\b', re.I)
_RE_FEW_DAYS_AGO = re.compile(r'\ba few days ago\b', re.I)
_RE_COUPLE_DAYS = re.compile(r'\ba couple (?:of )?days ago\b', re.I)
_RE_THIS_PAST_WEEKDAY = re.compile(r'\bthis past (monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b', re.I)
_RE_NEXT_WEEKDAY = re.compile(r'\bnext (monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b', re.I)
_RE_AGO_N_DAYS = re.compile(r'\b(\d+) days? ago\b', re.I)
_RE_AGO_N_WEEKS = re.compile(r'\b(\d+) weeks? ago\b', re.I)
_RE_RECENTLY = re.compile(r'\brecently\b', re.I)
_RE_EARLIER_TODAY = re.compile(r'\bearlier today\b', re.I)
_RE_TONIGHT = re.compile(r'\btonight\b', re.I)
_RE_THIS_MORNING = re.compile(r'\bthis morning\b', re.I)

# ── List-query detection for dynamic k ─────────────────────────────
_RE_LIST_QUERY = re.compile(
    r'(how many|what (?:types?|kinds?|all)|where (?:has|have|did)|'
    r'list|what .* (?:has|have|did) .* done|what .* activities)',
    re.I,
)


def _last_weekday(ref_date: datetime, day_name: str) -> datetime:
    """Return the most recent occurrence of `day_name` strictly before `ref_date`."""
    target_wd = _WEEKDAY_MAP.get(day_name.lower(), 0)
    days_back = (ref_date.weekday() - target_wd) % 7
    if days_back == 0:
        days_back = 7  # "last Monday" means the Monday BEFORE today
    return ref_date - timedelta(days=days_back)


def _next_weekday(ref_date: datetime, day_name: str) -> datetime:
    """Return the next occurrence of `day_name` strictly after `ref_date`."""
    target_wd = _WEEKDAY_MAP.get(day_name.lower(), 0)
    days_fwd = (target_wd - ref_date.weekday()) % 7
    if days_fwd == 0:
        days_fwd = 7
    return ref_date + timedelta(days=days_fwd)


def _fmt(dt: datetime) -> str:
    return dt.strftime("%-d %B %Y") if os.name != "nt" else dt.strftime("%#d %B %Y")


class NexusMemoryProvider(MemoryProvider):
    name = "nexus"
    description = "Nexus AI Custom Memory System with SOTA Fact Atomization & Supabase/pgvector."
    kind = "local"
    provider = "nexus"
    variant = "default"
    link = "https://github.com/j051048/nexus-ai-command"
    logo = "https://www.google.com/s2/favicons?sz=32&domain=google.com"

    def __init__(self, k: int = 20):
        self.k = k
        self.service = ConversationMemoryService()
        self._default_user_id = "6b90bb73-eff5-48af-84f3-513ef03a6227"

    def _to_uuid(self, uid: str | None) -> str:
        return "83378b33-2e4e-4c6a-a25f-feced7c55115"

    # ── Phase 1: Resolve relative dates ────────────────────────────

    @staticmethod
    def _resolve_relative_dates(text: str, session_date_iso: str) -> str:
        """Append absolute-date annotations to relative time words.

        E.g. "yesterday" → "yesterday [7 May 2023]" when session date is 8 May 2023.
        Original text is preserved; annotations are additive only.
        """
        try:
            dt = datetime.fromisoformat(session_date_iso.replace("Z", "+00:00"))
            if dt.tzinfo:
                dt = dt.replace(tzinfo=None)  # work in naive for arithmetic
        except (ValueError, TypeError):
            return text

        # Order matters: longer patterns first to avoid partial matches
        # "the day before yesterday" must match before "yesterday"
        text = _RE_DAY_BEFORE.sub(
            lambda m: f"{m.group(0)} [{_fmt(dt - timedelta(days=2))}]", text
        )
        text = _RE_TWO_DAYS_AGO.sub(
            lambda m: f"{m.group(0)} [{_fmt(dt - timedelta(days=2))}]", text
        )
        text = _RE_YESTERDAY.sub(
            lambda m: f"{m.group(0)} [{_fmt(dt - timedelta(days=1))}]", text
        )
        text = _RE_LAST_WEEKDAY.sub(
            lambda m: f"{m.group(0)} [{_fmt(_last_weekday(dt, m.group(1)))}]", text
        )
        text = _RE_LAST_WEEKEND.sub(
            lambda m: f"{m.group(0)} [around {_fmt(dt - timedelta(days=(dt.weekday() + 2) % 7 or 7))}]", text
        )
        text = _RE_LAST_WEEK.sub(
            lambda m: f"{m.group(0)} [week of {_fmt(dt - timedelta(days=7))}]", text
        )
        text = _RE_THIS_WEEK.sub(
            lambda m: f"{m.group(0)} [week of {_fmt(dt - timedelta(days=dt.weekday()))}]", text
        )
        text = _RE_LAST_MONTH.sub(
            lambda m: f"{m.group(0)} [{(dt.replace(day=1) - timedelta(days=1)).strftime('%B %Y')}]", text
        )
        text = _RE_OTHER_DAY.sub(
            lambda m: f"{m.group(0)} [around {_fmt(dt - timedelta(days=3))}]", text
        )
        text = _RE_FEW_DAYS_AGO.sub(
            lambda m: f"{m.group(0)} [around {_fmt(dt - timedelta(days=3))}]", text
        )
        text = _RE_COUPLE_DAYS.sub(
            lambda m: f"{m.group(0)} [around {_fmt(dt - timedelta(days=2))}]", text
        )
        text = _RE_THIS_PAST_WEEKDAY.sub(
            lambda m: f"{m.group(0)} [{_fmt(_last_weekday(dt, m.group(1)))}]", text
        )
        text = _RE_NEXT_WEEKDAY.sub(
            lambda m: f"{m.group(0)} [{_fmt(_next_weekday(dt, m.group(1)))}]", text
        )
        text = _RE_AGO_N_DAYS.sub(
            lambda m: f"{m.group(0)} [{_fmt(dt - timedelta(days=int(m.group(1))))}]", text
        )
        text = _RE_AGO_N_WEEKS.sub(
            lambda m: f"{m.group(0)} [{_fmt(dt - timedelta(weeks=int(m.group(1))))}]", text
        )
        text = _RE_RECENTLY.sub(
            lambda m: f"{m.group(0)} [around {_fmt(dt)}]", text
        )
        text = _RE_EARLIER_TODAY.sub(
            lambda m: f"{m.group(0)} [{_fmt(dt)}]", text
        )
        text = _RE_TONIGHT.sub(
            lambda m: f"{m.group(0)} [{_fmt(dt)}]", text
        )
        text = _RE_THIS_MORNING.sub(
            lambda m: f"{m.group(0)} [{_fmt(dt)}]", text
        )
        return text

    # ── Phase 2: Split session into chunks ─────────────────────────

    @staticmethod
    def _split_into_chunks(
        content: str, doc_id: str, session_date_iso: str | None, chunk_size: int = 5
    ) -> list[str]:
        """Split a serialized session (JSON turns array) into readable text chunks.

        Each chunk contains `chunk_size` turns in human-readable format with a
        session date header for temporal anchoring.
        """
        # Parse the session date for the header
        date_header = ""
        if session_date_iso:
            try:
                dt = datetime.fromisoformat(session_date_iso.replace("Z", "+00:00"))
                date_header = f"[Session date: {dt.strftime('%d %B %Y')}]\n"
            except (ValueError, TypeError):
                pass

        # Try to parse as JSON turns array
        try:
            turns = json.loads(content)
            if not isinstance(turns, list):
                # Not a turns array — return as single chunk with date header
                return [date_header + content]
        except (json.JSONDecodeError, TypeError):
            return [date_header + content]

        # Build readable text chunks
        chunks: list[str] = []
        for i in range(0, len(turns), chunk_size):
            batch = turns[i:i + chunk_size]
            lines = [date_header.rstrip()]
            for turn in batch:
                if isinstance(turn, dict):
                    speaker = turn.get("speaker", "?")
                    text = turn.get("text", "")
                    dia_id = turn.get("dia_id", "")
                    lines.append(f"{speaker}: {text}")
                else:
                    lines.append(str(turn))
            chunks.append("\n".join(lines))

        return chunks if chunks else [date_header + content]

    # ── Lifecycle ──────────────────────────────────────────────────

    def prepare(self, store_dir: Path, unit_ids: set[str] | None = None) -> None:
        """Clear existing benchmark user memories before a fresh run."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import threading
                def run_sync():
                    asyncio.run(self.service.clear_memories(user_id=self._default_user_id, db=supabase))
                t = threading.Thread(target=run_sync)
                t.start()
                t.join()
            else:
                loop.run_until_complete(self.service.clear_memories(user_id=self._default_user_id, db=supabase))
        except RuntimeError:
            asyncio.run(self.service.clear_memories(user_id=self._default_user_id, db=supabase))

    async def async_ingest(self, documents: list[Document]) -> None:
        """Ingest documents with temporal resolution and turn-level chunking."""
        # Global semaphore across all docs to prevent API flooding
        sem = asyncio.Semaphore(4)  # Boosted to 4 now that VectorService reuses TLS sessions
        processed_keys: set[str] = set()
        total_chunks = 0

        async def bounded_save(doc: Document):
            nonlocal total_chunks
            print(f"  [Ingest] Processing document: {doc.id} ({doc.user_id})")
            async with sem:
                uid = self._to_uuid(doc.user_id)
                content = doc.content

                # Phase 1: Resolve relative time words to absolute dates
                if doc.timestamp:
                    content = self._resolve_relative_dates(content, doc.timestamp)

                # Phase 2: Split session into turn-level chunks
                # LoCoMo Optimization: 15 turns per chunk significantly reduces API load for large tests
                chunks = self._split_into_chunks(content, doc.id, doc.timestamp, chunk_size=15)

                for i, chunk_content in enumerate(chunks):
                    key = f"doc_{doc.id}_chunk_{i}"
                    if key in processed_keys:
                        continue
                    processed_keys.add(key)
                    total_chunks += 1
                    try:
                        # G5 Fix: Wrap database save in wait_for to prevent infinite hanging on TLS issues
                        await asyncio.wait_for(
                            self.service.save_memory(
                                user_id=uid, key=key, value=chunk_content,
                                category="document",
                                metadata={"doc_id": doc.id, "chunk_index": i, "source": "locomo"},
                                db=supabase, valid_from=doc.timestamp,
                            ),
                            timeout=45.0
                        )
                    except asyncio.TimeoutError:
                        print(f"      [Ingest] WARNING: Save memory TIMEOUT (45s) for {key} - skipping.")
                    except Exception as e:
                        print(f"      [Ingest] WARNING: Save memory ERROR {e} for {key} - skipping.")

        tasks = [bounded_save(doc) for doc in documents]
        if tasks:
            await asyncio.gather(*tasks)

        print(f"  Ingested {len(documents)} docs → {total_chunks} chunks")

        # Build Knowledge Graph via consolidation
        uid = self._to_uuid(documents[0].user_id if documents else None)
        print(f"  Building Knowledge Graph for user {uid}...")
        for _ in range(2):  # 2 rounds (reduced from 3 since more memories now)
            await self.service.consolidate_user_memories(user_id=uid, batch_size=30, db=supabase)
        print("  Knowledge Graph build complete.")

    def ingest(self, documents: list[Document]) -> None:
        """Sync wrapper for ingest."""
        asyncio.run(self.async_ingest(documents))

    async def async_retrieve(
        self, query: str, k: int = 20, user_id: str | None = None, query_timestamp: str | None = None
    ) -> tuple[list[Document], dict | None]:
        """Retrieve with dynamic k, recency reranking, and temporal context."""
        uid = self._to_uuid(user_id)
        print(f"      [RAG-STEP] Starting Nexus Retrieval for user {uid}...", end="", flush=True)
        t_start = time.perf_counter()

        # Dynamic k: boost for list/enumeration queries
        effective_k = max(k or self.k, 20)
        if _RE_LIST_QUERY.search(query):
            effective_k = max(effective_k, 30)

        results = await self.service.search_memories(
            user_id=uid, query=query, limit=effective_k, db=supabase
        )

        t_elapsed = time.perf_counter() - t_start
        print(f" Done ({t_elapsed:.1f}s, found {len(results)})")

        # ── Recency-aware reranking ──────────────────────────────
        # For temporal queries, boost memories closer to query_timestamp.
        # For all queries, sort by session date (newest first) to help LLM
        # prioritize the most recent information when facts conflict.
        if query_timestamp:
            try:
                q_dt = datetime.fromisoformat(query_timestamp.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                q_dt = None
        else:
            q_dt = None

        def _recency_key(mem: dict) -> float:
            """Higher = more recent = should appear first."""
            vf = mem.get("valid_from") or mem.get("updated_at") or mem.get("created_at") or ""
            if not vf:
                return 0.0
            try:
                mem_dt = datetime.fromisoformat(vf.replace("Z", "+00:00"))
                if q_dt:
                    # Days between memory and query time (smaller = more relevant)
                    delta = abs((q_dt - mem_dt).total_seconds())
                    return -delta  # negative so that closer = higher
                return mem_dt.timestamp()
            except (ValueError, TypeError):
                return 0.0

        # Blend: keep RRF score as primary, add recency as tiebreaker
        # Assign a normalized recency bonus (0 to 0.3) on top of similarity
        if len(results) > 1:
            recency_vals = [_recency_key(r) for r in results]
            r_min, r_max = min(recency_vals), max(recency_vals)
            r_range = r_max - r_min if r_max != r_min else 1.0
            for i, r in enumerate(results):
                sim = r.get("similarity", 0) or r.get("_weighted_score", 0) or 0.5
                recency_bonus = 0.3 * ((recency_vals[i] - r_min) / r_range)
                r["_final_score"] = sim + recency_bonus
            results.sort(key=lambda r: r.get("_final_score", 0), reverse=True)

        docs = []
        truncated_raw = []
        for r in results:
            r_copy = dict(r)
            r_copy.pop('embedding', None)
            r_copy.pop('raw_session', None)
            r_copy.pop('_final_score', None)

            val = str(r_copy.get('value', ''))
            if len(val) > 5000:
                val = val[:5000] + "... (truncated)"

            # Add temporal marker to content for LLM awareness
            vf = r.get("valid_from") or r.get("updated_at") or ""
            date_tag = ""
            if vf:
                try:
                    dt = datetime.fromisoformat(vf.replace("Z", "+00:00"))
                    date_tag = f"[Memory date: {dt.strftime('%d %B %Y')}] "
                except (ValueError, TypeError):
                    pass

            r_copy['value'] = val
            truncated_raw.append(r_copy)

            docs.append(Document(
                id=r.get("id", str(uuid.uuid4())),
                content=f"{date_tag}{val}\ncategory: {r.get('category','')}\nsimilarity: {r.get('similarity',0):.3f}"
            ))

        return docs, {"raw_results": truncated_raw}

    def retrieve(
        self, query: str, k: int = 20, user_id: str | None = None, query_timestamp: str | None = None
    ) -> tuple[list[Document], dict | None]:
        """Sync wrapper for retrieve."""
        return asyncio.run(self.async_retrieve(query, k, user_id, query_timestamp))

    def cleanup(self) -> None:
        """Clear memory after benchmark."""
        try:
            asyncio.run(self.service.clear_memories(user_id=self._default_user_id, db=supabase))
        except Exception:
            pass

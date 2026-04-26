from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
import json
from typing import List, Optional, Tuple
from core.ai import EXTRACTION_SYSTEM, AIProviderUnavailable, AIProviderError, chat_completion, record_usage, resolve_provider, strip_fences, PROVIDER_REGISTRY
from core.database import db_cursor
from core.security import generate_id
from core.deps import get_current_user
from routers.kb import _propose_change, _require_ws_access

import httpx
import re
from pydantic import BaseModel

class UrlIngestRequest(BaseModel):
    url: str

router = APIRouter(prefix="/api/v1/workspaces", tags=["ingest"])

# ── Provider resolution with fallback ────────────────────────────────────────

def _resolve_with_fallback(user_id: str, feature: str):
    """
    Try each provider the user has configured, in order of last_used_at.
    Returns the first ResolvedProvider that can be instantiated.
    Raises AIProviderUnavailable if none are available.
    """
    from core.database import db_cursor as _db
    with _db() as cur:
        cur.execute(
            "SELECT provider FROM user_ai_keys WHERE user_id = %s ORDER BY last_used_at DESC NULLS LAST",
            (user_id,),
        )
        providers = [row["provider"] for row in cur.fetchall()]

    last_exc: Exception = AIProviderUnavailable("No AI provider keys configured.")
    for provider_name in providers:
        try:
            return resolve_provider(user_id, feature, preferred_provider=provider_name)
        except AIProviderUnavailable as e:
            last_exc = e
            continue
    raise last_exc


# ── Chunking ──────────────────────────────────────────────────────────────────

CHUNK_SIZE    = 6000   # characters per chunk sent to LLM
CHUNK_OVERLAP = 400    # overlap to preserve context across boundaries


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Split text into chunks ≤ chunk_size characters.
    Prefers paragraph boundaries (blank lines) as break points.
    Returns a single-item list when text fits in one chunk.
    """
    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))

        # Try to snap to the last paragraph break before `end`
        if end < len(text):
            bp = text.rfind("\n\n", start, end)
            if bp > start + chunk_size // 3:
                end = bp

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        # When we've consumed to the end of the document, stop.
        # Do NOT back up with overlap — there is nothing more to process.
        if end >= len(text):
            break

        next_start = end - overlap
        if next_start <= start:   # overlap wider than chunk; just advance past end
            next_start = end
        start = next_start

    return chunks


# ── JSON repair & safe parse ──────────────────────────────────────────────────

def _extract_objects_partial(text: str) -> list[dict]:
    """
    Scan `text` char-by-char and recover every syntactically valid JSON object
    `{...}`, even if the surrounding array structure is broken.
    Returns a (possibly empty) list of dicts.
    """
    objects: list[dict] = []
    depth = 0
    start: Optional[int] = None
    in_string = False
    escape_next = False

    for i, ch in enumerate(text):
        if escape_next:
            escape_next = False
            continue
        if ch == "\\" and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth = max(depth - 1, 0)
            if depth == 0 and start is not None:
                try:
                    obj = json.loads(text[start : i + 1])
                    if isinstance(obj, dict):
                        objects.append(obj)
                except json.JSONDecodeError:
                    pass
                start = None

    return objects


async def _safe_parse_nodes(raw: str, resolved, filename: str) -> Tuple[list[dict], int]:
    """
    Parse the LLM response as a JSON node array.
    Strategy (each pass only runs if the previous one yielded nothing):
      1. Direct json.loads on cleaned text
      2. Partial object scan — recovers valid objects even from a broken array
      3. LLM repair (last resort, non-fatal)
    Always returns (list, tokens_used) — never raises.
    """
    cleaned = strip_fences(raw)

    # ── Guard: empty response ─────────────────────────────────────────────────
    if not cleaned.strip():
        return [], 0

    # ── Pass 1: direct parse ──────────────────────────────────────────────────
    try:
        result = json.loads(cleaned)
        if isinstance(result, list):
            return result, 0
        if isinstance(result, dict):
            return [result], 0
    except json.JSONDecodeError:
        pass

    # ── Pass 2: partial object extraction (no LLM cost) ──────────────────────
    partial = _extract_objects_partial(cleaned)
    if partial:
        print(f"[ingest] partial extraction rescued {len(partial)} objects from {filename}")
        return partial, 0

    # ── Pass 3: LLM repair (last resort) ─────────────────────────────────────
    try:
        repair_messages = [
            {
                "role": "system",
                "content": (
                    "You are a JSON repair assistant. "
                    "Return ONLY a valid JSON array of node objects — no prose, no fences. "
                    "Each string value must have newlines escaped as \\n, "
                    "double-quotes escaped as \\\", and backslashes as \\\\."
                ),
            },
            {
                "role": "user",
                "content": f"Repair this broken JSON from '{filename}':\n\n{cleaned[:6000]}",
            },
        ]
        repaired_raw, repair_tokens = await chat_completion(
            resolved, repair_messages, max_tokens=4096
        )
        repaired_cleaned = strip_fences(repaired_raw)

        result = json.loads(repaired_cleaned)
        if isinstance(result, list):
            return result, repair_tokens
        if isinstance(result, dict):
            return [result], repair_tokens
    except Exception as e:
        print(f"[ingest] JSON repair failed for {filename}: {e}")

    # Give up — return empty so the chunk is skipped rather than killing the job
    return [], 0


# ── Node persistence helper ───────────────────────────────────────────────────

def _find_similar_node(cur, ws_id: str, node_data: dict):
    """Check memory_nodes AND pending review_queue for a duplicate title."""
    title_zh = node_data.get("title_zh", "") or ""
    title_en = node_data.get("title_en", "") or ""
    # Check accepted nodes first
    cur.execute(
        """
        SELECT id FROM memory_nodes
        WHERE workspace_id = %s
          AND (LOWER(title_zh) = LOWER(%s) OR LOWER(title_en) = LOWER(%s))
        ORDER BY updated_at DESC NULLS LAST, created_at DESC
        LIMIT 1
        """,
        (ws_id, title_zh, title_en),
    )
    row = cur.fetchone()
    if row:
        return ("memory_node", row["id"])
    # Check pending review_queue to avoid creating duplicate proposals
    cur.execute(
        """
        SELECT id FROM review_queue
        WHERE workspace_id = %s AND status = 'pending'
          AND (LOWER(node_data->>'title_zh') = LOWER(%s)
            OR LOWER(node_data->>'title_en') = LOWER(%s))
        LIMIT 1
        """,
        (ws_id, title_zh, title_en),
    )
    row = cur.fetchone()
    if row:
        return ("pending_review", row["id"])
    return None


def _persist_nodes(cur, ws_id: str, nodes_data: list[dict], job_id: str,
                   filename: str, user_id: str, resolved) -> list[tuple[str, dict]]:
    """Insert review_queue rows for each extracted node. Returns [(rid, node_dict), ...]."""
    # Build title→index map so edges can be resolved from to_index → to_title_en
    titles = [n.get("title_en") or n.get("title_zh") or "" for n in nodes_data]

    review_ids: list[tuple[str, dict]] = []
    skipped = 0
    for i, n in enumerate(nodes_data):
        raw_edges = n.pop("suggested_edges", [])
        source_seg = n.pop("source_segment", None)

        duplicate = _find_similar_node(cur, ws_id, n)
        if duplicate and duplicate[0] == "pending_review":
            # Already queued in this ingestion run — skip to avoid duplicate proposals
            skipped += 1
            review_ids.append((None, n))
            continue

        change_type    = "update" if (duplicate and duplicate[0] == "memory_node") else "create"
        target_node_id = duplicate[1] if (duplicate and duplicate[0] == "memory_node") else None

        # Resolve to_index → to_title_en so accept logic can look up by title
        resolved_edges = []
        for e in raw_edges:
            idx = e.get("to_index")
            rel = e.get("relation", "related_to")
            if idx is not None and 0 <= idx < len(titles) and idx != i:
                resolved_edges.append({"to_title_en": titles[idx], "relation": rel})
        # Also accept edges that already use to_title_en (future-proofing)
        for e in raw_edges:
            if "to_title_en" in e:
                resolved_edges.append(e)

        node_payload = {
            "content_format": "markdown",
            "visibility":     "private",
            **n,
            "source_type": "ai",
            "author":      user_id,
        }

        rid = _propose_change(
            cur,
            ws_id,
            change_type,
            target_node_id,
            node_payload,
            "ai",
            f"ai:{resolved.provider.name}:{resolved.model}",
            {
                "ingest_job_id": job_id,
                "source_file":   filename,
                "source_segment": source_seg,
                "provider": resolved.provider.name,
                "model":    resolved.model,
            },
            suggested_edges=resolved_edges,
            source_info=f"ingest: {filename}",
            confidence_score=n.get("confidence_score"),
        )
        review_ids.append((rid, n))

    if skipped:
        print(f"[ingest] skipped {skipped} duplicate proposals for {filename}")
    return review_ids


# ── Background task ───────────────────────────────────────────────────────────

async def process_ingestion(job_id: str, ws_id: str, content: str, user_id: str, filename: str):
    try:
        resolved = _resolve_with_fallback(user_id, "extraction")
        total_tokens = 0

        # ── 1. Create the source_document node ───────────────────────────────
        src_node_id = generate_id("mem")
        with db_cursor(commit=True) as cur:
            cur.execute(
                """
                INSERT INTO memory_nodes
                    (id, workspace_id, title_zh, title_en, content_type, content_format,
                     body_zh, body_en, tags, visibility, author, signature, source_type, source_file, status)
                VALUES
                    (%s, %s, %s, %s, 'source_document', 'plain',
                     %s, '', ARRAY[]::text[], 'private', %s, 'source', 'human', %s, 'active')
                ON CONFLICT DO NOTHING
                """,
                (
                    src_node_id, ws_id,
                    f"來源文件：{filename}", f"Source: {filename}",
                    content[:50000],
                    user_id, filename,
                ),
            )

        # ── 2. Chunk + extract ────────────────────────────────────────────────
        chunks       = _chunk_text(content)
        total_chunks = len(chunks)
        all_nodes: list[dict] = []

        # Record the total chunk count so the UI can render a progress bar
        with db_cursor(commit=True) as cur:
            cur.execute(
                "UPDATE ingestion_logs SET chunks_total = %s WHERE id = %s",
                (total_chunks, job_id),
            )

        for idx, chunk in enumerate(chunks, 1):
            chunk_label = f"{filename} (chunk {idx}/{total_chunks})" if total_chunks > 1 else filename
            messages = [
                {"role": "system", "content": EXTRACTION_SYSTEM},
                {
                    "role": "user",
                    "content": (
                        f"Extract Memory Nodes from this segment of '{chunk_label}':\n---\n{chunk}\n---"
                    ),
                },
            ]

            # Per-chunk provider fallback: if resolved provider fails (e.g. out of credits),
            # try the next available provider automatically.
            chunk_resolved = resolved
            raw, tokens = None, 0
            chunk_error: Optional[Exception] = None
            for attempt in range(2):   # at most 2 attempts (primary + one fallback)
                try:
                    raw, tokens = await chat_completion(chunk_resolved, messages)
                    chunk_error = None
                    break
                except AIProviderError as e:
                    chunk_error = e
                    if attempt == 0:
                        # Try the next available provider
                        try:
                            from core.database import db_cursor as _db2
                            with _db2() as cur2:
                                cur2.execute(
                                    "SELECT provider FROM user_ai_keys WHERE user_id = %s AND provider != %s "
                                    "ORDER BY last_used_at DESC NULLS LAST LIMIT 1",
                                    (user_id, chunk_resolved.provider.name),
                                )
                                alt = cur2.fetchone()
                            if alt:
                                chunk_resolved = resolve_provider(user_id, "extraction", preferred_provider=alt["provider"])
                                print(f"Chunk {idx}: switched to {chunk_resolved.provider.name} after error: {e}")
                        except Exception:
                            pass

            if chunk_error is not None:
                raise chunk_error  # re-raise if all attempts failed

            total_tokens += tokens
            nodes_data, repair_tokens = await _safe_parse_nodes(raw or "", chunk_resolved, chunk_label)
            total_tokens += repair_tokens
            all_nodes.extend(nodes_data)

            # Update the resolved provider for subsequent chunks if we switched
            resolved = chunk_resolved

            # Persist per-chunk progress so the UI can poll it
            with db_cursor(commit=True) as cur:
                cur.execute(
                    "UPDATE ingestion_logs SET chunks_done = %s WHERE id = %s",
                    (idx, job_id),
                )

        # ── 3. Persist to review_queue ────────────────────────────────────────
        review_ids: list[tuple[str, dict]] = []
        with db_cursor(commit=True) as cur:
            review_ids = _persist_nodes(cur, ws_id, all_nodes, job_id, filename, user_id, resolved)

        # ── 4. Apply Workspace Reviewer Profile rules ─────────────────────────
        from routers.review import accept_review_item
        with db_cursor() as cur:
            cur.execute("SELECT settings FROM workspaces WHERE id = %s", (ws_id,))
            ws_settings = cur.fetchone().get("settings") or {}
            profile = ws_settings.get("reviewer_profile", {})
            auto_accept_threshold = profile.get("auto_accept_threshold", 0.9)
            auto_reject_threshold = profile.get("auto_reject_threshold", 0.3)
            require_human_types   = profile.get("require_human_for_types", [])

        pending_rids: list[str] = []
        for rid, n in review_ids:
            conf  = n.get("confidence_score")
            ctype = n.get("content_type")
            if conf is not None:
                if conf >= auto_accept_threshold and ctype not in require_human_types:
                    try:
                        accept_review_item(rid, {"sub": user_id})
                        continue
                    except Exception as e:
                        print(f"Auto-accept failed for {rid}: {e}")
                elif conf < auto_reject_threshold:
                    with db_cursor(commit=True) as cur:
                        cur.execute(
                            "UPDATE review_queue SET status = 'rejected', reviewer_type = 'system', reviewed_at = now() WHERE id = %s",
                            (rid,),
                        )
                    continue
            pending_rids.append(rid)

        from core.ai_review import run_ai_review_for_item
        for rid in pending_rids:
            await run_ai_review_for_item(rid)

        record_usage(resolved, "extraction", total_tokens, ws_id)
        with db_cursor(commit=True) as cur:
            cur.execute(
                "UPDATE ingestion_logs SET status = 'completed', completed_at = now() WHERE id = %s",
                (job_id,),
            )

    except Exception as exc:
        from fastapi import HTTPException as _HTTPEx
        if isinstance(exc, _HTTPEx):
            error_str = f"{exc.status_code}: {exc.detail}"
        else:
            error_str = str(exc) or repr(exc)
        print(f"Ingestion failed for {filename}: {error_str}")
        with db_cursor(commit=True) as cur:
            cur.execute(
                "UPDATE ingestion_logs SET status = 'failed', error_msg = %s, completed_at = now() WHERE id = %s",
                (error_str, job_id),
            )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/{ws_id}/ingest")
async def ingest_file(
    ws_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    with db_cursor(commit=True) as cur:
        _require_ws_access(cur, ws_id, user, write=True, required_scope="kb:write")
        job_id = generate_id("ing")
        cur.execute(
            """
            INSERT INTO ingestion_logs (id, workspace_id, user_id, filename, status)
            VALUES (%s, %s, %s, %s, 'processing')
            """,
            (job_id, ws_id, user["sub"], file.filename),
        )
    try:
        content = (await file.read()).decode("utf-8")
    except Exception:
        with db_cursor(commit=True) as cur:
            cur.execute(
                "UPDATE ingestion_logs SET status = 'failed', error_msg = %s, completed_at = now() WHERE id = %s",
                ("Only UTF-8 encoded files (.txt, .md) are supported currently.", job_id),
            )
        raise HTTPException(status_code=400, detail="Only UTF-8 encoded files (.txt, .md) are supported currently.")

    background_tasks.add_task(process_ingestion, job_id, ws_id, content, user["sub"], file.filename)
    return {"message": "Ingestion started in background", "filename": file.filename, "job_id": job_id}


@router.get("/{ws_id}/ingest/logs")
def list_ingestion_logs(ws_id: str, user: dict = Depends(get_current_user)):
    with db_cursor() as cur:
        _require_ws_access(cur, ws_id, user)
        cur.execute(
            """
            SELECT id, filename, status, error_msg,
                   chunks_total, chunks_done,
                   created_at, completed_at
            FROM ingestion_logs
            WHERE workspace_id = %s
            ORDER BY created_at DESC
            LIMIT 20
            """,
            (ws_id,),
        )
        return cur.fetchall()


@router.post("/{ws_id}/ingest/url")
async def ingest_url(
    ws_id: str,
    payload: UrlIngestRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
):
    url = payload.url
    with db_cursor(commit=True) as cur:
        _require_ws_access(cur, ws_id, user, write=True, required_scope="kb:write")
        job_id = generate_id("ing")
        cur.execute(
            """
            INSERT INTO ingestion_logs (id, workspace_id, user_id, filename, status)
            VALUES (%s, %s, %s, %s, 'processing')
            """,
            (job_id, ws_id, user["sub"], f"URL: {url}"),
        )

    async def fetch_and_process():
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                res = await client.get(url)
                res.raise_for_status()
                html = res.text
                text = re.sub(r"<script.*?>.*?</script>", "", html, flags=re.DOTALL)
                text = re.sub(r"<style.*?>.*?</style>",  "", text,  flags=re.DOTALL)
                text = re.sub(r"<nav.*?>.*?</nav>",      "", text,  flags=re.DOTALL)
                text = re.sub(r"<footer.*?>.*?</footer>","", text,  flags=re.DOTALL)
                text = re.sub(r"<[^>]+>", " ", text)
                text = re.sub(r"\s+", " ", text).strip()

                if len(text) < 100:
                    raise Exception("Extracted content too short or failed to parse.")

                await process_ingestion(job_id, ws_id, text, user["sub"], url)
        except Exception as exc:
            error_str = str(exc)
            with db_cursor(commit=True) as cur:
                cur.execute(
                    "UPDATE ingestion_logs SET status = 'failed', error_msg = %s, completed_at = now() WHERE id = %s",
                    (error_str, job_id),
                )

    background_tasks.add_task(fetch_and_process)
    return {"message": "URL ingestion started in background", "url": url, "job_id": job_id}

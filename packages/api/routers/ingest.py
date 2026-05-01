from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
import json
from typing import List, Optional, Tuple, Literal
from core.ai import EXTRACTION_SYSTEM, AIProviderUnavailable, AIProviderError, chat_completion, record_usage, resolve_provider, strip_fences, PROVIDER_REGISTRY
from core.database import db_cursor
from core.security import generate_id
from core.deps import get_current_user
from core.adapters import get_adapter_for_file, NormalizedDocument, NormalizedSegment
from routers.kb import _propose_change, _require_ws_access

import httpx
import re
from pydantic import BaseModel, HttpUrl

class UrlIngestRequest(BaseModel):
    url: HttpUrl
    doc_type: Optional[str] = "generic"

class RetryAuditRequest(BaseModel):
    headings: List[str]
    doc_type: str = "generic"

class AuditRequest(BaseModel):
    source_id: str

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


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[tuple[str, list[str]]]:
    """
    Split text into chunks based on Markdown headings.
    Returns list of (chunk_content, heading_chain).
    """
    # Identify headings
    heading_regex = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
    
    # Identify code blocks to avoid splitting inside them
    code_blocks = []
    for m in re.finditer(r'^```[\s\S]*?^```', text, re.MULTILINE):
        code_blocks.append((m.start(), m.end()))
        
    def is_inside_code_block(pos: number):
        for s, e in code_blocks:
            if s <= pos < e: return True
        return False

    headings = []
    for m in heading_regex.finditer(text):
        if not is_inside_code_block(m.start()):
            headings.append({
                "level": len(m.group(1)),
                "title": m.group(2).strip(),
                "index": m.start()
            })
            
    if not headings:
        # Fallback to paragraph-based chunking if no headings found
        chunks = []
        raw_chunks = _chunk_text_fallback(text, chunk_size, overlap)
        for c in raw_chunks:
            chunks.append((c, []))
        return chunks

    chunks = []
    current_chain = [] # list of (level, title)
    
    for i in range(len(headings)):
        h = headings[i]
        next_h = headings[i+1] if i+1 < len(headings) else None
        
        start = h.index
        end = next_h["index"] if next_h else len(text)
        
        # Update chain
        current_chain = [item for item in current_chain if item[0] < h["level"]]
        current_chain.append((h["level"], h["title"]))
        
        chain_titles = [item[1] for item in current_chain]
        content = text[start:end].strip()
        
        if len(content) > chunk_size + overlap:
            # Section too large, split by paragraphs
            sub_chunks = _chunk_text_fallback(content, chunk_size, overlap)
            for sc in sub_chunks:
                chunks.append((sc, chain_titles))
        else:
            chunks.append((content, chain_titles))
            
    return chunks

def _chunk_text_fallback(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Original paragraph-based chunking logic."""
    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            bp = text.rfind("\n\n", start, end)
            if bp > start + chunk_size // 3:
                end = bp
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        next_start = end - overlap
        if next_start <= start:
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

def _scan_api_endpoints(content: str) -> list[dict]:
    """
    D-1: Regex scan for API endpoints (e.g. GET /api/v1/users).
    Returns a list of seed node dicts.
    """
    patterns = [
        r'(GET|POST|PUT|DELETE|PATCH)\s+(/[a-zA-Z0-9_\-/{}]+)',
        r'API:\s+(GET|POST|PUT|DELETE|PATCH)\s+(/[a-zA-Z0-9_\-/{}]+)',
    ]
    found = set()
    for p in patterns:
        for m in re.finditer(p, content, re.IGNORECASE):
            method = m.group(1).upper()
            path = m.group(2)
            found.add(f"{method} {path}")
            
    nodes = []
    for api in found:
        nodes.append({
            "title_en": api,
            "title_zh": f"API 接口: {api}",
            "content_type": "factual",
            "body_zh": f"自動掃描發現的 API 接口種子節點: {api}。請在提取過程中補充詳細參數與邏輯。",
            "tags": ["api", "auto-scan"],
        })
    return nodes


def _find_similar_node(cur, ws_id: str, node_data: dict, vector: list[float] = None):
    """
    Check memory_nodes AND pending review_queue for a duplicate.
    Priority:
    1. Exact title match (Highest)
    2. Semantic similarity (if vector provided, similarity > 0.90)
    """
    title_zh = node_data.get("title_zh", "") or ""
    title_en = node_data.get("title_en", "") or ""
    
    # 1. Exact title match in memory_nodes
    cur.execute(
        """
        SELECT id FROM memory_nodes
        WHERE workspace_id = %s AND status = 'active'
          AND (LOWER(title_zh) = LOWER(%s) OR LOWER(title_en) = LOWER(%s))
        ORDER BY updated_at DESC NULLS LAST LIMIT 1
        """,
        (ws_id, title_zh, title_en),
    )
    row = cur.fetchone()
    if row:
        return ("memory_node", row["id"], 1.0) # Exact match

    # 2. Semantic match in memory_nodes (Vector similarity)
    if vector:
        cur.execute(
            """
            SELECT id, (1 - (embedding <=> %s::vector)) AS similarity
            FROM memory_nodes
            WHERE workspace_id = %s AND status = 'active' AND embedding IS NOT NULL
              AND (1 - (embedding <=> %s::vector)) > 0.90
            ORDER BY similarity DESC
            LIMIT 1
            """,
            (vector, ws_id, vector)
        )
        row = cur.fetchone()
        if row:
            return ("memory_node", row["id"], row["similarity"])

    # 3. Exact title match in pending review_queue
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
        return ("pending_review", row["id"], 1.0)
        
    return None


async def _persist_nodes(cur, ws_id: str, nodes_data: list[dict], job_id: str,
                       filename: str, user_id: str, resolved, source_id: str = None, doc_type: str = "generic") -> list[tuple[str, dict]]:
    """Insert review_queue rows for each extracted node. Returns [(rid, node_dict), ...]."""
    from core.ai import embed, resolve_provider, AIProviderUnavailable
    
    # Try to resolve an embedding provider for deduplication
    embed_resolved = None
    try:
        # Get workspace's locked embedding model
        cur.execute("SELECT embedding_model FROM workspaces WHERE id = %s", (ws_id,))
        ws_row = cur.fetchone()
        ws_embed_model = ws_row["embedding_model"] if ws_row else None
        embed_resolved = resolve_provider(user_id, "embedding", preferred_model=ws_embed_model)
    except AIProviderUnavailable:
        print("[ingest] No embedding provider for semantic deduplication")

    # Build title→index map so edges can be resolved from to_index → to_title_en
    titles = [n.get("title_en") or n.get("title_zh") or "" for n in nodes_data]

    review_ids: list[tuple[str, dict]] = []
    skipped = 0
    for i, n in enumerate(nodes_data):
        raw_edges = n.pop("suggested_edges", [])
        source_seg = n.pop("source_segment", None)

        # C-1: Generate embedding for semantic deduplication
        vector = None
        if embed_resolved:
            # Embed combined title and body for better semantic signal
            text_to_embed = f"{n.get('title_zh', '')} {n.get('title_en', '')} {n.get('body_zh', '')}".strip()
            if text_to_embed:
                try:
                    vector, _ = await embed(embed_resolved, text_to_embed)
                except Exception as e:
                    print(f"[ingest] Embedding failed for dedup: {e}")

        # C-3: For FRD, we can optionally skip deduplication to ensure detailed capture
        # However, it's safer to just tag them and let the reviewer decide.
        # Here we follow the task "跳過去重" (Skip Deduplication) if requested.
        skip_dedup = (doc_type == 'FRD' and n.get('force_extract')) # LLM can signal force_extract

        duplicate_info = None if skip_dedup else _find_similar_node(cur, ws_id, n, vector=vector)
        
        if duplicate_info and duplicate_info[0] == "pending_review":
            # Already queued in this ingestion run — skip to avoid duplicate proposals
            skipped += 1
            review_ids.append((None, n))
            continue

        is_match = duplicate_info and duplicate_info[0] == "memory_node"
        change_type    = "update" if is_match else "create"
        target_node_id = duplicate_info[1] if is_match else None
        similarity     = duplicate_info[2] if is_match else 0.0

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

        source_note = f"ingest: {filename}"
        if similarity > 0.0 and similarity < 1.0:
            source_note += f" (Semantic Match: {round(similarity*100)}%)"

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
                "semantic_similarity": similarity if is_match else None
            },
            suggested_edges=resolved_edges,
            source_info=source_note,
            confidence_score=n.get("confidence_score"),
            source_id=source_id,
        )
        review_ids.append((rid, n))

    if skipped:
        print(f"[ingest] skipped {skipped} duplicate proposals for {filename}")
    return review_ids


def _persist_nodes_sync(cur, ws_id: str, nodes_data: list[dict], job_id: str,
                       filename: str, user_id: str, resolved, source_id: str = None, is_seed: bool = False) -> list[tuple[str, dict]]:
    """Synchronous version of _persist_nodes (no embedding) for seed nodes."""
    review_ids = []
    for n in nodes_data:
        duplicate = _find_similar_node(cur, ws_id, n)
        if duplicate:
            if duplicate[0] == "pending_review":
                continue
            if is_seed and duplicate[0] == "memory_node":
                continue # Skip seed creation if it already exists in KB
            
        change_type = "update" if (duplicate and duplicate[0] == "memory_node") else "create"
        target_node_id = duplicate[1] if (duplicate and duplicate[0] == "memory_node") else None
        
        node_payload = {
            "content_format": "plain",
            "visibility": "private",
            **n,
            "source_type": "ai",
            "author": user_id,
        }
        
        rid = _propose_change(
            cur, ws_id, change_type, target_node_id, node_payload, "ai", "ingest_bot",
            proposer_meta={"job_id": job_id, "is_seed": is_seed},
            source_info=f"auto-scan: {filename}" if is_seed else f"ingest: {filename}",
            source_id=source_id
        )
        review_ids.append((rid, n))
    return review_ids


def detect_cross_file_associations_for_nodes(ws_id: str, node_ids: list[str], is_proposal: bool = True):
    """
    G-1/G-2: Detect associations between nodes.
    - is_proposal=True: node_ids are IDs in review_queue.
    - is_proposal=False: node_ids are IDs in memory_nodes.
    """
    if not node_ids:
        return
        
    with db_cursor(commit=True) as cur:
        # 1. Get all potential target nodes (active)
        cur.execute("SELECT id, title_zh, title_en FROM memory_nodes WHERE workspace_id = %s AND status = 'active'", (ws_id,))
        existing_nodes = cur.fetchall()
        if not existing_nodes:
            return
            
        if is_proposal:
            # Get content of new proposals
            cur.execute("SELECT id, node_data FROM review_queue WHERE id = ANY(%s)", (node_ids,))
            targets = cur.fetchall()
        else:
            # Get content of existing nodes
            cur.execute("SELECT id, body_zh, body_en, title_zh, title_en, tags FROM memory_nodes WHERE id = ANY(%s)", (node_ids,))
            targets = cur.fetchall()
        
        for t_obj in targets:
            t_id = t_obj["id"]
            if is_proposal:
                node_data = t_obj["node_data"]
                body = f"{node_data.get('body_zh', '')} {node_data.get('body_en', '')}"
                current_titles = [node_data.get("title_zh"), node_data.get("title_en")]
            else:
                body = f"{t_obj.get('body_zh', '')} {t_obj.get('body_en', '')}"
                current_titles = [t_obj.get("title_zh"), t_obj.get("title_en")]
            
            found_links = []
            for existing in existing_nodes:
                # Avoid self-link
                if existing["id"] == t_id or any(existing[k] in current_titles for k in ["title_zh", "title_en"] if existing[k]):
                    continue
                    
                # Search for title mentions
                titles = [t for t in [existing["title_zh"], existing["title_en"]] if t and len(t) > 2]
                for t in titles:
                    if t in body:
                        found_links.append(existing)
                        break
                        
            if found_links:
                if is_proposal:
                    # Update proposal node_data
                    edges = node_data.get("suggested_edges", [])
                    for link in found_links:
                        if not any(e.get("to_title_en") == link["title_en"] for e in edges):
                            edges.append({"to_title_en": link["title_en"], "relation": "related_to", "meta": {"auto_detected": True}})
                    cur.execute("UPDATE review_queue SET node_data = %s WHERE id = %s", (json.dumps(node_data), t_id))
                else:
                    # Create edge proposals for existing nodes
                    for link in found_links:
                        # Check if edge already exists
                        cur.execute("SELECT 1 FROM edges WHERE workspace_id = %s AND (from_id = %s AND to_id = %s OR from_id = %s AND to_id = %s) AND status = 'active'", (ws_id, t_id, link["id"], link["id"], t_id))
                        if not cur.fetchone():
                            # Create a proposal to link existing nodes
                            _propose_edge(cur, ws_id, t_id, link["id"], "related_to", "ai", "link_detector", {"auto_detected": True})

def _propose_edge(cur, ws_id, from_id, to_id, relation, source_type, proposer, meta=None):
    # This would need an edge proposal system. For now, let's just create the edge if it's an internal maintenance task.
    # Actually, let's stick to the simplest: create the edge directly if it's a background maintenance task.
    from core.security import generate_id
    eid = generate_id("edg")
    cur.execute(
        """
        INSERT INTO edges (id, workspace_id, from_id, to_id, relation, status, source_type, proposer, metadata)
        VALUES (%s, %s, %s, %s, %s, 'active', %s, %s, %s)
        ON CONFLICT DO NOTHING
        """,
        (eid, ws_id, from_id, to_id, relation, source_type, proposer, json.dumps(meta or {}))
    )


# ── Background task ───────────────────────────────────────────────────────────

async def process_ingestion(job_id: str, ws_id: str, content: str, user_id: str, filename: str, doc_type: str = "generic", approved_seeds: Optional[list[str]] = None, doc: Optional[NormalizedDocument] = None):
    try:
        from core.security import generate_id
        source_id = generate_id("src")
        
        # If we have a NormalizedDocument, the "content" we store in DB 
        # should be the joined text of all segments for search/audit.
        if doc:
            content = "\n\n".join([f"{' '.join(s.heading_chain + ([s.heading] if s.heading else []))}\n{s.content}" for s in doc.segments])
        
        # Record the import source
        with db_cursor(commit=True) as cur:
            page_count = doc.metadata.get("page_count") if doc else None
            has_ocr    = doc.metadata.get("has_ocr")    if doc else False
            
            cur.execute(
                """
                INSERT INTO import_sources (id, workspace_id, filename, doc_type, raw_content, page_count, has_ocr)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (source_id, ws_id, filename, doc_type, content, page_count, has_ocr)
            )

        resolved = _resolve_with_fallback(user_id, "extraction")
        total_tokens = 0

        # ── 1a. Scan for API Seed Nodes (D-2) ────────────────────────────────
        seed_nodes = _scan_api_endpoints(content)
        if approved_seeds is not None:
            # Filter by approved titles (e.g. "GET /api/v1/users")
            seed_nodes = [n for n in seed_nodes if n["title_en"] in approved_seeds]

        if seed_nodes:
            with db_cursor(commit=True) as cur:
                _persist_nodes_sync(cur, ws_id, seed_nodes, job_id, filename, user_id, resolved, source_id=source_id, is_seed=True)
            print(f"[ingest] Created {len(seed_nodes)} API seed nodes for {filename}")

        # ── 1b. Create the source_document node ───────────────────────────────
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
        if doc:
            # Use segments from the adapter
            chunks = []
            for s in doc.segments:
                chunks.append((s.content, s.heading_chain + ([s.heading] if s.heading else []), s.metadata))
        else:
            # Fallback to heading-aware chunking for plain text
            chunks = [(c, h, {}) for c, h in _chunk_text(content)]
            
        total_chunks = len(chunks)
        all_nodes: list[dict] = []

        # Record the total chunk count so the UI can render a progress bar
        with db_cursor(commit=True) as cur:
            cur.execute(
                "UPDATE ingestion_logs SET chunks_total = %s WHERE id = %s",
                (total_chunks, job_id),
            )

        for idx, (chunk_content, heading_chain, meta) in enumerate(chunks, 1):
            chunk_label = f"{filename} (chunk {idx}/{total_chunks})" if total_chunks > 1 else filename
            
            # Inject heading chain context
            context_prefix = " > ".join([f"[§{h}]" for h in heading_chain])
            if context_prefix:
                chunk_to_process = f"{context_prefix}\n\n{chunk_content}"
            else:
                chunk_to_process = chunk_content

            from core.ai import get_extraction_prompt
            system_prompt = get_extraction_prompt(doc_type)
            
            # H-2: Diagram-type specialization
            if meta.get("image_base64"):
                # Determine diagram type from filename/heading heuristics
                ctx_lower = f"{chunk_label} {' '.join(heading_chain)}".lower()
                if any(kw in ctx_lower for kw in ["erd", "er diagram", "entity", "database", "schema", "table"]):
                    diagram_prompt = (
                        "\nSPECIAL INSTRUCTION: This is an ER Diagram."
                        " Identify all Tables/Entities (as nodes with title 'Table: {name}')."
                        " Identify Foreign Key / association relationships between tables (as 'references' edges)."
                        " Include column details (name, type, constraints) in each node body."
                    )
                elif any(kw in ctx_lower for kw in ["architecture", "system", "service", "infra", "deploy"]):
                    diagram_prompt = (
                        "\nSPECIAL INSTRUCTION: This is a System Architecture Diagram."
                        " Identify all Services/Components (as individual nodes)."
                        " Identify call/communication relationships between services (as 'calls' or 'depends_on' edges)."
                        " Include protocols, ports, or technologies mentioned."
                    )
                elif any(kw in ctx_lower for kw in ["state", "fsm", "狀態", "transition"]):
                    diagram_prompt = (
                        "\nSPECIAL INSTRUCTION: This is a State Machine Diagram."
                        " Identify all States (as individual nodes)."
                        " Identify Transitions between states (as 'transitions_to' edges)."
                        " Include transition conditions/triggers in edge labels."
                    )
                elif any(kw in ctx_lower for kw in ["flow", "process", "step", "流程", "判斷"]):
                    diagram_prompt = (
                        "\nSPECIAL INSTRUCTION: This is a Flowchart / Process Diagram."
                        " Identify all Steps and Decision points (as individual nodes)."
                        " Identify the flow between steps (as 'follows' edges) and branching (as 'branches_to' edges)."
                        " Include decision conditions where visible."
                    )
                else:
                    diagram_prompt = (
                        "\nSPECIAL INSTRUCTION: This is an image/screenshot."
                        " Describe the architecture, entities, and relationships visible in the diagram."
                        " Identify major blocks/nodes and their connections before extracting knowledge nodes."
                    )
                system_prompt += diagram_prompt

            messages = [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"Extract Memory Nodes from this segment of '{chunk_label}':\n---\n{chunk_to_process}\n---"}
                    ]
                },
            ]

            # H-1: Multimodal injection
            if meta.get("image_base64"):
                messages[1]["content"].append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{meta.get('mime_type', 'image/png')};base64,{meta['image_base64']}"}
                })

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

            # Merge adapter-level suggested_edges into LLM-extracted nodes
            adapter_edges = meta.get("suggested_edges", [])
            if adapter_edges and nodes_data:
                # Attach adapter edges to the first extracted node from this chunk
                existing = nodes_data[0].get("suggested_edges", [])
                nodes_data[0]["suggested_edges"] = existing + adapter_edges

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
            review_ids = await _persist_nodes(cur, ws_id, all_nodes, job_id, filename, user_id, resolved, source_id=source_id, doc_type=doc_type)
            
            # G-1: Cross-file association detection
            new_rids = [r[0] for r in review_ids if r[0]]
            detect_cross_file_associations_for_nodes(ws_id, new_rids, is_proposal=True)

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

@router.post("/{ws_id}/ingest/excel-preview")
async def excel_preview(
    ws_id: str,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    """
    B-3: Parse an Excel/CSV file and return sheet metadata for the UI
    to display sheet selection and column mapping controls.
    """
    import io
    with db_cursor() as cur:
        _require_ws_access(cur, ws_id, user, write=True, required_scope="kb:write")

    ext = file.filename.split('.')[-1].lower() if '.' in file.filename else ""
    if ext not in ["xlsx", "xls", "csv"]:
        raise HTTPException(status_code=400, detail="Only Excel/CSV files supported for preview")

    import pandas as pd
    file_bytes = await file.read()
    stream = io.BytesIO(file_bytes)

    if ext == "csv":
        content = file_bytes.decode("utf-8", errors="replace")
        delimiter = "\t" if ("\t" in content and content.count("\t") > content.count(",")) else ","
        df_dict = {"Sheet1": pd.read_csv(io.StringIO(content), sep=delimiter, nrows=100)}
    else:
        df_dict = pd.read_excel(io.BytesIO(file_bytes), sheet_name=None, nrows=100)

    sheets = []
    for sheet_name, df in df_dict.items():
        cols = list(df.columns.astype(str))
        col_lower = [c.lower() for c in cols]
        title_cols = [c for c, cl in zip(cols, col_lower) if any(kw in cl for kw in ["title", "name", "主題", "名稱", "標題"])]
        desc_cols = [c for c, cl in zip(cols, col_lower) if any(kw in cl for kw in ["description", "desc", "說明", "描述"])]
        tag_cols = [c for c, cl in zip(cols, col_lower) if any(kw in cl for kw in ["tag", "label", "標籤", "分類"])]

        mode = "row" if len(cols) <= 8 and title_cols else "table"

        # Sample rows (first 5)
        sample = df.head(5).fillna("").to_dict(orient="records")

        sheets.append({
            "name": str(sheet_name),
            "columns": cols,
            "row_count": int(len(df)),
            "detected_mode": mode,
            "detected_title_col": title_cols[0] if title_cols else None,
            "detected_desc_col": desc_cols[0] if desc_cols else None,
            "detected_tag_col": tag_cols[0] if tag_cols else None,
            "sample_rows": sample,
        })

    return {"filename": file.filename, "sheets": sheets}


@router.post("/{ws_id}/ingest")
async def ingest_file(
    ws_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    doc_type: str = "generic",
    seeds: Optional[str] = None, # JSON array of approved seed titles
    excel_config: Optional[str] = None,  # B-3: JSON object with sheet/column mapping
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
        # Core-2: Use adapter system
        import io
        file_bytes = await file.read()
        stream = io.BytesIO(file_bytes)
        adapter = get_adapter_for_file(file.filename, file.content_type)

        # B-3: Pass excel_config to ExcelAdapter if applicable
        config = json.loads(excel_config) if excel_config else None
        if config and hasattr(adapter, 'parse_with_config'):
            doc = await adapter.parse_with_config(stream, file.filename, config)
        else:
            doc = await adapter.parse(stream, file.filename)
    except Exception as e:
        with db_cursor(commit=True) as cur:
            cur.execute(
                "UPDATE ingestion_logs SET status = 'failed', error_msg = %s, completed_at = now() WHERE id = %s",
                (f"File parsing failed: {str(e)}", job_id),
            )
        raise HTTPException(status_code=400, detail=f"File parsing failed: {str(e)}")

    approved_seeds = json.loads(seeds) if seeds else None
    background_tasks.add_task(process_ingestion, job_id, ws_id, "", user["sub"], file.filename, doc_type, approved_seeds, doc=doc)
    return {"message": "Ingestion started in background", "filename": file.filename, "job_id": job_id}


@router.get("/{ws_id}/sources")
def list_sources(ws_id: str, user: dict = Depends(get_current_user)):
    """D-3: List all imported sources for this workspace."""
    with db_cursor() as cur:
        _require_ws_access(cur, ws_id, user)
        cur.execute(
            """
            SELECT id, filename, doc_type, created_at
            FROM import_sources
            WHERE workspace_id = %s
            ORDER BY created_at DESC
            """,
            (ws_id,),
        )
        return cur.fetchall()


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
            async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
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

                await process_ingestion(job_id, ws_id, text, user["sub"], url, payload.doc_type)
        except Exception as exc:
            error_str = str(exc)
            with db_cursor(commit=True) as cur:
                cur.execute(
                    "UPDATE ingestion_logs SET status = 'failed', error_msg = %s, completed_at = now() WHERE id = %s",
                    (error_str, job_id),
                )

    background_tasks.add_task(fetch_and_process)
    return {"message": "URL ingestion started in background", "url": url, "job_id": job_id}

@router.post("/{ws_id}/import-audit")
@router.get("/{ws_id}/audit/{source_id}")
def audit_import(ws_id: str, source_id: Optional[str] = None, body: Optional[AuditRequest] = None, user: dict = Depends(get_current_user)):
    """
    E-1: Perform regex-based gap detection on an ingested source.
    Aligns with Spec: POST /workspaces/{ws_id}/import-audit
    """
    sid = source_id or (body.source_id if body else None)
    if not sid:
        raise HTTPException(status_code=400, detail="source_id is required")
        
    with db_cursor() as cur:
        _require_ws_access(cur, ws_id, user)
        
        # 1. Fetch source
        cur.execute("SELECT raw_content, filename FROM import_sources WHERE id = %s AND workspace_id = %s", (sid, ws_id))
        src = cur.fetchone()
        if not src:
            raise HTTPException(status_code=404, detail="Source not found")
        
        content = src["raw_content"]
        
        # 2. Extract items (regex)
        patterns = {
            "api": r'(GET|POST|PUT|DELETE|PATCH)\s+(/[a-zA-Z0-9_\-/{}]+)',
            "br": r'BR-\d+',
            "bl": r'BL-\d+',
            "us": r'US-\d+',
            "heading": r'^(#{1,6})\s+(.+)$'
        }
        
        found_items = {k: [] for k in patterns}
        for k, p in patterns.items():
            if k == "heading":
                for m in re.finditer(p, content, re.MULTILINE):
                    found_items[k].append(m.group(2).strip())
            else:
                # API regex has 2 groups
                if k == "api":
                    for m in re.finditer(p, content, re.IGNORECASE):
                        found_items[k].append(f"{m.group(1).upper()} {m.group(2)}")
                else:
                    for m in re.finditer(p, content):
                        found_items[k].append(m.group(0))
        
        # Deduplicate
        for k in found_items:
            found_items[k] = sorted(list(set(found_items[k])))

        # 3. Check for coverage in memory_nodes and review_queue
        audit_results = {}
        total_found = 0
        total_covered = 0

        for category, items in found_items.items():
            missing = []
            covered = []
            for item in items:
                search_term = item.lower()
                cur.execute(
                    """
                    SELECT 1 FROM memory_nodes 
                    WHERE workspace_id = %s AND status = 'active'
                      AND (LOWER(title_zh) LIKE %s OR LOWER(title_en) LIKE %s)
                    UNION
                    SELECT 1 FROM review_queue
                    WHERE workspace_id = %s AND status = 'pending'
                      AND (LOWER(node_data->>'title_zh') LIKE %s OR LOWER(node_data->>'title_en') LIKE %s)
                    LIMIT 1
                    """,
                    (ws_id, f"%{search_term}%", f"%{search_term}%", ws_id, f"%{search_term}%", f"%{search_term}%")
                )
                if cur.fetchone():
                    covered.append(item)
                    total_covered += 1
                else:
                    missing.append(item)
                total_found += 1
            
            audit_results[category] = {
                "total": len(items),
                "covered": len(covered),
                "missing": missing
            }

        coverage = total_covered / total_found if total_found > 0 else 1.0
        
        return {
            "source_id": source_id,
            "filename": src["filename"],
            "coverage": round(coverage, 2),
            "results": audit_results,
            "missing": [item for cat in audit_results.values() for item in cat["missing"]] # Flatten for backward compatibility
        }


@router.post("/{ws_id}/audit/{source_id}/retry")
async def retry_audit_headings(
    ws_id: str,
    source_id: str,
    payload: RetryAuditRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user)
):
    """
    F-2: Retry extraction for specific missing headings.
    Locates the text segment for each heading and triggers background extraction.
    """
    with db_cursor() as cur:
        _require_ws_access(cur, ws_id, user, write=True)
        cur.execute("SELECT raw_content, filename FROM import_sources WHERE id = %s AND workspace_id = %s", (source_id, ws_id))
        src = cur.fetchone()
        if not src:
            raise HTTPException(status_code=404, detail="Source not found")
        
        content = src["raw_content"]
        filename = src["filename"]

    # 1. Locate segments for each requested heading
    segments_to_process = []
    lines = content.splitlines()
    
    for target_h in payload.headings:
        # Find the line index of the heading
        # Use regex to match '# Target Heading' precisely
        target_pattern = re.compile(rf'^#+\s+{re.escape(target_h)}$', re.MULTILINE)
        match = target_pattern.search(content)
        if not match:
            continue
            
        start_pos = match.start()
        # Find where this section ends: the next heading of same or higher level
        # Get the level of the current heading
        level = len(match.group().split()[0])
        
        # Look for next heading with level <= current level
        next_h_pattern = re.compile(rf'^#{{1,{level}}}\s+.+$', re.MULTILINE)
        next_match = next_h_pattern.search(content, match.end())
        
        end_pos = next_match.start() if next_match else len(content)
        segment_text = content[start_pos:end_pos].strip()
        
        # Add a bit of preceding context (up to 5 lines) to help the LLM
        # Find start of line for start_pos
        line_start = content.rfind('\n', 0, start_pos) + 1
        pre_context_start = line_start
        for _ in range(5):
            idx = content.rfind('\n', 0, max(0, pre_context_start - 1))
            if idx == -1:
                pre_context_start = 0
                break
            pre_context_start = idx + 1
            
        context = content[pre_context_start:line_start]
        final_text = f"Context (Preceding):\n{context}\n\nTarget Section:\n{segment_text}"
        segments_to_process.append(final_text)

    if not segments_to_process:
        return {"message": "No matching headings found in source"}

    # 2. Trigger background jobs for these segments
    # We'll create a single ingestion job for all selected segments
    job_id = generate_id("ing")
    with db_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO ingestion_logs (id, workspace_id, user_id, filename, status, chunks_total)
            VALUES (%s, %s, %s, %s, 'processing', %s)
            """,
            (job_id, ws_id, user["sub"], f"Retry: {filename}", len(segments_to_process)),
        )

    async def _process_retry():
        try:
            resolved = _resolve_with_fallback(user["sub"], "extraction")
            all_nodes = []
            
            for idx, text in enumerate(segments_to_process, 1):
                from core.ai import get_extraction_prompt
                messages = [
                    {"role": "system", "content": get_extraction_prompt(payload.doc_type)},
                    {"role": "user", "content": f"Extract missing nodes from this specific section of '{filename}':\n\n{text}"}
                ]
                
                try:
                    from core.ai import chat_completion
                    raw, tokens = await chat_completion(resolved, messages)
                    nodes_data, _ = await _safe_parse_nodes(raw, resolved, filename)
                    all_nodes.extend(nodes_data)
                    
                    with db_cursor(commit=True) as cur:
                        cur.execute("UPDATE ingestion_logs SET chunks_done = %s WHERE id = %s", (idx, job_id))
                except Exception as e:
                    print(f"[ingest] Retry chunk {idx} failed: {e}")

            # Persist
            with db_cursor(commit=True) as cur:
                await _persist_nodes(cur, ws_id, all_nodes, job_id, filename, user["sub"], resolved, source_id=source_id)
                cur.execute("UPDATE ingestion_logs SET status = 'done', completed_at = now() WHERE id = %s", (job_id,))
        except Exception as e:
            with db_cursor(commit=True) as cur:
                cur.execute("UPDATE ingestion_logs SET status = 'failed', error_msg = %s, completed_at = now() WHERE id = %s", (str(e), job_id))

    background_tasks.add_task(_process_retry)
    return {"message": "Retry ingestion started", "job_id": job_id, "segment_count": len(segments_to_process)}

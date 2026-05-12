"""
services/nodes.py — Node CRUD, validation, revision, and change proposal logic.

Extracted from routers/kb.py (S2-2). All callers (REST + MCP routers) should
import from here. The original _functions in kb.py are kept temporarily as
backward-compat shims during migration.

Key exports:
  - validate_node_payload(data)
  - prepare_node_data(data, author, source_type, status)
  - create_node_in_db(cur, ws_id, node_data)
  - update_node_in_db(cur, ws_id, node_id, node_data, actor_id)
  - delete_node_in_db(cur, ws_id, node_id)
  - write_node_revision(cur, node_id, workspace_id, snapshot, signature, ...)
  - propose_change(cur, ws_id, change_type, target_node_id, node_data, ...)
  - create_edges_directly(cur, ws_id, from_id, suggested_edges)
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import HTTPException

from core.constants import VALID_CONTENT_T, VALID_FORMAT, VALID_NODE_VIS, VALID_RELATIONS
from core.diff import build_node_diff
from core.security import compute_signature, generate_id


class NodeValidationError(HTTPException):
    def __init__(self, message: str, field: str, hint: str):
        super().__init__(status_code=400, detail={
            "error": message,
            "field": field,
            "hint": hint
        })

class AICapacityExceeded(HTTPException):
    def __init__(self, detail: str = "AI rate limit or capacity reached"):
        super().__init__(status_code=429, detail=detail)


# ─── Column lists (single source, shared with BFS query) ─────────────────────

NODE_PUBLIC_COLUMNS = """
    id, schema_version, workspace_id, title_zh, title_en, content_type, content_format,
    body_zh, body_en, tags, visibility, author, created_at, updated_at,
    signature, source_type, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep,
    traversal_count, unique_traverser_count, status, archived_at,
    copied_from_node, copied_from_ws, validity_confirmed_at, validity_confirmed_by,
    ask_count, miss_count, source_id, source_doc_node_id, source_paragraph_ref
"""

NODE_EDITABLE_FIELDS = [
    "title_zh", "title_en", "content_type", "content_format",
    "body_zh", "body_en", "tags", "visibility",
    "source_doc_node_id", "source_paragraph_ref"
]


# ─── Validation ───────────────────────────────────────────────────────────────

def validate_node_payload(data: dict) -> None:
    """Raise NodeValidationError if mandatory fields are invalid."""
    if data.get("content_type") not in VALID_CONTENT_T:
        raise NodeValidationError(
            "Invalid content_type", 
            "content_type", 
            f"Must be one of: {', '.join(sorted(VALID_CONTENT_T))}"
        )
    if data.get("content_format") not in VALID_FORMAT:
        raise NodeValidationError(
            "Invalid content_format", 
            "content_format", 
            "Must be 'plain' or 'markdown'"
        )
    if data.get("visibility") not in VALID_NODE_VIS:
        raise NodeValidationError(
            "Invalid visibility", 
            "visibility", 
            "Must be 'public', 'private', or 'internal'"
        )
    if not (data.get("title_zh") or data.get("title_en")):
        raise NodeValidationError(
            "Missing title", 
            "title_en", 
            "At least one of 'title_zh' or 'title_en' must be provided."
        )
    if not (data.get("body_zh") or data.get("body_en")):
        raise NodeValidationError(
            "Missing body", 
            "body_en", 
            "At least one of 'body_zh' or 'body_en' must be provided."
        )


def _initial_author_rep(source_type: str, status: str) -> float:
    """Determine initial author reputation (P4.5-3D-1)."""
    if source_type == "human":
        return 0.8
    if source_type == "document":
        return 0.6
    if source_type == "qa_conversation":
        return 0.3 if status == "active" else 0.5
    if source_type in ("mcp", "ai"):
        return 0.5
    return 0.5


def prepare_node_data(
    data: dict,
    author: str,
    source_type: str = "human",
    status: str = "active",
) -> dict:
    """
    Merge, validate, and compute derived fields for node creation/update.
    Returns a dict ready for SQL INSERT/UPDATE.
    """
    payload = {field: data.get(field) for field in NODE_EDITABLE_FIELDS}
    payload["tags"] = list(payload.get("tags") or [])
    validate_node_payload(payload)
    payload["author"] = data.get("author") or author
    payload["source_type"] = data.get("source_type") or source_type
    payload["dim_author_rep"] = data.get("dim_author_rep") or _initial_author_rep(payload["source_type"], status)

    # Ensure mandatory text fields are not None
    payload["title_zh"] = payload.get("title_zh") or ""
    payload["title_en"] = payload.get("title_en") or ""
    payload["body_zh"] = payload.get("body_zh") or ""
    payload["body_en"] = payload.get("body_en") or ""
    payload["content_format"] = payload.get("content_format") or "plain"
    payload["visibility"] = payload.get("visibility") or "private"

    # Compute initial trust_score
    if payload["source_type"] in ("ai", "mcp"):
        payload["trust_score"] = 0.7
    else:
        acc   = 0.5
        fresh = 1.0
        util  = 0.5
        rep   = float(payload["dim_author_rep"])
        payload["trust_score"] = (acc * 0.4) + (fresh * 0.25) + (util * 0.25) + (rep * 0.1)

    payload["signature"] = compute_signature(
        {"zh-TW": payload["title_zh"], "en": payload["title_en"]},
        {
            "type": payload["content_type"],
            "format": payload["content_format"],
            "body": {"zh-TW": payload["body_zh"], "en": payload["body_en"]},
        },
        payload["tags"],
        payload["author"],
    )
    return payload


def node_row_to_snapshot(row: Optional[dict]) -> Optional[dict]:
    """Convert a DB row dict to a snapshot dict (only editable fields)."""
    if not row:
        return None
    return {
        field: (list(row[field]) if field == "tags" and row.get(field) is not None else row.get(field))
        for field in NODE_EDITABLE_FIELDS
    }


# ─── CRUD Operations ──────────────────────────────────────────────────────────

def create_node_in_db(cur, ws_id: str, node_data: dict) -> dict:
    """Insert a new memory_node and return the created row."""
    payload = prepare_node_data(
        node_data, node_data["author"], node_data.get("source_type", "human"), node_data.get("status", "active")
    )
    node_id = node_data.get("id") or generate_id("mem")
    cur.execute(
        f"""
        INSERT INTO memory_nodes (
            id, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en,
            tags, visibility, author, signature, source_type, copied_from_node, copied_from_ws,
            status, dim_author_rep, trust_score, source_id,
            source_doc_node_id, source_paragraph_ref
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        RETURNING {NODE_PUBLIC_COLUMNS}
        """,
        (
            node_id, ws_id,
            payload["title_zh"], payload["title_en"],
            payload["content_type"], payload["content_format"],
            payload["body_zh"], payload["body_en"],
            payload["tags"], payload["visibility"],
            payload["author"], payload["signature"], payload["source_type"],
            node_data.get("copied_from_node"), node_data.get("copied_from_ws"),
            node_data.get("status", "active"),
            payload["dim_author_rep"], payload["trust_score"], node_data.get("source_id"),
            payload.get("source_doc_node_id"), payload.get("source_paragraph_ref"),
        ),
    )
    return cur.fetchone()


def update_node_in_db(cur, ws_id: str, node_id: str, node_data: dict, actor_id: str) -> dict:
    """Update an existing memory_node and return the updated row."""
    cur.execute(
        f"SELECT {NODE_PUBLIC_COLUMNS} FROM memory_nodes WHERE id = %s AND workspace_id = %s",
        (node_id, ws_id),
    )
    existing = cur.fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Node not found")

    merged = {**dict(existing), **{field: node_data.get(field, existing.get(field)) for field in NODE_EDITABLE_FIELDS}}
    payload = prepare_node_data(merged, actor_id, merged.get("source_type", "human"))
    cur.execute(
        f"""
        UPDATE memory_nodes
        SET title_zh = %s, title_en = %s, content_type = %s, content_format = %s,
            body_zh = %s, body_en = %s, tags = %s, visibility = %s, signature = %s, updated_at = %s,
            source_id = %s, source_doc_node_id = %s, source_paragraph_ref = %s
        WHERE id = %s AND workspace_id = %s
        RETURNING {NODE_PUBLIC_COLUMNS}
        """,
        (
            payload["title_zh"], payload["title_en"],
            payload["content_type"], payload["content_format"],
            payload["body_zh"], payload["body_en"],
            payload["tags"], payload["visibility"],
            payload["signature"], datetime.now(timezone.utc),
            node_data.get("source_id", existing.get("source_id")),
            payload.get("source_doc_node_id"), payload.get("source_paragraph_ref"),
            node_id, ws_id,
        ),
    )
    return cur.fetchone()


def delete_node_in_db(cur, ws_id: str, node_id: str) -> dict:
    """Archive (DELETE) a memory_node and return the deleted row."""
    cur.execute(
        f"DELETE FROM memory_nodes WHERE id = %s AND workspace_id = %s RETURNING {NODE_PUBLIC_COLUMNS}",
        (node_id, ws_id),
    )
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Node not found")
    return row

def confirm_node_validity_in_db(cur, ws_id: str, node_id: str, user_email: str) -> None:
    """Mark a node as confirmed by the user and boost its accuracy to 1.0."""
    cur.execute(
        """
        UPDATE memory_nodes
        SET validity_confirmed_at = NOW(),
            validity_confirmed_by = %s
        WHERE id = %s AND workspace_id = %s
        """,
        (user_email, node_id, ws_id)
    )
    
    cur.execute("SELECT dim_freshness, dim_utility, dim_author_rep FROM memory_nodes WHERE id = %s", (node_id,))
    node = cur.fetchone()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
        
    freshness = float(node["dim_freshness"])
    utility = float(node["dim_utility"])
    author_rep = float(node["dim_author_rep"])
    
    new_accuracy = 1.0
    trust_score = (new_accuracy * 0.4) + (freshness * 0.25) + (utility * 0.25) + (author_rep * 0.1)
    
    cur.execute(
        """
        UPDATE memory_nodes
        SET dim_accuracy = %s, trust_score = %s
        WHERE id = %s
        """,
        (new_accuracy, trust_score, node_id)
    )


# ─── Revision Tracking ────────────────────────────────────────────────────────

def write_node_revision(
    cur,
    node_id: str,
    workspace_id: str,
    snapshot: dict,
    signature: str,
    proposer_type: str,
    proposer_id: Optional[str],
    review_id: Optional[str],
) -> None:
    """Insert a new node_revision record and prune to keep only the last 10."""
    cur.execute(
        "SELECT COALESCE(MAX(revision_no), 0) AS max_rev FROM node_revisions WHERE node_id = %s",
        (node_id,),
    )
    revision_no = int(cur.fetchone()["max_rev"]) + 1
    cur.execute(
        """
        INSERT INTO node_revisions (id, node_id, workspace_id, revision_no, snapshot, signature, proposer_type, proposer_id, review_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            generate_id("nrev"), node_id, workspace_id, revision_no,
            json.dumps(snapshot, ensure_ascii=False), signature,
            proposer_type, proposer_id, review_id,
        ),
    )
    # Keep only the most recent 10 revisions
    cur.execute(
        """
        DELETE FROM node_revisions
        WHERE id IN (
          SELECT id FROM node_revisions
          WHERE node_id = %s
          ORDER BY revision_no DESC
          OFFSET 10
        )
        """,
        (node_id,),
    )


# ─── Change Proposal ──────────────────────────────────────────────────────────

def propose_change(
    cur,
    ws_id: str,
    change_type: Literal["create", "update", "delete"],
    target_node_id: Optional[str],
    node_data: Optional[dict],
    proposer_type: Literal["human", "ai"],
    proposer_id: Optional[str],
    proposer_meta: Optional[dict] = None,
    suggested_edges: Optional[list[dict]] = None,
    source_info: Optional[str] = None,
    confidence_score: Optional[float] = None,
    source_id: Optional[str] = None,
    source_doc_node_id: Optional[str] = None,
    source_paragraph_ref: Optional[str] = None,
) -> str:
    """Queue a node change into review_queue. Returns the new review_id."""
    if node_data is not None:
        if source_doc_node_id:
            node_data["source_doc_node_id"] = source_doc_node_id
        if source_paragraph_ref:
            node_data["source_paragraph_ref"] = source_paragraph_ref
    before_snapshot = None
    after_snapshot = None

    if target_node_id:
        cur.execute(
            f"SELECT {NODE_PUBLIC_COLUMNS} FROM memory_nodes WHERE id = %s AND workspace_id = %s",
            (target_node_id, ws_id),
        )
        existing = cur.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Target node not found")
        before_snapshot = node_row_to_snapshot(existing)

    if change_type != "delete":
        payload = dict(node_data or {})
        if change_type == "update" and before_snapshot:
            payload = {**before_snapshot, **payload}
        payload["tags"] = list(payload.get("tags") or [])
        prepared = prepare_node_data(
            payload,
            payload.get("author") or proposer_id or "system",
            payload.get("source_type", proposer_type),
        )
        after_snapshot = {field: prepared[field] for field in NODE_EDITABLE_FIELDS} | {
            "author": payload.get("author") or proposer_id,
            "source_type": payload.get("source_type", proposer_type),
            "signature": prepared["signature"],
            "copied_from_node": payload.get("copied_from_node"),
            "copied_from_ws": payload.get("copied_from_ws"),
        }

    diff_summary = build_node_diff(before_snapshot, after_snapshot, change_type)
    review_id = generate_id("rev")
    cur.execute(
        """
        INSERT INTO review_queue (
            id, workspace_id, change_type, target_node_id, before_snapshot, node_data, diff_summary,
            suggested_edges, status, source_info, proposer_type, proposer_id, proposer_meta, confidence_score, source_id
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'pending', %s, %s, %s, %s, %s, %s)
        """,
        (
            review_id, ws_id, change_type, target_node_id,
            json.dumps(before_snapshot, ensure_ascii=False) if before_snapshot is not None else None,
            json.dumps(after_snapshot or {}, ensure_ascii=False),
            json.dumps(diff_summary, ensure_ascii=False),
            json.dumps(suggested_edges or [], ensure_ascii=False),
            source_info, proposer_type, proposer_id,
            json.dumps(proposer_meta or {}, ensure_ascii=False) if proposer_meta is not None else None,
            confidence_score, source_id,
        ),
    )
    return review_id


# ─── Edge helpers ─────────────────────────────────────────────────────────────

def create_edges_directly(cur, ws_id: str, from_id: str, suggested_edges: list[dict]) -> None:
    """Directly insert edges (for admin-role creates/updates)."""
    if not suggested_edges:
        return
    for edge in suggested_edges:
        to_id    = edge.get("to_id")
        relation = edge.get("relation")
        weight   = edge.get("weight", 1.0)
        if not to_id or not relation or relation not in VALID_RELATIONS or from_id == to_id:
            continue
        cur.execute("SELECT 1 FROM memory_nodes WHERE id = %s AND workspace_id = %s", (to_id, ws_id))
        if not cur.fetchone():
            continue
        cur.execute(
            "SELECT 1 FROM edges WHERE workspace_id=%s AND from_id=%s AND to_id=%s AND relation=%s",
            (ws_id, from_id, to_id, relation),
        )
        if cur.fetchone():
            continue
        cur.execute(
            "INSERT INTO edges (id, workspace_id, from_id, to_id, relation, weight) VALUES (%s,%s,%s,%s,%s,%s)",
            (generate_id("edge"), ws_id, from_id, to_id, relation, weight),
        )


# ─── Backward-compat aliases ──────────────────────────────────────────────────
# Keep old _ names working during migration; remove once kb.py is fully updated.

_validate_node_payload   = validate_node_payload
_prepare_node_data       = prepare_node_data
_node_row_to_snapshot    = node_row_to_snapshot
_create_node_in_db       = create_node_in_db
_update_node_in_db       = update_node_in_db
_delete_node_in_db       = delete_node_in_db
_write_node_revision     = write_node_revision
_propose_change          = propose_change
_create_edges_directly   = create_edges_directly
_confirm_node_validity_in_db = confirm_node_validity_in_db

def list_nodes_in_db(
    cur,
    ws_id: str,
    q: Optional[str] = None,
    tag: Optional[str] = None,
    content_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    status: str = "active",
    filter: Optional[str] = None,
    include_source: bool = False,
    user: Optional[dict] = None
) -> list[dict]:
    from services.workspaces import require_ws_access, get_effective_role, strip_body_if_viewer
    from services.search import apply_text_search
    ws = require_ws_access(cur, ws_id, user)
    filters = ["workspace_id = %s"]
    params: list = [ws_id]

    if filter == "orphan":
        filters.append("NOT EXISTS (SELECT 1 FROM edges e WHERE e.status = 'active' AND (e.from_id = memory_nodes.id OR e.to_id = memory_nodes.id))")
    elif filter == "faded":
        filters.append("NOT EXISTS (SELECT 1 FROM edges e WHERE e.status = 'active' AND (e.from_id = memory_nodes.id OR e.to_id = memory_nodes.id)) AND EXISTS (SELECT 1 FROM edges e2 WHERE e2.status = 'faded' AND (e2.from_id = memory_nodes.id OR e2.to_id = memory_nodes.id))")
    elif filter == "never_traversed":
        filters.append("traversal_count = 0")
    elif filter == "empty_body":
        filters.append("(body_zh IS NULL OR body_zh = '') AND (body_en IS NULL OR body_en = '')")
    else:
        if status != "all":
            filters.append("status = %s")
            params.append(status)

    if q:
        apply_text_search(filters, params, q)
    if tag:
        filters.append("%s = ANY(tags)")
        params.append(tag)
    if content_type:
        filters.append("content_type = %s")
        params.append(content_type)
    if not include_source and not content_type:
        filters.append("content_type != 'source_document'")
        
    params += [limit, offset]
    cur.execute(f"SELECT {NODE_PUBLIC_COLUMNS} FROM memory_nodes WHERE {' AND '.join(filters)} ORDER BY created_at DESC LIMIT %s OFFSET %s", params)
    rows = cur.fetchall()
    role = get_effective_role(cur, ws_id, ws["owner_id"], user["sub"] if user else None)
    return [strip_body_if_viewer(row, role) for row in rows]

def get_table_view_in_db(cur, ws_id: str, q: Optional[str], filter: Optional[str], sort_by: Optional[str], order: Optional[str], limit: int, offset: int, user: Optional[dict]) -> dict:
    from services.workspaces import require_ws_access, get_effective_role, strip_body_if_viewer
    from services.search import apply_text_search
    ws = require_ws_access(cur, ws_id, user)
    filters = ["workspace_id = %s", "status = 'active'", "content_type != 'source_document'"]
    params = [ws_id]
    if q:
        apply_text_search(filters, params, q)
    
    if filter == "orphan":
        filters.append("NOT EXISTS (SELECT 1 FROM edges WHERE (from_id = memory_nodes.id OR to_id = memory_nodes.id) AND status = 'active')")

    cur.execute(f"SELECT COUNT(*) FROM memory_nodes WHERE {' AND '.join(filters)}", params)
    total = cur.fetchone()["count"]
    
    sort_col = "created_at"
    if sort_by in ("title", "title_en", "title_zh"):
        sort_col = "title_en"
    elif sort_by == "content_type":
        sort_col = "content_type"
    elif sort_by == "trust_score":
        sort_col = "trust_score"
    
    sort_order = "DESC" if order.lower() == "desc" else "ASC"
    
    params_list = list(params) + [limit, offset]
    cur.execute(f"SELECT {NODE_PUBLIC_COLUMNS} FROM memory_nodes WHERE {' AND '.join(filters)} ORDER BY {sort_col} {sort_order} LIMIT %s OFFSET %s", params_list)
    rows = cur.fetchall()
    role = get_effective_role(cur, ws_id, ws["owner_id"], user["sub"] if user else None)
    nodes = [strip_body_if_viewer(row, role) for row in rows]
    return {"nodes": nodes, "total_count": total}

async def search_nodes_in_db(cur, ws_id: str, query: str, limit: int, user: Optional[dict]) -> list[dict]:
    from services.search import search_nodes_in_db as _search
    return await _search(cur, ws_id, query, limit, user)

def get_nodes_health_in_db(cur, ws_id: str, user: Optional[dict]) -> dict:
    from services.workspaces import require_ws_access
    require_ws_access(cur, ws_id, user)
    cur.execute(
        """
        SELECT
            COUNT(*) FILTER (WHERE status = 'active') AS total,
            COUNT(*) FILTER (WHERE status = 'active' AND (body_zh IS NULL OR body_zh = '') AND (body_en IS NULL OR body_en = '')) AS empty_body,
            COUNT(*) FILTER (WHERE status = 'active' AND (((body_zh IS NULL OR body_zh = '') AND (body_en IS NOT NULL AND body_en != '')) OR ((body_en IS NULL OR body_en = '') AND (body_zh IS NOT NULL AND body_zh != '')))) AS single_language_only,
            COUNT(*) FILTER (WHERE status = 'active' AND trust_score < 0.3) AS low_trust,
            COUNT(*) FILTER (WHERE status = 'active' AND embedding IS NULL) AS no_embedding
        FROM memory_nodes
        WHERE workspace_id = %s
        """,
        (ws_id,),
    )
    row = cur.fetchone()
    cur.execute(
        """
        SELECT COUNT(*) FROM memory_nodes
        WHERE workspace_id = %s AND status = 'active'
            AND NOT EXISTS (
            SELECT 1 FROM edges e
            WHERE e.status = 'active'
                AND (e.from_id = memory_nodes.id OR e.to_id = memory_nodes.id)
            )
        """,
        (ws_id,),
    )
    orphan_row = cur.fetchone()
    return {
        "total":               row["total"],
        "empty_body":          row["empty_body"],
        "single_language_only": row["single_language_only"],
        "no_edges":            orphan_row["count"],
        "low_trust":           row["low_trust"],
        "no_embedding":        row["no_embedding"],
    }

def suggest_edges_for_node_in_db(cur, ws_id: str, node_id: str, user: dict) -> dict:
    from services.workspaces import require_ws_access, get_effective_role
    ws = require_ws_access(cur, ws_id, user, write=True, required_role="admin")
    role = get_effective_role(cur, ws_id, ws["owner_id"], user["sub"])
    if role not in ("admin",):
        raise HTTPException(status_code=403, detail="Admin only")
    cur.execute("SELECT 1 FROM memory_nodes WHERE id = %s AND workspace_id = %s", (node_id, ws_id))
    if not cur.fetchone():
        raise HTTPException(status_code=404, detail="Node not found")

    proposed = 0
    cur.execute("SELECT embedding FROM memory_nodes WHERE id = %s AND workspace_id = %s", (node_id, ws_id))
    row = cur.fetchone()
    if row and row["embedding"] is not None:
        cur.execute(
            """
            SELECT id, (1 - (embedding <=> %s::vector)) AS sim
            FROM memory_nodes
            WHERE workspace_id = %s AND id != %s
              AND embedding IS NOT NULL AND status = 'active'
              AND content_type != 'source_document'
            ORDER BY sim DESC LIMIT 5
            """,
            (row["embedding"], ws_id, node_id),
        )
        candidates = [r for r in cur.fetchall() if r["sim"] > 0.70]
        for c in candidates:
            try:
                propose_change(
                    cur, ws_id, "create_edge", None,
                    {"from_id": node_id, "to_id": c["id"],
                     "relation": "related_to", "weight": round(float(c["sim"]), 2)},
                    "ai", user["sub"],
                    {"source": "manual_edge_suggestion"},
                    source_info=f"Manual edge suggestion (similarity={c['sim']:.2f})",
                )
                proposed += 1
            except Exception:
                pass
    return {"proposed": proposed}

def get_node_in_db(cur, ws_id: str, node_id: str, user: Optional[dict]) -> dict:
    from services.workspaces import require_ws_access, get_effective_role, strip_body_if_viewer
    # NODE_PUBLIC_COLUMNS is available in local scope
    # from routers.kb import NODE_PUBLIC_COLUMNS
    ws = require_ws_access(cur, ws_id, user)
    cur.execute(f"SELECT {NODE_PUBLIC_COLUMNS} FROM memory_nodes WHERE id = %s AND workspace_id = %s", (node_id, ws_id))
    node = cur.fetchone()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    role = get_effective_role(cur, ws_id, ws["owner_id"], user["sub"] if user else None)
    return strip_body_if_viewer(node, role)

def bulk_archive_nodes_in_db(cur, ws_id: str, node_ids: list, user: dict) -> int:
    from services.workspaces import require_ws_access, get_effective_role
    ws = require_ws_access(cur, ws_id, user, write=True, required_role="admin")
    role = get_effective_role(cur, ws_id, ws["owner_id"], user["sub"])
    if role not in ("editor", "admin"):
        raise HTTPException(status_code=403, detail="Editor or Admin role required")
    if not node_ids:
        return 0
    cur.execute(
        """
        UPDATE memory_nodes
        SET status = 'archived', archived_at = NOW()
        WHERE id = ANY(%s) AND workspace_id = %s AND status != 'archived'
        """,
        (node_ids, ws_id),
    )
    return cur.rowcount

def archive_node_in_db(cur, ws_id: str, node_id: str, user: dict) -> None:
    from services.workspaces import require_ws_access, get_effective_role
    ws = require_ws_access(cur, ws_id, user, write=True, required_role="admin")
    role = get_effective_role(cur, ws_id, ws["owner_id"], user["sub"])
    if role not in ("editor", "admin"):
        raise HTTPException(status_code=403, detail="Editor or Admin role required")
    cur.execute(
        "UPDATE memory_nodes SET status = 'archived', archived_at = NOW() WHERE id = %s AND workspace_id = %s RETURNING id",
        (node_id, ws_id),
    )
    if not cur.fetchone():
        raise HTTPException(status_code=404, detail="Node not found")

def restore_node_in_db(cur, ws_id: str, node_id: str, user: dict) -> None:
    from services.workspaces import require_ws_access, get_effective_role
    ws = require_ws_access(cur, ws_id, user, write=True, required_role="admin")
    role = get_effective_role(cur, ws_id, ws["owner_id"], user["sub"])
    if role not in ("editor", "admin"):
        raise HTTPException(status_code=403, detail="Editor or Admin role required")
    cur.execute(
        "UPDATE memory_nodes SET status = 'active', archived_at = NULL WHERE id = %s AND workspace_id = %s RETURNING id",
        (node_id, ws_id),
    )
    if not cur.fetchone():
        raise HTTPException(status_code=404, detail="Node not found or not archived")

def get_health_scores_in_db(cur, ws_id: str, user: Optional[dict]) -> list:
    from services.workspaces import require_ws_access
    ws = require_ws_access(cur, ws_id, user)
    kb_type = ws.get("kb_type", "evergreen")

    cur.execute("SELECT id FROM memory_nodes WHERE workspace_id=%s AND status='active'", (ws_id,))
    node_ids = [r["id"] for r in cur.fetchall()]

    results = []
    for nid in node_ids:
        if kb_type == "evergreen":
            cur.execute("SELECT COUNT(*) AS cnt FROM edges WHERE status='active' AND (from_id=%s OR to_id=%s)", (nid, nid))
            edge_count = cur.fetchone()["cnt"]
            score = min(1.0, edge_count / 5)
            reason = f"{edge_count} active edges"
        else:
            cur.execute("SELECT MAX(traversed_at) FROM traversal_log WHERE node_id=%s", (nid,))
            last_t = cur.fetchone()["max"]
            if last_t is None:
                days_since = 999
            else:
                from datetime import datetime, timezone
                days_since = (datetime.now(timezone.utc) - last_t).days
            score = max(0.0, 1.0 - days_since / 180)
            reason = f"{days_since} days since last traversal"

        if score >= 0.6:
            label = "healthy"
        elif score >= 0.3:
            label = "warning"
        else:
            label = "critical"

        results.append({"node_id": nid, "score": round(score, 4), "label": label, "reason": reason})

    return results

def create_node_full_in_db(cur, ws_id: str, payload: dict, user: dict) -> tuple[dict, str]:
    from services.workspaces import require_ws_access, get_effective_role
    from services.nodes import validate_node_payload, propose_change, create_node_in_db
    validate_node_payload(payload)
    ws = require_ws_access(cur, ws_id, user, write=True, required_role="admin")
    
    if payload.get("copied_from_ws"):
        require_ws_access(cur, payload["copied_from_ws"], user)
        
    role = get_effective_role(cur, ws_id, ws["owner_id"], user["sub"])
    proposer_id = user["sub"]
    
    if role == "editor":
        review_id = propose_change(
            cur,
            ws_id,
            "create",
            None,
            payload | {"author": proposer_id, "source_type": payload.get("source_type", "human")},
            payload.get("source_type", "human"),
            proposer_id,
            {"source": "node_editor"},
            suggested_edges=payload.get("suggested_edges", []),
            source_info=f"Proposed new node by {proposer_id}",
        )
        return None, review_id

    node = create_node_in_db(cur, ws_id, payload | {"author": proposer_id, "source_type": payload.get("source_type", "human")})
    
    if payload.get("suggested_edges"):
        create_edges_directly(cur, ws_id, node["id"], payload["suggested_edges"])
        
    return node, None

async def create_node_full_with_dedup(
    cur, 
    ws_id: str, 
    payload: dict, 
    user: dict, 
    force_create: bool = False
) -> tuple[Optional[dict], Optional[str], Optional[dict]]:
    """
    P4.8-S9-2: Create node with semantic dedup.
    Returns (node_row, review_id, duplicate_info).
    If duplicate_found and not force_create, returns (None, None, dup_info).
    """
    from services.workspaces import require_ws_access
    ws = require_ws_access(cur, ws_id, user, write=True)
    settings = ws.get("settings") or {}
    threshold = settings.get("auto_dedup_threshold", 0.92)

    if not force_create:
        text_to_check = f"{payload.get('title_en', '')}\n{payload.get('body_en', '')}".strip()
        if text_to_check:
            similar = await find_similar_node_in_db(cur, ws_id, text_to_check, user["sub"], threshold=threshold)
            if similar:
                dup_info = {
                    "action": "duplicate_found",
                    "existing_node_id": similar["id"],
                    "existing_title": similar["title_en"],
                    "similarity": round(float(similar["similarity"]), 3),
                    "message": "A highly similar node already exists. Use force_create=true to override."
                }
                return None, None, dup_info

    node, review_id = create_node_full_in_db(cur, ws_id, payload, user)
    return node, review_id, None

def update_node_full_in_db(cur, ws_id: str, node_id: str, payload: dict, user: dict) -> tuple[dict, str]:
    from services.workspaces import require_ws_access, get_effective_role
    from services.nodes import propose_change, update_node_in_db
    ws = require_ws_access(cur, ws_id, user, write=True, required_role="admin")
    role = get_effective_role(cur, ws_id, ws["owner_id"], user["sub"])
    proposer_id = user["sub"]
    
    if role == "editor":
        review_id = propose_change(
            cur, ws_id, "update", node_id, payload,
            payload.get("source_type", "human"), proposer_id, {"source": "node_editor"},
            suggested_edges=payload.get("suggested_edges", []),
            source_info=f"Proposed update by {proposer_id}",
        )
        return None, review_id

    node = update_node_in_db(cur, ws_id, node_id, payload, proposer_id)
    return node, None

def delete_node_full_in_db(cur, ws_id: str, node_id: str, user: dict) -> tuple[dict, str]:
    from services.workspaces import require_ws_access, get_effective_role
    from services.nodes import propose_change, delete_node_in_db
    ws = require_ws_access(cur, ws_id, user, write=True, required_role="admin")
    role = get_effective_role(cur, ws_id, ws["owner_id"], user["sub"])
    proposer_id = user["sub"]
    
    if role == "editor":
        review_id = propose_change(
            cur, ws_id, "delete", node_id, None,
            "human", proposer_id, {"source": "node_editor"},
            source_info=f"Proposed deletion by {proposer_id}",
        )
        return None, review_id
        
    node = delete_node_in_db(cur, ws_id, node_id)
    return node, None

def list_node_revisions_in_db(cur, ws_id: str, node_id: str, user: Optional[dict]) -> list[dict]:
    from services.workspaces import require_ws_access
    require_ws_access(cur, ws_id, user)
    cur.execute(
        """
        SELECT id, revision_no, created_at, created_by, change_type, change_source
        FROM node_revisions
        WHERE workspace_id = %s AND node_id = %s
        ORDER BY revision_no DESC
        """,
        (ws_id, node_id)
    )
    return cur.fetchall()

def get_node_revision_in_db(cur, ws_id: str, node_id: str, revision_no: int, user: Optional[dict]) -> dict:
    from services.workspaces import require_ws_access
    require_ws_access(cur, ws_id, user)
    cur.execute(
        """
        SELECT * FROM node_revisions
        WHERE workspace_id = %s AND node_id = %s AND revision_no = %s
        """,
        (ws_id, node_id, revision_no)
    )
    row = cur.fetchone()
    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Revision not found")
    return row

def diff_node_revisions_in_db(cur, ws_id: str, node_id: str, rev_a: int, rev_b: int, user: Optional[dict]) -> dict:
    from services.workspaces import require_ws_access
    from core.diff import build_node_diff
    require_ws_access(cur, ws_id, user)
    cur.execute(
        "SELECT snapshot FROM node_revisions WHERE workspace_id = %s AND node_id = %s AND revision_no IN (%s, %s)",
        (ws_id, node_id, rev_a, rev_b)
    )
    rows = cur.fetchall()
    if len(rows) != 2:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="One or both revisions not found")
        
    snap_a = rows[0]["snapshot"] if rows[0]["revision_no"] == rev_a else rows[1]["snapshot"]
    snap_b = rows[1]["snapshot"] if rows[1]["revision_no"] == rev_b else rows[0]["snapshot"]
    
    return build_node_diff(snap_a, snap_b)

def restore_node_revision_in_db(cur, ws_id: str, node_id: str, revision_no: int, user: dict) -> tuple[dict, str]:
    from services.workspaces import require_ws_access, get_effective_role
    from services.nodes import propose_change, update_node_in_db
    from fastapi import HTTPException
    
    ws = require_ws_access(cur, ws_id, user, write=True, required_role="admin")
    role = get_effective_role(cur, ws_id, ws["owner_id"], user["sub"])
    proposer_id = user["sub"]
    
    cur.execute(
        "SELECT snapshot FROM node_revisions WHERE workspace_id = %s AND node_id = %s AND revision_no = %s",
        (ws_id, node_id, revision_no)
    )
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Revision not found")
        
    payload = row["snapshot"]
    if "id" in payload:
        del payload["id"]
    if "workspace_id" in payload:
        del payload["workspace_id"]
        
    if role == "editor":
        review_id = propose_change(
            cur, ws_id, "update", node_id, payload,
            "human", proposer_id, {"source": "revision_restore"},
            source_info=f"Proposed restore to rev {revision_no} by {proposer_id}",
        )
        return None, review_id

    node = update_node_in_db(cur, ws_id, node_id, payload, proposer_id)
    return node, None

def vote_trust_in_db(cur, ws_id: str, node_id: str, body_dict: dict, user: dict) -> dict:
    from services.workspaces import require_ws_access
    # from routers.kb import _actor_has_traversed_node
    from services.nodes import actor_has_traversed_node as _actor_has_traversed_node
    from fastapi import HTTPException
    require_ws_access(cur, ws_id, user)
    if not _actor_has_traversed_node(cur, node_id, user["sub"]):
         raise HTTPException(status_code=403, detail="Must traverse node before voting")
         
    cur.execute(
        """
        INSERT INTO node_trust_votes (id, node_id, user_id, workspace_id, accuracy, utility)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (node_id, user_id)
        DO UPDATE SET accuracy = EXCLUDED.accuracy, utility = EXCLUDED.utility
        """,
        (generate_id("vote"), node_id, user["sub"], ws_id, body_dict["accuracy"], body_dict["utility"])
    )

    cur.execute(
        """
        SELECT AVG(accuracy)::float / 5 as avg_acc, AVG(utility)::float / 5 as avg_util
        FROM node_trust_votes
        WHERE node_id = %s
        """,
        (node_id,)
    )
    stats = cur.fetchone()
    avg_acc = stats["avg_acc"]
    avg_util = stats["avg_util"]
    
    cur.execute("SELECT dim_freshness, dim_author_rep FROM memory_nodes WHERE id = %s", (node_id,))
    node = cur.fetchone()
    if not node:
         raise HTTPException(status_code=404, detail="Node not found")
         
    freshness = float(node["dim_freshness"])
    author_rep = float(node["dim_author_rep"])
    
    trust_score = (avg_acc * 0.4) + (avg_util * 0.25) + (freshness * 0.25) + (author_rep * 0.1)
    
    cur.execute(
        """
        UPDATE memory_nodes
        SET dim_accuracy = %s, dim_utility = %s, trust_score = %s
        WHERE id = %s
        """,
        (avg_acc, avg_util, trust_score, node_id)
    )
    return {"status": "ok", "trust_score": trust_score}

def reembed_all_nodes_in_db(cur, ws_id: str, user: dict) -> int:
    from services.workspaces import require_ws_access
    ws = require_ws_access(cur, ws_id, user)
    if ws["owner_id"] != user["sub"]:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Only the workspace owner can trigger re-embedding")
    cur.execute("SELECT COUNT(*) FROM memory_nodes WHERE workspace_id = %s AND embedding IS NULL AND status = 'active'", (ws_id,))
    return cur.fetchone()["count"]

def backfill_embeddings_in_db(cur, ws_id: str, user: dict) -> list[dict]:
    from services.workspaces import require_ws_access, get_effective_role
    ws = require_ws_access(cur, ws_id, user, write=True, required_role="admin")
    role = get_effective_role(cur, ws_id, ws["owner_id"], user["sub"])
    if role not in ("admin",):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Admin only")
    cur.execute(
        "SELECT id, title_zh, title_en, body_zh, body_en FROM memory_nodes "
        "WHERE workspace_id = %s AND embedding IS NULL AND status = 'active'",
        (ws_id,),
    )
    return cur.fetchall()

def traverse_node_in_db(cur, node_id: str, user: dict) -> str:
    from services.workspaces import require_ws_access
    from core.ratelimit import TraversalGuard
    from fastapi import HTTPException
    TraversalGuard.check(user["sub"])
    cur.execute("SELECT workspace_id FROM memory_nodes WHERE id = %s", (node_id,))
    node_row = cur.fetchone()
    if not node_row:
        raise HTTPException(status_code=404, detail="Node not found")
    require_ws_access(cur, node_row["workspace_id"], user)
    return node_row["workspace_id"]

def trigger_link_detection_in_db(cur, ws_id: str, user: dict) -> list[str]:
    from services.workspaces import require_ws_access
    require_ws_access(cur, ws_id, user, write=True)
    cur.execute("SELECT id FROM memory_nodes WHERE workspace_id = %s AND status = 'active'", (ws_id,))
    return [r["id"] for r in cur.fetchall()]

def actor_has_traversed_node(cur, node_id: str, actor_id: str) -> bool:
    cur.execute("SELECT 1 FROM traversal_log WHERE node_id = %s AND actor_id = %s", (node_id, actor_id))
    return bool(cur.fetchone())

CONNECT_SYSTEM = (
    "You suggest semantic edges in a knowledge graph. "
    "Given a list of ORPHAN nodes and ANCHOR nodes, your goal is to connect orphans to anchors or other orphans. "
    "Relations: depends_on, extends, related_to, contradicts. "
    "RULES:\n"
    "1. Use EXACT titles from the provided lists for 'from_title' and 'to_title'.\n"
    "2. Output ONLY a raw JSON array of objects.\n"
    "3. Format: [{\"from_title\":\"...\",\"to_title\":\"...\",\"relation\":\"...\"}].\n"
    "4. No markdown, no fences, no explanations."
)

def list_review_queue_in_db(cur, ws_id: str, limit: int, user: dict) -> dict:
    from services.workspaces import require_ws_access
    require_ws_access(cur, ws_id, user, write=False)

    # 1. Fetch pending proposals from review_queue table
    cur.execute(
        """SELECT id, change_type, target_node_id, status, created_at, proposer_type,
                  COALESCE(node_data->>'title_en', '') as title_en, 
                  COALESCE(node_data->>'title_zh', '') as title_zh
           FROM review_queue
           WHERE workspace_id = %s AND status = 'pending'
           ORDER BY created_at DESC
           LIMIT %s""",
        (ws_id, limit),
    )
    proposals = [dict(r) for r in cur.fetchall()]

    # 2. Fetch anomalous nodes from memory_nodes (quality issues)
    cur.execute(
        """SELECT id, title_zh, title_en, content_type, trust_score,
                  source_type, updated_at, validity_confirmed_at,
                  char_length(COALESCE(body_zh, '')) AS body_zh_len
           FROM memory_nodes
           WHERE workspace_id = %s AND status = 'active'
             AND (
               -- Low trust
               trust_score < 0.7
               -- AI-generated node with very short body AND low traversal (atomic facts are OK if well-used)
               OR (source_type = 'ai' AND char_length(COALESCE(body_zh, '')) < 80 AND traversal_count < 3)
               -- Body contains unfilled placeholders
               OR body_zh LIKE '%%??%%'
               OR body_en LIKE '%%??%%'
             )
           ORDER BY trust_score ASC, updated_at DESC
           LIMIT %s""",
        (ws_id, limit),
    )
    anomalous = [dict(r) for r in cur.fetchall()]

    return {
        "pending_proposals": proposals,
        "anomalous_nodes": anomalous
    }

async def find_similar_node_in_db(cur, ws_id: str, text: str, user_id: str, threshold: float = 0.92) -> Optional[dict]:
    """Find a node in the database that is semantically similar to the given text."""
    from services.search import perform_semantic_search
    from core.database import db_cursor
    
    # Get workspace config
    cur.execute("SELECT embedding_model, embedding_provider FROM workspaces WHERE id = %s", (ws_id,))
    ws_row = cur.fetchone()
    ws_model = ws_row["embedding_model"] if ws_row else None
    ws_prov = ws_row["embedding_provider"] if ws_row else None
    
    results = await perform_semantic_search(cur, ws_id, text, user_id, limit=1, ws_model=ws_model, ws_prov=ws_prov)
    if results and results[0].get("similarity", 0) >= threshold:
        return results[0]
    return None


def apply_split_in_db(cur, ws_id: str, rev_id: Optional[str], node_id: str, proposals: list[dict], user_id: str) -> dict:
    """
    P4.8-S9-3f: Apply a node split proposal.
    Creates new atomic nodes and archives the original node.
    """
    from services.nodes import create_node_in_db, delete_node_in_db, create_edges_directly
    from core.security import generate_id
    
    # 1. Fetch original node for context (optional, but good for inheriting tags/visibility)
    cur.execute("SELECT * FROM memory_nodes WHERE id = %s AND workspace_id = %s", (node_id, ws_id))
    original = cur.fetchone()
    if not original:
        raise HTTPException(status_code=404, detail="Original node not found")
        
    new_nodes = []
    # 2. Create new nodes
    for p in proposals:
        # Use 'proposed' sub-object if present (RESTRUCTURE_SYSTEM format)
        data = p.get("proposed") or p
        
        node_payload = {
            "title_zh": data.get("title_zh"),
            "title_en": data.get("title_en"),
            "body_zh": data.get("body_zh"),
            "body_en": data.get("body_en"),
            "content_type": data.get("content_type") or original["content_type"],
            "content_format": original["content_format"],
            "tags": list(set(original.get("tags", []) + data.get("tags", []))),
            "visibility": original["visibility"],
            "author": user_id,
            "source_type": "ai"
        }
        new_node = create_node_in_db(cur, ws_id, node_payload)
        new_nodes.append(new_node)
        
    # 3. Establish internal edges between new nodes (default to 'related_to' or 'extends')
    if len(new_nodes) > 1:
        first_id = new_nodes[0]["id"]
        for other in new_nodes[1:]:
            create_edges_directly(cur, ws_id, first_id, [{"to_id": other["id"], "relation": "related_to"}])
            
    # 4. Archive original node
    cur.execute("UPDATE memory_nodes SET status = 'archived' WHERE id = %s AND workspace_id = %s", (node_id, ws_id))
    
    # 5. Mark review as completed if it exists
    if rev_id:
        cur.execute("UPDATE review_queue SET status = 'approved', reviewed_at = now(), reviewed_by = %s WHERE id = %s", (user_id, rev_id))
        
    return {"original_node_id": node_id, "new_nodes_count": len(new_nodes), "new_nodes": new_nodes}


async def archive_qa_to_kb(ws_id: str, user_id: str, question: str, answer: str, source_node_ids: list[str], force_auto_active: bool = False):
    """
    Background task to distill a Q&A interaction into structured Memory Nodes.
    """
    try:
        from core.ai import chat_completion, resolve_provider, strip_fences
        from core.database import db_cursor
        from core.security import generate_id
        from services.nodes import propose_change as _propose_change, create_node_in_db as _create_node_in_db
        import json
        
        # 1. Resolve AI provider for distillation
        resolved = resolve_provider(user_id, "extraction")
        
        system_prompt = (
            "You are a Knowledge Archiver. Distill the following Q&A into a set of MemTrace nodes.\n"
            "RULES:\n"
            "1. The question itself MUST be one 'inquiry' node.\n"
            "2. Each independent piece of knowledge in the answer should be a separate node (factual/procedural/preference).\n"
            "3. If the answer has conditions (version, environment), create 'context' nodes for them.\n"
            "4. Return a JSON array of nodes with 'title_zh', 'title_en', 'content_type', 'body_zh', 'body_en', 'tags'.\n"
            "Example: [{\"title_zh\": \"...\", \"content_type\": \"inquiry\", ...}, {\"title_zh\": \"...\", \"content_type\": \"factual\", ...}]"
        )
        user_prompt = f"QUESTION: {question}\n\nANSWER: {answer}"
        
        raw, _ = await chat_completion(resolved, [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}])
        nodes_data = json.loads(strip_fences(raw))
        
        if not isinstance(nodes_data, list) or not nodes_data:
            return

        with db_cursor(commit=True) as cur:
            cur.execute("SELECT qa_archive_mode FROM workspaces WHERE id = %s", (ws_id,))
            row = cur.fetchone()
            mode = "auto_active" if force_auto_active else (row["qa_archive_mode"] if row else "manual_review")
            initial_status = "active" if mode == "auto_active" else "archived"

            # 2. Extract inquiry node and knowledge nodes
            inquiry_nodes = [n for n in nodes_data if n.get("content_type") == "inquiry"]
            knowledge_nodes = [n for n in nodes_data if n.get("content_type") != "inquiry"]

            if not inquiry_nodes:
                print(f"[qa-archiver] No inquiry node found; skipping")
                return
            
            # 3. Create nodes and edges
            inquiry_data = inquiry_nodes[0]
            inquiry_data["source_type"] = "qa_conversation"
            inquiry_status = "answered" if knowledge_nodes else "gap"
            inquiry_data["status"] = inquiry_status if mode == "auto_active" else "archived"
            
            if mode == "auto_active":
                # Create Inquiry node
                inquiry_created = _create_node_in_db(cur, ws_id, inquiry_data)
                inquiry_id = inquiry_created["id"]

                # P4.5-3A-7: Similar Inquiry Linking
                try:
                    from core.ai import embed
                    from core.constants import SIMILAR_INQUIRY_LINK, FAQ_CACHE_HIT
                    embed_prov = resolve_provider(user_id, "embedding")
                    inquiry_vector, _ = await embed(embed_prov, inquiry_data["title_zh"] + " " + inquiry_data["body_zh"])
                    
                    cur.execute("UPDATE memory_nodes SET embedding = %s::vector WHERE id = %s", (inquiry_vector, inquiry_id))
                    
                    cur.execute("""
                        SELECT id, (1 - (embedding <=> %s::vector)) AS similarity
                        FROM memory_nodes
                        WHERE workspace_id = %s
                          AND content_type = 'inquiry'
                          AND id != %s
                          AND embedding IS NOT NULL
                          AND (1 - (embedding <=> %s::vector)) >= %s
                          AND (1 - (embedding <=> %s::vector)) < %s
                        ORDER BY similarity DESC LIMIT 5
                    """, (inquiry_vector, ws_id, inquiry_id, inquiry_vector, SIMILAR_INQUIRY_LINK, inquiry_vector, FAQ_CACHE_HIT))
                    
                    for similar in cur.fetchall():
                        cur.execute("""
                            INSERT INTO edges (id, workspace_id, from_id, to_id, relation, weight, status)
                            VALUES (%s, %s, %s, %s, 'similar_to', %s, 'active')
                            ON CONFLICT DO NOTHING
                        """, (generate_id("edge"), ws_id, inquiry_id, similar["id"], similar["similarity"]))
                except Exception as _sim_err:
                    print(f"[qa-archiver] Similar inquiry linking failed: {_sim_err}")
                
                # Create Knowledge nodes and link them
                for kn in knowledge_nodes:
                    kn["source_type"] = "qa_conversation"
                    kn["status"] = "active"
                    kn_created = _create_node_in_db(cur, ws_id, kn)
                    
                    # Link answer to inquiry
                    cur.execute("""
                        INSERT INTO edges (id, workspace_id, from_id, to_id, relation, weight, status)
                        VALUES (%s, %s, %s, %s, 'answered_by', 0.7, 'active')
                    """, (generate_id("edge"), ws_id, inquiry_id, kn_created["id"]))

                    # P4.5-3C-1: Contradiction Detection
                    kn_vector = kn_created.get("embedding")
                    if kn_vector:
                        from core.constants import CONTRADICTION_CHECK
                        cur.execute("""
                            SELECT id, title_zh, body_zh, content_type
                            FROM memory_nodes
                            WHERE workspace_id = %s
                              AND id != %s
                              AND content_type IN ('factual', 'preference')
                              AND status = 'active'
                              AND embedding IS NOT NULL
                              AND (1 - (embedding <=> %s::vector)) >= %s
                            ORDER BY (1 - (embedding <=> %s::vector)) DESC LIMIT 5
                        """, (ws_id, kn_created["id"], kn_vector, CONTRADICTION_CHECK, kn_vector))
                        candidates = cur.fetchall()
                        
                        if candidates:
                            for cand in candidates:
                                try:
                                    prompt = f"判斷以下兩段陳述是否互相矛盾：\nA: {kn['body_zh']}\nB: {cand['body_zh']}\n\n請以 JSON 格式回傳，包含 'contradicts' (boolean) 與 'reason' (string)。"
                                    raw, _ = await chat_completion(resolved, [{"role": "user", "content": prompt}])
                                    res = json.loads(strip_fences(raw))
                                    if res.get("contradicts"):
                                        cur.execute("""
                                            INSERT INTO edges (id, workspace_id, from_id, to_id, relation, weight, status, metadata)
                                            VALUES (%s, %s, %s, %s, 'contradicts', 0.5, 'active', %s)
                                        """, (generate_id("edge"), ws_id, kn_created["id"], cand["id"], json.dumps({"reason": res.get("reason")})))
                                        
                                        cur.execute("UPDATE memory_nodes SET status = 'conflicted' WHERE id = %s", (inquiry_id,))
                                        inquiry_status = "conflicted"
                                        inquiry_data["status"] = "conflicted"
                                        _propose_change(
                                            cur, ws_id, "update", inquiry_id, inquiry_data, "ai", "qa_archiver",
                                            proposer_meta={"source": "contradiction_detector", "conflict_reason": res.get("reason")},
                                            source_info=f"Conflict detected! Reason: {res.get('reason')}"
                                        )
                                except Exception as exc:
                                    print(f"[qa-archiver] Contradiction check failed: {exc}")
            else:
                # manual_review
                inquiry_data["status"] = inquiry_status
                inquiry_rev_id = _propose_change(cur, ws_id, "create", None, inquiry_data, "ai", "qa_archiver", source_info="Q&A Archive (Inquiry)")
                
                for kn in knowledge_nodes:
                    kn["source_type"] = "qa_conversation"
                    kn["status"] = "archived"
                    _propose_change(cur, ws_id, "create", None, kn, "ai", "qa_archiver", source_info=f"Q&A Archive (Answer for {inquiry_rev_id})")
                
    except Exception as e:
        print(f"[qa-archiver] Failed to archive Q&A: {e}")


async def increment_ask_count(node_id: str):
    """Background task to increment ask_count for an inquiry node."""
    try:
        from core.database import db_cursor
        with db_cursor(commit=True) as cur:
            cur.execute("UPDATE memory_nodes SET ask_count = ask_count + 1 WHERE id = %s", (node_id,))
    except Exception as e:
        print(f"[ask_count] Failed to increment for {node_id}: {e}")

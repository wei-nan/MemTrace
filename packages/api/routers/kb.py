from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, List, Literal, Optional, Union
import hashlib
import hmac
import json
from collections import defaultdict, deque

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from core.database import db_cursor
from core.config import settings


def _preview_id(node_id: str) -> str:
    """Derive an opaque, non-enumerable preview ID via HMAC-SHA256.

    Using the server's SECRET_KEY as the HMAC key means:
    - IDs are non-guessable without the key.
    - The same node always maps to the same preview_id (stable for graph rendering).
    - Sequential node IDs do NOT produce sequential preview_ids.
    """
    digest = hmac.new(
        settings.secret_key.encode(),
        node_id.encode(),
        hashlib.sha256,
    ).hexdigest()
    return "p_" + digest[:20]


def _is_postgres() -> bool:
    return settings.database_url.startswith("postgresql")


def _apply_text_search(filters: list, params: list, q: str) -> None:
    """Add full-text search conditions. Uses tsvector on PostgreSQL, LIKE on SQLite."""
    if _is_postgres():
        import re
        # Extract CJK phrases and English words
        cjk_runs = re.findall(r'[\u4e00-\u9fff]+', q)
        eng_words = re.findall(r'[a-zA-Z0-9]{2,}', q)
        terms = cjk_runs + eng_words
        
        if terms:
            # Use a combination of full-text search and ILIKE for CJK support
            or_conds = []
            # 1. Standard full-text search for English/segmented parts
            or_conds.append("search_vector @@ plainto_tsquery('simple', %s)")
            params.append(q)
            
            # 2. ILIKE for each extracted term (especially CJK)
            for t in terms:
                or_conds.append("(title_zh ILIKE %s OR title_en ILIKE %s OR body_zh ILIKE %s)")
                like_t = f"%{t}%"
                params += [like_t, like_t, like_t]
            
            filters.append(f"({' OR '.join(or_conds)})")
        else:
            # Fallback if no specific terms extracted
            filters.append("search_vector @@ plainto_tsquery('simple', %s)")
            params.append(q)
    else:
        like = f"%{q}%"
        filters.append(
            "(title_zh LIKE %s OR title_en LIKE %s OR body_zh LIKE %s OR body_en LIKE %s)"
        )
        params += [like, like, like, like]
from core.deps import get_current_user, get_current_user_optional, RequireScope
from core.ratelimit import TraversalGuard
from core.diff import build_node_diff
from core.security import compute_signature, generate_id
from core.ai import resolve_provider, embed, record_usage, AIProviderUnavailable
from models.kb import (
    EdgeCreate,
    EdgeResponse,
    GraphPreviewResponse,
    NodeCreate,
    NodeResponse,
    NodeUpdate,
    RateEdgeRequest,
    TraverseEdgeRequest,
    ValidityConfirmationResponse,
    WorkspaceAssociationResponse,
    WorkspaceCreate,
    WorkspaceResponse,
    WorkspaceUpdate,
    TableViewResponse,
    WorkspacePurgeResponse,
    AnalyticsTopNode,
    WorkspaceAnalyticsResponse,
    TokenEfficiencyResponse,
    VoteTrustRequest,
    WorkspaceCloneRequest,
    WorkspaceCloneJobResponse,
    ForkWorkspaceRequest,
)
from core.agent import get_or_create_agent_node
from models.review import NodeRevisionMetaResponse, NodeRevisionResponse

router = APIRouter(prefix="/api/v1", tags=["knowledge-base"])

VALID_RELATIONS = {"depends_on", "extends", "related_to", "contradicts", "answered_by", "similar_to", "queried_via_mcp"}
VALID_KB_VIS = {"public", "conditional_public", "restricted", "private"}
VALID_NODE_VIS = {"public", "team", "private"}
VALID_CONTENT_T = {"factual", "procedural", "preference", "context", "inquiry"}
VALID_FORMAT = {"plain", "markdown"}
NODE_EDITABLE_FIELDS = [
    "title_zh",
    "title_en",
    "content_type",
    "content_format",
    "body_zh",
    "body_en",
    "tags",
    "visibility",
]

NODE_PUBLIC_COLUMNS = """
    id, workspace_id, title_zh, title_en, content_type, content_format,
    body_zh, body_en, tags, visibility, author, trust_score,
    dim_accuracy, dim_freshness, dim_utility, dim_author_rep,
    traversal_count, unique_traverser_count, validity_confirmed_at,
    source_type, status, created_at, updated_at
"""


def _bfs_neighborhood(
    cur,
    workspace_id: str,
    root_id: str,
    depth: int = 2,
    relation: Optional[str] = None,
    direction: Literal["both", "outbound", "inbound"] = "both",
    include_source: bool = True,
    viewer_role: Optional[str] = None,
    viewer_id: Optional[str] = None,
) -> dict:
    """BFS neighborhood query, returns {root_id, depth, nodes, edges, truncated, total_nodes}"""
    
    # P4.7-S3-1: Dynamic depth adjustment based on workspace density
    # If user provides default depth (2), we adjust based on node count.
    if depth <= 2:
        cur.execute("SELECT COUNT(*) FROM memory_nodes WHERE workspace_id = %s", (workspace_id,))
        ws_count = cur.fetchone()["count"]
        if ws_count < 1000:
            depth = 3
        elif ws_count > 10000:
            depth = 1
            
    depth = min(max(depth, 1), 3)
    
    nodes_found = {}
    edges_found = []
    queue = deque([(root_id, 0)])
    
    # Track which IDs are already in the queue to avoid redundant processing
    enqueued = {root_id}
    
    truncated = False
    
    while queue:
        curr_id, curr_depth = queue.popleft()
        
        # Load node
        cur.execute(
            f"SELECT {NODE_PUBLIC_COLUMNS} FROM memory_nodes WHERE id = %s AND workspace_id = %s AND status IN ('active', 'pending_review')",
            (curr_id, workspace_id)
        )
        node = cur.fetchone()
        if not node:
            continue
            
        # source_document filter
        if not include_source and node["content_type"] == "source_document":
            continue
            
        node = dict(node)
        
        # P4.7-S3-2: Enhanced Pending review flag (check both node status and review_queue)
        cur.execute(
            "SELECT 1 FROM review_queue WHERE node_id = %s AND status = 'pending' LIMIT 1",
            (curr_id,)
        )
        has_pending_review = (cur.fetchone() is not None)
        node["is_pending"] = (node["status"] == "pending_review") or has_pending_review
            
        # Visibility & Privacy check (Option B)
        # If not public and viewer is not authorized (not owner/editor/admin), redact
        is_owner = (viewer_id and viewer_id == node["author"])
        if node["visibility"] != "public" and viewer_role not in ("editor", "admin") and not is_owner:
            node["is_protected"] = True
            node["title_zh"] = None
            node["title_en"] = None
            node["body_zh"] = None
            node["body_en"] = None
            node["tags"] = []
        else:
            node["is_protected"] = False

        nodes_found[curr_id] = node
        
        if len(nodes_found) >= 500:
            truncated = True
            break

        if curr_depth < depth:
            # Find neighbors
            where_clauses = ["workspace_id = %s", "status IN ('active', 'faded')"]
            params = [workspace_id]
            
            direction_clause = ""
            if direction == "outbound":
                direction_clause = "AND from_id = %s"
                params.append(curr_id)
            elif direction == "inbound":
                direction_clause = "AND to_id = %s"
                params.append(curr_id)
            else: # both
                direction_clause = "AND (from_id = %s OR to_id = %s)"
                params.append(curr_id)
                params.append(curr_id)
                
            if relation:
                where_clauses.append("relation = %s")
                params.append(relation)
                
            query = f"SELECT id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, status FROM edges WHERE {' AND '.join(where_clauses)} {direction_clause}"
            cur.execute(query, params)
            
            for edge in cur.fetchall():
                edges_found.append(dict(edge))
                neighbor_id = edge["to_id"] if edge["from_id"] == curr_id else edge["from_id"]
                if neighbor_id not in enqueued:
                    enqueued.add(neighbor_id)
                    queue.append((neighbor_id, curr_depth + 1))

    return {
        "root_id": root_id,
        "depth": depth,
        "nodes": list(nodes_found.values()),
        "edges": edges_found,
        "truncated": truncated,
        "total_nodes": len(nodes_found)
    }



def _require_ws_access(cur, ws_id: str, user: Optional[dict], write: bool = False, required_scope: Optional[str] = None):
    # API key scope and workspace validation
    if user and "api_key_id" in user:
        # Check workspace scoping
        ak_ws_id = user.get("workspace_id")
        if ak_ws_id and ak_ws_id != ws_id:
            raise HTTPException(status_code=403, detail="API key is restricted to another workspace")
            
        if required_scope:
            scopes = user.get("scopes") or []
            if "*" not in scopes and required_scope not in scopes:
                raise HTTPException(status_code=403, detail={"error": "insufficient_scope", "required": required_scope})

    cur.execute("SELECT visibility, owner_id, kb_type FROM workspaces WHERE id = %s", (ws_id,))
    ws = cur.fetchone()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    vis = ws["visibility"]
    user_id = user["sub"] if user else None

    if user_id == ws["owner_id"]:
        return ws

    if vis == "private":
        raise HTTPException(status_code=403, detail="Access denied")

    if vis in ("public", "conditional_public") and not write:
        return ws

    if vis == "restricted" or write:
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")
        cur.execute(
            "SELECT role FROM workspace_members WHERE workspace_id = %s AND user_id = %s",
            (ws_id, user_id),
        )
        member = cur.fetchone()
        if not member:
            raise HTTPException(status_code=403, detail="Access denied")
        if write and member["role"] not in ("editor", "admin"):
            raise HTTPException(status_code=403, detail="Editor or Admin role required")

    return ws


def _get_effective_role(cur, ws_id: str, owner_id: str, user_id: Optional[str]) -> Optional[str]:
    if not user_id:
        return None
    if user_id == owner_id:
        return "admin"
    cur.execute(
        "SELECT role FROM workspace_members WHERE workspace_id = %s AND user_id = %s",
        (ws_id, user_id),
    )
    row = cur.fetchone()
    return row["role"] if row else None


def _strip_body_if_viewer(node_row: dict, role: Optional[str]):
    node_row = dict(node_row)
    node_row["content_stripped"] = False
    if role not in ("editor", "admin"):
        # Plan A: public nodes retain body even for non-members
        if node_row.get("visibility") == "public":
            return node_row
        node_row["body_zh"] = None
        node_row["body_en"] = None
        node_row["content_stripped"] = True
    return node_row


def _validate_node_payload(data: dict):
    if data.get("content_type") not in VALID_CONTENT_T:
        raise HTTPException(status_code=400, detail="Invalid content_type")
    if data.get("content_format") not in VALID_FORMAT:
        raise HTTPException(status_code=400, detail="Invalid content_format")
    if data.get("visibility") not in VALID_NODE_VIS:
        raise HTTPException(status_code=400, detail="Invalid visibility")
    if not (data.get("title_zh") or data.get("title_en")):
        raise HTTPException(status_code=400, detail="At least one title language field must be non-empty")
    if not (data.get("body_zh") or data.get("body_en")):
        raise HTTPException(status_code=400, detail="At least one body language field must be non-empty")


def _initial_author_rep(source_type: str, status: str) -> float:
    """依來源與初始狀態決定 author reputation (P4.5-3D-1)。"""
    if source_type == "human":
        return 0.8
    if source_type == "document":
        return 0.6
    if source_type == "qa_conversation":
        # active（auto_active）給 0.3，archived（manual_review）給 0.5
        return 0.3 if status == "active" else 0.5
    if source_type == "mcp":
        return 0.0
    return 0.5


def _node_row_to_snapshot(row: Optional[dict]) -> Optional[dict]:
    if not row:
        return None
    return {field: (list(row[field]) if field == "tags" and row.get(field) is not None else row.get(field)) for field in NODE_EDITABLE_FIELDS}


def _prepare_node_data(data: dict, author: str, source_type: str = "human", status: str = "active") -> dict:
    payload = {field: data.get(field) for field in NODE_EDITABLE_FIELDS}
    payload["tags"] = list(payload.get("tags") or [])
    _validate_node_payload(payload)
    payload["author"] = data.get("author") or author
    payload["source_type"] = data.get("source_type") or source_type
    payload["dim_author_rep"] = data.get("dim_author_rep") or _initial_author_rep(payload["source_type"], status)
    
    # Ensure mandatory text fields are not None (prevents DB NotNullViolation)
    payload["title_zh"] = payload.get("title_zh") or ""
    payload["title_en"] = payload.get("title_en") or ""
    payload["body_zh"] = payload.get("body_zh") or ""
    payload["body_en"] = payload.get("body_en") or ""
    
    # Calculate trust_score: Accuracy 0.4 (default 0.5), Freshness 0.25 (default 1.0), Utility 0.25 (default 0.5), Rep 0.1
    # Note: These are initial values. dim_accuracy/freshness/utility use DB defaults if not set.
    # But for a new node, we want a reasonable starting trust_score.
    acc = 0.5
    fresh = 1.0
    util = 0.5
    rep = payload["dim_author_rep"]
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


_KNOWN_DIMS = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
    "text-embedding-004":     768,   # Gemini
    "nomic-embed-text":       768,
    "mxbai-embed-large":      1024,
    "all-minilm":             384,
    "bge-m3":                 1024,
    "bge-large-en-v1.5":      1024,
    "snowflake-arctic-embed":  1024,
    "e5-mistral-7b-instruct":  4096,
}

def _get_embedding_dim(model: str) -> int:
    lower = model.lower()
    for known, dim in _KNOWN_DIMS.items():
        if lower.startswith(known) or known in lower:
            return dim
    return 1536  # Safe default


def _create_node_in_db(cur, ws_id: str, node_data: dict) -> dict:
    payload = _prepare_node_data(node_data, node_data["author"], node_data.get("source_type", "human"), node_data.get("status", "active"))
    node_id = node_data.get("id") or generate_id("mem")
    cur.execute(
        """
        INSERT INTO memory_nodes (
            id, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en,
            tags, visibility, author, signature, source_type, copied_from_node, copied_from_ws,
            status, dim_author_rep, trust_score
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        RETURNING {NODE_PUBLIC_COLUMNS}
        """,
        (
            node_id,
            ws_id,
            payload["title_zh"],
            payload["title_en"],
            payload["content_type"],
            payload["content_format"],
            payload["body_zh"],
            payload["body_en"],
            payload["tags"],
            payload["visibility"],
            payload["author"],
            payload["signature"],
            payload["source_type"],
            node_data.get("copied_from_node"),
            node_data.get("copied_from_ws"),
            node_data.get("status", "active"),
            payload["dim_author_rep"],
            payload["trust_score"],
        ),
    )
    return cur.fetchone()


def _update_node_in_db(cur, ws_id: str, node_id: str, node_data: dict, actor_id: str) -> dict:
    cur.execute(f"SELECT {NODE_PUBLIC_COLUMNS} FROM memory_nodes WHERE id = %s AND workspace_id = %s", (node_id, ws_id))
    existing = cur.fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Node not found")

    merged = {**dict(existing), **{field: node_data.get(field, existing.get(field)) for field in NODE_EDITABLE_FIELDS}}
    payload = _prepare_node_data(merged, actor_id, merged.get("source_type", "human"))
    cur.execute(
        """
        UPDATE memory_nodes
        SET title_zh = %s, title_en = %s, content_type = %s, content_format = %s,
            body_zh = %s, body_en = %s, tags = %s, visibility = %s, signature = %s, updated_at = %s
        WHERE id = %s AND workspace_id = %s
        RETURNING {NODE_PUBLIC_COLUMNS}
        """,
        (
            payload["title_zh"],
            payload["title_en"],
            payload["content_type"],
            payload["content_format"],
            payload["body_zh"],
            payload["body_en"],
            payload["tags"],
            payload["visibility"],
            payload["signature"],
            datetime.now(timezone.utc),
            node_id,
            ws_id,
        ),
    )
    return cur.fetchone()


def _delete_node_in_db(cur, ws_id: str, node_id: str):
    cur.execute(f"DELETE FROM memory_nodes WHERE id = %s AND workspace_id = %s RETURNING {NODE_PUBLIC_COLUMNS}", (node_id, ws_id))
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Node not found")
    return row


def _create_edges_directly(cur, ws_id: str, from_id: str, suggested_edges: list[dict]):
    if not suggested_edges:
        return
    for edge in suggested_edges:
        to_id = edge.get("to_id")
        relation = edge.get("relation")
        weight = edge.get("weight", 1.0)
        if not to_id or not relation or relation not in VALID_RELATIONS or from_id == to_id:
            continue
        # Verify target node exists in same workspace
        cur.execute("SELECT 1 FROM memory_nodes WHERE id = %s AND workspace_id = %s", (to_id, ws_id))
        if not cur.fetchone():
            continue
        # Check for existing edge to avoid unique constraint error
        cur.execute(
            "SELECT 1 FROM edges WHERE workspace_id=%s AND from_id=%s AND to_id=%s AND relation=%s",
            (ws_id, from_id, to_id, relation)
        )
        if cur.fetchone():
            continue
        cur.execute(
            "INSERT INTO edges (id, workspace_id, from_id, to_id, relation, weight) VALUES (%s, %s, %s, %s, %s, %s)",
            (generate_id("edge"), ws_id, from_id, to_id, relation, weight)
        )


def _write_node_revision(
    cur,
    node_id: str,
    workspace_id: str,
    snapshot: dict,
    signature: str,
    proposer_type: str,
    proposer_id: Optional[str],
    review_id: Optional[str],
):
    cur.execute("SELECT COALESCE(MAX(revision_no), 0) AS max_rev FROM node_revisions WHERE node_id = %s", (node_id,))
    revision_no = int(cur.fetchone()["max_rev"]) + 1
    cur.execute(
        """
        INSERT INTO node_revisions (id, node_id, workspace_id, revision_no, snapshot, signature, proposer_type, proposer_id, review_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            generate_id("nrev"),
            node_id,
            workspace_id,
            revision_no,
            json.dumps(snapshot, ensure_ascii=False),
            signature,
            proposer_type,
            proposer_id,
            review_id,
        ),
    )
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


def _propose_change(
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
) -> str:
    before_snapshot = None
    after_snapshot = None

    if target_node_id:
        cur.execute(f"SELECT {NODE_PUBLIC_COLUMNS} FROM memory_nodes WHERE id = %s AND workspace_id = %s", (target_node_id, ws_id))
        existing = cur.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Target node not found")
        before_snapshot = _node_row_to_snapshot(existing)

    if change_type != "delete":
        payload = dict(node_data or {})
        if change_type == "update" and before_snapshot:
            payload = {**before_snapshot, **payload}
        payload["tags"] = list(payload.get("tags") or [])
        after_snapshot = _prepare_node_data(payload, payload.get("author") or proposer_id or "system", payload.get("source_type", proposer_type))
        after_snapshot = {field: after_snapshot[field] for field in NODE_EDITABLE_FIELDS} | {
            "author": payload.get("author") or proposer_id,
            "source_type": payload.get("source_type", proposer_type),
            "signature": after_snapshot["signature"],
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
            review_id,
            ws_id,
            change_type,
            target_node_id,
            json.dumps(before_snapshot, ensure_ascii=False) if before_snapshot is not None else None,
            json.dumps(after_snapshot or {}, ensure_ascii=False),
            json.dumps(diff_summary, ensure_ascii=False),
            json.dumps(suggested_edges or [], ensure_ascii=False),
            source_info,
            proposer_type,
            proposer_id,
            json.dumps(proposer_meta or {}, ensure_ascii=False) if proposer_meta is not None else None,
            confidence_score,
            source_id,
        ),
    )
    return review_id


async def _bg_embed_node(ws_id: str, node_id: str, text: str, user_id: str):
    # Fetch workspace-locked embedding model
    with db_cursor() as cur:
        cur.execute("SELECT embedding_model FROM workspaces WHERE id = %s", (ws_id,))
        row = cur.fetchone()
    ws_embedding_model = row["embedding_model"] if row else None

    try:
        resolved = resolve_provider(user_id, "embedding", preferred_model=ws_embedding_model)
        vector, tokens = await embed(resolved, text)
        with db_cursor(commit=True) as cur:
            cur.execute("UPDATE memory_nodes SET embedding = %s WHERE id = %s AND workspace_id = %s", (vector, node_id, ws_id))
        record_usage(resolved, "embedding", tokens, ws_id, node_id)
    except Exception as exc:
        print(f"BG Embedding failed for node {node_id}: {exc}")


def _bg_suggest_edges(ws_id: str, node_id: str, user_id: str):
    """After a node is created, find semantically similar nodes and propose edges via review_queue."""
    import time
    # Wait briefly for the embedding background task to likely finish
    time.sleep(3)
    try:
        with db_cursor() as cur:
            cur.execute("SELECT embedding FROM memory_nodes WHERE id = %s AND workspace_id = %s", (node_id, ws_id))
            row = cur.fetchone()
            if not row or row["embedding"] is None:
                return

        with db_cursor() as cur:
            cur.execute("SELECT content_type FROM memory_nodes WHERE id = %s", (node_id,))
            node_row = cur.fetchone()
            content_type = node_row["content_type"] if node_row else "factual"

            cur.execute(
                """
                SELECT id, content_type, (1 - (embedding <=> %s::vector)) AS sim
                FROM memory_nodes
                WHERE workspace_id = %s AND id != %s
                  AND embedding IS NOT NULL AND status IN ('active', 'answered', 'answered-low-trust')
                  AND content_type != 'source_document'
                ORDER BY sim DESC
                LIMIT 5
                """,
                (row["embedding"], ws_id, node_id),
            )
            candidates = [r for r in cur.fetchall() if r["sim"] > 0.70]

        if not candidates:
            return

        with db_cursor(commit=True) as cur:
            for c in candidates:
                try:
                    relation = "related_to"
                    # P4.5-3A-7: Use similar_to for inquiries if similarity < 0.88
                    if content_type == "inquiry" and c["content_type"] == "inquiry":
                        if c["sim"] < 0.88: # FAQ_CACHE_HIT threshold
                            relation = "similar_to"
                        else:
                            continue # Skip if it would hit FAQ cache (handled elsewhere or by search)

                    _propose_change(
                        cur, ws_id, "create_edge", None,
                        {"from_id": node_id, "to_id": c["id"],
                         "relation": relation, "weight": round(float(c["sim"]), 2)},
                        "ai", user_id,
                        {"source": "auto_edge_suggestion"},
                        source_info=f"Auto-suggested edge (similarity={c['sim']:.2f})",
                    )
                except Exception:
                    pass  # Skip if duplicate or other constraint
    except Exception as exc:
        print(f"BG Edge suggestion failed for node {node_id}: {exc}")


async def _bg_clone_workspace(job_id: str, source_ws_id: str, target_ws_id: str, user_id: str):
    """
    Background worker for cloning a workspace.
    1. Copies nodes and edges.
    2. Re-embeds nodes if the target workspace has a different model/dimension.
    """
    try:
        # Update job to running
        with db_cursor(commit=True) as cur:
            cur.execute("UPDATE workspace_clone_jobs SET status = 'running' WHERE id = %s", (job_id,))

        # Fetch workspace embedding locks
        with db_cursor() as cur:
            cur.execute("SELECT embedding_model, embedding_dim FROM workspaces WHERE id = %s", (source_ws_id,))
            source_ws = cur.fetchone()
            cur.execute("SELECT embedding_model, embedding_dim FROM workspaces WHERE id = %s", (target_ws_id,))
            target_ws = cur.fetchone()

        if not source_ws or not target_ws:
            raise Exception("Source or target workspace not found")

        needs_reembed = (source_ws["embedding_model"] != target_ws["embedding_model"] or 
                         source_ws["embedding_dim"] != target_ws["embedding_dim"])

        # Copy Nodes
        node_map = {} # old_id -> new_id
        with db_cursor() as cur:
            cur.execute("SELECT * FROM memory_nodes WHERE workspace_id = %s", (source_ws_id,))
            source_nodes = cur.fetchall()

        with db_cursor(commit=True) as cur:
            cur.execute("UPDATE workspace_clone_jobs SET total_nodes = %s WHERE id = %s", (len(source_nodes), job_id))

        for i, node in enumerate(source_nodes):
            # ── P4.1-F: Cancellation check ─────────────────────────────────────
            # The user may call POST /clone-jobs/{job_id}/cancel which sets
            # status='cancelling'.  We honour that before processing each node.
            with db_cursor() as cur:
                cur.execute("SELECT status FROM workspace_clone_jobs WHERE id = %s", (job_id,))
                job_row = cur.fetchone()
            if job_row and job_row["status"] == "cancelling":
                with db_cursor(commit=True) as cur:
                    cur.execute(
                        "UPDATE workspace_clone_jobs SET status='cancelled', cancelled_at=now() WHERE id=%s",
                        (job_id,)
                    )
                print(f"Clone job {job_id} was cancelled by user after {i} nodes.")
                return
            # ───────────────────────────────────────────────────────────────────

            new_node_id = generate_id("mem")
            node_map[node["id"]] = new_node_id

            # Prepare new node data
            # If re-embedding is needed, we insert with null embedding first
            embedding = node["embedding"] if not needs_reembed else None

            with db_cursor(commit=True) as cur:
                cur.execute(
                    """
                    INSERT INTO memory_nodes (
                        id, workspace_id, title_zh, title_en, content_type, content_format,
                        body_zh, body_en, tags, visibility, author, trust_score,
                        dim_accuracy, dim_freshness, dim_utility, dim_author_rep,
                        traversal_count, unique_traverser_count, created_at, updated_at,
                        signature, source_type, status, archived_at, embedding,
                        validity_confirmed_at, validity_confirmed_by
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    """,
                    (
                        new_node_id, target_ws_id, node["title_zh"], node["title_en"],
                        node["content_type"], node["content_format"], node["body_zh"],
                        node["body_en"], node["tags"], node["visibility"], node["author"],
                        node["trust_score"], node["dim_accuracy"], node["dim_freshness"],
                        node["dim_utility"], node["dim_author_rep"], node["traversal_count"],
                        node["unique_traverser_count"], node["created_at"], node["updated_at"],
                        node["signature"], node["source_type"], node["status"],
                        node["archived_at"], embedding, node["validity_confirmed_at"],
                        node["validity_confirmed_by"]
                    )
                )

            # Re-embed if necessary
            if needs_reembed:
                text = f"{node['title_zh']} {node['title_en']} {node['body_zh']} {node['body_en']}"
                try:
                    resolved = resolve_provider(user_id, "embedding", preferred_model=target_ws["embedding_model"])
                    vector, tokens = await embed(resolved, text)
                    with db_cursor(commit=True) as cur:
                        cur.execute("UPDATE memory_nodes SET embedding = %s WHERE id = %s", (vector, new_node_id))
                        record_usage(resolved, "embedding", tokens, workspace_id=target_ws_id, node_id=new_node_id)
                except Exception as e:
                    print(f"Clone re-embed failed for node {new_node_id}: {e}")

            # Update progress
            with db_cursor(commit=True) as cur:
                cur.execute("UPDATE workspace_clone_jobs SET processed_nodes = %s WHERE id = %s", (i + 1, job_id))

        # Copy Edges
        with db_cursor() as cur:
            cur.execute("SELECT * FROM edges WHERE workspace_id = %s", (source_ws_id,))
            source_edges = cur.fetchall()

        with db_cursor(commit=True) as cur:
            for edge in source_edges:
                # Only copy if both nodes were successfully mapped
                new_from = node_map.get(edge["from_id"])
                new_to   = node_map.get(edge["to_id"])
                if not new_from or not new_to:
                    continue

                new_edge_id = generate_id("edge")
                cur.execute(
                    """
                    INSERT INTO edges (
                        id, workspace_id, from_id, to_id, relation, weight,
                        co_access_count, last_co_accessed, half_life_days,
                        min_weight, traversal_count, rating_sum, rating_count,
                        status, pinned, created_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    """,
                    (
                        new_edge_id, target_ws_id, new_from, new_to, edge["relation"],
                        edge["weight"], edge["co_access_count"], edge["last_co_accessed"],
                        edge["half_life_days"], edge["min_weight"], edge["traversal_count"],
                        edge["rating_sum"], edge["rating_count"], edge["status"],
                        edge["pinned"], edge["created_at"]
                    )
                )

        # Mark job as completed
        with db_cursor(commit=True) as cur:
            cur.execute("UPDATE workspace_clone_jobs SET status = 'completed' WHERE id = %s", (job_id,))

    except Exception as e:
        print(f"Clone job {job_id} failed: {e}")
        with db_cursor(commit=True) as cur:
            cur.execute("UPDATE workspace_clone_jobs SET status = 'failed', error_msg = %s WHERE id = %s", (str(e), job_id))


@router.post("/workspaces/{ws_id}/clone", response_model=WorkspaceCloneJobResponse)
def clone_workspace(ws_id: str, body: WorkspaceCloneRequest, background_tasks: BackgroundTasks, user: dict = Depends(get_current_user)):
    """
    Start a background job to clone a workspace.
    Creates a new target workspace first.
    """
    with db_cursor(commit=True) as cur:
        # Check source workspace access
        source = _require_ws_access(cur, ws_id, user)
        
        # Determine target workspace properties
        name_zh = body.name_zh or f"{source['name_zh']} (副本)"
        name_en = body.name_en or f"{source['name_en']} (Clone)"
        
        # New embedding model locking
        new_model = body.new_embedding_model
        if new_model:
            new_dim = _get_embedding_dim(new_model)
        else:
            new_model = source["embedding_model"]
            new_dim   = source["embedding_dim"]

        # Visibility — default to private for clones
        new_visibility = body.visibility if body.visibility in VALID_KB_VIS else "private"

        # 1. Create target workspace
        target_ws_id = generate_id("ws")
        cur.execute(
            """
            INSERT INTO workspaces (
                id, name_zh, name_en, visibility, kb_type, owner_id,
                archive_window_days, min_traversals, embedding_model, embedding_dim
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                target_ws_id, name_zh, name_en, new_visibility, source["kb_type"],
                user["sub"], source["archive_window_days"], source["min_traversals"],
                new_model, new_dim
            ),
        )

        # 2. Create clone job
        job_id = generate_id("cln")
        cur.execute(
            """
            INSERT INTO workspace_clone_jobs (id, source_ws_id, target_ws_id, status)
            VALUES (%s, %s, %s, 'pending')
            RETURNING *
            """,
            (job_id, ws_id, target_ws_id),
        )
        job = cur.fetchone()

        background_tasks.add_task(_bg_clone_workspace, job_id, ws_id, target_ws_id, user["sub"])
        return job


@router.get("/workspaces/{ws_id}/clone-status", response_model=Optional[WorkspaceCloneJobResponse])
def get_clone_status(ws_id: str, user: dict = Depends(get_current_user)):
    """Return the most recent clone job for this workspace (as target)."""
    with db_cursor() as cur:
        cur.execute(
            "SELECT * FROM workspace_clone_jobs WHERE target_ws_id = %s ORDER BY created_at DESC LIMIT 1",
            (ws_id,)
        )
        return cur.fetchone()


# ── P4.1-F: Fork public workspace ─────────────────────────────────────────────

@router.post("/workspaces/{ws_id}/fork", response_model=WorkspaceCloneJobResponse, status_code=202)
def fork_workspace(
    ws_id: str,
    body: ForkWorkspaceRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
):
    """
    Fork any readable workspace (including public ones the user doesn't own).
    Creates a private copy under the current user, then re-embeds all nodes
    in the background using the chosen (or inherited) embedding model.
    """
    with db_cursor(commit=True) as cur:
        # Only read access needed — public workspace anyone can fork
        source = _require_ws_access(cur, ws_id, user, write=False)

        # Determine embedding model for the new workspace
        new_model = body.embedding_model or source["embedding_model"]
        new_dim   = _get_embedding_dim(new_model)

        # Create target workspace owned by the current user (always private)
        target_ws_id = generate_id("ws")
        cur.execute(
            """
            INSERT INTO workspaces (
                id, name_zh, name_en, visibility, kb_type, owner_id,
                archive_window_days, min_traversals, embedding_model, embedding_dim
            )
            VALUES (%s, %s, %s, 'private', %s, %s, %s, %s, %s, %s)
            """,
            (
                target_ws_id, body.name_zh, body.name_en,
                source["kb_type"], user["sub"],
                source["archive_window_days"], source["min_traversals"],
                new_model, new_dim,
            ),
        )

        # Create clone job with is_fork = TRUE
        job_id = generate_id("cln")
        cur.execute(
            """
            INSERT INTO workspace_clone_jobs
              (id, source_ws_id, target_ws_id, status, is_fork)
            VALUES (%s, %s, %s, 'pending', TRUE)
            RETURNING *
            """,
            (job_id, ws_id, target_ws_id),
        )
        job = cur.fetchone()

    background_tasks.add_task(_bg_clone_workspace, job_id, ws_id, target_ws_id, user["sub"])
    return job


@router.post("/clone-jobs/{job_id}/cancel", status_code=204)
def cancel_clone_job(job_id: str, user: dict = Depends(get_current_user)):
    """
    Request cancellation of a running clone/fork job.
    Sets status to 'cancelling'; the background worker will notice and stop,
    then transition the status to 'cancelled'.
    """
    with db_cursor(commit=True) as cur:
        # Verify the job exists and the caller owns the target workspace
        cur.execute(
            """
            SELECT cj.id, cj.status, w.owner_id
            FROM workspace_clone_jobs cj
            JOIN workspaces w ON w.id = cj.target_ws_id
            WHERE cj.id = %s
            """,
            (job_id,),
        )
        job = cur.fetchone()
        if not job:
            raise HTTPException(status_code=404, detail="Clone job not found")
        if job["owner_id"] != user["sub"]:
            raise HTTPException(status_code=403, detail="Only the target workspace owner can cancel this job")
        if job["status"] not in ("pending", "running"):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel a job that is already '{job['status']}'",
            )

        cur.execute(
            "UPDATE workspace_clone_jobs SET status = 'cancelling' WHERE id = %s",
            (job_id,),
        )


# ── Re-embed all nodes ────────────────────────────────────────────────────────

@router.post("/workspaces/{ws_id}/reembed-all", status_code=202)
async def reembed_all_nodes(
    ws_id: str,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
):
    """
    Queue re-embedding for every active node in the workspace that currently
    lacks an embedding vector.  Useful when the KB was imported without
    embeddings, or when earlier embedding jobs failed.
    """
    with db_cursor() as cur:
        cur.execute("SELECT owner_id FROM workspaces WHERE id = %s", (ws_id,))
        ws = cur.fetchone()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if ws["owner_id"] != user["sub"]:
        raise HTTPException(status_code=403, detail="Only the workspace owner can trigger re-embedding")

    with db_cursor() as cur:
        cur.execute(
            """
            SELECT id, title_zh, title_en, body_zh, body_en
            FROM memory_nodes
            WHERE workspace_id = %s AND embedding IS NULL AND status = 'active'
            """,
            (ws_id,),
        )
        nodes_to_embed = cur.fetchall()

    count = len(nodes_to_embed)
    for node in nodes_to_embed:
        text = (
            f"{node['title_zh']}\n{node['title_en']}\n"
            f"{node['body_zh']}\n{node['body_en']}"
        )
        background_tasks.add_task(_bg_embed_node, ws_id, node["id"], text, user["sub"])

    return {"queued": count}


@router.get("/workspaces", response_model=list[WorkspaceResponse])
def list_workspaces(search: Optional[str] = Query(None), user: Optional[dict] = Depends(get_current_user_optional)):
    with db_cursor() as cur:
        uid = user["sub"] if user else None
        
        if uid:
            # Authenticated user
            filters = [
                """
                (
                    w.owner_id = %s
                    OR w.id IN (SELECT workspace_id FROM workspace_members WHERE user_id = %s)
                    OR w.visibility = 'public'
                )
                """
            ]
            params = [uid, uid]
            query_params = [uid, uid] + params
        else:
            # Anonymous user
            filters = ["w.visibility = 'public'"]
            params = []
            query_params = [None, None]

        if search:
            filters.append("(w.name_zh ILIKE %s OR w.name_en ILIKE %s)")
            like = f"%{search}%"
            query_params.extend([like, like])

        cur.execute(
            f"""
            SELECT w.*,
                   CASE WHEN w.owner_id = %s THEN 'admin'
                        ELSE wm.role::text
                   END AS my_role
            FROM workspaces w
            LEFT JOIN workspace_members wm ON wm.workspace_id = w.id AND wm.user_id = %s
            WHERE {' AND '.join(filters)}
            ORDER BY w.updated_at DESC
            """,
            query_params,
        )
        return cur.fetchall()




@router.post("/workspaces", response_model=WorkspaceResponse, status_code=201)
def create_workspace(body: WorkspaceCreate, user: dict = Depends(get_current_user)):
    if body.visibility not in VALID_KB_VIS:
        raise HTTPException(status_code=400, detail="Invalid visibility")
    
    # Resolve embedding model for locking.
    # P4.1-E: if the caller explicitly chose a model, honour it; otherwise auto-resolve.
    if body.embedding_model:
        embedding_model = body.embedding_model
        embedding_dim   = _get_embedding_dim(embedding_model)
    else:
        try:
            resolved = resolve_provider(user["sub"], "embedding")
            embedding_model = resolved.model
            embedding_dim   = _get_embedding_dim(embedding_model)
        except AIProviderUnavailable:
            embedding_model = "text-embedding-3-small"
            embedding_dim   = 1536

    ws_id = generate_id("ws")
    with db_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO workspaces (
                id, name_zh, name_en, visibility, kb_type, owner_id, 
                archive_window_days, min_traversals, embedding_model, embedding_dim, qa_archive_mode
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (
                ws_id, body.name_zh, body.name_en, body.visibility, body.kb_type, 
                user["sub"], body.archive_window_days, body.min_traversals,
                embedding_model, embedding_dim, body.qa_archive_mode
            ),
        )
        res = cur.fetchone()
        
        # P4.5-1B-0: Create Workspace Agent node
        from core.agent import get_or_create_agent_node
        get_or_create_agent_node(ws_id, cur)
        
        return {**dict(res), "my_role": "admin"}


@router.get("/workspaces/{ws_id}/decay-stats")
def get_decay_stats(ws_id: str, user: dict = Depends(get_current_user)):
    """Admin-only: return decay job status and edge weight distribution for a workspace."""
    with db_cursor() as cur:
        ws = _require_ws_access(cur, ws_id, user)
        role = _get_effective_role(cur, ws_id, ws["owner_id"], user["sub"])
        if role not in ("admin",):
            raise HTTPException(status_code=403, detail="Admin only")

        cur.execute("SELECT value FROM system_state WHERE key = 'last_decay_at'")
        state_row = cur.fetchone()
        last_decay_at = state_row["value"] if state_row else None

        cur.execute(
            "SELECT COUNT(*) FROM edges WHERE workspace_id = %s AND status = 'faded'",
            (ws_id,),
        )
        faded_count = cur.fetchone()["count"]

        cur.execute(
            "SELECT COUNT(*) FROM edges WHERE workspace_id = %s AND status = 'active' AND weight < 0.2",
            (ws_id,),
        )
        low_weight_count = cur.fetchone()["count"]

    return {
        "last_decay_at": last_decay_at,
        "faded_edge_count": faded_count,
        "low_weight_edge_count": low_weight_count,
    }


@router.get("/workspaces/{ws_id}/graph-preview", response_model=GraphPreviewResponse)
def get_graph_preview(ws_id: str):
    with db_cursor() as cur:
        cur.execute("SELECT visibility FROM workspaces WHERE id = %s", (ws_id,))
        ws = cur.fetchone()
        if not ws:
            raise HTTPException(status_code=404, detail="Workspace not found")
        if ws["visibility"] not in ("public", "conditional_public"):
            raise HTTPException(status_code=403, detail="Graph preview only available for public/conditional_public workspaces")
        cur.execute("SELECT id, content_type FROM memory_nodes WHERE workspace_id = %s AND status = 'active'", (ws_id,))
        nodes = cur.fetchall()
        cur.execute("SELECT from_id, to_id, relation FROM edges WHERE workspace_id = %s AND status = 'active'", (ws_id,))
        edges = cur.fetchall()
        id_map = {node["id"]: _preview_id(node["id"]) for node in nodes}
        return {
            "nodes": [{"preview_id": id_map[n["id"]], "content_type": n["content_type"]} for n in nodes],
            "edges": [
                {"from_preview_id": id_map[e["from_id"]], "to_preview_id": id_map[e["to_id"]], "relation": e["relation"]}
                for e in edges
                if e["from_id"] in id_map and e["to_id"] in id_map
            ],
        }


@router.patch("/workspaces/{ws_id}", response_model=WorkspaceResponse)
def update_workspace(ws_id: str, body: WorkspaceUpdate, user: dict = Depends(get_current_user)):
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT * FROM workspaces WHERE id = %s", (ws_id,))
        ws = cur.fetchone()
        if not ws:
            raise HTTPException(status_code=404, detail="Workspace not found")
        if ws["owner_id"] != user["sub"]:
            raise HTTPException(status_code=403, detail="Only workspace owner can update settings")
        updates = body.model_dump(exclude_unset=True)
        if not updates:
            return ws
        if "visibility" in updates and updates["visibility"] not in VALID_KB_VIS:
            raise HTTPException(status_code=400, detail="Invalid visibility")
        set_clause = ", ".join(f"{k} = %s" for k in updates)
        cur.execute(f"UPDATE workspaces SET {set_clause} WHERE id = %s RETURNING *", list(updates.values()) + [ws_id])
        return cur.fetchone()


@router.get("/workspaces/{ws_id}/associations", response_model=list[WorkspaceAssociationResponse])
def list_associations(ws_id: str, user: dict = Depends(get_current_user)):
    with db_cursor() as cur:
        _require_ws_access(cur, ws_id, user)
        cur.execute(
            """
            SELECT a.*, w.name_en AS target_name_en, w.name_zh AS target_name_zh
            FROM workspace_associations a
            JOIN workspaces w ON a.target_ws_id = w.id
            WHERE a.source_ws_id = %s
            """,
            (ws_id,),
        )
        return cur.fetchall()


@router.post("/workspaces/{ws_id}/associations/{target_ws_id}", response_model=WorkspaceAssociationResponse)
def create_association(ws_id: str, target_ws_id: str, user: dict = Depends(get_current_user)):
    if ws_id == target_ws_id:
        raise HTTPException(status_code=400, detail="Cannot associate a workspace with itself")
    with db_cursor(commit=True) as cur:
        _require_ws_access(cur, ws_id, user)
        _require_ws_access(cur, target_ws_id, user)
        assoc_id = generate_id("asc")
        cur.execute(
            """
            INSERT INTO workspace_associations (id, source_ws_id, target_ws_id)
            VALUES (%s, %s, %s)
            ON CONFLICT (source_ws_id, target_ws_id) DO UPDATE SET created_at = now()
            RETURNING id, source_ws_id, target_ws_id, created_at
            """,
            (assoc_id, ws_id, target_ws_id),
        )
        row = cur.fetchone()
        cur.execute("SELECT name_en, name_zh FROM workspaces WHERE id = %s", (target_ws_id,))
        names = cur.fetchone()
        return {**dict(row), "target_name_en": names["name_en"], "target_name_zh": names["name_zh"]}


@router.delete("/workspaces/{ws_id}/associations/{target_ws_id}", status_code=204)
def delete_association(ws_id: str, target_ws_id: str, user: dict = Depends(get_current_user)):
    with db_cursor(commit=True) as cur:
        _require_ws_access(cur, ws_id, user)
        cur.execute("DELETE FROM workspace_associations WHERE source_ws_id = %s AND target_ws_id = %s", (ws_id, target_ws_id))


@router.delete("/workspaces/{ws_id}", status_code=204)
def delete_workspace(ws_id: str, user: dict = Depends(get_current_user)):
    with db_cursor(commit=True) as cur:
        ws = _require_ws_access(cur, ws_id, user, write=True)
        if ws["owner_id"] != user["sub"]:
            raise HTTPException(
                status_code=403,
                detail="Only the workspace owner can delete it"
            )
        # CASCADE in the DB automatically clears all child tables
        cur.execute("DELETE FROM workspaces WHERE id = %s", (ws_id,))


@router.delete("/workspaces/{ws_id}/purge", response_model=WorkspacePurgeResponse)
def purge_workspace(ws_id: str, user: dict = Depends(get_current_user)):
    with db_cursor(commit=True) as cur:
        ws = _require_ws_access(cur, ws_id, user, write=True, required_scope="kb:write")
        if ws["owner_id"] != user["sub"]:
            raise HTTPException(status_code=403, detail="Only workspace owner can purge it")
        cur.execute("DELETE FROM edges WHERE workspace_id = %s", (ws_id,))
        ec = cur.rowcount
        cur.execute("DELETE FROM memory_nodes WHERE workspace_id = %s", (ws_id,))
        nc = cur.rowcount
        cur.execute("DELETE FROM review_queue WHERE workspace_id = %s", (ws_id,))
        cur.execute("DELETE FROM node_revisions WHERE workspace_id = %s", (ws_id,))
        cur.execute("DELETE FROM ingest_jobs WHERE workspace_id = %s", (ws_id,))
        return {"deleted_nodes_count": nc, "deleted_edges_count": ec}


@router.post("/workspaces/{ws_id}/nodes/{node_id}/vote-trust")
def vote_trust(ws_id: str, node_id: str, body: VoteTrustRequest, user: dict = Depends(get_current_user)):
    if not (1 <= body.accuracy <= 5 and 1 <= body.utility <= 5):
        raise HTTPException(status_code=400, detail="Scores must be between 1 and 5")
        
    with db_cursor(commit=True) as cur:
        _require_ws_access(cur, ws_id, user)
        
        # Insert or update vote
        vote_id = generate_id("vote")
        cur.execute(
            """
            INSERT INTO node_trust_votes (id, workspace_id, node_id, user_id, accuracy, utility)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (node_id, user_id) 
            DO UPDATE SET accuracy = EXCLUDED.accuracy, utility = EXCLUDED.utility, created_at = NOW()
            """,
            (vote_id, ws_id, node_id, user["sub"], body.accuracy, body.utility)
        )
        
        # Re-calculate dimensions and trust_score
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
        
        # Get existing freshness and author_rep
        cur.execute("SELECT dim_freshness, dim_author_rep FROM memory_nodes WHERE id = %s", (node_id,))
        node = cur.fetchone()
        if not node:
             raise HTTPException(status_code=404, detail="Node not found")
             
        freshness = float(node["dim_freshness"])
        author_rep = float(node["dim_author_rep"])
        
        # trust_score = (accuracy * 0.4) + (utility * 0.25) + (freshness * 0.25) + (author_rep * 0.1)
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


@router.get("/workspaces/{ws_id}", response_model=WorkspaceResponse)
def get_workspace(ws_id: str, user: dict = Depends(get_current_user_optional)):
    with db_cursor() as cur:
        _require_ws_access(cur, ws_id, user)
        cur.execute("SELECT * FROM workspaces WHERE id = %s", (ws_id,))
        return cur.fetchone()


@router.get("/workspaces/{workspace_id}/nodes/{node_id}/neighborhood")
async def get_neighborhood(
    workspace_id: str,
    node_id: str,
    depth: int = Query(2, ge=1, le=3),
    relation: Optional[str] = None,
    direction: Literal["both", "outbound", "inbound"] = "both",
    include_source: bool = Query(True),
    current_user = Depends(get_current_user_optional),
):
    with db_cursor() as cur:
        workspace = _require_ws_access(cur, workspace_id, current_user)
        
        viewer_id = current_user["sub"] if current_user else None
        viewer_role = _get_effective_role(cur, workspace_id, workspace["owner_id"], viewer_id)

        result = _bfs_neighborhood(
            cur, workspace_id, node_id, depth, relation, direction,
            include_source=include_source,
            viewer_role=viewer_role,
            viewer_id=viewer_id,
        )

        return result


@router.get("/workspaces/{ws_id}/nodes", response_model=list[NodeResponse])
def list_nodes(
    ws_id: str,
    q: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    content_type: Optional[str] = Query(None),
    limit: int = Query(50, description="Use a large number for unlimited"),
    offset: int = Query(0),
    status: str = Query("active"),
    filter: Optional[str] = Query(None, description="orphan | faded | never_traversed"),
    include_source: bool = Query(False, description="Include source_document nodes"),
    user: dict = Depends(get_current_user_optional),
):
    with db_cursor() as cur:
        ws = _require_ws_access(cur, ws_id, user)
        filters = ["workspace_id = %s"]
        params: list = [ws_id]

        # A4: Special filter modes override the status filter
        if filter == "orphan":
            filters.append(
                "NOT EXISTS ("
                "SELECT 1 FROM edges e "
                "WHERE e.status = 'active' AND (e.from_id = memory_nodes.id OR e.to_id = memory_nodes.id)"
                ")"
            )
        elif filter == "faded":
            # Nodes where every connected active/faded edge is faded (no active edges)
            filters.append(
                "NOT EXISTS ("
                "SELECT 1 FROM edges e "
                "WHERE e.status = 'active' AND (e.from_id = memory_nodes.id OR e.to_id = memory_nodes.id)"
                ") AND EXISTS ("
                "SELECT 1 FROM edges e2 "
                "WHERE e2.status = 'faded' AND (e2.from_id = memory_nodes.id OR e2.to_id = memory_nodes.id)"
                ")"
            )
        elif filter == "never_traversed":
            filters.append("traversal_count = 0")
        elif filter == "empty_body":
            filters.append(
                "(body_zh IS NULL OR body_zh = '') AND (body_en IS NULL OR body_en = '')"
            )
        else:
            if status != "all":
                filters.append("status = %s")
                params.append(status)

        if q:
            _apply_text_search(filters, params, q)
        if tag:
            filters.append("%s = ANY(tags)")
            params.append(tag)
        if content_type:
            filters.append("content_type = %s")
            params.append(content_type)
        # C4: exclude source_document nodes by default
        if not include_source and not content_type:
            filters.append("content_type != 'source_document'")
        params += [limit, offset]
        cur.execute(f"SELECT {NODE_PUBLIC_COLUMNS} FROM memory_nodes WHERE {' AND '.join(filters)} ORDER BY created_at DESC LIMIT %s OFFSET %s", params)
        rows = cur.fetchall()  # fetchall BEFORE any further cur.execute calls
        role = _get_effective_role(cur, ws_id, ws["owner_id"], user["sub"] if user else None)
        return [_strip_body_if_viewer(row, role) for row in rows]


@router.get("/workspaces/{ws_id}/table-view", response_model=TableViewResponse)
def get_table_view(
    ws_id: str, 
    q: Optional[str] = Query(None),
    filter: Optional[str] = Query(None),
    sort_by: Optional[str] = Query("created_at"),
    order: Optional[str] = Query("desc"),
    limit: int = Query(50, le=200), 
    offset: int = Query(0), 
    user: dict = Depends(get_current_user_optional)
):
    with db_cursor() as cur:
        ws = _require_ws_access(cur, ws_id, user)
        filters = ["workspace_id = %s", "status = 'active'", "content_type != 'source_document'"]
        params = [ws_id]
        if q:
            _apply_text_search(filters, params, q)
        
        if filter == "orphan":
            filters.append("NOT EXISTS (SELECT 1 FROM edges WHERE (from_id = memory_nodes.id OR to_id = memory_nodes.id) AND status = 'active')")

        cur.execute(f"SELECT COUNT(*) FROM memory_nodes WHERE {' AND '.join(filters)}", params)
        total = cur.fetchone()["count"]
        
        # Sort logic
        sort_col = "created_at"
        if sort_by in ("title", "title_en", "title_zh"):
            sort_col = "title_en" # Fallback
        elif sort_by == "content_type":
            sort_col = "content_type"
        elif sort_by == "trust_score":
            sort_col = "trust_score"
        
        sort_order = "DESC" if order.lower() == "desc" else "ASC"
        
        params_list = list(params) + [limit, offset]
        cur.execute(f"SELECT {NODE_PUBLIC_COLUMNS} FROM memory_nodes WHERE {' AND '.join(filters)} ORDER BY {sort_col} {sort_order} LIMIT %s OFFSET %s", params_list)
        rows = cur.fetchall()
        role = _get_effective_role(cur, ws_id, ws["owner_id"], user["sub"] if user else None)
        nodes = [_strip_body_if_viewer(row, role) for row in rows]
        return {"nodes": nodes, "total_count": total}


@router.get("/workspaces/{ws_id}/nodes-search", response_model=List[NodeResponse])
def search_nodes(ws_id: str, query: str = Query(...), limit: int = 20, user: dict = Depends(get_current_user_optional)):
    with db_cursor() as cur:
        ws = _require_ws_access(cur, ws_id, user)
        filters = ["workspace_id = %s", "status = 'active'"]
        params: list = [ws_id]
        _apply_text_search(filters, params, query)
        params.append(limit)
        cur.execute(
            f"SELECT {NODE_PUBLIC_COLUMNS} FROM memory_nodes WHERE {' AND '.join(filters)} ORDER BY updated_at DESC, created_at DESC LIMIT %s",
            params,
        )
        rows = cur.fetchall()  # fetchall before _get_effective_role to avoid cursor reuse
        role = _get_effective_role(cur, ws_id, ws["owner_id"], user["sub"] if user else None)
        return [_strip_body_if_viewer(row, role) for row in rows]


@router.post("/workspaces/{ws_id}/nodes/search-semantic", response_model=List[NodeResponse])
async def search_nodes_semantic(ws_id: str, query: str, limit: int = 10, user: dict = Depends(get_current_user)):
    with db_cursor() as cur:
        _require_ws_access(cur, ws_id, user)
        cur.execute("SELECT embedding_model FROM workspaces WHERE id = %s", (ws_id,))
        ws_row = cur.fetchone()
    
    ws_model = ws_row["embedding_model"] if ws_row else None
    try:
        resolved = resolve_provider(user["sub"], "embedding", preferred_model=ws_model)
        vector, tokens = await embed(resolved, query)
        record_usage(resolved, "embedding", tokens, ws_id)
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT *, (1 - (embedding <=> %s::vector)) AS similarity
                FROM memory_nodes
                WHERE workspace_id = %s AND embedding IS NOT NULL
                ORDER BY similarity DESC
                LIMIT %s
                """,
                (vector, ws_id, limit),
            )
            return cur.fetchall()
    except AIProviderUnavailable as exc:
        raise HTTPException(status_code=402, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Embedding error: {exc}")


@router.get("/workspaces/{ws_id}/nodes/health")
def get_nodes_health(ws_id: str, user: dict = Depends(get_current_user_optional)):
    """Return content quality stats for a workspace (viewer+ role required)."""
    with db_cursor() as cur:
        _require_ws_access(cur, ws_id, user)
        cur.execute(
            """
            SELECT
              COUNT(*) FILTER (WHERE status = 'active')                                       AS total,
              COUNT(*) FILTER (WHERE status = 'active'
                                 AND (body_zh IS NULL OR body_zh = '')
                                 AND (body_en IS NULL OR body_en = ''))                        AS empty_body,
              COUNT(*) FILTER (WHERE status = 'active'
                                 AND (
                                   ((body_zh IS NULL OR body_zh = '') AND (body_en IS NOT NULL AND body_en != ''))
                                   OR
                                   ((body_en IS NULL OR body_en = '') AND (body_zh IS NOT NULL AND body_zh != ''))
                                 ))                                                            AS single_language_only,
              COUNT(*) FILTER (WHERE status = 'active' AND trust_score < 0.3)                 AS low_trust,
              COUNT(*) FILTER (WHERE status = 'active' AND embedding IS NULL)                 AS no_embedding
            FROM memory_nodes
            WHERE workspace_id = %s
            """,
            (ws_id,),
        )
        row = cur.fetchone()
        # Orphan count: active nodes with no active edges
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


@router.post("/workspaces/{ws_id}/nodes/backfill-embeddings")
async def backfill_embeddings(ws_id: str, background_tasks: BackgroundTasks, user: dict = Depends(get_current_user)):
    """Admin-only: queue embedding computation for all nodes missing embeddings."""
    with db_cursor() as cur:
        ws = _require_ws_access(cur, ws_id, user, write=True, required_scope="kb:write")
        role = _get_effective_role(cur, ws_id, ws["owner_id"], user["sub"])
        if role not in ("admin",):
            raise HTTPException(status_code=403, detail="Admin only")
        cur.execute(
            "SELECT id, title_zh, title_en, body_zh, body_en FROM memory_nodes "
            "WHERE workspace_id = %s AND embedding IS NULL AND status = 'active'",
            (ws_id,),
        )
        rows = cur.fetchall()
    for row in rows:
        text = " ".join(filter(None, [row["title_zh"], row["title_en"], row["body_zh"], row["body_en"]]))
        background_tasks.add_task(_bg_embed_node, ws_id, row["id"], text, user["sub"])
    return {"queued": len(rows)}


@router.post("/workspaces/{ws_id}/nodes/{node_id}/suggest-edges")
def suggest_edges_for_node(ws_id: str, node_id: str, user: dict = Depends(get_current_user)):
    """Admin-only: manually trigger edge suggestions for a specific node."""
    with db_cursor() as cur:
        ws = _require_ws_access(cur, ws_id, user, write=True, required_scope="kb:write")
        role = _get_effective_role(cur, ws_id, ws["owner_id"], user["sub"])
        if role not in ("admin",):
            raise HTTPException(status_code=403, detail="Admin only")
        cur.execute("SELECT 1 FROM memory_nodes WHERE id = %s AND workspace_id = %s", (node_id, ws_id))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Node not found")

    # Run synchronously (small operation) and count proposals created
    proposed = 0
    try:
        with db_cursor() as cur:
            cur.execute("SELECT embedding FROM memory_nodes WHERE id = %s AND workspace_id = %s", (node_id, ws_id))
            row = cur.fetchone()
        if row and row["embedding"] is not None:
            with db_cursor() as cur:
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
            with db_cursor(commit=True) as cur:
                for c in candidates:
                    try:
                        _propose_change(
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
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Edge suggestion failed: {exc}")
    return {"proposed": proposed}


@router.get("/workspaces/{ws_id}/nodes/{node_id}", response_model=NodeResponse)
def get_node(ws_id: str, node_id: str, user: dict = Depends(get_current_user_optional)):
    with db_cursor() as cur:
        ws = _require_ws_access(cur, ws_id, user)
        cur.execute(f"SELECT {NODE_PUBLIC_COLUMNS} FROM memory_nodes WHERE id = %s AND workspace_id = %s", (node_id, ws_id))
        node = cur.fetchone()
        if not node:
            raise HTTPException(status_code=404, detail="Node not found")
        role = _get_effective_role(cur, ws_id, ws["owner_id"], user["sub"] if user else None)
        return _strip_body_if_viewer(node, role)


@router.post("/workspaces/{ws_id}/nodes", response_model=NodeResponse, status_code=201)
def create_node(ws_id: str, body: NodeCreate, background_tasks: BackgroundTasks, user: dict = Depends(get_current_user)):
    payload = body.model_dump()
    _validate_node_payload(payload)
    with db_cursor(commit=True) as cur:
        ws = _require_ws_access(cur, ws_id, user, write=True, required_scope="kb:write")
        
        # D1: Verify source workspace access if copying
        if payload.get("copied_from_ws"):
            _require_ws_access(cur, payload["copied_from_ws"], user) # At least viewer access
            
        role = _get_effective_role(cur, ws_id, ws["owner_id"], user["sub"])
        proposer_id = user["sub"]
        if role == "editor":
            review_id = _propose_change(
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
            from core.ai_review import run_ai_review_for_item
            background_tasks.add_task(run_ai_review_for_item, review_id)
            return JSONResponse(status_code=202, content={"review_id": review_id, "detail": "Your new node has been submitted for review"})

        node = _create_node_in_db(cur, ws_id, payload | {"author": proposer_id, "source_type": payload.get("source_type", "human")})
        _create_edges_directly(cur, ws_id, node["id"], payload.get("suggested_edges", []))
        _write_node_revision(cur, node["id"], ws_id, _node_row_to_snapshot(node), node["signature"], payload.get("source_type", "human"), proposer_id, None)
        background_tasks.add_task(_bg_embed_node, ws_id, node["id"], f"{node['title_zh']}\n{node['title_en']}\n{node['body_zh']}\n{node['body_en']}", user["sub"])
        background_tasks.add_task(_bg_suggest_edges, ws_id, node["id"], user["sub"])
        return node


@router.patch("/workspaces/{ws_id}/nodes/{node_id}", response_model=NodeResponse)
def update_node(ws_id: str, node_id: str, body: NodeUpdate, background_tasks: BackgroundTasks, user: dict = Depends(get_current_user)):
    updates = body.model_dump(exclude_none=True)
    with db_cursor(commit=True) as cur:
        ws = _require_ws_access(cur, ws_id, user, write=True, required_scope="kb:write")
        cur.execute(f"SELECT {NODE_PUBLIC_COLUMNS} FROM memory_nodes WHERE id = %s AND workspace_id = %s", (node_id, ws_id))
        existing = cur.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Node not found")
        if not updates:
            return existing
        role = _get_effective_role(cur, ws_id, ws["owner_id"], user["sub"])
        if role == "editor":
            review_id = _propose_change(
                cur,
                ws_id,
                "update",
                node_id,
                updates,
                updates.get("source_type", "human"),
                user["sub"],
                {"source": "node_editor"},
                suggested_edges=updates.get("suggested_edges", []),
                source_info=f"Proposed edit by {user['sub']} for {node_id}",
            )
            from core.ai_review import run_ai_review_for_item
            background_tasks.add_task(run_ai_review_for_item, review_id)
            return JSONResponse(status_code=202, content={"review_id": review_id, "detail": "Your changes have been submitted for review"})

        node = _update_node_in_db(cur, ws_id, node_id, updates, user["sub"])
        _create_edges_directly(cur, ws_id, node_id, updates.get("suggested_edges", []))
        _write_node_revision(cur, node["id"], ws_id, _node_row_to_snapshot(node), node["signature"], updates.get("source_type", "human"), user["sub"], None)
        # A5: Reset dim_freshness to 1.0 and recompute trust_score on content update
        cur.execute(
            """
            UPDATE memory_nodes
            SET
                dim_freshness = 1.0,
                trust_score = (
                    dim_accuracy   * 0.30 +
                    1.0            * 0.25 +
                    dim_utility    * 0.25 +
                    dim_author_rep * 0.20
                )
            WHERE id = %s AND workspace_id = %s
            """,
            (node_id, ws_id),
        )
        return node


@router.delete("/workspaces/{ws_id}/nodes/{node_id}", status_code=204)
def delete_node(ws_id: str, node_id: str, background_tasks: BackgroundTasks, user: dict = Depends(get_current_user)):
    with db_cursor(commit=True) as cur:
        ws = _require_ws_access(cur, ws_id, user, write=True, required_scope="kb:write")
        role = _get_effective_role(cur, ws_id, ws["owner_id"], user["sub"])
        if role == "editor":
            review_id = _propose_change(
                cur,
                ws_id,
                "delete",
                node_id,
                None,
                "human",
                user["sub"],
                {"source": "node_editor"},
                source_info=f"Proposed delete by {user['sub']} for {node_id}",
            )
            from core.ai_review import run_ai_review_for_item
            background_tasks.add_task(run_ai_review_for_item, review_id)
            return JSONResponse(status_code=202, content={"review_id": review_id, "detail": "Your changes have been submitted for review"})
        _delete_node_in_db(cur, ws_id, node_id)


@router.get("/workspaces/{ws_id}/nodes/{node_id}/revisions", response_model=list[NodeRevisionMetaResponse])
def list_node_revisions(ws_id: str, node_id: str, user: dict = Depends(get_current_user_optional)):
    with db_cursor() as cur:
        _require_ws_access(cur, ws_id, user)
        cur.execute(
            """
            SELECT id, node_id, workspace_id, revision_no, signature, proposer_type, proposer_id, review_id, created_at
            FROM node_revisions
            WHERE workspace_id = %s AND node_id = %s
            ORDER BY revision_no DESC
            """,
            (ws_id, node_id),
        )
        return cur.fetchall()


@router.get("/workspaces/{ws_id}/nodes/{node_id}/revisions/{revision_no}", response_model=NodeRevisionResponse)
def get_node_revision(ws_id: str, node_id: str, revision_no: int, user: dict = Depends(get_current_user_optional)):
    with db_cursor() as cur:
        _require_ws_access(cur, ws_id, user)
        cur.execute("SELECT * FROM node_revisions WHERE workspace_id = %s AND node_id = %s AND revision_no = %s", (ws_id, node_id, revision_no))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Revision not found")
        return row


@router.get("/workspaces/{ws_id}/nodes/{node_id}/revisions/{rev_a}/diff/{rev_b}")
def diff_node_revisions(ws_id: str, node_id: str, rev_a: int, rev_b: int, user: dict = Depends(get_current_user_optional)):
    with db_cursor() as cur:
        _require_ws_access(cur, ws_id, user)
        cur.execute(
            "SELECT revision_no, snapshot FROM node_revisions WHERE workspace_id = %s AND node_id = %s AND revision_no IN (%s, %s)",
            (ws_id, node_id, rev_a, rev_b),
        )
        rows = {row["revision_no"]: row["snapshot"] for row in cur.fetchall()}
        if rev_a not in rows or rev_b not in rows:
            raise HTTPException(status_code=404, detail="Revision not found")
        return build_node_diff(rows[rev_a], rows[rev_b], "update")


@router.post("/workspaces/{ws_id}/nodes/{node_id}/revisions/{revision_no}/restore")
def restore_node_revision(ws_id: str, node_id: str, revision_no: int, background_tasks: BackgroundTasks, user: dict = Depends(get_current_user)):
    with db_cursor(commit=True) as cur:
        ws = _require_ws_access(cur, ws_id, user, write=True, required_scope="kb:write")
        cur.execute("SELECT snapshot FROM node_revisions WHERE workspace_id = %s AND node_id = %s AND revision_no = %s", (ws_id, node_id, revision_no))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Revision not found")
        role = _get_effective_role(cur, ws_id, ws["owner_id"], user["sub"])
        review_id = _propose_change(
            cur, ws_id, "update", node_id, row["snapshot"], "human", user["sub"], {"source": "restore", "revision_no": revision_no},
            source_info=f"Restore node {node_id} from revision {revision_no}"
        )
        from core.ai_review import run_ai_review_for_item
        background_tasks.add_task(run_ai_review_for_item, review_id)
        return {"review_id": review_id, "status": "pending_review"}


@router.get("/workspaces/{ws_id}/edges", response_model=list[EdgeResponse])
def list_edges(ws_id: str, node_id: Optional[str] = Query(None), user: dict = Depends(get_current_user_optional)):
    with db_cursor() as cur:
        _require_ws_access(cur, ws_id, user)
        if node_id:
            cur.execute(
                """
                SELECT *, CASE WHEN rating_count > 0 THEN ROUND(rating_sum / rating_count, 2) ELSE NULL END AS rating_avg
                FROM edges
                WHERE workspace_id = %s AND (from_id = %s OR to_id = %s)
                ORDER BY weight DESC
                """,
                (ws_id, node_id, node_id),
            )
        else:
            cur.execute(
                """
                SELECT *, CASE WHEN rating_count > 0 THEN ROUND(rating_sum / rating_count, 2) ELSE NULL END AS rating_avg
                FROM edges WHERE workspace_id = %s AND status = 'active' ORDER BY weight DESC
                """,
                (ws_id,),
            )
        return cur.fetchall()


@router.post("/workspaces/{ws_id}/edges/connect-orphans")
async def connect_orphans(ws_id: str, background_tasks: BackgroundTasks, user: dict = Depends(get_current_user)):
    """Use AI to suggest and create edges for orphan nodes (nodes with no edges)."""
    from core.ai import chat_completion, AIProviderUnavailable, AIProviderError, strip_fences
    from routers.ingest import _resolve_with_fallback

    with db_cursor() as cur:
        _require_ws_access(cur, ws_id, user, write=True, required_scope="kb:write")

        # Collect orphan nodes (only nodes with NO active edges)
        cur.execute("""
            SELECT id, title_en, title_zh, body_en, tags, content_type
            FROM memory_nodes
            WHERE workspace_id = %s AND status = 'active'
              AND content_type != 'source_document'
              AND NOT EXISTS (
                SELECT 1 FROM edges e
                WHERE e.workspace_id = %s
                  AND (e.from_id = memory_nodes.id OR e.to_id = memory_nodes.id)
                  AND e.status = 'active'
              )
            ORDER BY created_at ASC
        """, (ws_id, ws_id))
        orphans = cur.fetchall()

        if not orphans:
            return {"message": "No orphan nodes found", "edges_created": 0, "orphan_count": 0}

        # Collect anchor nodes (most connected, for AI context)
        cur.execute("""
            SELECT n.id, n.title_en, n.content_type, n.tags,
                   COUNT(e.id) as edge_count
            FROM memory_nodes n
            JOIN edges e ON e.workspace_id = n.workspace_id
              AND (e.from_id = n.id OR e.to_id = n.id)
            WHERE n.workspace_id = %s AND n.status = 'active'
              AND n.content_type != 'source_document'
            GROUP BY n.id, n.title_en, n.content_type, n.tags
            ORDER BY edge_count DESC
            LIMIT 40
        """, (ws_id,))
        anchors = cur.fetchall()

    try:
        resolved = _resolve_with_fallback(user["sub"], "extraction")
    except AIProviderUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))

    background_tasks.add_task(
        _run_connect_orphans, ws_id, orphans, anchors, resolved
    )
    return {
        "message": f"Auto-connecting {len(orphans)} orphan nodes in background",
        "orphan_count": len(orphans),
    }


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


async def _run_connect_orphans(ws_id: str, orphans: list, anchors: list, resolved):
    from core.ai import chat_completion, strip_fences
    from routers.ingest import _extract_objects_partial
    import json

    # Keep prompt short: top 20 anchors, truncated titles
    anchor_titles = [a['title_en'][:60] for a in anchors[:20] if a['title_en']]
    anchor_text = "\n".join(f"- {t}" for t in anchor_titles)

    BATCH = 3  # smaller batch = shorter prompt = reliable output
    total_created = 0

    # Pre-fetch title→id map once
    title_to_id: dict[str, str] = {}
    with db_cursor() as cur:
        cur.execute(
            "SELECT id, title_en FROM memory_nodes WHERE workspace_id = %s AND status = 'active'",
            (ws_id,)
        )
        for row in cur.fetchall():
            if row["title_en"]:
                title_to_id[row["title_en"].strip().lower()] = row["id"]

    for i in range(0, len(orphans), BATCH):
        batch = orphans[i:i + BATCH]
        orphan_items = []
        for o in batch:
            orphan_items.append(
                f"TITLE: {o['title_en'][:60]}\n"
                f"TYPE: {o['content_type']}\n"
                f"CONTEXT: {(o['body_en'] or '')[:60]}\n"
            )
        orphan_text = "\n---\n".join(orphan_items)

        prompt = (
            f"AVAILABLE ANCHOR TITLES:\n{anchor_text}\n\n"
            f"ORPHAN NODES TO CONNECT:\n{orphan_text}\n\n"
            "Generate edges connecting these orphans to anchors or other orphans. "
            "Use ONLY the exact titles listed above."
        )
        try:
            messages = [
                {"role": "system", "content": CONNECT_SYSTEM},
                {"role": "user", "content": prompt},
            ]
            raw, _ = await chat_completion(resolved, messages, max_tokens=2048, temperature=0.1)
            print(f"[connect-orphans] batch {i//BATCH} raw ({len(raw)} chars): {raw[:400]}")
            raw = strip_fences(raw)
            if not raw:
                continue

            suggestions = _extract_objects_partial(raw)
            if not suggestions:
                try:
                    parsed = json.loads(raw)
                    suggestions = parsed if isinstance(parsed, list) else [parsed]
                    suggestions = [s for s in suggestions if isinstance(s, dict)]
                except json.JSONDecodeError:
                    pass
            if not suggestions:
                print(f"[connect-orphans] batch {i//BATCH}: no suggestions parsed from: {raw[:80]}")
                continue
        except Exception as exc:
            print(f"[connect-orphans] batch {i//BATCH} AI error: {exc}")
            continue

        with db_cursor(commit=True) as cur:
            for s in suggestions:
                from_title = (s.get("from_title") or "").strip().lower()
                to_title   = (s.get("to_title") or "").strip().lower()
                relation   = s.get("relation", "related_to")
                if relation not in ("depends_on", "extends", "related_to", "contradicts"):
                    relation = "related_to"
                
                from_id = title_to_id.get(from_title)
                to_id   = title_to_id.get(to_title)
                
                if not from_id or not to_id or from_id == to_id:
                    continue

                cur.execute(
                    "SELECT 1 FROM edges WHERE workspace_id=%s AND "
                    "((from_id=%s AND to_id=%s) OR (from_id=%s AND to_id=%s)) LIMIT 1",
                    (ws_id, from_id, to_id, to_id, from_id)
                )
                if cur.fetchone():
                    continue
                cur.execute(
                    "INSERT INTO edges (id, workspace_id, from_id, to_id, relation, weight, status) "
                    "VALUES (%s, %s, %s, %s, %s, 1.0, 'active')",
                    (generate_id("edge"), ws_id, from_id, to_id, relation)
                )
                total_created += 1

    print(f"[connect-orphans] ws={ws_id} created {total_created} edges for {len(orphans)} orphans")


@router.post("/workspaces/{ws_id}/edges", response_model=EdgeResponse, status_code=201)
def create_edge(ws_id: str, body: EdgeCreate, user: dict = Depends(get_current_user)):
    if body.relation not in VALID_RELATIONS:
        raise HTTPException(status_code=400, detail="Invalid relation type")
    if body.from_id == body.to_id:
        raise HTTPException(status_code=400, detail="Cannot link a node to itself")
    if not (0.1 <= body.weight <= 1.0):
        raise HTTPException(status_code=400, detail="Weight must be between 0.1 and 1.0")
    edge_id = generate_id("edge")
    with db_cursor(commit=True) as cur:
        _require_ws_access(cur, ws_id, user, write=True, required_scope="kb:write")
        for nid in (body.from_id, body.to_id):
            cur.execute("SELECT id FROM memory_nodes WHERE id = %s AND workspace_id = %s", (nid, ws_id))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail=f"Node not found: {nid}")
        if body.half_life_days == 30:
            cur.execute("SELECT content_type FROM memory_nodes WHERE id = %s", (body.from_id,))
            row = cur.fetchone()
            if row:
                body.half_life_days = {"factual": 365, "procedural": 90, "preference": 30, "context": 14}.get(row["content_type"], 30)
        try:
            cur.execute(
                """
                INSERT INTO edges (id, workspace_id, from_id, to_id, relation, weight, half_life_days, pinned)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *, CASE WHEN rating_count > 0 THEN ROUND(rating_sum / rating_count, 2) ELSE NULL END AS rating_avg
                """,
                (edge_id, ws_id, body.from_id, body.to_id, body.relation, body.weight, body.half_life_days, body.pinned),
            )
            return cur.fetchone()
        except Exception as exc:
            if "unique_edge" in str(exc):
                raise HTTPException(status_code=409, detail="Edge with this relation already exists")
            raise


@router.post("/nodes/{node_id}/traverse", status_code=204)
def traverse_node(
    node_id: str,
    background_tasks: BackgroundTasks,
    user: dict = Depends(RequireScope("node:traverse"))
):
    """
    P4.7: Explicitly record node traversal and update trust metrics.
    Delegates to _record_traversal background task.
    """
    TraversalGuard.check(user["sub"])
    with db_cursor() as cur:
        cur.execute("SELECT workspace_id FROM memory_nodes WHERE id = %s", (node_id,))
        node_row = cur.fetchone()
        if not node_row:
            raise HTTPException(status_code=404, detail="Node not found")
        _require_ws_access(cur, node_row["workspace_id"], user)
        ws_id = node_row["workspace_id"]

    background_tasks.add_task(_record_traversal, ws_id, node_id, user["sub"])


@router.post(
    "/workspaces/{ws_id}/nodes/{node_id}/confirm-validity",
    response_model=ValidityConfirmationResponse,
)
def confirm_node_validity(ws_id: str, node_id: str, user: dict = Depends(get_current_user)):
    with db_cursor(commit=True) as cur:
        _require_ws_access(cur, ws_id, user, write=True, required_scope="kb:write")
        
        # Mark as confirmed
        cur.execute(
            """
            UPDATE memory_nodes
            SET validity_confirmed_at = NOW(),
                validity_confirmed_by = %s
            WHERE id = %s AND workspace_id = %s
            """,
            (user["email"], node_id, ws_id)
        )
        
        # C-2: Auto-vote accuracy=1.0, utility=1.0 (utility might be high, but let's use current dim_utility)
        # Actually, let's just update dim_accuracy to 1.0 and recompute.
        cur.execute("SELECT dim_freshness, dim_utility, dim_author_rep FROM memory_nodes WHERE id = %s", (node_id,))
        node = cur.fetchone()
        if not node:
            raise HTTPException(status_code=404, detail="Node not found")
            
        freshness = float(node["dim_freshness"])
        utility = float(node["dim_utility"])
        author_rep = float(node["dim_author_rep"])
        
        # Accuracy 40%, Freshness 25%, Utility 25%, Author Rep 10%
        # Confirmation mainly boosts accuracy to 1.0
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
        
        return {"confirmed_at": datetime.now(timezone.utc).isoformat(), "confirmed_by": user["email"]}


@router.post("/edges/{edge_id}/traverse", status_code=204)
def traverse_edge(edge_id: str, body: TraverseEdgeRequest, user: dict = Depends(get_current_user)):
    TraversalGuard.check(user["sub"])  # anomaly detection: 500/10m soft, 2000/10m hard-suspend
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT from_id, to_id, workspace_id FROM edges WHERE id = %s", (edge_id,))
        edge = cur.fetchone()
        if not edge:
            raise HTTPException(status_code=404, detail="Edge not found")
        # Verify the caller has read access to this edge's workspace
        _require_ws_access(cur, edge["workspace_id"], user)
        cur.execute("SELECT record_traversal(%s, %s, NULL, %s)", (edge_id, user["sub"], body.note))


@router.post("/edges/{edge_id}/rate", status_code=204)
def rate_edge(edge_id: str, body: RateEdgeRequest, user: dict = Depends(RequireScope("node:rate"))):
    if not (1 <= body.rating <= 5):
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT workspace_id FROM edges WHERE id = %s", (edge_id,))
        edge_row = cur.fetchone()
        if not edge_row:
            raise HTTPException(status_code=404, detail="Edge not found")
        # Rating affects trust scores → require workspace access (read sufficient,
        # since editor/admin already covered by RequireScope's API-key gating)
        _require_ws_access(cur, edge_row["workspace_id"], user)
        cur.execute("SELECT record_traversal(%s, %s, %s, %s)", (edge_id, user["sub"], body.rating, body.note))


def _actor_has_traversed_node(cur, node_id: str, actor_id: str) -> bool:
    cur.execute("SELECT 1 FROM traversal_log WHERE node_id = %s AND actor_id = %s", (node_id, actor_id))
    return bool(cur.fetchone())


@router.post("/internal/mcp-log", status_code=204)
def log_mcp_query(
    body: dict,
    authorization: Optional[str] = Header(default=None),
):
    if not settings.internal_service_token:
        raise HTTPException(status_code=503, detail="Internal logging token is not configured")
    if authorization != f"Bearer {settings.internal_service_token}":
        raise HTTPException(status_code=403, detail="Invalid internal service token")
    if not body.get("workspace_id") or not body.get("tool_name"):
        raise HTTPException(status_code=400, detail="workspace_id and tool_name are required")

    with db_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO mcp_query_logs (
                id, workspace_id, tool_name, query_text, result_node_count, estimated_tokens
            ) VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                generate_id("mcp"),
                body["workspace_id"],
                body["tool_name"],
                body.get("query_text"),
                int(body.get("result_node_count") or 0),
                int(body.get("estimated_tokens") or 0),
            ),
        )


@router.get("/workspaces/{ws_id}/analytics")
def get_workspace_analytics(ws_id: str, user: dict = Depends(get_current_user_optional)):
    with db_cursor() as cur:
        ws = _require_ws_access(cur, ws_id, user)
        cur.execute(
            """
            SELECT id, title_zh, title_en, trust_score, traversal_count
            FROM memory_nodes
            WHERE workspace_id = %s AND status = 'active'
            ORDER BY created_at DESC
            """,
            (ws_id,),
        )
        nodes = [dict(row) for row in cur.fetchall()]
        cur.execute(
            """
            SELECT from_id, to_id, status, last_co_accessed
            FROM edges
            WHERE workspace_id = %s
            """,
            (ws_id,),
        )
        edges = [dict(row) for row in cur.fetchall()]
        active_edges = [edge for edge in edges if edge["status"] == "active"]

        node_ids = {node["id"] for node in nodes}
        adjacency: dict[str, set[str]] = defaultdict(set)
        touched_nodes: set[str] = set()
        for edge in active_edges:
            if edge["from_id"] in node_ids and edge["to_id"] in node_ids:
                adjacency[edge["from_id"]].add(edge["to_id"])
                adjacency[edge["to_id"]].add(edge["from_id"])
                touched_nodes.add(edge["from_id"])
                touched_nodes.add(edge["to_id"])

        orphan_node_count = sum(1 for node in nodes if node["id"] not in touched_nodes)
        avg_trust_score = (
            float(sum(float(node["trust_score"]) for node in nodes) / len(nodes))
            if nodes else 0.0
        )
        faded_edge_ratio = float((len(edges) - len(active_edges)) / len(edges)) if edges else 0.0

        cur.execute(
            """
            SELECT DATE(traversed_at) AS day, COUNT(*) AS count
            FROM traversal_log
            WHERE traversed_at >= now() - INTERVAL '30 days'
              AND (
                node_id IN (
                  SELECT id FROM memory_nodes WHERE workspace_id = %s
                )
                OR edge_id IN (
                  SELECT id FROM edges WHERE workspace_id = %s
                )
              )
            GROUP BY DATE(traversed_at)
            ORDER BY day ASC
            """,
            (ws_id, ws_id),
        )
        trend_rows = cur.fetchall()
        trend_map = {row["day"].isoformat(): int(row["count"]) for row in trend_rows}

        traversal_trend = []
        monthly_traversal_count = 0
        cur.execute("SELECT CURRENT_DATE - offs AS day FROM generate_series(29, 0, -1) AS offs")
        for row in cur.fetchall():
            day_key = row["day"].isoformat()
            count = trend_map.get(day_key, 0)
            monthly_traversal_count += count
            traversal_trend.append({"date": day_key, "count": count})

        top_nodes = [
            {
                "id": node["id"],
                "title": node["title_zh"] or node["title_en"],
                "traversal_count": node["traversal_count"],
            }
            for node in sorted(nodes, key=lambda item: item["traversal_count"], reverse=True)[:5]
        ]

        kb_type_metrics: dict[str, Union[float, int]] = {}
        if ws["kb_type"] == "evergreen":
            components = 0
            visited: set[str] = set()
            for node_id in touched_nodes:
                if node_id in visited:
                    continue
                queue = deque([node_id])
                visited.add(node_id)
                size = 0
                while queue:
                    current = queue.popleft()
                    size += 1
                    for neighbor in adjacency[current]:
                        if neighbor not in visited:
                            visited.add(neighbor)
                            queue.append(neighbor)
                if size > 1:
                    components += 1
            kb_type_metrics = {
                "avg_edges_per_node": float(len(active_edges) / len(nodes)) if nodes else 0.0,
                "isolated_subgraph_count": components,
            }
        else:
            never_traversed_ratio = float(sum(1 for node in nodes if node["traversal_count"] == 0) / len(nodes)) if nodes else 0.0
            traversed_edges = [edge for edge in edges if edge.get("last_co_accessed")]
            avg_days_between_traversals = 0.0
            if traversed_edges:
                total_days = 0.0
                for edge in traversed_edges:
                    total_days += max(0.0, (datetime.now(timezone.utc) - edge["last_co_accessed"]).total_seconds() / 86400.0)
                avg_days_between_traversals = total_days / len(traversed_edges)
            kb_type_metrics = {
                "never_traversed_ratio": never_traversed_ratio,
                "avg_days_between_traversals": avg_days_between_traversals,
            }

        return {
            "total_nodes": len(nodes),
            "active_edges": len(active_edges),
            "orphan_node_count": orphan_node_count,
            "avg_trust_score": avg_trust_score,
            "faded_edge_ratio": faded_edge_ratio,
            "monthly_traversal_count": monthly_traversal_count,
            "top_nodes": top_nodes,
            "kb_type": ws["kb_type"],
            "kb_type_metrics": kb_type_metrics,
            "traversal_trend": traversal_trend,
        }


@router.get("/workspaces/{ws_id}/stats/top-gaps")
def get_top_gaps(ws_id: str, user: dict = Depends(get_current_user_optional)):
    """Return top 10 unanswered or low-trust inquiries sorted by ask_count."""
    with db_cursor() as cur:
        _require_ws_access(cur, ws_id, user)
        cur.execute(
            """
            SELECT id, title_zh, title_en, status, ask_count
            FROM memory_nodes
            WHERE workspace_id = %s
              AND content_type = 'inquiry'
              AND status IN ('gap', 'answered-low-trust')
            ORDER BY ask_count DESC
            LIMIT 10
            """,
            (ws_id,),
        )
        return [dict(row) for row in cur.fetchall()]


@router.get("/workspaces/{ws_id}/analytics/token-efficiency")
def get_workspace_token_efficiency(ws_id: str, user: dict = Depends(get_current_user_optional)):
    with db_cursor() as cur:
        _require_ws_access(cur, ws_id, user)
        cur.execute(
            """
            SELECT
                COALESCE(AVG(estimated_tokens), 0) AS avg_tokens_per_query,
                COUNT(*) AS monthly_query_count
            FROM mcp_query_logs
            WHERE workspace_id = %s
              AND created_at >= now() - INTERVAL '30 days'
            """,
            (ws_id,),
        )
        query_stats = cur.fetchone()
        cur.execute(
            """
            SELECT COALESCE(SUM(LENGTH(COALESCE(body_zh, '')) + LENGTH(COALESCE(body_en, ''))), 0) AS total_chars
            FROM memory_nodes
            WHERE workspace_id = %s AND status = 'active'
            """,
            (ws_id,),
        )
        total_chars = int(cur.fetchone()["total_chars"] or 0)
        estimated_full_doc_tokens = total_chars // 4
        avg_tokens_per_query = float(query_stats["avg_tokens_per_query"] or 0)
        savings_ratio = 0.0
        if estimated_full_doc_tokens > 0:
            savings_ratio = max(0.0, min(1.0, 1 - (avg_tokens_per_query / estimated_full_doc_tokens)))
        return {
            "avg_tokens_per_query": round(avg_tokens_per_query, 2),
            "estimated_full_doc_tokens": estimated_full_doc_tokens,
            "savings_ratio": round(savings_ratio, 4),
            "monthly_query_count": int(query_stats["monthly_query_count"] or 0),
        }


# ─── A4 / D4: Archive & Restore ───────────────────────────────────────────────

class TableViewRequest(BaseModel):
    q: str


class BulkArchiveRequest(BaseModel):
    node_ids: List[str]


class BulkArchiveResponse(BaseModel):
    archived_count: int


@router.post("/workspaces/{ws_id}/nodes/bulk-archive", response_model=BulkArchiveResponse)
def bulk_archive_nodes(ws_id: str, body: BulkArchiveRequest, user: dict = Depends(get_current_user)):
    """A4: Batch-archive a list of nodes (editor/admin only)."""
    with db_cursor(commit=True) as cur:
        ws = _require_ws_access(cur, ws_id, user, write=True, required_scope="kb:write")
        role = _get_effective_role(cur, ws_id, ws["owner_id"], user["sub"])
        if role not in ("editor", "admin"):
            raise HTTPException(status_code=403, detail="Editor or Admin role required")
        if not body.node_ids:
            return {"archived_count": 0}
        cur.execute(
            """
            UPDATE memory_nodes
            SET status = 'archived', archived_at = NOW()
            WHERE id = ANY(%s) AND workspace_id = %s AND status != 'archived'
            """,
            (body.node_ids, ws_id),
        )
        return {"archived_count": cur.rowcount}


@router.post("/workspaces/{ws_id}/nodes/{node_id}/archive", status_code=204)
def archive_node(ws_id: str, node_id: str, user: dict = Depends(get_current_user)):
    """D4: Archive a single node."""
    with db_cursor(commit=True) as cur:
        ws = _require_ws_access(cur, ws_id, user, write=True, required_scope="kb:write")
        role = _get_effective_role(cur, ws_id, ws["owner_id"], user["sub"])
        if role not in ("editor", "admin"):
            raise HTTPException(status_code=403, detail="Editor or Admin role required")
        cur.execute(
            "UPDATE memory_nodes SET status = 'archived', archived_at = NOW() WHERE id = %s AND workspace_id = %s RETURNING id",
            (node_id, ws_id),
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Node not found")


@router.post("/workspaces/{ws_id}/nodes/{node_id}/restore", status_code=204)
def restore_node(ws_id: str, node_id: str, user: dict = Depends(get_current_user)):
    """D4: Restore a previously archived node."""
    with db_cursor(commit=True) as cur:
        ws = _require_ws_access(cur, ws_id, user, write=True, required_scope="kb:write")
        role = _get_effective_role(cur, ws_id, ws["owner_id"], user["sub"])
        if role not in ("editor", "admin"):
            raise HTTPException(status_code=403, detail="Editor or Admin role required")
        cur.execute(
            "UPDATE memory_nodes SET status = 'active', archived_at = NULL WHERE id = %s AND workspace_id = %s RETURNING id",
            (node_id, ws_id),
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Node not found or not archived")


# ─── A3: Node Health Scores ────────────────────────────────────────────────────

@router.get("/workspaces/{ws_id}/nodes/health-scores")
def get_health_scores(ws_id: str, user: dict = Depends(get_current_user_optional)):
    with db_cursor() as cur:
        ws = _require_ws_access(cur, ws_id, user)
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


# ─── A6: Manual Validity Stamp ────────────────────────────────────────────────



# ─── B1: viewer body stripping on GET single node ─────────────────────────────
# (handled via _strip_body_if_viewer already in the existing get_node endpoint)


# ─── D3 / D1: Workspace search for cross-KB operations ───────────────────────




# ─── G-2: Manual Link Detection ──────────────────────────────────────────────

@router.post("/workspaces/{ws_id}/nodes/detect-links", status_code=202)
def trigger_link_detection(
    ws_id: str, 
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user)
):
    """G-2: Manually trigger cross-file association detection for all active nodes."""
    with db_cursor() as cur:
        _require_ws_access(cur, ws_id, user, write=True)
        
        # Get all active nodes
        cur.execute("SELECT id FROM memory_nodes WHERE workspace_id = %s AND status = 'active'", (ws_id,))
        node_ids = [r["id"] for r in cur.fetchall()]

    from routers.ingest import detect_cross_file_associations_for_nodes
    background_tasks.add_task(detect_cross_file_associations_for_nodes, ws_id, node_ids)
    return {"message": "Link detection started in background", "nodes_checked": len(node_ids)}

# ─── MCP Interaction Tracking ───────────────────────────────────────────────

def _write_mcp_interaction_edge(ws_id: str, node_id: str, tool_name: str, query_text: str = ""):
    """
    P4.5-1B-2: Record interaction edges for nodes retrieved via MCP.
    Updates existing edge count or creates a new one.
    """
    from core.agent import get_or_create_agent_node
    from core.security import generate_id
    from datetime import datetime, timezone
    import json

    with db_cursor(commit=True) as cur:
        agent_id = get_or_create_agent_node(ws_id, cur)
        
        # Check if edge already exists
        cur.execute("""
            SELECT id, metadata FROM edges
            WHERE workspace_id = %s AND from_id = %s AND to_id = %s AND relation = 'queried_via_mcp'
        """, (ws_id, agent_id, node_id))
        edge_row = cur.fetchone()
        
        now_str = datetime.now(timezone.utc).isoformat()
        if edge_row:
            meta = edge_row["metadata"] or {}
            meta["count"] = meta.get("count", 0) + 1
            meta["last_hit"] = now_str
            # Keep track of tools/queries in a list (limited to last 5)
            history = meta.get("history", [])
            history.insert(0, {"tool": tool_name, "query": query_text, "ts": now_str})
            meta["history"] = history[:5]
            
            cur.execute("""
                UPDATE edges SET metadata = %s, last_co_accessed = now()
                WHERE id = %s
            """, (json.dumps(meta), edge_row["id"]))
        else:
            edge_id = generate_id("edge")
            meta = {
                "count": 1, 
                "last_hit": now_str,
                "history": [{"tool": tool_name, "query": query_text, "ts": now_str}]
            }
            cur.execute("""
                INSERT INTO edges (id, workspace_id, from_id, to_id, relation, weight, metadata)
                VALUES (%s, %s, %s, %s, 'queried_via_mcp', 1.0, %s)
            """, (edge_id, ws_id, agent_id, node_id, json.dumps(meta)))


def _record_traversal(ws_id: str, node_id: str, user_id: str):
    """
    Background task to record node traversal and update trust metrics (freshness).
    P4.7-S1-2 & S3-4.
    """
    with db_cursor(commit=True) as cur:
        # Record in log
        # Note: traversal_log schema is (node_id, actor_id, traversed_at)
        cur.execute(
            "INSERT INTO traversal_log (node_id, actor_id) VALUES (%s, %s)",
            (node_id, user_id)
        )
        
        # Check if this is a new traverser for this node
        cur.execute(
            "SELECT COUNT(*) FROM traversal_log WHERE node_id = %s AND actor_id = %s",
            (node_id, user_id)
        )
        count = cur.fetchone()["count"]
        is_new = (count == 1)

        # Update node counters and freshness
        # Freshness is reset to 1.0 when a node is 'traversed' (viewed/explored)
        cur.execute(
            """
            UPDATE memory_nodes
            SET traversal_count = traversal_count + 1,
                unique_traverser_count = unique_traverser_count + %s,
                dim_freshness = 1.0,
                validity_confirmed_at = now()
            WHERE id = %s AND workspace_id = %s
            """,
            (1 if is_new else 0, node_id, ws_id)
        )
        
        # Recompute trust_score with new utility (based on traversal_count)
        # Weights: Accuracy 40%, Freshness 25%, Utility 25%, Author Rep 10%
        cur.execute(
            """
            UPDATE memory_nodes
            SET
                dim_utility = LEAST(1.0, (traversal_count)::float / 100.0),
                trust_score = (
                    dim_accuracy   * 0.40 +
                    1.0            * 0.25 +
                    LEAST(1.0, (traversal_count)::float / 100.0) * 0.25 +
                    dim_author_rep * 0.10
                )
            WHERE id = %s AND workspace_id = %s
            """,
            (node_id, ws_id)
        )

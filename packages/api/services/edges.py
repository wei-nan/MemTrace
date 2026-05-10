"""
services/edges.py — Edge creation, MCP interaction edge, and traversal recording.

Extracted from routers/kb.py (S2-3).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from core.database import db_cursor
from core.security import generate_id
from core.constants import VALID_RELATIONS

logger = logging.getLogger(__name__)


# ─── MCP Interaction Edge ─────────────────────────────────────────────────────

def write_mcp_interaction_edge(
    ws_id: str,
    node_id: str,
    tool_name: str = "unknown",
    query_text: str = "",
) -> None:
    """
    P4.5-1B-2: Record interaction edges for nodes retrieved via MCP.
    Updates existing edge count/history or creates a new queried_via_mcp edge.

    Called from routers/mcp.py after any read tool that returns node data.
    Now lives in services/edges.py so mcp.py doesn't need to lazy-import from routers/kb.
    """
    from core.agent import get_or_create_agent_node

    with db_cursor(commit=True) as cur:
        agent_id = get_or_create_agent_node(ws_id, cur)

        cur.execute(
            """
            SELECT id, metadata FROM edges
            WHERE workspace_id = %s AND from_id = %s AND to_id = %s AND relation = 'queried_via_mcp'
            """,
            (ws_id, agent_id, node_id),
        )
        edge_row = cur.fetchone()

        now_str = datetime.now(timezone.utc).isoformat()
        if edge_row:
            meta = edge_row["metadata"] or {}
            meta["count"] = meta.get("count", 0) + 1
            meta["last_hit"] = now_str
            history = meta.get("history", [])
            history.insert(0, {"tool": tool_name, "query": query_text, "ts": now_str})
            meta["history"] = history[:5]
            cur.execute(
                "UPDATE edges SET metadata = %s, last_co_accessed = now() WHERE id = %s",
                (json.dumps(meta), edge_row["id"]),
            )
        else:
            meta = {
                "count": 1,
                "last_hit": now_str,
                "history": [{"tool": tool_name, "query": query_text, "ts": now_str}],
            }
            cur.execute(
                """
                INSERT INTO edges (id, workspace_id, from_id, to_id, relation, weight, metadata)
                VALUES (%s, %s, %s, %s, 'queried_via_mcp', 1.0, %s)
                """,
                (generate_id("edge"), ws_id, agent_id, node_id, json.dumps(meta)),
            )


# ─── Traversal Recording ──────────────────────────────────────────────────────

def record_traversal(ws_id: str, node_id: str, user_id: str) -> None:
    """
    Background task: record a node traversal and update trust metrics (freshness).
    P4.7-S1-2 & S3-4.
    """
    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO traversal_log (node_id, actor_id) VALUES (%s, %s)",
            (node_id, user_id),
        )
        cur.execute(
            """
            UPDATE memory_nodes
            SET traversal_count = traversal_count + 1,
                unique_traverser_count = (
                    SELECT COUNT(DISTINCT actor_id) FROM traversal_log WHERE node_id = %s
                ),
                dim_freshness = LEAST(1.0, dim_freshness + 0.01),
                trust_score = (
                    dim_accuracy       * 0.40 +
                    LEAST(1.0, dim_freshness + 0.01) * 0.25 +
                    dim_utility        * 0.25 +
                    dim_author_rep     * 0.10
                )
            WHERE id = %s AND workspace_id = %s
            """,
            (node_id, node_id, ws_id),
        )


from fastapi import HTTPException

# ─── Edge CRUD Operations ─────────────────────────────────────────────────────

def create_edge_in_db(cur, ws_id: str, body_dict: dict) -> dict:
    """Insert a new edge into the database and return it."""
    from_id = body_dict["from_id"]
    to_id = body_dict["to_id"]
    relation = body_dict["relation"]
    weight = body_dict["weight"]
    half_life_days = body_dict.get("half_life_days", 30)
    pinned = body_dict.get("pinned", False)

    if relation not in VALID_RELATIONS:
        raise HTTPException(status_code=400, detail="Invalid relation type")
    if from_id == to_id:
        raise HTTPException(status_code=400, detail="Cannot link a node to itself")
    if not (0.1 <= weight <= 1.0):
        raise HTTPException(status_code=400, detail="Weight must be between 0.1 and 1.0")
        
    edge_id = generate_id("edge")
    
    for nid in (from_id, to_id):
        cur.execute("SELECT id FROM memory_nodes WHERE id = %s AND workspace_id = %s", (nid, ws_id))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail=f"Node not found: {nid}")
            
    if half_life_days == 30:
        cur.execute("SELECT content_type FROM memory_nodes WHERE id = %s", (from_id,))
        row = cur.fetchone()
        if row:
            half_life_days = {"factual": 365, "procedural": 90, "preference": 30, "context": 14}.get(row["content_type"], 30)
            
    try:
        cur.execute(
            """
            INSERT INTO edges (id, workspace_id, from_id, to_id, relation, weight, half_life_days, pinned)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *, CASE WHEN rating_count > 0 THEN ROUND(rating_sum / rating_count, 2) ELSE NULL END AS rating_avg
            """,
            (edge_id, ws_id, from_id, to_id, relation, weight, half_life_days, pinned),
        )
        return cur.fetchone()
    except Exception as exc:
        if "unique_edge" in str(exc):
            raise HTTPException(status_code=409, detail="Edge with this relation already exists")
        raise

# ─── Backward-compat aliases ──────────────────────────────────────────────────

_write_mcp_interaction_edge = write_mcp_interaction_edge
_record_traversal = record_traversal
_create_edge_in_db = create_edge_in_db

def list_edges_in_db(cur, ws_id: str, node_id: Optional[str], user: Optional[dict]) -> list[dict]:
    from services.workspaces import require_ws_access
    require_ws_access(cur, ws_id, user)
    if node_id:
        cur.execute(
            """
            SELECT *, CASE WHEN rating_count > 0 THEN ROUND(rating_sum / rating_count, 2) ELSE NULL END AS rating_avg
            FROM edges 
            WHERE workspace_id = %s AND status = 'active' AND (from_id = %s OR to_id = %s)
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

def traverse_edge_in_db(cur, edge_id: str, note: Optional[str], user: dict) -> None:
    from services.workspaces import require_ws_access
    from core.ratelimit import TraversalGuard
    from fastapi import HTTPException
    TraversalGuard.check(user["sub"])
    cur.execute("SELECT from_id, to_id, workspace_id FROM edges WHERE id = %s", (edge_id,))
    edge = cur.fetchone()
    if not edge:
        raise HTTPException(status_code=404, detail="Edge not found")
    require_ws_access(cur, edge["workspace_id"], user)
    cur.execute("SELECT record_traversal(%s, %s, NULL, %s)", (edge_id, user["sub"], note))

def rate_edge_in_db(cur, edge_id: str, rating: int, note: Optional[str], user: dict) -> None:
    from services.workspaces import require_ws_access
    from fastapi import HTTPException
    if not (1 <= rating <= 5):
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    cur.execute("SELECT workspace_id FROM edges WHERE id = %s", (edge_id,))
    edge_row = cur.fetchone()
    if not edge_row:
        raise HTTPException(status_code=404, detail="Edge not found")
    require_ws_access(cur, edge_row["workspace_id"], user)
    cur.execute("SELECT record_traversal(%s, %s, %s, %s)", (edge_id, user["sub"], rating, note))

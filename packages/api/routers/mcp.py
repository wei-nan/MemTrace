"""
MCP SSE Transport — Remote access to MemTrace knowledge graphs.

Protocol:
  GET  /sse          → SSE stream; first event tells client where to POST
  POST /messages     → JSON-RPC 2.0 messages; responses go back via SSE

Auth: Authorization: Bearer mt_<api_key>   (same key generated in WorkspaceSettings)

Claude Code config:
  {
    "mcpServers": {
      "memtrace": {
        "type": "sse",
        "url": "https://<your-host>/sse",
        "headers": { "Authorization": "Bearer mt_..." }
      }
    }
  }
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, BackgroundTasks
from fastapi.responses import StreamingResponse

from core.database import db_cursor
from core.deps import get_current_user

from routers.kb import _require_ws_access
from core.ai import resolve_provider, record_usage
from core.constants import SEARCH_MISS_DEDUP

logger = logging.getLogger(__name__)

router = APIRouter(tags=["mcp"])

@router.get("/status")
async def mcp_status(user: dict = Depends(get_current_user)):
    """Return real-time MCP session status."""
    user_sub = user.get("sub")
    user_sessions = [
        {
            "session_id": sid,
            "created_at": s.get("created_at"),
            "last_accessed": s.get("last_accessed")
        }
        for sid, s in _sessions.items()
        if s.get("user_sub") == user_sub
    ]
    return {
        "active_sessions_total": len(_sessions),
        "user_sessions": user_sessions,
        "server_info": _SERVER_INFO
    }


# ── In-memory session map: session_id → dict ─────────────────────────
_sessions: Dict[str, dict] = {}

# ── MCP server metadata ────────────────────────────────────────────────────────
_SERVER_INFO = {
    "name":    "memtrace",
    "version": "1.0.0",
}
_PROTOCOL_VERSION = "2024-11-05"


# ═══════════════════════════════════════════════════════════════════════════════
# Tool definitions
# ═══════════════════════════════════════════════════════════════════════════════

_TOOLS = [
    {
        "name": "list_workspaces",
        "description": "List all workspaces accessible to the authenticated user.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "list_nodes",
        "description": "List knowledge nodes in a workspace. Supports keyword search and filtering.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string", "description": "Workspace ID"},
                "q":  {"type": "string",  "description": "Keyword search query (optional)"},
                "limit":  {"type": "integer", "description": "Max results (default 50, max 200)"},
                "offset": {"type": "integer", "description": "Pagination offset"},
            },
            "required": ["workspace_id"],
        },
    },
    {
        "name": "get_node",
        "description": "Get a single knowledge node by ID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "node_id":      {"type": "string"},
            },
            "required": ["workspace_id", "node_id"],
        },
    },
    {
        "name": "search_nodes",
        "description": "Search nodes by keyword (supports Chinese/CJK). Returns matching nodes.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "query":        {"type": "string", "description": "Search query"},
                "limit":        {"type": "integer", "description": "Max results (default 20)"},
            },
            "required": ["workspace_id", "query"],
        },
    },
    {
        "name": "create_node",
        "description": "Create a new knowledge node in a workspace.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "title_zh":     {"type": "string", "description": "Node title in Chinese"},
                "title_en":     {"type": "string", "description": "Node title in English"},
                "body_zh":      {"type": "string", "description": "Node body in Chinese"},
                "body_en":      {"type": "string", "description": "Node body in English"},
                "content_type": {
                    "type": "string",
                    "enum": ["factual", "procedural", "preference", "context", "inquiry"],
                    "description": "Node content type",
                },
                "tags":         {"type": "array", "items": {"type": "string"}},
                "trust_score":  {"type": "number", "description": "Trust score 0.0–1.0"},
            },
            "required": ["workspace_id"],
        },
    },
    {
        "name": "update_node",
        "description": "Update an existing knowledge node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "node_id":      {"type": "string"},
                "title_zh":     {"type": "string"},
                "title_en":     {"type": "string"},
                "body_zh":      {"type": "string"},
                "body_en":      {"type": "string"},
                "content_type": {"type": "string"},
                "tags":         {"type": "array", "items": {"type": "string"}},
                "trust_score":  {"type": "number"},
            },
            "required": ["workspace_id", "node_id"],
        },
    },
    {
        "name": "delete_node",
        "description": "Archive (soft-delete) a knowledge node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "node_id":      {"type": "string"},
            },
            "required": ["workspace_id", "node_id"],
        },
    },
    {
        "name": "create_edge",
        "description": "Create a directed edge (relationship) between two nodes.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "from_id":      {"type": "string", "description": "Source node ID"},
                "to_id":        {"type": "string", "description": "Target node ID"},
                "relation": {
                    "type": "string",
                    "enum": ["depends_on", "extends", "related_to", "contradicts", "answered_by", "similar_to", "queried_via_mcp"],
                },
                "weight": {"type": "number", "description": "Edge weight 0.0–1.0"},
            },
            "required": ["workspace_id", "from_id", "to_id", "relation"],
        },
    },
    {
        "name": "traverse",
        "description": "Traverse the knowledge graph from a starting node, following edges up to a given depth.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "node_id":      {"type": "string", "description": "Starting node ID"},
                "depth":        {"type": "integer", "description": "Max traversal depth (default 2)"},
                "relation":     {"type": "string", "description": "Filter by relation type (optional)"},
            },
            "required": ["workspace_id", "node_id"],
        },
    },
    {
        "name": "list_by_tag",
        "description": "List all nodes in a workspace that have a specific tag.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "tag":          {"type": "string"},
            },
            "required": ["workspace_id", "tag"],
        },
    },
    {
        "name": "get_schema",
        "description": "Return the MemTrace node schema (content types, relations, field definitions).",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "list_review_queue",
        "description": "List nodes that need review (low trust score or flagged).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "limit":        {"type": "integer", "description": "Max results (default 20)"},
            },
            "required": ["workspace_id"],
        },
    },
    {
        "name": "confirm_node_validity",
        "description": "Mark a node as reviewed and valid, updating its validity timestamp.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "node_id":      {"type": "string"},
            },
            "required": ["workspace_id", "node_id"],
        },
    },
]


# ═══════════════════════════════════════════════════════════════════════════════
# Tool execution
# ═══════════════════════════════════════════════════════════════════════════════

# _check_workspace_access removed in favor of _require_ws_access

async def _handle_search_miss(ws_id: str, query_text: str, user_id: str):
    """Background task to record a gap node when search yields 0 results."""
    from core.security import generate_id
    
    try:
        resolved = resolve_provider(user_id, "embedding")
        vector, tokens = await resolved.provider.embed(resolved, query_text)
        record_usage(resolved, "embedding", tokens, workspace_id=ws_id)
    except Exception as e:
        logger.error("Failed to generate embedding for search miss: %s", e)
        return

    with db_cursor(commit=True) as cur:
        # Check if a similar gap node already exists
        cur.execute(
            """SELECT id FROM memory_nodes 
               WHERE workspace_id = %s 
                 AND status = 'gap'
                 AND content_type = 'inquiry'
                 AND embedding IS NOT NULL
                 AND (1 - (embedding <=> %s::vector)) >= %s
               ORDER BY (1 - (embedding <=> %s::vector)) DESC LIMIT 1""",
            (ws_id, vector, SEARCH_MISS_DEDUP, vector)
        )
        row = cur.fetchone()
        
        if row:
            cur.execute("UPDATE memory_nodes SET miss_count = miss_count + 1 WHERE id = %s", (row["id"],))
        else:
            node_id = generate_id("node")
            cur.execute(
                """INSERT INTO memory_nodes
                     (id, workspace_id, title_zh, title_en, body_zh, body_en,
                      content_type, tags, trust_score, status, source_type, dim_author_rep, embedding)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::vector)""",
                (
                    node_id, ws_id,
                    query_text, query_text, "", "",
                    "inquiry", ["auto:search-miss"], 0.0, "gap", "mcp", 0.0, vector
                )
            )

async def _execute_tool(name: str, args: dict, user: dict, background_tasks: BackgroundTasks) -> Any:
    """Dispatch a tool call to the appropriate DB query."""

    # ── list_workspaces ───────────────────────────────────────────────────────
    if name == "list_workspaces":
        with db_cursor() as cur:
            params: list = [user["sub"], user["sub"]]
            ws_restriction = ""
            # Workspace-level API key: only show the designated workspace
            if user.get("api_key_id") and user.get("workspace_id"):
                ws_restriction = "AND w.id = %s"
                params.append(user["workspace_id"])
            cur.execute(
                f"""SELECT w.id, w.name_en, w.name_zh, w.kb_type, w.visibility,
                          (SELECT count(*) FROM memory_nodes WHERE workspace_id = w.id AND status='active') AS node_count
                   FROM workspaces w
                   LEFT JOIN workspace_members wm ON wm.workspace_id = w.id AND wm.user_id = %s
                   WHERE w.status = 'active'
                     AND (w.owner_id = %s OR wm.user_id IS NOT NULL)
                     {ws_restriction}
                   ORDER BY w.created_at DESC""",
                params,
            )
            return cur.fetchall()

    # ── list_nodes ────────────────────────────────────────────────────────────
    if name == "list_nodes":
        ws_id = args.get("workspace_id", "")
        q      = args.get("q", "")
        limit  = min(int(args.get("limit", 50)), 200)
        offset = int(args.get("offset", 0))
        with db_cursor() as cur:
            _require_ws_access(cur, ws_id, user, write=False)
            conditions = ["workspace_id = %s", "status = 'active'"]
            params: list = [ws_id]
            if q:
                cjk = re.findall(r'[一-鿿぀-ゟ゠-ヿ]+', q)
                eng = re.findall(r'[a-zA-Z0-9]{2,}', q)
                or_conds = ["search_vector @@ plainto_tsquery('simple', %s)"]
                params.append(q)
                for t in (cjk + eng):
                    or_conds.append("(title_zh ILIKE %s OR title_en ILIKE %s)")
                    like = f"%{t}%"
                    params += [like, like]
                conditions.append(f"({' OR '.join(or_conds)})")
            where = " AND ".join(conditions)
            cur.execute(
                f"""SELECT id, title_zh, title_en, content_type, tags,
                           trust_score, created_at, updated_at
                    FROM memory_nodes WHERE {where}
                    ORDER BY trust_score DESC, updated_at DESC
                    LIMIT %s OFFSET %s""",
                params + [limit, offset],
            )
            return cur.fetchall()

    # ── get_node ──────────────────────────────────────────────────────────────
    if name == "get_node":
        ws_id   = args["workspace_id"]
        node_id = args["node_id"]
        with db_cursor() as cur:
            _require_ws_access(cur, ws_id, user, write=False)
            
            # P4.5-1B-2: Record interaction edge
            from routers.kb import _write_mcp_interaction_edge
            background_tasks.add_task(_write_mcp_interaction_edge, ws_id, node_id, name, "node_lookup")
            
            cur.execute(
                """SELECT id, workspace_id, title_zh, title_en, body_zh, body_en,
                          content_type, tags, trust_score, status,
                          created_at, updated_at, validity_confirmed_at
                   FROM memory_nodes WHERE id = %s AND workspace_id = %s""",
                (node_id, ws_id),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Node '{node_id}' not found")
            
            return row

    # ── search_nodes ──────────────────────────────────────────────────────────
    if name == "search_nodes":
        ws_id = args["workspace_id"]
        query = args.get("query", "")
        limit = min(int(args.get("limit", 20)), 100)
        with db_cursor() as cur:
            _require_ws_access(cur, ws_id, user, write=False)
            cjk = re.findall(r'[一-鿿぀-ゟ゠-ヿ]+', query)
            eng = re.findall(r'[a-zA-Z0-9]{2,}', query)
            or_conds = ["search_vector @@ plainto_tsquery('simple', %s)"]
            params: list = [ws_id, query]
            for t in (cjk + eng):
                or_conds.append("(title_zh ILIKE %s OR title_en ILIKE %s OR body_zh ILIKE %s OR body_en ILIKE %s)")
                like = f"%{t}%"
                params += [like, like, like, like]
            cur.execute(
                f"""SELECT id, title_zh, title_en, body_zh, body_en,
                           content_type, tags, trust_score
                    FROM memory_nodes
                    WHERE workspace_id = %s AND status = 'active'
                      AND ({' OR '.join(or_conds)})
                    ORDER BY trust_score DESC LIMIT %s""",
                params + [limit],
            )
            results = cur.fetchall()
            
            if len(results) == 0 and query:
                background_tasks.add_task(_handle_search_miss, ws_id, query, user["sub"])
            elif len(results) > 0:
                # P4.5-1B-2: Record interaction edges for top results
                from routers.kb import _write_mcp_interaction_edge
                for r in results[:3]: # Only record for top 3 to avoid noise
                    logger.info(f"Adding interaction edge task for {r['id']}")
                    background_tasks.add_task(_write_mcp_interaction_edge, ws_id, r["id"], name, query)
                
                # P4.5-1B-1: Log MCP query
                logger.info(f"Adding query log task for {name}")
                background_tasks.add_task(_log_mcp_query, ws_id, name, query, len(results))
                
            return results

    # ── create_node ───────────────────────────────────────────────────────────
    if name == "create_node":
        ws_id = args["workspace_id"]
        from core.security import generate_id
        node_id = generate_id("node")
        # P4.5-2B-1: Compute signature and set author
        from core.security import compute_signature
        sig = compute_signature(
            {"en": args.get("title_en", ""), "zh": args.get("title_zh", "")},
            {"en": args.get("body_en", ""), "zh": args.get("body_zh", "")},
            args.get("tags", []),
            user["sub"]
        )
        
        with db_cursor(commit=True) as cur:
            _require_ws_access(cur, ws_id, user, write=True, required_scope="kb:write")
            cur.execute(
                """INSERT INTO memory_nodes
                     (id, workspace_id, title_zh, title_en, body_zh, body_en,
                      content_type, tags, trust_score, author, signature)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING id, title_zh, title_en, content_type, tags,
                             trust_score, created_at""",
                (
                    node_id, ws_id,
                    args.get("title_zh", ""),
                    args.get("title_en", ""),
                    args.get("body_zh", ""),
                    args.get("body_en", ""),
                    args.get("content_type", "factual"),
                    args.get("tags", []),
                    args.get("trust_score", 0.5),
                    user["sub"],
                    sig
                ),
            )
            return cur.fetchone()

    # ── update_node ───────────────────────────────────────────────────────────
    if name == "update_node":
        ws_id   = args["workspace_id"]
        node_id = args["node_id"]
        allowed = {"title_zh", "title_en", "body_zh", "body_en",
                   "content_type", "tags", "trust_score"}
        updates = {k: v for k, v in args.items() if k in allowed}
        if not updates:
            raise ValueError("No updatable fields provided")
        set_clause = ", ".join(f"{k} = %s" for k in updates)
        with db_cursor(commit=True) as cur:
            _require_ws_access(cur, ws_id, user, write=True, required_scope="kb:write")
            cur.execute(
                f"""UPDATE memory_nodes SET {set_clause}, updated_at = now()
                    WHERE id = %s AND workspace_id = %s
                    RETURNING id, title_zh, title_en, content_type, tags, trust_score, updated_at""",
                list(updates.values()) + [node_id, ws_id],
            )
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Node '{node_id}' not found")
            return row

    # ── delete_node ───────────────────────────────────────────────────────────
    if name == "delete_node":
        ws_id   = args["workspace_id"]
        node_id = args["node_id"]
        with db_cursor(commit=True) as cur:
            _require_ws_access(cur, ws_id, user, write=True, required_scope="kb:write")
            cur.execute(
                """UPDATE memory_nodes SET status = 'archived', archived_at = now()
                   WHERE id = %s AND workspace_id = %s AND status = 'active'""",
                (node_id, ws_id),
            )
            if cur.rowcount == 0:
                raise ValueError(f"Node '{node_id}' not found or already archived")
            return {"archived": True, "node_id": node_id}

    # ── create_edge ───────────────────────────────────────────────────────────
    if name == "create_edge":
        ws_id = args["workspace_id"]
        from core.security import generate_id
        edge_id = generate_id("edge")
        with db_cursor(commit=True) as cur:
            _require_ws_access(cur, ws_id, user, write=True, required_scope="kb:write")
            cur.execute(
                """INSERT INTO edges (id, workspace_id, from_id, to_id, relation, weight)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   ON CONFLICT (workspace_id, from_id, to_id, relation) DO UPDATE
                     SET weight = EXCLUDED.weight, last_co_accessed = now()
                   RETURNING id, from_id, to_id, relation, weight, created_at""",
                (
                    edge_id, ws_id,
                    args["from_id"], args["to_id"],
                    args["relation"],
                    float(args.get("weight", 1.0)),
                ),
            )
            return cur.fetchone()

    # ── traverse ──────────────────────────────────────────────────────────────
    if name == "traverse":
        ws_id     = args["workspace_id"]
        node_id   = args["node_id"]
        max_depth = min(int(args.get("depth", 2)), 4)
        relation  = args.get("relation")
        with db_cursor() as cur:
            _require_ws_access(cur, ws_id, user, write=False)
            # BFS
            visited: dict = {}
            queue: list = [(node_id, 0)]
            edges_found: list = []
            while queue:
                curr_id, depth = queue.pop(0)
                if curr_id in visited or depth > max_depth:
                    continue
                cur.execute(
                    "SELECT * FROM memory_nodes WHERE id = %s AND workspace_id = %s AND status='active'",
                    (curr_id, ws_id),
                )
                node = cur.fetchone()
                if not node:
                    continue
                visited[curr_id] = node
                if depth < max_depth:
                    rel_filter = "AND relation = %s" if relation else ""
                    rel_params = [relation] if relation else []
                    cur.execute(
                        f"""SELECT from_id, to_id, relation, weight
                            FROM edges
                            WHERE workspace_id = %s AND status = 'active'
                              AND (from_id = %s OR to_id = %s)
                              {rel_filter}""",
                        [ws_id, curr_id, curr_id] + rel_params,
                    )
                    for e in cur.fetchall():
                        edges_found.append(e)
                        neighbor = e["to_id"] if e["from_id"] == curr_id else e["from_id"]
                        if neighbor not in visited:
                            queue.append((neighbor, depth + 1))
            # P4.5-1B-2: Record interaction edge for the root node
            from routers.kb import _write_mcp_interaction_edge
            background_tasks.add_task(_write_mcp_interaction_edge, ws_id, node_id, name)

            return {"nodes": list(visited.values()), "edges": edges_found}

    # ── list_by_tag ───────────────────────────────────────────────────────────
    if name == "list_by_tag":
        ws_id = args["workspace_id"]
        tag   = args["tag"]
        with db_cursor() as cur:
            _require_ws_access(cur, ws_id, user, write=False)
            cur.execute(
                """SELECT id, title_zh, title_en, content_type, tags, trust_score
                   FROM memory_nodes
                   WHERE workspace_id = %s AND status = 'active' AND %s = ANY(tags)
                   ORDER BY trust_score DESC""",
                (ws_id, tag),
            )
            return cur.fetchall()

    # ── get_schema ────────────────────────────────────────────────────────────
    if name == "get_schema":
        return {
            "content_types": ["factual", "procedural", "preference", "context"],
            "relations":     ["depends_on", "extends", "related_to", "contradicts"],
            "fields": {
                "id":            "string — unique node ID",
                "title_zh":      "string — Chinese title",
                "title_en":      "string — English title",
                "body_zh":       "string — Chinese body",
                "body_en":       "string — English body",
                "content_type":  "one of content_types",
                "tags":          "array of strings",
                "trust_score":   "float 0.0–1.0",
                "status":        "active | archived",
                "created_at":    "ISO8601 datetime",
                "updated_at":    "ISO8601 datetime",
            },
        }

    # ── list_review_queue ─────────────────────────────────────────────────────
    if name == "list_review_queue":
        ws_id = args["workspace_id"]
        limit = min(int(args.get("limit", 20)), 100)
        with db_cursor() as cur:
            _require_ws_access(cur, ws_id, user, write=False)
            cur.execute(
                """SELECT id, title_zh, title_en, content_type, trust_score,
                          updated_at, validity_confirmed_at
                   FROM memory_nodes
                   WHERE workspace_id = %s AND status = 'active'
                     AND (trust_score < 0.5 OR validity_confirmed_at IS NULL
                          OR validity_confirmed_at < now() - interval '90 days')
                   ORDER BY trust_score ASC LIMIT %s""",
                (ws_id, limit),
            )
            return cur.fetchall()

    # ── confirm_node_validity ─────────────────────────────────────────────────
    if name == "confirm_node_validity":
        ws_id   = args["workspace_id"]
        node_id = args["node_id"]
        with db_cursor(commit=True) as cur:
            _require_ws_access(cur, ws_id, user, write=True, required_scope="kb:write")
            cur.execute(
                """UPDATE memory_nodes
                   SET validity_confirmed_at = now(), trust_score = LEAST(trust_score + 0.05, 1.0)
                   WHERE id = %s AND workspace_id = %s AND status = 'active'
                   RETURNING id, trust_score, validity_confirmed_at""",
                (node_id, ws_id),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Node '{node_id}' not found")
            return row

    raise ValueError(f"Unknown tool: {name}")


# ═══════════════════════════════════════════════════════════════════════════════
# JSON-RPC 2.0 dispatcher
# ═══════════════════════════════════════════════════════════════════════════════

def _jsonrpc_error(id: Any, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": id, "error": {"code": code, "message": message}}


def _jsonrpc_ok(id: Any, result: Any) -> dict:
    return {"jsonrpc": "2.0", "id": id, "result": result}


def _serialize(obj: Any) -> Any:
    """Convert psycopg2 Row objects and datetime to JSON-serializable types."""
    import datetime
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serialize(i) for i in obj]
    # psycopg2 RealDictRow — treat like dict
    try:
        return {k: _serialize(v) for k, v in dict(obj).items()}
    except Exception:
        return str(obj)


async def _dispatch(msg: dict, user: dict, background_tasks: BackgroundTasks) -> dict:
    method = msg.get("method", "")
    msg_id = msg.get("id")

    if method == "initialize":
        return _jsonrpc_ok(msg_id, {
            "protocolVersion": _PROTOCOL_VERSION,
            "serverInfo": _SERVER_INFO,
            "capabilities": {"tools": {"listChanged": False}},
        })

    if method == "ping":
        return _jsonrpc_ok(msg_id, {})

    if method == "tools/list":
        return _jsonrpc_ok(msg_id, {"tools": _TOOLS})

    if method == "tools/call":
        params  = msg.get("params", {})
        tool    = params.get("name", "")
        args    = params.get("arguments", {})
        try:
            result = await _execute_tool(tool, args, user, background_tasks)
            serialized = _serialize(result)
            return _jsonrpc_ok(msg_id, {
                "content": [{"type": "text", "text": json.dumps(serialized, ensure_ascii=False, indent=2)}],
                "isError": False,
            })
        except ValueError as e:
            return _jsonrpc_ok(msg_id, {
                "content": [{"type": "text", "text": str(e)}],
                "isError": True,
            })
        except Exception as e:
            logger.exception("MCP tool error — tool=%s", tool)
            return _jsonrpc_error(msg_id, -32603, f"Internal error: {e}")

    # Unknown method
    return _jsonrpc_error(msg_id, -32601, f"Method not found: {method}")


# ═══════════════════════════════════════════════════════════════════════════════
# SSE endpoint
# ═══════════════════════════════════════════════════════════════════════════════

import time

MAX_SESSIONS_PER_USER = 5
SESSION_TTL_SECONDS = 3600

@router.get("/sse")
async def mcp_sse(
    request: Request,
    user: dict = Depends(get_current_user),
):
    """
    MCP SSE stream endpoint.
    Sends an 'endpoint' event telling the client where to POST messages,
    then streams responses back as 'message' events.
    """
    user_sub = user.get("sub")
    
    # Prune expired sessions globally (optional but good practice)
    now = time.time()
    expired = [sid for sid, s in _sessions.items() if now - s.get("created_at", 0) > SESSION_TTL_SECONDS]
    for sid in expired:
        _sessions.pop(sid, None)
        
    # Enforce max sessions per user limit
    user_sessions = [sid for sid, s in _sessions.items() if s.get("user_sub") == user_sub]
    if len(user_sessions) >= MAX_SESSIONS_PER_USER:
        # Prune oldest session for this user
        oldest_sid = min(user_sessions, key=lambda sid: _sessions[sid].get("created_at", 0))
        _sessions.pop(oldest_sid, None)

    session_id = str(uuid.uuid4())
    queue: asyncio.Queue = asyncio.Queue()
    _sessions[session_id] = {
        "queue": queue,
        "user_sub": user_sub,
        "api_key_id": user.get("api_key_id"),
        "created_at": now,
        "last_accessed": now,
    }

    # Build the POST URL the client should use
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme
    host = request.headers.get("x-forwarded-host") or request.headers.get("host", "")
    base = f"{proto}://{host}"
    post_url = f"{base}/messages?sessionId={session_id}"

    async def event_stream():
        try:
            # 1 — Tell client where to POST
            yield f"event: endpoint\ndata: {json.dumps({'uri': post_url})}\n\n"

            # 2 — Relay responses from the queue
            while True:
                if await request.is_disconnected():
                    break
                try:
                    response = await asyncio.wait_for(queue.get(), timeout=20)
                    yield f"data: {json.dumps(response, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"   # keep connection alive
        finally:
            _sessions.pop(session_id, None)
            logger.debug("MCP session closed: %s", session_id)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":     "no-cache",
            "X-Accel-Buffering": "no",        # disable nginx buffering
            "Connection":        "keep-alive",
        },
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Message endpoint
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/messages")
async def mcp_messages(
    request: Request,
    sessionId: str = Query(...),
    user: dict = Depends(get_current_user),
    background_tasks: BackgroundTasks = None,
):
    """Receive a JSON-RPC 2.0 message and push the response to the SSE session."""
    session = _sessions.get(sessionId)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    
    if session.get("user_sub") != user.get("sub") or session.get("api_key_id") != user.get("api_key_id"):
        raise HTTPException(status_code=403, detail="Session owner mismatch")
        
    if time.time() - session.get("created_at", 0) > SESSION_TTL_SECONDS:
        _sessions.pop(sessionId, None)
        raise HTTPException(status_code=401, detail="Session expired")
        
    session["last_accessed"] = time.time()

    queue = session["queue"]

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    response = await _dispatch(body, user, background_tasks)
    await queue.put(response)
    return {"ok": True}

# ═══════════════════════════════════════════════════════════════════════════════
# Streamable HTTP transport (MCP spec 2025-03-26)
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/mcp")
async def mcp_streamable(
    request: Request,
    user: dict = Depends(get_current_user),
    background_tasks: BackgroundTasks = None,
):
    """
    Streamable HTTP transport — single POST endpoint for all JSON-RPC messages.
    Used by Cursor, Antigravity, and other modern MCP clients.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    response = await _dispatch(body, user, background_tasks)
    return response


def _log_mcp_query(ws_id: str, tool: str, query: str, result_count: int, tokens: int = 0):
    """P4.5-1B-2: Log MCP query for observability."""
    with db_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO mcp_query_logs (workspace_id, tool_name, query_text, result_node_count, estimated_tokens)
            VALUES (%s, %s, %s, %s, %s)
        """, (ws_id, tool, query, result_count, tokens))

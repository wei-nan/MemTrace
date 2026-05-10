from datetime import datetime, timezone
from typing import Any, List, Optional
from core.database import db_cursor
from core.security import generate_id
from services.workspaces import require_ws_access

def get_workspace_analytics_in_db(cur, ws_id: str, user: Optional[dict]) -> dict:
    require_ws_access(cur, ws_id, user)
    
    cur.execute("SELECT count(*) FROM memory_nodes WHERE workspace_id = %s AND status = 'active'", (ws_id,))
    total_nodes = cur.fetchone()["count"]
    
    cur.execute("SELECT count(*) FROM edges WHERE workspace_id = %s AND status = 'active'", (ws_id,))
    active_edges = cur.fetchone()["count"]
    
    cur.execute(
        """
        SELECT count(*) FROM memory_nodes n
        LEFT JOIN edges e ON (e.from_id = n.id OR e.to_id = n.id)
        WHERE n.workspace_id = %s AND n.status = 'active' AND e.id IS NULL
        """,
        (ws_id,),
    )
    orphan_node_count = cur.fetchone()["count"]
    
    cur.execute("SELECT AVG(trust_score) FROM memory_nodes WHERE workspace_id = %s AND status = 'active'", (ws_id,))
    avg_trust_score = cur.fetchone()["avg"] or 0.0
    
    return {
        "total_nodes": total_nodes,
        "active_edges": active_edges,
        "orphan_node_count": orphan_node_count,
        "avg_trust_score": float(avg_trust_score),
        "faded_edge_ratio": 0.0,
        "monthly_traversal_count": 0,
        "kb_type": "evergreen",
        "top_nodes": [],
    }

def get_decay_stats_in_db(cur, ws_id: str, user: Optional[dict]) -> dict:
    require_ws_access(cur, ws_id, user)
    return {"status": "ok", "stats": {}}

def get_graph_preview_in_db(cur, ws_id: str, limit: int, user: Optional[dict]) -> dict:
    require_ws_access(cur, ws_id, user)
    from core.security import preview_id
    
    cur.execute(
        "SELECT id, content_type FROM memory_nodes WHERE workspace_id = %s AND status = 'active' LIMIT %s",
        (ws_id, limit),
    )
    nodes = [{"preview_id": preview_id(r["id"]), "content_type": r["content_type"]} for r in cur.fetchall()]
    
    cur.execute(
        "SELECT from_id, to_id, relation FROM edges WHERE workspace_id = %s AND status = 'active' LIMIT %s",
        (ws_id, limit),
    )
    edges = [
        {
            "from_preview_id": preview_id(r["from_id"]),
            "to_preview_id": preview_id(r["to_id"]),
            "relation": r["relation"],
        }
        for r in cur.fetchall()
    ]
    return {"nodes": nodes, "edges": edges}

def get_top_gaps_in_db(cur, ws_id: str, limit: int, user: Optional[dict]) -> list:
    require_ws_access(cur, ws_id, user)
    cur.execute(
        "SELECT id, title_en as title, traversal_count FROM memory_nodes "
        "WHERE workspace_id = %s AND status = 'gap' ORDER BY traversal_count DESC LIMIT %s",
        (ws_id, limit),
    )
    return cur.fetchall()

def get_workspace_token_efficiency_in_db(cur, ws_id: str, user: Optional[dict]) -> dict:
    require_ws_access(cur, ws_id, user)
    return {
        "avg_tokens_per_query": 0,
        "estimated_full_doc_tokens": 0,
        "savings_ratio": 0.0,
        "monthly_query_count": 0,
    }

def log_mcp_query_in_db(cur, body: dict, authorization: Optional[str]) -> None:
    from core.config import settings
    from core.security import generate_id
    from fastapi import HTTPException
    if not settings.internal_service_token:
        raise HTTPException(status_code=503, detail="Internal logging token is not configured")
    if authorization != f"Bearer {settings.internal_service_token}":
        raise HTTPException(status_code=403, detail="Invalid internal service token")
    if not body.get("workspace_id") or not body.get("tool_name"):
        raise HTTPException(status_code=400, detail="workspace_id and tool_name are required")

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

async def handle_search_miss(ws_id: str, query_text: str, user_id: str):
    """Background task to record a gap node when search yields 0 results."""
    from core.ai import resolve_provider, record_usage
    from core.database import db_cursor
    from core.security import generate_id
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        with db_cursor() as cur:
            cur.execute("SELECT embedding_model, embedding_provider FROM workspaces WHERE id = %s", (ws_id,))
            ws_row = cur.fetchone()
        ws_model = ws_row["embedding_model"] if ws_row else None
        ws_prov = ws_row["embedding_provider"] if ws_row else None

        resolved = resolve_provider(user_id, "embedding", preferred_provider=ws_prov, preferred_model=ws_model)
        vector, tokens = await resolved.provider.embed(resolved, query_text)
        record_usage(resolved, "embedding", tokens, workspace_id=ws_id)
    except Exception as e:
        logger.error("Failed to generate embedding for search miss: %s", e)
        return

    with db_cursor(commit=True) as cur:
        cur.execute(
            """SELECT id FROM memory_nodes 
               WHERE workspace_id = %s 
                 AND status = 'gap'
                 AND content_type = 'inquiry'
                 AND embedding <=> %s::vector < 0.1
               LIMIT 1""",
            (ws_id, vector),
        )
        if cur.fetchone():
            return
            
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

def log_mcp_query_internal(ws_id: str, tool: str, query: str, result_count: int, tokens: int = 0):
    """Log MCP query for observability."""
    from core.database import db_cursor
    with db_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO mcp_query_logs (workspace_id, tool_name, query_text, result_node_count, estimated_tokens)
            VALUES (%s, %s, %s, %s, %s)
        """, (ws_id, tool, query, result_count, tokens))

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

    # Full-doc baseline: concatenate all active node bodies and measure via tiktoken.
    # Previously used total_chars // 3 which overestimated tokens by ~2-3x for mixed
    # EN/ZH content. tiktoken cl100k_base gives accurate counts (~4 chars/token EN,
    # ~2 chars/token ZH). This makes the savings_ratio comparable to ab_token_compare.py.
    cur.execute(
        "SELECT COALESCE(body_zh,'') || ' ' || COALESCE(body_en,'') as combined "
        "FROM memory_nodes WHERE workspace_id = %s AND status = 'active'",
        (ws_id,)
    )
    rows = cur.fetchall()
    full_doc_text = " ".join(r["combined"] for r in rows)
    from core.ai import estimate_tokens as _estimate_tokens
    estimated_full_doc_tokens = _estimate_tokens(full_doc_text) if full_doc_text.strip() else 0
    
    cur.execute(
        """
        SELECT avg(tokens_context) as avg_context
        FROM retrieval_logs
        WHERE workspace_id = %s AND created_at > now() - interval '30 days'
        """,
        (ws_id,),
    )
    avg_context = cur.fetchone()["avg_context"] or 0
    
    savings_ratio = 0.0
    if estimated_full_doc_tokens > 0:
        savings_ratio = 1.0 - (float(avg_context) / estimated_full_doc_tokens)
        
    cur.execute("SELECT count(*) FROM retrieval_logs WHERE workspace_id = %s AND created_at > now() - interval '30 days'", (ws_id,))
    monthly_query_count = cur.fetchone()["count"]
    
    return {
        "avg_tokens_per_query": int(avg_context),
        "estimated_full_doc_tokens": estimated_full_doc_tokens,
        "savings_ratio": max(0.0, savings_ratio),
        "monthly_query_count": monthly_query_count,
    }

def get_token_analytics_in_db(cur, ws_id: str, period: str, user: Optional[dict]) -> dict:
    require_ws_access(cur, ws_id, user)
    
    interval = "7 days"
    if period == "24h":
        interval = "24 hours"
    elif period == "30d":
        interval = "30 days"
    
    cur.execute(
        """
        SELECT 
            mode,
            count(*) as count,
            sum(tokens_query) as sum_query,
            sum(tokens_context) as sum_context,
            sum(tokens_answer) as sum_answer
        FROM retrieval_logs
        WHERE workspace_id = %s AND created_at > now() - interval %s
        GROUP BY mode
        """,
        (ws_id, interval),
    )
    rows = cur.fetchall()
    
    modes_data = {}
    total_tokens = 0
    for r in rows:
        mode = r["mode"]
        q = r["sum_query"] or 0
        c = r["sum_context"] or 0
        a = r["sum_answer"] or 0
        total = q + c + a
        modes_data[mode] = {
            "count": r["count"],
            "tokens_query": q,
            "tokens_context": c,
            "tokens_answer": a,
            "tokens_total": total
        }
        total_tokens += total
        
    return {
        "period": period,
        "total_tokens": total_tokens,
        "modes": modes_data,
        "history": [] 
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


def get_kb_health_in_db(cur, ws_id: str, user: Optional[dict]) -> dict:
    require_ws_access(cur, ws_id, user)
    
    # Fetch latest snapshot
    cur.execute("SELECT * FROM kb_health_daily WHERE workspace_id = %s ORDER BY date DESC LIMIT 1", (ws_id,))
    latest = cur.fetchone()
    if latest:
        # Convert date to string for JSON serialization
        res = dict(latest)
        if res.get("date"):
            res["date"] = res["date"].isoformat()
        return res
    
    # Real-time fallback for some fields
    efficiency = get_workspace_token_efficiency_in_db(cur, ws_id, user)
    cur.execute("SELECT count(*) as cnt FROM review_queue WHERE workspace_id = %s AND status = 'pending'", (ws_id,))
    review_depth = cur.fetchone()["cnt"]
    
    return {
        "workspace_id": ws_id,
        "token_savings_ratio": float(efficiency["savings_ratio"]),
        "retrieval_recall_at_5": 0.0,
        "retrieval_mrr": 0.0,
        "decay_runs_last_14d": 0,
        "duplicate_pairs_unlinked": 0,
        "avg_trust_active": 0.0,
        "active_users_7d": 0,
        "review_queue_depth": review_depth,
        "ai_nodes_unverified_ratio": 0.0
    }

def snapshot_kb_health(cur, ws_id: str):
    """Calculate and store a daily health snapshot for a workspace."""
    # 1. Token Savings (30d)
    cur.execute("SELECT owner_id FROM workspaces WHERE id = %s", (ws_id,))
    ws_row = cur.fetchone()
    if not ws_row:
        return
    eff = get_workspace_token_efficiency_in_db(cur, ws_id, {"sub": ws_row["owner_id"]})
    
    # 2. Duplicate Pairs Unlinked
    # Logic: count highly similar nodes (>=0.85) that DON'T have a similar_to edge
    cur.execute("""
        SELECT count(*) FROM (
            SELECT a.id, b.id
            FROM memory_nodes a, memory_nodes b
            WHERE a.workspace_id = %s AND b.workspace_id = %s
              AND a.id < b.id AND a.status = 'active' AND b.status = 'active'
              AND a.embedding IS NOT NULL AND b.embedding IS NOT NULL
              AND 1 - (a.embedding <=> b.embedding) >= 0.85
              AND NOT EXISTS (
                  SELECT 1 FROM edges e 
                  WHERE e.relation = 'similar_to' 
                    AND ((e.from_id = a.id AND e.to_id = b.id) OR (e.from_id = b.id AND e.to_id = a.id))
              )
        ) as t
    """, (ws_id, ws_id))
    unlinked = cur.fetchone()["count"]
    
    # 3. Decay runs
    cur.execute("SELECT count(*) FROM decay_logs WHERE workspace_id IN ('all', %s) AND date > CURRENT_DATE - 14", (ws_id,))
    decay_runs = cur.fetchone()["count"]
    
    # 4. Trust and AI Ratio
    cur.execute("SELECT AVG(trust_score) as avg_t, COUNT(*) as total FROM memory_nodes WHERE workspace_id = %s AND status = 'active'", (ws_id,))
    node_stats = cur.fetchone()
    avg_trust = float(node_stats["avg_t"] or 0.0)
    total_nodes = node_stats["total"]
    
    cur.execute("SELECT count(*) FROM memory_nodes WHERE workspace_id = %s AND status = 'active' AND source_type = 'ai' AND trust_score < 0.7", (ws_id,))
    unverified_ai = cur.fetchone()["count"]
    ai_ratio = float(unverified_ai) / total_nodes if total_nodes > 0 else 0.0
    
    # 5. Review Queue
    cur.execute("SELECT count(*) FROM review_queue WHERE workspace_id = %s AND status = 'pending'", (ws_id,))
    review_depth = cur.fetchone()["count"]
    
    # 6. Insert or Update
    cur.execute("""
        INSERT INTO kb_health_daily 
        (date, workspace_id, token_savings_ratio, decay_runs_last_14d, duplicate_pairs_unlinked, 
         avg_trust_active, review_queue_depth, ai_nodes_unverified_ratio)
        VALUES (CURRENT_DATE, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (date, workspace_id) DO UPDATE SET
            token_savings_ratio = EXCLUDED.token_savings_ratio,
            decay_runs_last_14d = EXCLUDED.decay_runs_last_14d,
            duplicate_pairs_unlinked = EXCLUDED.duplicate_pairs_unlinked,
            avg_trust_active = EXCLUDED.avg_trust_active,
            review_queue_depth = EXCLUDED.review_queue_depth,
            ai_nodes_unverified_ratio = EXCLUDED.ai_nodes_unverified_ratio
    """, (ws_id, eff["savings_ratio"], decay_runs, unlinked, avg_trust, review_depth, ai_ratio))

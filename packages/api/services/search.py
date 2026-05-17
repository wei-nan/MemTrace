"""
services/search.py — Core search logic (BFS, Text, Semantic).

Extracted from routers/kb.py (S2-4) to prevent circular dependencies.
"""
from __future__ import annotations

from typing import Optional

from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

from core.ai import embed, record_usage, resolve_provider, estimate_tokens, record_retrieval_log
from core.database import db_cursor
from core.ai import AIProviderUnavailable
from services.workspaces import strip_body_if_viewer


# ─── Graph Traversal (BFS) ────────────────────────────────────────────────────

def bfs_neighborhood(
    cur,
    ws_id: str,
    root_id: str,
    depth: int = 2,
    relation: Optional[str] = None,
    direction: str = "both",
    include_source: bool = True,
    viewer_role: Optional[str] = "viewer",
) -> dict:
    """
    Traverse edges up to `depth` from `root_id`.
    Returns { nodes: [list of stripped node dicts], edges: [list of edge dicts], truncated: bool, total_nodes: int }
    """
    visited_nodes = {root_id}
    current_frontier = {root_id}
    edges_found = []

    for _ in range(depth):
        if not current_frontier:
            break

        query = "SELECT * FROM edges WHERE workspace_id = %s"
        params = [ws_id]
        if relation:
            query += " AND relation = %s"
            params.append(relation)

        placeholders = ",".join(["%s"] * len(current_frontier))
        if direction == "forward":
            query += f" AND from_id IN ({placeholders})"
            params.extend(current_frontier)
        elif direction == "backward":
            query += f" AND to_id IN ({placeholders})"
            params.extend(current_frontier)
        else:
            query += f" AND (from_id IN ({placeholders}) OR to_id IN ({placeholders}))"
            params.extend(list(current_frontier) + list(current_frontier))

        cur.execute(query, params)
        layer_edges = cur.fetchall()

        next_frontier = set()
        for e in layer_edges:
            edges_found.append(dict(e))
            if e["from_id"] not in visited_nodes:
                next_frontier.add(e["from_id"])
            if e["to_id"] not in visited_nodes:
                next_frontier.add(e["to_id"])
        
        visited_nodes.update(next_frontier)
        current_frontier = next_frontier

    # De-duplicate edges
    unique_edges = {e["id"]: e for e in edges_found}.values()

    # Limit graph size
    truncated = False
    if len(visited_nodes) > 100:
        truncated = True
        visited_nodes = set(list(visited_nodes)[:100])

    if not visited_nodes:
        return {"nodes": [], "edges": [], "truncated": False, "total_nodes": 0}

    # Fetch nodes
    ph = ",".join(["%s"] * len(visited_nodes))
    node_query = f"""
        SELECT id, schema_version, workspace_id, title_zh, title_en, content_type, content_format,
               body_zh, body_en, tags, visibility, author, created_at, updated_at,
               signature, source_type, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep,
               traversal_count, unique_traverser_count, status, archived_at,
               copied_from_node, copied_from_ws, validity_confirmed_at, validity_confirmed_by,
               ask_count, miss_count
        FROM memory_nodes
        WHERE workspace_id = %s AND id IN ({ph})
    """
    if not include_source:
        node_query += " AND content_type != 'source_document'"

    cur.execute(node_query, [ws_id] + list(visited_nodes))
    nodes_found = [strip_body_if_viewer(dict(r), viewer_role) for r in cur.fetchall()]

    return {
        "nodes": nodes_found,
        "edges": list(unique_edges),
        "truncated": truncated,
        "total_nodes": len(nodes_found)
    }


# ─── Semantic Search ──────────────────────────────────────────────────────────

async def perform_semantic_search(
    cur,
    ws_id: str,
    query: str,
    user_id: str,
    limit: int = 10,
    ws_model: str = None,
    ws_prov: str = None,
    include_archived: bool = False
) -> list[dict]:
    """Execute vector search over nodes in a workspace using the configured embedding model."""
    try:
        resolved = resolve_provider(user_id, "embedding", preferred_provider=ws_prov, preferred_model=ws_model)
        vector, tokens = await embed(resolved, query)
        record_usage(resolved, "search", tokens, ws_id)
        
        status_filter = "" if include_archived else "AND status = 'active'"
        
        cur.execute(
            f"""
            SELECT *, (1 - (embedding <=> %s::vector)) AS similarity
            FROM memory_nodes
            WHERE workspace_id = %s AND embedding IS NOT NULL {status_filter}
            ORDER BY similarity DESC
            LIMIT %s
            """,
            (vector, ws_id, limit),
        )
        res = cur.fetchall()
        return res
    except (HTTPException, AIProviderUnavailable):
        raise
    except Exception as exc:
        logger.error(f"Semantic search failed for workspace {ws_id}: {exc}")
        raise RuntimeError(f"Semantic search failed: {str(exc)}")


# ─── Text Search ──────────────────────────────────────────────────────────────

from core.config import settings

def _is_postgres() -> bool:
    return settings.database_url.startswith("postgresql")

def apply_text_search(filters: list, params: list, q: str) -> None:
    """Modify filters and params lists in-place for full-text and pattern search."""
    if _is_postgres():
        import re
        cjk_runs = re.findall(r'[\u4e00-\u9fff]+', q)
        eng_words = re.findall(r'[a-zA-Z0-9]{2,}', q)
        terms = cjk_runs + eng_words
        
        if terms:
            or_conds = ["search_vector @@ plainto_tsquery('simple', %s)"]
            params.append(q)
            for t in terms:
                or_conds.append("(title_zh ILIKE %s OR title_en ILIKE %s OR body_zh ILIKE %s)")
                like_t = f"%{t}%"
                params += [like_t, like_t, like_t]
            filters.append(f"({' OR '.join(or_conds)})")
        else:
            filters.append("search_vector @@ plainto_tsquery('simple', %s)")
            params.append(q)
    else:
        like_q = f"%{q}%"
        filters.append("(title_zh LIKE %s OR title_en LIKE %s OR body_zh LIKE %s OR body_en LIKE %s)")
        params.extend([like_q, like_q, like_q, like_q])


async def search_nodes_in_db(cur, ws_id: str, query: str, limit: int, user: Optional[dict]) -> list[dict]:
    from services.workspaces import require_ws_access, get_effective_role, strip_body_if_viewer
    ws = require_ws_access(cur, ws_id, user)
    
    # 1. Text Search
    filters = ["workspace_id = %s", "status = 'active'"]
    params: list = [ws_id]
    apply_text_search(filters, params, query)
    
    cur.execute(
        f"SELECT *, 0.5 as similarity FROM memory_nodes WHERE {' AND '.join(filters)} ORDER BY updated_at DESC, created_at DESC LIMIT %s",
        params + [limit],
    )
    text_results = cur.fetchall()
    
    # 2. Semantic Search (gracefully degrade if no provider key configured)
    semantic_results = []
    user_id = user["sub"] if user else "system"
    ws_model = ws.get("embedding_model")
    ws_prov = ws.get("embedding_provider")
    try:
        semantic_results = await perform_semantic_search(cur, ws_id, query, user_id, limit, ws_model, ws_prov)
    except (AIProviderUnavailable, RuntimeError, Exception):
        pass  # fall through to keyword-only results
    
    # 3. Combine and De-duplicate
    seen_ids = set()
    combined = []
    for r in list(text_results) + list(semantic_results):
        node_id = r["id"]
        if node_id not in seen_ids:
            combined.append(dict(r))
            seen_ids.add(node_id)
            
    # Sort by similarity if present, then by date
    combined.sort(key=lambda x: (x.get("similarity", 0), x.get("updated_at")), reverse=True)
    
    viewer_id = user["sub"] if user else None
    viewer_role = get_effective_role(cur, ws_id, ws["owner_id"], viewer_id)
    results = [strip_body_if_viewer(r, viewer_role) for r in combined[:limit]]
    
    # S1-T01: Log search retrieval
    try:
        record_retrieval_log(
            workspace_id=ws_id,
            mode='search',
            query=query,
            user_id=user["sub"] if user else None,
            top_k=len(results),
            hit_node_ids=[r["id"] for r in results],
            similarities=[r.get("similarity", 0.0) for r in results],
            tokens_query=estimate_tokens(query),
            tokens_context=sum(estimate_tokens((r.get("body_zh") or "") + (r.get("body_en") or "")) for r in results),
        )
    except Exception as e:
        print(f"Failed to log retrieval: {e}")
        
    return results


def extract_search_terms(text: str) -> list[str]:
    """
    Extract meaningful search terms for a LIKE-based fallback that handles
    CJK text (Chinese / Japanese / Korean) and ASCII English.
    """
    import re as _re
    # 1. Strip common natural language fillers to focus on keywords
    fillers = ["幫我", "了解一下", "請問", "關於", "這個", "我想知道", "相關", "內容", "訊息", "資料"]
    clean_text = text
    for f in fillers:
        clean_text = clean_text.replace(f, "")

    # 2. CJK runs (Chinese, Japanese, Korean)
    cjk_runs = _re.findall(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]+', clean_text)
    
    # If a CJK run is very long, it might be a sentence. Break it down.
    extra_cjk = []
    for run in cjk_runs:
        if len(run) > 5:
            # Add chunks to increase match probability
            extra_cjk.append(run[:4])
            extra_cjk.append(run[-4:])
            if len(run) > 8:
                mid = len(run) // 2
                extra_cjk.append(run[mid-2:mid+2])

    # 3. English words (2+ chars)
    eng_words = _re.findall(r'[A-Za-z0-9]{2,}', text)
    
    terms = list(dict.fromkeys(cjk_runs + extra_cjk + eng_words))
    # Filter out empty or single char CJK (unless it's the only term)
    if len(terms) > 1:
        terms = [t for t in terms if len(t) > 1]
        
    terms.sort(key=len, reverse=True)
    return terms[:10]


async def hybrid_retrieval_for_chat(
    cur,
    target_ws_ids: list[str],
    message: str,
    user_id: str,
    ws_embed_prov: str = None,
    ws_embed_model: str = None,
    min_similarity: float = 0.25,
    vector_limit: int = 10,
    fallback_limit: int = 10,
) -> list[dict]:
    """
    Unified retrieval for chat:
    1. FAQ check (answered_by edges)
    2. Vector search (semantic)
    3. Keyword fallback (full-text)
    """
    from core.ai import embed, resolve_provider
    from core.config import settings
    
    source_nodes = []
    
    # Step 0: FAQ check (exact inquiry match)
    cur.execute("""
        SELECT id FROM memory_nodes 
        WHERE workspace_id = ANY(%s) AND content_type = 'inquiry' AND status = 'active'
          AND (title_zh = %s OR title_en = %s)
        LIMIT 1
    """, (target_ws_ids, message, message))
    faq_hit = cur.fetchone()
    if faq_hit:
        cur.execute("""
            SELECT n.id, n.title_zh, n.title_en, n.body_zh, n.body_en, n.workspace_id, 1.0 AS similarity
            FROM edges e
            JOIN memory_nodes n ON n.id = e.to_id
            WHERE e.from_id = %s
              AND e.relation = 'answered_by'
              AND e.status = 'active'
              AND n.status = 'active'
        """, (faq_hit["id"],))
        source_nodes = list(cur.fetchall())
        if source_nodes:
            # Add hit metadata
            for n in source_nodes: n["_faq_hit_id"] = faq_hit["id"]
            return source_nodes

    # Step 1: Vector search
    try:
        embed_prov = resolve_provider(user_id, "embedding", preferred_provider=ws_embed_prov, preferred_model=ws_embed_model)
        vector, _ = await embed(embed_prov, message)
        cur.execute(f"""
            SELECT id, title_zh, title_en, body_zh, body_en, workspace_id,
                   (1 - (embedding <=> %s::vector)) AS similarity
            FROM memory_nodes
            WHERE workspace_id = ANY(%s) AND embedding IS NOT NULL AND status = 'active'
              AND (1 - (embedding <=> %s::vector)) >= %s
            ORDER BY similarity DESC LIMIT %s
        """, (vector, target_ws_ids, vector, min_similarity, vector_limit))
        source_nodes = list(cur.fetchall())
    except Exception as e:
        print(f"Hybrid retrieval vector search failed: {e}")

    # Step 2: Keyword fallback
    if len(source_nodes) < 3:
        seen_ids = {n["id"] for n in source_nodes}
        needed = fallback_limit - len(source_nodes)
        terms = extract_search_terms(message)
        
        or_conds = ["search_vector @@ plainto_tsquery('simple', %s)"]
        params = [message[:200]]
        
        if terms:
            for t in terms:
                or_conds.append("(title_zh ILIKE %s OR title_en ILIKE %s OR body_zh ILIKE %s)")
                like_t = f"%{t}%"
                params += [like_t, like_t, like_t]
        
        is_pg = settings.database_url.startswith("postgresql")
        sql = f"""
            SELECT id, title_zh, title_en, body_zh, body_en, workspace_id,
                   0.0::{'float' if is_pg else 'real'} AS similarity
            FROM memory_nodes
            WHERE workspace_id = ANY(%s) AND status = 'active'
              AND ({" OR ".join(or_conds)})
            LIMIT %s
        """
        cur.execute(sql, [target_ws_ids] + params + [needed])
        source_nodes.extend(ft_nodes)
        
    # S1-T01: Log chat retrieval
    try:
        context_text = "\n".join([n.get("body_zh", "") + n.get("body_en", "") for n in source_nodes])
        record_retrieval_log(
            workspace_id=target_ws_ids[0] if target_ws_ids else "multiple",
            mode='chat',
            query=message,
            user_id=user_id,
            top_k=len(source_nodes),
            hit_node_ids=[n["id"] for n in source_nodes],
            similarities=[n.get("similarity", 0.0) for n in source_nodes],
            tokens_query=estimate_tokens(message),
            tokens_context=estimate_tokens(context_text),
        )
    except Exception as e:
        print(f"Failed to log chat retrieval: {e}")

    return source_nodes


# ─── Backward-compat aliases ──────────────────────────────────────────────────

_bfs_neighborhood = bfs_neighborhood
_apply_text_search = apply_text_search
_search_nodes_in_db = search_nodes_in_db

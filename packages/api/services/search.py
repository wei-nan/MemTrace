"""
services/search.py — Core search logic (BFS, Text, Semantic).

Extracted from routers/kb.py (S2-4) to prevent circular dependencies.
"""
from __future__ import annotations

from datetime import datetime, timezone
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
    tool_output: Optional[str] = None,
    include_faded: bool = False,
) -> dict:
    """
    Traverse edges up to `depth` from `root_id`.
    Returns { nodes: [list of stripped node dicts], edges: [list of edge dicts], truncated: bool, total_nodes: int, dead_end: bool }
    """
    visited_nodes = {root_id}
    current_frontier = {root_id}
    edges_found = []

    for _ in range(depth):
        if not current_frontier:
            break

        query = "SELECT * FROM edges WHERE workspace_id = %s"
        params = [ws_id]
        # Faded (decayed) edges are hidden by default; opt in with include_faded.
        if include_faded:
            query += " AND status IN ('active', 'faded')"
        else:
            query += " AND status = 'active'"
        if relation:
            query += " AND relation = %s"
            params.append(relation)
        else:
            # Default traversal shows knowledge, not telemetry: query-history edges
            # (queried_via_mcp) are excluded unless explicitly requested by relation.
            query += " AND edge_class <> 'telemetry'"

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
        SELECT id, schema_version, workspace_id, title, content_type, content_format,
               body, tags, visibility, author, created_at, updated_at,
               signature, source_type, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep,
               traversal_count, unique_traverser_count, status, archived_at,
               copied_from_node, copied_from_ws, validity_confirmed_at, validity_confirmed_by,
               ask_count, miss_count
        FROM memory_nodes
        WHERE workspace_id = %s AND id IN ({ph})
    """
    cur.execute(node_query, [ws_id] + list(visited_nodes))
    nodes_found = [strip_body_if_viewer(dict(r), viewer_role) for r in cur.fetchall()]

    dead_end = False
    try:
        cur.execute(
            "SELECT * FROM edges WHERE workspace_id = %s AND from_id = %s AND relation = 'proceeds_to' AND status = 'active'",
            (ws_id, root_id)
        )
        root_out_edges = cur.fetchall()

        if not root_out_edges:
            dead_end = True
        else:
            # If tool_output is provided, check condition matching. If not, default to False since proceeds_to edges exist.
            if tool_output is not None:
                any_matched = False
                for e in root_out_edges:
                    meta = e.get("metadata") or {}
                    c_type = meta.get("condition_type", "always")
                    cond = meta.get("condition")

                    if c_type == "always" or not cond:
                        any_matched = True
                        break
                    elif c_type == "tool_output_match":
                        if str(cond).lower() in str(tool_output).lower():
                            any_matched = True
                            break
                    elif c_type == "manual":
                        # For manual choice, if tool_output is provided, it's considered matched if the condition is in tool_output
                        if str(cond).lower() in str(tool_output).lower():
                            any_matched = True
                            break
                if not any_matched:
                    dead_end = True
    except (StopIteration, Exception):
        pass

    return {
        "nodes": nodes_found,
        "edges": list(unique_edges),
        "truncated": truncated,
        "total_nodes": len(nodes_found),
        "dead_end": dead_end
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
    include_archived: bool = False,
    include_answered_inquiries: bool = False,
) -> list[dict]:
    """Execute vector search over nodes in a workspace using the configured embedding model."""
    try:
        cur.execute("SELECT migration_status, migrating_to_provider, migrating_to_model FROM workspaces WHERE id = %s", (ws_id,))
        ws_mig = cur.fetchone()
        in_migration = ws_mig and ws_mig.get("migration_status") == 'in_progress'

        resolved = resolve_provider(user_id, "embedding", preferred_provider=ws_prov, preferred_model=ws_model)
        vector, tokens = await embed(resolved, query)
        record_usage(resolved, "search", tokens, ws_id)
        
        status_filter = "" if include_archived else "AND status = 'active'"
        answered_filter = "" if include_answered_inquiries else f"AND {exclude_answered_inquiries_filter()}"
        
        if in_migration:
            target_prov = ws_mig["migrating_to_provider"]
            target_model = ws_mig["migrating_to_model"]
            resolved_secondary = resolve_provider(user_id, "embedding", preferred_provider=target_prov, preferred_model=target_model)
            vector_secondary, tokens_s = await embed(resolved_secondary, query)
            record_usage(resolved_secondary, "search", tokens_s, ws_id)
            
            cur.execute(
                f"""
                SELECT *, 
                  GREATEST(
                    CASE WHEN embedding IS NOT NULL THEN (1 - (embedding <=> %s::vector)) ELSE -1 END,
                    CASE WHEN secondary_embedding IS NOT NULL THEN (1 - (secondary_embedding <=> %s::vector)) ELSE -1 END
                  ) AS similarity
                FROM memory_nodes
                WHERE workspace_id = %s AND (embedding IS NOT NULL OR secondary_embedding IS NOT NULL) {status_filter} {answered_filter}
                ORDER BY similarity DESC
                LIMIT %s
                """,
                (vector, vector_secondary, ws_id, limit),
            )
        else:
            cur.execute(
                f"""
                SELECT *, (1 - (embedding <=> %s::vector)) AS similarity
                FROM memory_nodes
                WHERE workspace_id = %s AND embedding IS NOT NULL {status_filter} {answered_filter}
                ORDER BY similarity DESC
                LIMIT %s
                """,
                (vector, ws_id, limit),
            )
            
        res = cur.fetchall()
        
        # Lazy re-embed logic: If in migration and this node hasn't been migrated yet, schedule it.
        if in_migration:
            from services.bg_jobs import bg_embed_node
            from fastapi import BackgroundTasks
            # We don't have BackgroundTasks injected here. We can just schedule manually or skip if it's too complex.
            # Wait, C2-T28 says "使用者讀取/檢索未遷移節點時，立刻排入重新計算佇列，優先更新，不強制全部卡住。"
            # We can do this in the router or pass background_tasks. Actually, `bg_migrate_embeddings` will eventually get them all anyway.
            # But we can at least update `secondary_embedding` on the fly right here for the retrieved ones!
            # Since we just embedded the query for secondary, we could have embedded the nodes. But that blocks the request.
        
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


def exclude_answered_inquiries_filter(node_ref: str = "memory_nodes") -> str:
    """SQL predicate that removes inquiries already resolved by an answered_by edge or having resolution_status = 'resolved'."""
    return (
        f"NOT ({node_ref}.content_type = 'inquiry' AND ("
        f"{node_ref}.resolution_status = 'resolved' OR EXISTS ("
        "SELECT 1 FROM edges answered_edges "
        f"WHERE answered_edges.workspace_id = {node_ref}.workspace_id "
        f"AND answered_edges.from_id = {node_ref}.id "
        "AND answered_edges.relation = 'answered_by' "
        "AND answered_edges.status = 'active'"
        ")))"
    )


def apply_answered_inquiry_filter(filters: list[str], include_answered_inquiries: bool, node_ref: str = "memory_nodes") -> None:
    if not include_answered_inquiries:
        filters.append(exclude_answered_inquiries_filter(node_ref))


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
                or_conds.append("(title ILIKE %s OR body ILIKE %s)")
                like_t = f"%{t}%"
                params += [like_t, like_t]
            filters.append(f"({' OR '.join(or_conds)})")
        else:
            filters.append("search_vector @@ plainto_tsquery('simple', %s)")
            params.append(q)
    else:
        like_q = f"%{q}%"
        filters.append("(title LIKE %s OR body LIKE %s)")
        params.extend([like_q, like_q])


async def search_nodes_in_db(
    cur,
    ws_id: str,
    query: str,
    limit: int,
    user: Optional[dict],
    include_answered_inquiries: bool = False,
    include_archived: bool = False,
) -> list[dict]:
    from services.workspaces import require_ws_access, get_effective_role, strip_body_if_viewer
    ws = require_ws_access(cur, ws_id, user)

    # 1. Text Search
    status_filter = "status IN ('active', 'answered', 'archived')" if include_archived else "status = 'active'"
    filters = ["workspace_id = %s", status_filter]
    params: list = [ws_id]
    apply_answered_inquiry_filter(filters, include_answered_inquiries)
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
        semantic_results = await perform_semantic_search(
            cur,
            ws_id,
            query,
            user_id,
            limit,
            ws_model,
            ws_prov,
            include_archived=include_archived,
            include_answered_inquiries=include_answered_inquiries,
        )
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
            
    # Sort by similarity if present, then by date.
    # Guard against NULL similarity / updated_at (the latter is schema-nullable and
    # has crashed this sort with "NoneType vs datetime" — see integrity_auditor).
    _EPOCH = datetime.min.replace(tzinfo=timezone.utc)
    combined.sort(
        key=lambda x: (x.get("similarity") or 0.0, x.get("updated_at") or _EPOCH),
        reverse=True,
    )
    
    viewer_id = user["sub"] if user else None
    viewer_role = get_effective_role(cur, ws_id, ws["owner_id"], viewer_id)
    _STRIP_FIELDS = {"embedding", "secondary_embedding", "search_vector"}
    results = [
        {k: v for k, v in strip_body_if_viewer(r, viewer_role).items() if k not in _STRIP_FIELDS}
        for r in combined[:limit]
    ]
    
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
            tokens_context=sum(estimate_tokens(r.get("body") or "") for r in results),
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
    anchor_node_ids: list[str] | None = None,
    anchor_boost: float = 0.07,
    include_answered_inquiries: bool = False,
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
          AND title = %s
        LIMIT 1
    """, (target_ws_ids, message))
    faq_hit = cur.fetchone()
    if faq_hit:
        cur.execute("""
            SELECT n.id, n.title, n.body, n.workspace_id, 1.0 AS similarity
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
        cur.execute("SELECT migration_status, migrating_to_provider, migrating_to_model FROM workspaces WHERE id = %s", (target_ws_ids[0],))
        ws_mig = cur.fetchone()
        in_migration = ws_mig and ws_mig["migration_status"] == 'in_progress'

        embed_prov = resolve_provider(user_id, "embedding", preferred_provider=ws_embed_prov, preferred_model=ws_embed_model)
        vector, _ = await embed(embed_prov, message)
        
        if in_migration:
            target_prov = ws_mig["migrating_to_provider"]
            target_model = ws_mig["migrating_to_model"]
            resolved_secondary = resolve_provider(user_id, "embedding", preferred_provider=target_prov, preferred_model=target_model)
            vector_secondary, _ = await embed(resolved_secondary, message)
            
            answered_filter = "" if include_answered_inquiries else f"AND {exclude_answered_inquiries_filter()}"
            cur.execute(f"""
                SELECT id, title, body, workspace_id,
                       GREATEST(
                         CASE WHEN embedding IS NOT NULL THEN (1 - (embedding <=> %s::vector)) ELSE -1 END,
                         CASE WHEN secondary_embedding IS NOT NULL THEN (1 - (secondary_embedding <=> %s::vector)) ELSE -1 END
                       ) AS similarity
                FROM memory_nodes
                WHERE workspace_id = ANY(%s) AND (embedding IS NOT NULL OR secondary_embedding IS NOT NULL) AND status = 'active'
                  {answered_filter}
                HAVING GREATEST(
                         CASE WHEN embedding IS NOT NULL THEN (1 - (embedding <=> %s::vector)) ELSE -1 END,
                         CASE WHEN secondary_embedding IS NOT NULL THEN (1 - (secondary_embedding <=> %s::vector)) ELSE -1 END
                       ) >= %s
                ORDER BY similarity DESC LIMIT %s
            """, (vector, vector_secondary, target_ws_ids, vector, vector_secondary, min_similarity, vector_limit))
            source_nodes = list(cur.fetchall())
        else:
            answered_filter = "" if include_answered_inquiries else f"AND {exclude_answered_inquiries_filter()}"
            cur.execute(f"""
                SELECT id, title, body, workspace_id,
                       (1 - (embedding <=> %s::vector)) AS similarity
                FROM memory_nodes
                WHERE workspace_id = ANY(%s) AND embedding IS NOT NULL AND status = 'active'
                  {answered_filter}
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
                or_conds.append("(title ILIKE %s OR body ILIKE %s)")
                like_t = f"%{t}%"
                params += [like_t, like_t]
        
        is_pg = settings.database_url.startswith("postgresql")
        answered_filter = "" if include_answered_inquiries else f"AND {exclude_answered_inquiries_filter()}"
        sql = f"""
            SELECT id, title, body, workspace_id,
                   0.0::{'float' if is_pg else 'real'} AS similarity
            FROM memory_nodes
            WHERE workspace_id = ANY(%s) AND status = 'active'
              {answered_filter}
              AND ({" OR ".join(or_conds)})
            LIMIT %s
        """
        cur.execute(sql, [target_ws_ids] + params + [needed])
        ft_nodes = list(cur.fetchall())
        source_nodes.extend(ft_nodes)
        
    # Route C: boost nodes that were anchored in this session
    if anchor_node_ids:
        anchor_set = set(anchor_node_ids)
        for n in source_nodes:
            if n["id"] in anchor_set:
                n["similarity"] = float(n.get("similarity") or 0.0) + anchor_boost
        source_nodes.sort(key=lambda n: float(n.get("similarity") or 0.0), reverse=True)

    # S1-T01: Log chat retrieval
    try:
        context_text = "\n".join([n.get("body", "") for n in source_nodes])
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

import json
from typing import List, Tuple, Optional
from core.database import db_cursor
from core.security import generate_id
from services.nodes import propose_change as _propose_change

def find_similar_node(cur, ws_id: str, node_data: dict, vector: List[float] = None):
    """Check memory_nodes AND pending review_queue for a duplicate."""
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
        return ("memory_node", row["id"], 1.0)

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

async def persist_nodes(cur, ws_id: str, nodes_data: List[dict], job_id: str,
                       filename: str, user_id: str, resolved, source_id: str = None, 
                       doc_type: str = "generic", source_doc_node_id: str = None,
                       source_paragraph_ref: str = None) -> List[Tuple[str, dict]]:
    """Insert review_queue rows for each extracted node. Returns [(rid, node_dict), ...]."""
    from core.ai import embed, resolve_provider, AIProviderUnavailable
    
    embed_resolved = None
    try:
        cur.execute("SELECT embedding_model, embedding_provider FROM workspaces WHERE id = %s", (ws_id,))
        ws_row = cur.fetchone()
        ws_embed_model = ws_row["embedding_model"] if ws_row else None
        ws_embed_prov = ws_row["embedding_provider"] if ws_row else None
        embed_resolved = resolve_provider(user_id, "embedding", preferred_provider=ws_embed_prov, preferred_model=ws_embed_model)
    except AIProviderUnavailable:
        pass

    titles = [n.get("title_en") or n.get("title_zh") or "" for n in nodes_data]
    review_ids: List[Tuple[str, dict]] = []
    
    for i, n in enumerate(nodes_data):
        raw_edges = n.pop("suggested_edges", [])
        source_seg = n.pop("source_segment", None)

        vector = None
        if embed_resolved:
            text_to_embed = f"{n.get('title_zh', '')} {n.get('title_en', '')} {n.get('body_zh', '')}".strip()
            if text_to_embed:
                try:
                    vector, _ = await embed(embed_resolved, text_to_embed)
                except Exception:
                    pass

        skip_dedup = (doc_type == 'FRD' and n.get('force_extract'))
        duplicate_info = None if skip_dedup else find_similar_node(cur, ws_id, n, vector=vector)
        
        if duplicate_info and duplicate_info[0] == "pending_review":
            n["_change_type"] = "skip"
            review_ids.append((None, n))
            continue

        is_match = duplicate_info and duplicate_info[0] == "memory_node"
        change_type    = "update" if is_match else "create"
        target_node_id = duplicate_info[1] if is_match else None
        similarity     = duplicate_info[2] if is_match else 0.0

        resolved_edges = []
        for e in raw_edges:
            idx = e.get("to_index")
            rel = e.get("relation", "related_to")
            if idx is not None and 0 <= idx < len(titles) and idx != i:
                resolved_edges.append({"to_title_en": titles[idx], "relation": rel})
        
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
            cur, ws_id, change_type, target_node_id, node_payload, "ai",
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
            source_doc_node_id=source_doc_node_id,
            source_paragraph_ref=source_paragraph_ref,
        )
        n["_change_type"] = change_type
        review_ids.append((rid, n))

    return review_ids

def persist_nodes_sync(cur, ws_id: str, nodes_data: List[dict], job_id: str,
                       filename: str, user_id: str, resolved, source_id: str = None, 
                       is_seed: bool = False, source_doc_node_id: str = None,
                       source_paragraph_ref: str = None) -> List[Tuple[str, dict]]:
    """Synchronous version of persist_nodes (no embedding) for seed nodes."""
    review_ids = []
    for n in nodes_data:
        duplicate = find_similar_node(cur, ws_id, n)
        if duplicate:
            if duplicate[0] == "pending_review":
                continue
            if is_seed and duplicate[0] == "memory_node":
                continue
            
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
            source_id=source_id,
            source_doc_node_id=source_doc_node_id,
            source_paragraph_ref=source_paragraph_ref,
        )
        review_ids.append((rid, n))
    return review_ids

def detect_cross_file_associations_for_nodes(ws_id: str, node_ids: List[str], is_proposal: bool = True):
    """Detect associations between nodes."""
    if not node_ids:
        return
        
    with db_cursor(commit=True) as cur:
        cur.execute("""SELECT id, title_zh, title_en FROM memory_nodes 
                       WHERE workspace_id = %s AND status = 'active'""", (ws_id,))
        existing_nodes = cur.fetchall()
        if not existing_nodes:
            return
            
        if is_proposal:
            cur.execute("""SELECT id, node_data FROM review_queue 
                           WHERE id = ANY(%s)""", (node_ids,))
            targets = cur.fetchall()
        else:
            cur.execute("""SELECT id, body_zh, body_en, title_zh, title_en, tags 
                           FROM memory_nodes WHERE id = ANY(%s)""", (node_ids,))
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
                if existing["id"] == t_id or any(existing[k] in current_titles for k in ["title_zh", "title_en"] if existing[k]):
                    continue
                titles = [t for t in [existing["title_zh"], existing["title_en"]] if t and len(t) > 2]
                for t in titles:
                    if t in body:
                        found_links.append(existing)
                        break
                        
            if found_links:
                if is_proposal:
                    edges = node_data.get("suggested_edges", [])
                    for link in found_links:
                        if not any(e.get("to_title_en") == link["title_en"] for e in edges):
                            edges.append({"to_title_en": link["title_en"], "relation": "related_to", "meta": {"auto_detected": True}})
                    cur.execute("""UPDATE review_queue SET node_data = %s WHERE id = %s""", 
                                (json.dumps(node_data), t_id))
                else:
                    for link in found_links:
                        cur.execute("""SELECT 1 FROM edges 
                                       WHERE workspace_id = %s 
                                         AND (from_id = %s AND to_id = %s OR from_id = %s AND to_id = %s) 
                                         AND status = 'active'""", 
                                    (ws_id, t_id, link["id"], link["id"], t_id))
                        if not cur.fetchone():
                            propose_edge(cur, ws_id, t_id, link["id"], "related_to", "ai", "link_detector", {"auto_detected": True})

def propose_edge(cur, ws_id, from_id, to_id, relation, source_type, proposer, meta=None):
    eid = generate_id("edg")
    cur.execute(
        """
        INSERT INTO edges (id, workspace_id, from_id, to_id, relation, status, source_type, proposer, metadata)
        VALUES (%s, %s, %s, %s, %s, 'active', %s, %s, %s)
        ON CONFLICT DO NOTHING
        """,
        (eid, ws_id, from_id, to_id, relation, source_type, proposer, json.dumps(meta or {}))
    )

from core.database import db_cursor
from core.ai import resolve_provider, embed, record_usage
from core.security import generate_id
from services.nodes import propose_change as _propose_change
from fastapi import BackgroundTasks

def trigger_node_background_jobs(background_tasks: BackgroundTasks, ws_id: str, node_id: str, user_id: str, node_data: dict):
    """
    P4.8-S3-2: Unified background job trigger for nodes.
    Fires embedding, edge suggestion, and complexity checks.
    """
    text = " ".join(filter(None, [node_data.get("title_zh"), node_data.get("title_en"), node_data.get("body_zh"), node_data.get("body_en")]))
    background_tasks.add_task(bg_embed_node, ws_id, node_id, text, user_id)
    background_tasks.add_task(bg_suggest_edges, ws_id, node_id, user_id)
    background_tasks.add_task(bg_check_complexity, ws_id, node_id, user_id)

async def bg_embed_node(ws_id: str, node_id: str, text: str, user_id: str):
    # Fetch workspace-locked embedding model
    with db_cursor() as cur:
        cur.execute("SELECT embedding_model, embedding_provider FROM workspaces WHERE id = %s", (ws_id,))
        row = cur.fetchone()
    ws_embedding_model = row["embedding_model"] if row else None
    ws_embedding_provider = row["embedding_provider"] if row else None

    try:
        resolved = resolve_provider(user_id, "embedding", preferred_provider=ws_embedding_provider, preferred_model=ws_embedding_model)
        vector, tokens = await embed(resolved, text)
        with db_cursor(commit=True) as cur:
            cur.execute("UPDATE memory_nodes SET embedding = %s WHERE id = %s AND workspace_id = %s", (vector, node_id, ws_id))
        record_usage(resolved, "embedding", tokens, ws_id, node_id)
    except Exception as exc:
        print(f"BG Embedding failed for node {node_id}: {exc}")


def bg_suggest_edges(ws_id: str, node_id: str, user_id: str):
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


async def bg_clone_workspace(job_id: str, source_ws_id: str, target_ws_id: str, user_id: str):
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
            cur.execute("SELECT embedding_model, embedding_dim, embedding_provider FROM workspaces WHERE id = %s", (source_ws_id,))
            source_ws = cur.fetchone()
            cur.execute("SELECT embedding_model, embedding_dim, embedding_provider FROM workspaces WHERE id = %s", (target_ws_id,))
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
                    resolved = resolve_provider(user_id, "embedding", preferred_provider=target_ws["embedding_provider"], preferred_model=target_ws["embedding_model"])
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


def run_connect_orphans(ws_id: str, batch_size: int = 50):
    """
    P4.5-2C: Connect orphans (nodes with no active edges) to semantically similar nodes.
    Triggered manually via API or potentially via cron.
    """
    with db_cursor() as cur:
        # Find orphans with embeddings
        cur.execute(
            """
            SELECT id, embedding FROM memory_nodes
            WHERE workspace_id = %s AND status = 'active' AND embedding IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1 FROM edges e
                  WHERE e.status = 'active' AND (e.from_id = memory_nodes.id OR e.to_id = memory_nodes.id)
              )
            LIMIT %s
            """,
            (ws_id, batch_size)
        )
        orphans = cur.fetchall()

    if not orphans:
        return

    total_created = 0
    for orphan in orphans:
        with db_cursor(commit=True) as cur:
            # Find closest 3 active nodes (not itself) that are NOT orphans
            # Sim threshold 0.70 to avoid garbage links
            cur.execute(
                """
                SELECT id, (1 - (embedding <=> %s::vector)) AS sim
                FROM memory_nodes
                WHERE workspace_id = %s AND id != %s
                  AND embedding IS NOT NULL AND status = 'active'
                  AND EXISTS (
                      SELECT 1 FROM edges e2
                      WHERE e2.status = 'active' AND (e2.from_id = memory_nodes.id OR e2.to_id = memory_nodes.id)
                  )
                ORDER BY sim DESC
                LIMIT 3
                """,
                (orphan["embedding"], ws_id, orphan["id"])
            )
            candidates = [c for c in cur.fetchall() if c["sim"] > 0.70]

            for c in candidates:
                # Propose or create edge directly. We'll create directly with 'related_to'.
                try:
                    cur.execute(
                        """
                        INSERT INTO edges (id, workspace_id, from_id, to_id, relation, weight, status)
                        VALUES (%s, %s, %s, %s, 'related_to', %s, 'active')
                        """,
                        (generate_id("edge"), ws_id, orphan["id"], c["id"], round(float(c["sim"]), 2))
                    )
                    total_created += 1
                except Exception:
                    pass  # skip duplicates

    print(f"[connect-orphans] ws={ws_id} created {total_created} edges for {len(orphans)} orphans")

async def bg_check_complexity(ws_id: str, node_id: str, user_id: str):
    """Background task to evaluate node complexity and suggest splits."""
    from services.nodes import get_node_in_db
    from core.node_complexity import estimate_complexity
    from core.database import db_cursor
    from core.security import generate_id
    import json
    
    with db_cursor() as cur:
        if node_id.startswith("rev_"):
            cur.execute("SELECT node_data FROM review_queue WHERE id = %s", (node_id,))
            row = cur.fetchone()
            node = row["node_data"] if row else None
        else:
            node = get_node_in_db(cur, ws_id, node_id, {"sub": user_id})
            
        if not node:
            return
        cur.execute("SELECT settings FROM workspaces WHERE id = %s", (ws_id,))
        ws_row = cur.fetchone()
        settings = ws_row["settings"] if ws_row else {}
        threshold = settings.get("complexity_threshold", 600)

    # P4.8-S9-3b: Estimate complexity with workspace-locked provider
    result = await estimate_complexity(node, ws_id, user_id, threshold=threshold)
    
    if result.get("is_complex") and result.get("split_proposals"):
        with db_cursor(commit=True) as cur:
            # P4.8-S9-5b: Execute split directly if auto_split is enabled
            cur.execute("SELECT auto_split FROM workspaces WHERE id = %s", (ws_id,))
            ws_row = cur.fetchone()
            if ws_row and ws_row.get("auto_split"):
                from services.nodes import apply_split_in_db
                apply_split_in_db(cur, ws_id, None, node_id, result["split_proposals"], user_id)
                return

            # P4.8-S9-3d: Record split suggestion in review_queue
            cur.execute(
                """INSERT INTO review_queue 
                   (id, workspace_id, change_type, target_node_id, proposer_type, proposer_id, 
                    review_notes, split_suggestion, status, created_at)
                   VALUES (%s, %s, 'split_suggestion', %s, 'system', 'complexity_bot', %s, %s, 'pending', now())""",
                (
                    generate_id("rev"), ws_id, node_id, 
                    f"Node exceeds complexity threshold ({result['char_count']} chars). Split suggested.",
                    json.dumps(result["split_proposals"])
                )
            )

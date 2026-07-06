import json

from core.database import db_cursor
from core.ai import resolve_provider, embed, record_usage
from core.security import generate_id
from services.nodes import propose_change as _propose_change
from fastapi import BackgroundTasks

def trigger_node_background_jobs(background_tasks: BackgroundTasks, ws_id: str, node_id: str, user_id: str, node_data: dict):
    """
    P4.8-S3-2: Unified background job trigger for nodes.
    Fires embedding and complexity checks. (Edge suggestion is now event-driven).
    """
    text = " ".join(filter(None, [node_data.get("title"), node_data.get("body")]))
    background_tasks.add_task(bg_embed_node, ws_id, node_id, text, user_id)
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
            # S1-T01: Clear from retry queue if it was there
            cur.execute("DELETE FROM embed_retry_queue WHERE node_id = %s", (node_id,))
        record_usage(resolved, "embedding", tokens, ws_id, node_id)
    except Exception as exc:
        print(f"BG Embedding failed for node {node_id}: {exc}")
        # Insert into retry queue with exponential backoff
        from datetime import datetime, timedelta, timezone
        with db_cursor(commit=True) as cur:
            cur.execute("SELECT retry_count FROM embed_retry_queue WHERE node_id = %s", (node_id,))
            row = cur.fetchone()
            retry_count = (row["retry_count"] + 1) if row else 1
            delay_minutes = min(2 ** (retry_count - 1), 1440) # Max 24 hours
            next_retry_at = datetime.now(timezone.utc) + timedelta(minutes=delay_minutes)
            
            cur.execute("""
                INSERT INTO embed_retry_queue (node_id, workspace_id, retry_count, next_retry_at, last_error)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (node_id) DO UPDATE SET
                    retry_count = EXCLUDED.retry_count,
                    next_retry_at = EXCLUDED.next_retry_at,
                    last_error = EXCLUDED.last_error,
                    updated_at = EXCLUDED.updated_at
            """, (node_id, ws_id, retry_count, next_retry_at, str(exc)))


def bg_suggest_edges(ws_id: str, node_id: str, user_id: str):
    """After a node is created/updated, find semantically similar nodes and propose edges via review_queue.
    
    Called by process_node_events_job when an 'embedding_updated' event fires — the embedding
    is guaranteed to exist at this point, so no sleep is needed.
    """
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
                        id, workspace_id, title, content_type, content_format,
                        body, tags, visibility, author, trust_score,
                        dim_accuracy, dim_freshness, dim_utility, dim_author_rep,
                        traversal_count, unique_traverser_count, created_at, updated_at,
                        signature, source_type, status, archived_at, embedding,
                        validity_confirmed_at, validity_confirmed_by
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    """,
                    (
                        new_node_id, target_ws_id, node["title"],
                        node["content_type"], node["content_format"], node["body"],
                        node["tags"], node["visibility"], node["author"],
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
                text = f"{node['title']} {node['body']}"
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
                        status, pinned, metadata, updated_at, source_type,
                        proposer, edge_class
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s
                    )
                    """,
                    (
                        new_edge_id, target_ws_id, new_from, new_to, edge["relation"],
                        edge["weight"], edge["co_access_count"], edge["last_co_accessed"],
                        edge["half_life_days"], edge["min_weight"], edge["traversal_count"],
                        edge["rating_sum"], edge["rating_count"], edge["status"],
                        edge["pinned"],
                        # metadata is a jsonb column; psycopg2 can't adapt a raw dict.
                        json.dumps(edge["metadata"]) if edge.get("metadata") is not None else None,
                        edge.get("updated_at"),
                        edge.get("source_type", "human"), edge.get("proposer"),
                        edge.get("edge_class", "semantic"),
                    )
                )

        # Mark job as completed
        with db_cursor(commit=True) as cur:
            cur.execute("UPDATE workspace_clone_jobs SET status = 'completed' WHERE id = %s", (job_id,))

    except Exception as e:
        print(f"Clone job {job_id} failed: {e}")
        with db_cursor(commit=True) as cur:
            cur.execute("UPDATE workspace_clone_jobs SET status = 'failed', error_msg = %s WHERE id = %s", (str(e), job_id))


async def bg_migrate_embeddings(ws_id: str, user_id: str):
    """
    C2-T27, C2-T28: Run background embedding migration.
    Re-embeds all nodes into secondary_embedding.
    Once all are done, swaps secondary to primary and clears secondary.
    """
    from datetime import datetime, timezone
    
    with db_cursor() as cur:
        cur.execute("SELECT * FROM workspace_migrations WHERE workspace_id = %s AND status = 'in_progress' ORDER BY started_at DESC LIMIT 1", (ws_id,))
        migration = cur.fetchone()
        
        cur.execute("SELECT * FROM workspaces WHERE id = %s", (ws_id,))
        ws = cur.fetchone()
        
    if not migration or not ws:
        return

    try:
        with db_cursor() as cur:
            cur.execute("SELECT id, title, body FROM memory_nodes WHERE workspace_id = %s AND status = 'active'", (ws_id,))
            nodes = cur.fetchall()

        target_provider = migration["target_provider"]
        target_model = migration["target_model"]
        resolved = resolve_provider(user_id, "embedding", preferred_provider=target_provider, preferred_model=target_model)

        for node in nodes:
            text = f"{node['title']}\n{node['body']}"
            vector, tokens = await embed(resolved, text)
            with db_cursor(commit=True) as cur:
                cur.execute(
                    "UPDATE memory_nodes SET secondary_embedding = %s, secondary_embedding_model = %s, secondary_embedding_provider = %s WHERE id = %s",
                    (vector, target_model, target_provider, node["id"])
                )
                record_usage(resolved, "embedding", tokens, workspace_id=ws_id, node_id=node["id"])

        # Swap primary and secondary
        with db_cursor(commit=True) as cur:
            # We don't change dim here in workspaces yet, but pgvector vector column has no typmod now so it accepts any dim!
            cur.execute("""
                UPDATE memory_nodes 
                SET embedding = secondary_embedding,
                    secondary_embedding = NULL,
                    secondary_embedding_model = NULL,
                    secondary_embedding_provider = NULL
                WHERE workspace_id = %s
            """, (ws_id,))
            
            cur.execute("""
                UPDATE workspaces
                SET embedding_model = %s,
                    embedding_provider = %s,
                    embedding_dim = COALESCE(
                        (SELECT vector_dims(embedding) FROM memory_nodes
                         WHERE workspace_id = %s AND embedding IS NOT NULL LIMIT 1),
                        embedding_dim
                    ),
                    migrating_to_model = NULL,
                    migrating_to_provider = NULL,
                    migration_status = 'completed'
                WHERE id = %s
            """, (target_model, target_provider, ws_id, ws_id))
            
            cur.execute("""
                UPDATE workspace_migrations
                SET status = 'completed', completed_at = %s
                WHERE id = %s
            """, (datetime.now(timezone.utc), migration["id"]))

    except Exception as e:
        print(f"Migration {migration['id']} failed: {e}")
        with db_cursor(commit=True) as cur:
            cur.execute("UPDATE workspace_migrations SET status = 'failed', error = %s WHERE id = %s", (str(e), migration["id"]))
            cur.execute("UPDATE workspaces SET migration_status = 'paused' WHERE id = %s", (ws_id,))


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
            # node_data is NOT NULL on review_queue; split_suggestion rows carry their
            # payload in the split_suggestion column, so store an empty object here.
            cur.execute(
                """INSERT INTO review_queue
                   (id, workspace_id, change_type, target_node_id, proposer_type, proposer_id,
                    review_notes, split_suggestion, node_data, status, created_at)
                   VALUES (%s, %s, 'split_suggestion', %s, 'system', 'complexity_bot', %s, %s, %s, 'pending', now())""",
                (
                    generate_id("rev"), ws_id, node_id,
                    f"Node exceeds complexity threshold ({result['char_count']} chars). Split suggested.",
                    json.dumps(result["split_proposals"]),
                    json.dumps({}),
                )
            )

async def bg_reindex_workspace_embeddings(ws_id: str, user_id: str):
    """
    Background task to recalculate embeddings for all active nodes in a workspace.
    Typically triggered after workspace migration or settings change.
    """
    from core.database import db_cursor
    from core.ai import resolve_provider, embed, record_usage
    
    # 1. Fetch workspace embedding config
    with db_cursor() as cur:
        cur.execute("SELECT embedding_model, embedding_provider FROM workspaces WHERE id = %s", (ws_id,))
        row = cur.fetchone()
        if not row:
            return
        ws_model = row["embedding_model"]
        ws_prov = row["embedding_provider"]
        
    try:
        resolved = resolve_provider(user_id, "embedding", preferred_provider=ws_prov, preferred_model=ws_model)
    except Exception as exc:
        print(f"BG Reindex: Failed to resolve provider: {exc}")
        return

    # 2. Fetch all active memory nodes in workspace
    with db_cursor() as cur:
        cur.execute(
            "SELECT id, title, body FROM memory_nodes WHERE workspace_id = %s AND status = 'active'",
            (ws_id,)
        )
        nodes = cur.fetchall()

    print(f"BG Reindex: Recalculating embeddings for {len(nodes)} nodes in workspace {ws_id}")

    # 3. Recalculate and update each node's embedding
    for node in nodes:
        text_to_embed = f"{node['title']}\n{node['body']}".strip()
        if not text_to_embed:
            continue
        try:
            vector, tokens = await embed(resolved, text_to_embed)
            with db_cursor(commit=True) as cur:
                cur.execute(
                    "UPDATE memory_nodes SET embedding = %s WHERE id = %s AND workspace_id = %s",
                    (vector, node["id"], ws_id)
                )
            record_usage(resolved, "embedding", tokens, ws_id, node["id"])
        except Exception as exc:
            print(f"BG Reindex: Failed to embed node {node['id']}: {exc}")


async def retry_failed_embeddings_job():
    """
    C3-T30: Periodically check embed_retry_queue and trigger bg_embed_node for nodes
    whose next_retry_at has passed.
    """
    from datetime import datetime, timezone
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT r.node_id, r.workspace_id, n.title, n.body
            FROM embed_retry_queue r
            JOIN memory_nodes n ON n.id = r.node_id
            WHERE r.next_retry_at <= %s
            """,
            (datetime.now(timezone.utc),)
        )
        jobs = cur.fetchall()

    for job in jobs:
        text = f"{job['title']}\n{job['body']}"
        with db_cursor() as cur:
            cur.execute("SELECT owner_id FROM workspaces WHERE id = %s", (job["workspace_id"],))
            ws_row = cur.fetchone()
            user_id = ws_row["owner_id"] if ws_row else "system"
            
        await bg_embed_node(job["workspace_id"], job["node_id"], text, user_id)

async def process_node_events_job():
    """
    C3-T31: Periodically process node events (e.g. suggesting edges after embedding updates).
    """
    from datetime import datetime, timezone
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT id, workspace_id, node_id, event_type
            FROM node_events
            WHERE processed_at IS NULL
            ORDER BY created_at ASC
            LIMIT 50
            """
        )
        events = cur.fetchall()

    if not events:
        return

    for event in events:
        try:
            if event["event_type"] in ('created', 'embedding_updated'):
                try:
                    with db_cursor() as cur:
                        cur.execute("SELECT author FROM memory_nodes WHERE id = %s", (event["node_id"],))
                        n_row = cur.fetchone()
                        user_id = n_row["author"] if n_row else "system"

                    # bg_suggest_edges does DB operations but it's synchronous.
                    # In a real async job we could run it in a threadpool, but for now we just call it.
                    bg_suggest_edges(event["workspace_id"], event["node_id"], user_id)
                except Exception as exc:
                    print(f"Node event edge suggestion failed for {event['id']}: {exc}")

            if event["event_type"] in ("created", "updated"):
                try:
                    from services.safety_queue import enqueue_safety_review
                    with db_cursor(commit=True) as cur:
                        enqueue_safety_review(
                            cur,
                            workspace_id=event["workspace_id"],
                            node_id=event["node_id"],
                            event_type=event["event_type"],
                            event_id=f"node_event:{event['id']}:safety",
                            source="node_event",
                        )
                except Exception as exc:
                    print(f"Node event safety enqueue failed for {event['id']}: {exc}")

                try:
                    from services.conductor import record_conductor_run
                    await record_conductor_run(
                        event["workspace_id"],
                        event["node_id"],
                        trigger_reason=f"node_event:{event['event_type']}",
                    )
                except Exception as exc:
                    print(f"Node event conductor dispatch failed for {event['id']}: {exc}")
            
            with db_cursor(commit=True) as cur:
                cur.execute("UPDATE node_events SET processed_at = %s WHERE id = %s", (datetime.now(timezone.utc), event["id"]))
        except Exception as e:
            print(f"Failed to process node event {event['id']}: {e}")
            with db_cursor(commit=True) as cur:
                cur.execute("UPDATE node_events SET processed_at = %s WHERE id = %s", (datetime.now(timezone.utc), event["id"]))

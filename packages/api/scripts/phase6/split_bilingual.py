"""
scripts/phase6/split_bilingual.py — S2-T06: Bilingual workspace split execution.

For workspaces classified as 'bilingual' or 'mixed':
  1. Within a single transaction:
     a. Create a new EN workspace (orig_id + '_en' suffix)
     b. Copy all workspace_members (same roles)
     c. Deep-copy all memory_nodes (new IDs) with all metadata preserved
     d. Deep-copy all edges (with remapped node IDs)
     e. Clear zh fields from new EN workspace nodes
     f. Clear en fields from original ZH workspace nodes
     g. Set language='zh-TW' on original, language='en' on new
     h. Set linked_workspace_id pointing both ways
  2. Write _migration_split_log_v6 entry
  3. Trigger embedding re-index for new workspace
  4. Send owner notification email

For workspaces classified as 'zh' or 'en':
  Simply set the language field accordingly.

Usage (via CLI):
    python -m scripts.phase6 split-bilingual [--dry-run] [--ws-id <id>]
"""
from __future__ import annotations

import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def _ensure_split_log_table(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS _migration_split_log_v6 (
            orig_id     TEXT PRIMARY KEY,
            new_id      TEXT NOT NULL,
            split_at    TIMESTAMPTZ DEFAULT now(),
            node_count  INT,
            edge_count  INT
        )
    """)


def _copy_workspace(cur, orig_ws: dict) -> str:
    """Create the new EN workspace record. Returns new_ws_id."""
    from core.security import generate_id
    import json as _json

    new_ws_id = orig_ws["id"] + "_en"

    # Determine names
    name_en = orig_ws.get("name_en") or orig_ws.get("name_zh") or "Workspace (EN)"

    cur.execute(
        """
        INSERT INTO workspaces (
            id, name_zh, name_en, language,
            visibility, kb_type, owner_id,
            archive_window_days, min_traversals,
            embedding_model, embedding_dim,
            qa_archive_mode, extraction_provider, embedding_provider,
            auto_split, settings
        )
        VALUES (
            %s, %s, %s, 'en',
            %s, %s, %s,
            %s, %s,
            %s, %s,
            %s, %s, %s,
            %s, %s
        )
        ON CONFLICT (id) DO NOTHING
        RETURNING id
        """,
        (
            new_ws_id,
            name_en, name_en,  # name_zh mirrors name_en for the EN workspace
            orig_ws["visibility"],
            orig_ws["kb_type"],
            orig_ws["owner_id"],
            orig_ws["archive_window_days"],
            orig_ws["min_traversals"],
            orig_ws["embedding_model"],
            orig_ws["embedding_dim"],
            orig_ws["qa_archive_mode"],
            orig_ws.get("extraction_provider"),
            orig_ws.get("embedding_provider"),
            orig_ws.get("auto_split", False),
            orig_ws["settings"] if isinstance(orig_ws["settings"], str)
                else json.dumps(orig_ws["settings"] or {}),
        ),
    )
    return new_ws_id


def _copy_members(cur, orig_ws_id: str, new_ws_id: str):
    """Replicate workspace_members to the new workspace."""
    cur.execute(
        "SELECT user_id, role FROM workspace_members WHERE workspace_id = %s",
        (orig_ws_id,),
    )
    members = cur.fetchall()
    for m in members:
        cur.execute(
            """
            INSERT INTO workspace_members (workspace_id, user_id, role)
            VALUES (%s, %s, %s)
            ON CONFLICT DO NOTHING
            """,
            (new_ws_id, m["user_id"], m["role"]),
        )
    return len(members)


def _copy_nodes(cur, orig_ws_id: str, new_ws_id: str) -> dict:
    """Deep-copy all memory_nodes. Returns {orig_node_id: new_node_id}."""
    from core.security import generate_id

    cur.execute(
        """
        SELECT * FROM memory_nodes
        WHERE workspace_id = %s
        ORDER BY created_at
        """,
        (orig_ws_id,),
    )
    orig_nodes = cur.fetchall()
    id_map = {}

    for n in orig_nodes:
        new_node_id = generate_id("mem")
        id_map[n["id"]] = new_node_id

        cur.execute(
            """
            INSERT INTO memory_nodes (
                id, schema_version, workspace_id,
                title_zh, title_en, content_type, content_format,
                body_zh, body_en, tags, visibility,
                author, created_at, updated_at, signature, source_type,
                source_document, extraction_model, copied_from_node, copied_from_ws,
                trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep,
                votes_up, votes_down, verifications,
                traversal_count, unique_traverser_count,
                status, archived_at, miss_count, ask_count,
                source_file, cluster_id
            )
            VALUES (
                %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s,
                %s, %s, %s, %s,
                %s, NULL
            )
            ON CONFLICT (id) DO NOTHING
            """,
            (
                new_node_id,
                n.get("schema_version", "1.0"),
                new_ws_id,
                n["title_zh"], n["title_en"],
                n["content_type"], n["content_format"],
                n["body_zh"], n["body_en"],
                n["tags"], n["visibility"],
                n["author"],
                n["created_at"], n.get("updated_at"),
                n["signature"], n["source_type"],
                n.get("source_document"), n.get("extraction_model"),
                n.get("copied_from_node"), n.get("copied_from_ws"),
                n["trust_score"], n["dim_accuracy"], n["dim_freshness"],
                n["dim_utility"], n["dim_author_rep"],
                n.get("votes_up", 0), n.get("votes_down", 0), n.get("verifications", 0),
                n.get("traversal_count", 0), n.get("unique_traverser_count", 0),
                n["status"], n.get("archived_at"),
                n.get("miss_count", 0), n.get("ask_count", 0),
                n.get("source_file"),
            ),
        )
    return id_map


def _copy_edges(cur, orig_ws_id: str, new_ws_id: str, id_map: dict) -> int:
    """Deep-copy all edges with remapped node IDs."""
    from core.security import generate_id

    cur.execute(
        "SELECT * FROM edges WHERE workspace_id = %s",
        (orig_ws_id,),
    )
    orig_edges = cur.fetchall()
    copied = 0

    for e in orig_edges:
        new_from = id_map.get(e["from_id"])
        new_to   = id_map.get(e["to_id"])
        if not new_from or not new_to:
            continue  # Skip if node wasn't copied (shouldn't happen)

        new_edge_id = generate_id("edg")
        cur.execute(
            """
            INSERT INTO edges (
                id, workspace_id, from_id, to_id, relation,
                weight, co_access_count, last_co_accessed,
                half_life_days, min_weight, status, pinned,
                traversal_count, rating_sum, rating_count
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
            """,
            (
                new_edge_id, new_ws_id, new_from, new_to,
                e["relation"],
                e["weight"], e.get("co_access_count", 0),
                e.get("last_co_accessed"),
                e.get("half_life_days", 30),
                e.get("min_weight", 0.1),
                e["status"], e.get("pinned", False),
                e.get("traversal_count", 0),
                e.get("rating_sum", 0), e.get("rating_count", 0),
            ),
        )
        copied += 1
    return copied


def _clear_en_fields(cur, ws_id: str):
    """Clear English fields on all nodes of a ZH workspace."""
    cur.execute(
        "UPDATE memory_nodes SET title_en = '', body_en = '' WHERE workspace_id = %s",
        (ws_id,),
    )


def _clear_zh_fields(cur, ws_id: str):
    """Clear Chinese fields on all nodes of an EN workspace."""
    cur.execute(
        "UPDATE memory_nodes SET title_zh = '', body_zh = '' WHERE workspace_id = %s",
        (ws_id,),
    )


def _send_split_notification(owner_id: str, orig_ws_id: str, new_ws_id: str, ws_name: str):
    """Send email notification to workspace owner about the split."""
    try:
        from core.database import db_cursor
        from core.email import send_email

        with db_cursor() as cur:
            cur.execute("SELECT email, display_name FROM users WHERE id = %s", (owner_id,))
            user = cur.fetchone()
            if not user:
                return

        send_email(
            to_email=user["email"],
            subject="[MemTrace] 雙語 KB 已自動拆分",
            body_html=f"""
<p>您好 {user['display_name']}，</p>
<p>您的知識庫「<strong>{ws_name}</strong>」原為中英雙語，已依 Phase 6 政策自動拆分為兩份單語知識庫：</p>
<ul>
  <li>🇹🇼 <strong>中文版</strong>：原 KB（ID: {orig_ws_id}）</li>
  <li>🇺🇸 <strong>英文版</strong>：新建 KB（ID: {new_ws_id}）</li>
</ul>
<p>兩份知識庫的內容均已完整保留。您可在管理頁面查看並視需要刪除不需要的版本。</p>
<p>如有疑問請聯繫系統管理員。</p>
""",
        )
    except Exception as e:
        logger.warning("Failed to send split notification to %s: %s", owner_id, e)


def split_workspace(cur, orig_ws_id: str, dry_run: bool, verbose: bool):
    """Perform the full bilingual split for one workspace."""
    cur.execute("SELECT * FROM workspaces WHERE id = %s", (orig_ws_id,))
    orig_ws = dict(cur.fetchone())

    logger.info("Splitting workspace %s ('%s')...", orig_ws_id, orig_ws.get("name_zh", ""))

    if dry_run:
        cur.execute(
            "SELECT count(*) AS cnt FROM memory_nodes WHERE workspace_id = %s",
            (orig_ws_id,),
        )
        node_cnt = cur.fetchone()["cnt"]
        logger.info(
            "  [DRY-RUN] Would create %s_en with %d nodes", orig_ws_id, node_cnt
        )
        return

    new_ws_id = _copy_workspace(cur, orig_ws)
    member_cnt = _copy_members(cur, orig_ws_id, new_ws_id)
    id_map = _copy_nodes(cur, orig_ws_id, new_ws_id)
    edge_cnt = _copy_edges(cur, orig_ws_id, new_ws_id, id_map)
    node_cnt = len(id_map)

    # Clear opposite language fields
    _clear_en_fields(cur, orig_ws_id)    # keep ZH, clear EN
    _clear_zh_fields(cur, new_ws_id)     # keep EN, clear ZH

    # Set language & linked_workspace_id
    cur.execute(
        """
        UPDATE workspaces
        SET language = 'zh-TW', linked_workspace_id = %s
        WHERE id = %s
        """,
        (new_ws_id, orig_ws_id),
    )
    cur.execute(
        """
        UPDATE workspaces
        SET language = 'en', linked_workspace_id = %s
        WHERE id = %s
        """,
        (orig_ws_id, new_ws_id),
    )

    # Write split log
    cur.execute(
        """
        INSERT INTO _migration_split_log_v6 (orig_id, new_id, node_count, edge_count)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (orig_id) DO UPDATE SET
            new_id = EXCLUDED.new_id,
            split_at = now(),
            node_count = EXCLUDED.node_count,
            edge_count = EXCLUDED.edge_count
        """,
        (orig_ws_id, new_ws_id, node_cnt, edge_cnt),
    )

    if verbose:
        logger.info(
            "  ✅ Created %s: %d nodes, %d edges, %d members",
            new_ws_id, node_cnt, edge_cnt, member_cnt,
        )

    # Send notification (non-blocking)
    _send_split_notification(
        orig_ws["owner_id"],
        orig_ws_id,
        new_ws_id,
        orig_ws.get("name_zh") or orig_ws.get("name_en", ""),
    )


def run(
    dry_run: bool = False,
    ws_id: Optional[str] = None,
    verbose: bool = False,
):
    """Main entry point for split-bilingual command."""
    from core.database import db_cursor

    with db_cursor(commit=not dry_run) as cur:
        _ensure_split_log_table(cur)

        # Fetch classification
        cur.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_name = '_migration_classification_v6'"
        )
        if not cur.fetchone():
            logger.error(
                "Classification table not found. Run 'classify-bilingual' first."
            )
            return

        if ws_id:
            cur.execute(
                "SELECT * FROM _migration_classification_v6 WHERE workspace_id = %s",
                (ws_id,),
            )
        else:
            cur.execute("SELECT * FROM _migration_classification_v6 ORDER BY workspace_id")
        rows = cur.fetchall()

        for row in rows:
            wid = row["workspace_id"]
            category = row["category"]

            if category in ("zh", "en"):
                lang = "zh-TW" if category == "zh" else "en"
                if not dry_run:
                    cur.execute(
                        "UPDATE workspaces SET language = %s WHERE id = %s",
                        (lang, wid),
                    )
                if verbose:
                    logger.info("  ws=%s → language=%s (no split needed)", wid, lang)

            elif category in ("bilingual", "mixed"):
                split_workspace(cur, wid, dry_run=dry_run, verbose=verbose)

    logger.info(
        "split-bilingual complete%s.", " (dry-run — no data written)" if dry_run else ""
    )

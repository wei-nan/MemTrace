"""
scripts/phase6/consolidate_fields.py — S2-T07: Merge bilingual columns into single-language columns.

After the bilingual split, each node in each workspace has content in only one language.
This script:
  1. Fills memory_nodes.title from (title_zh or title_en) based on workspace.language
  2. Fills memory_nodes.body  from (body_zh  or body_en)  based on workspace.language
  3. Fills workspaces.name    from (name_zh  or name_en)  based on workspace.language

It does NOT DROP the old columns — that happens in Stage 3 (055_drop_bilingual_columns.sql).

Prerequisites:
  - 052_node_single_lang.sql applied (title, body columns exist on memory_nodes)
  - 053_workspace_name_single.sql applied (name column exists on workspaces)
  - 054_language_not_null.sql applied (language IS NOT NULL)

Usage (via CLI):
    python -m scripts.phase6 consolidate-fields [--dry-run] [--ws-id <id>]
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def _check_column_exists(cur, table: str, column: str) -> bool:
    cur.execute(
        """
        SELECT 1 FROM information_schema.columns
        WHERE table_name = %s AND column_name = %s
        """,
        (table, column),
    )
    return cur.fetchone() is not None


def run(
    dry_run: bool = False,
    ws_id: Optional[str] = None,
    verbose: bool = False,
):
    """Main entry point for consolidate-fields command."""
    from core.database import db_cursor

    with db_cursor(commit=not dry_run) as cur:
        # Pre-flight checks
        missing = []
        for tbl, col in [("memory_nodes", "title"), ("memory_nodes", "body"), ("workspaces", "name")]:
            if not _check_column_exists(cur, tbl, col):
                missing.append(f"{tbl}.{col}")
        if missing:
            logger.error(
                "Missing columns: %s — apply migrations 052 and 053 first.", ", ".join(missing)
            )
            return

        # Check language NOT NULL
        cur.execute("SELECT count(*) AS cnt FROM workspaces WHERE language IS NULL")
        null_lang = cur.fetchone()["cnt"]
        if null_lang > 0:
            logger.warning(
                "%d workspaces still have language=NULL — they will be skipped.", null_lang
            )

        # ── 1. Consolidate memory_nodes.title + body ───────────────────────────
        ws_filter = "AND n.workspace_id = %s" if ws_id else ""
        params_ws = [ws_id] if ws_id else []

        if dry_run:
            cur.execute(
                f"""
                SELECT count(*) AS cnt FROM memory_nodes n
                JOIN workspaces w ON w.id = n.workspace_id
                WHERE w.language IS NOT NULL
                  AND (n.title IS NULL OR length(n.title) = 0)
                  {ws_filter}
                """,
                params_ws,
            )
            cnt = cur.fetchone()["cnt"]
            logger.info("[DRY-RUN] Would update %d memory_nodes.title/body rows.", cnt)
        else:
            cur.execute(
                f"""
                UPDATE memory_nodes n
                SET
                    title = CASE w.language
                        WHEN 'zh-TW' THEN COALESCE(NULLIF(n.title_zh, ''), n.title_en)
                        ELSE              COALESCE(NULLIF(n.title_en, ''), n.title_zh)
                    END,
                    body  = CASE w.language
                        WHEN 'zh-TW' THEN COALESCE(n.body_zh, '')
                        ELSE              COALESCE(n.body_en, '')
                    END
                FROM workspaces w
                WHERE n.workspace_id = w.id
                  AND w.language IS NOT NULL
                  {ws_filter}
                """,
                params_ws,
            )
            updated_nodes = cur.rowcount
            logger.info("Updated %d memory_nodes rows (title + body).", updated_nodes)

            # Verify no empty titles remain (skip if ws_id is restricted)
            cur.execute(
                f"""
                SELECT count(*) AS cnt FROM memory_nodes n
                JOIN workspaces w ON w.id = n.workspace_id
                WHERE (n.title IS NULL OR length(n.title) = 0)
                  AND w.language IS NOT NULL
                  AND n.status = 'active'
                  {ws_filter}
                """,
                params_ws,
            )
            empty_after = cur.fetchone()["cnt"]
            if empty_after > 0:
                logger.warning(
                    "%d active nodes still have empty title after consolidation.", empty_after
                )
            else:
                logger.info("✅ All active nodes have non-empty title.")

        # ── 2. Consolidate workspaces.name ──────────────────────────────────────
        ws_id_filter = "AND id = %s" if ws_id else ""
        params_id = [ws_id] if ws_id else []

        if dry_run:
            cur.execute(
                f"""
                SELECT count(*) AS cnt FROM workspaces
                WHERE language IS NOT NULL
                  AND (name IS NULL OR length(name) = 0)
                  {ws_id_filter}
                """,
                params_id,
            )
            cnt = cur.fetchone()["cnt"]
            logger.info("[DRY-RUN] Would update %d workspaces.name rows.", cnt)
        else:
            cur.execute(
                f"""
                UPDATE workspaces
                SET name = CASE language
                    WHEN 'zh-TW' THEN COALESCE(NULLIF(name_zh, ''), name_en)
                    ELSE              COALESCE(NULLIF(name_en, ''), name_zh)
                END
                WHERE language IS NOT NULL
                  {ws_id_filter}
                """,
                params_id,
            )
            logger.info("Updated %d workspaces.name rows.", cur.rowcount)

    if dry_run:
        logger.info("[DRY-RUN] No data written.")
    else:
        logger.info("consolidate-fields complete.")

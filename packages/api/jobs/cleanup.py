"""
jobs/cleanup.py — Daily cleanup background jobs.

Extracted from main.py (S4-2):
  - _cleanup_loop: invite expiry, ledger cleanup, export cleanup, API key auto-revoke
  - _deletion_notification_loop / _run_deletion_notifications: workspace pending-deletion emails
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone, timedelta

from core.database import db_cursor
from core.config import settings
from core.email import send_workspace_deletion_notice

logger = logging.getLogger(__name__)

CLEANUP_INTERVAL_SECONDS = 86400   # 24 hours
DECAY_INTERVAL_SECONDS   = 86400   # reuse same cadence for deletion notifications


# ─── Cleanup Loop ─────────────────────────────────────────────────────────────

async def cleanup_job():
    """Daily cleanup of expired invites, old ai_usage_log and kb_exports."""
    try:
        with db_cursor(commit=True) as cur:
            # G4: Mark expired invites
            cur.execute(
                "UPDATE workspace_invites SET status = 'expired' WHERE expires_at < NOW() AND status = 'pending'"
            )
            # G4: Weekly — delete ai_credit_ledger older than retention limit
            cur.execute(
                "DELETE FROM ai_credit_ledger WHERE created_at < NOW() - (%s * INTERVAL '1 month')",
                (settings.ai_usage_retention_months,)
            )
            # G4: Weekly — delete old completed kb_exports (30+ days) and their files
            cur.execute(
                "SELECT id, file_path FROM kb_exports WHERE status = 'done' AND completed_at < NOW() - INTERVAL '30 days'"
            )
            old_exports = cur.fetchall()
            for exp in old_exports:
                if exp["file_path"]:
                    try:
                        os.remove(exp["file_path"])
                    except OSError:
                        pass
            if old_exports:
                cur.execute(
                    "DELETE FROM kb_exports WHERE id = ANY(%s)",
                    ([e["id"] for e in old_exports],)
                )

            # P4-D8: Monthly summary
            now_dt = datetime.now()
            for m_offset in [0, 1]:
                target_month = (now_dt.replace(day=1) - timedelta(days=m_offset * 28)).strftime("%Y-%m")
                cur.execute("""
                    INSERT INTO ai_usage_summary (workspace_id, year_month, token_count)
                    SELECT workspace_id, TO_CHAR(created_at, 'YYYY-MM') as ym, SUM(tokens_used)
                    FROM ai_credit_ledger
                    WHERE TO_CHAR(created_at, 'YYYY-MM') = %s
                    GROUP BY workspace_id, ym
                    ON CONFLICT (workspace_id, year_month) DO UPDATE
                    SET token_count = EXCLUDED.token_count, last_updated = now()
                """, (target_month,))

            # P4-D8 part 2: Cleanup ledger (retention policy)
            retention = settings.ai_usage_retention_months
            cur.execute(
                "DELETE FROM ai_credit_ledger WHERE created_at < NOW() - (%s * INTERVAL '1 month')",
                (retention,)
            )

            # P4-D9: Apply Node Archiving — evergreen KBs
            cur.execute("""
                UPDATE memory_nodes
                SET status = 'archived', archived_at = now()
                FROM workspaces
                WHERE memory_nodes.workspace_id = workspaces.id
                  AND workspaces.kb_type = 'evergreen'
                  AND memory_nodes.status = 'active'
                  AND memory_nodes.created_at < now() - interval '90 days'
                  AND NOT EXISTS (
                      SELECT 1 FROM traversal_log
                      WHERE traversal_log.node_id = memory_nodes.id
                        AND traversal_log.traversed_at > now() - interval '90 days'
                  )
            """)

            # Ephemeral: Archive if all edges faded OR 60 days without traversal
            cur.execute("""
                UPDATE memory_nodes
                SET status = 'archived', archived_at = now()
                FROM workspaces
                WHERE memory_nodes.workspace_id = workspaces.id
                  AND workspaces.kb_type = 'ephemeral'
                  AND memory_nodes.status = 'active'
                  AND (
                      (
                        memory_nodes.created_at < now() - interval '60 days'
                        AND NOT EXISTS (
                            SELECT 1 FROM traversal_log
                            WHERE traversal_log.node_id = memory_nodes.id
                              AND traversal_log.traversed_at > now() - interval '60 days'
                        )
                      )
                      OR NOT EXISTS (
                          SELECT 1 FROM edges
                          WHERE (edges.from_id = memory_nodes.id OR edges.to_id = memory_nodes.id)
                            AND edges.status = 'active'
                      )
                  )
            """)

            # P2-3: Auto-revoke API keys inactive for 90 days.
            cur.execute("""
                UPDATE api_keys
                SET revoked_at = now()
                WHERE revoked_at IS NULL
                  AND (
                        (last_used_at IS NULL AND created_at < now() - INTERVAL '90 days')
                     OR (last_used_at IS NOT NULL AND last_used_at < now() - INTERVAL '90 days')
                       )
                RETURNING id, user_id, name
            """)
            revoked_keys = cur.fetchall()
            if revoked_keys:
                logger.info(
                    "Auto-revoked %d inactive API key(s): %s",
                    len(revoked_keys),
                    [r["id"] for r in revoked_keys],
                )
        logger.info("Daily cleanup complete")
    except Exception as exc:
        logger.warning("Cleanup job error: %s", exc)

    # Purge access-log separately
    try:
        with db_cursor(commit=True) as cur:
            cur.execute("SELECT purge_old_access_logs()")
    except Exception:
        pass

    # Purge expired/revoked refresh tokens.
    try:
        with db_cursor(commit=True) as cur:
            cur.execute("SELECT purge_old_refresh_tokens()")
    except Exception:
        pass


async def deletion_notification_job():
    """Send email warnings for workspaces pending deletion."""
    try:
        _run_deletion_notifications()
    except Exception as exc:
        logger.warning("Deletion notification job error: %s", exc)


# Aliases
_cleanup_loop = cleanup_job
_deletion_notification_loop = deletion_notification_job


def _run_deletion_notifications() -> None:
    with db_cursor(commit=True) as cur:
        # ── Purge workspaces past the grace period ────────────────────────────
        cur.execute("""
            SELECT w.id, w.name_en, w.name_zh, u.email, u.display_name,
                   w.kb_type,
                   CASE w.kb_type
                     WHEN 'ephemeral' THEN 7
                     ELSE 30
                   END AS grace_days
            FROM workspaces w
            JOIN users u ON u.id = w.owner_id
            WHERE w.status = 'pending_deletion'
              AND w.deleted_at < now() - (
                    CASE w.kb_type WHEN 'ephemeral' THEN INTERVAL '7 days'
                                   ELSE INTERVAL '30 days' END
                  )
        """)
        to_purge = cur.fetchall()
        for ws in to_purge:
            try:
                send_workspace_deletion_notice(
                    ws["email"], ws["name_zh"] or ws["name_en"], days_left=0
                )
                logger.info("Purging workspace %s (%s)", ws["id"], ws["name_en"])
            except Exception as e:
                logger.warning("Failed to send purge notice for %s: %s", ws["id"], e)
            cur.execute("DELETE FROM workspaces WHERE id = %s", (ws["id"],))

        # ── 5-day urgent warning ──────────────────────────────────────────────
        cur.execute("""
            SELECT w.id, w.name_en, w.name_zh, u.email,
                   w.kb_type,
                   CASE w.kb_type WHEN 'ephemeral' THEN 7 ELSE 30 END AS grace_days
            FROM workspaces w
            JOIN users u ON u.id = w.owner_id
            WHERE w.status = 'pending_deletion'
              AND w.deleted_at BETWEEN
                    now() - (CASE w.kb_type WHEN 'ephemeral' THEN INTERVAL '7 days'
                                            ELSE INTERVAL '30 days' END)
                              + INTERVAL '1 day'
                AND now() - (CASE w.kb_type WHEN 'ephemeral' THEN INTERVAL '7 days'
                                            ELSE INTERVAL '30 days' END)
                              + INTERVAL '2 days'
        """)
        for ws in cur.fetchall():
            days_left = 5 if ws["kb_type"] != "ephemeral" else 2
            restore_url = f"http://localhost:5173/workspaces/{ws['id']}/restore"
            try:
                send_workspace_deletion_notice(
                    ws["email"],
                    ws["name_zh"] or ws["name_en"],
                    days_left=days_left,
                    restore_url=restore_url,
                )
            except Exception as e:
                logger.warning("Failed to send warning notice for %s: %s", ws["id"], e)

    logger.info("Deletion notification cycle complete (purged=%d)", len(to_purge))

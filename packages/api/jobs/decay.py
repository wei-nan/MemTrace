"""
jobs/decay.py — Edge decay and ephemeral node expiry background jobs.

Extracted from main.py (S4-3):
  - _decay_loop: daily edge weight decay + node archiving
  - _ephemeral_decay_loop: hourly edge decay for ephemeral workspaces
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from core.database import db_cursor
from services.analytics import snapshot_kb_health

logger = logging.getLogger(__name__)

DECAY_INTERVAL_SECONDS          = 86400   # 24 hours
EPHEMERAL_DECAY_INTERVAL_SECONDS = 3600   # 1 hour


async def decay_job():
    """Apply edge weight decay, node archiving, and freshness recalculation."""
    try:
        with db_cursor(commit=True) as cur:
            # S1-T02: Recalculate freshness for all nodes
            recalculate_freshness(cur)
            
            # S3-T03: Recalculate author reputation
            recalculate_author_rep(cur)
            
            # S1-T08: Snapshot health for all active workspaces
            cur.execute("SELECT id FROM workspaces WHERE kb_type != 'ephemeral'")
            ws_ids = [r["id"] for r in cur.fetchall()]
            for ws_id in ws_ids:
                snapshot_kb_health(cur, ws_id)
            
            # Existing logic
            cur.execute("SELECT apply_edge_decay()")
            cur.execute("SELECT apply_node_archiving()")
            cur.execute(
                """
                INSERT INTO system_state (key, value, updated_at)
                VALUES ('last_decay_at', %s, now())
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now()
                """,
                (datetime.now(timezone.utc).isoformat(),),
            )
        logger.info("Decay and archiving applied successfully")
    except Exception as exc:
        logger.warning("Edge decay failed: %s", exc)


def recalculate_freshness(cur, ws_id: str | None = None):
    """
    Apply S1-T02 decay formula: dim_freshness = 0.5 ^ (days_since_update / 180)
    Triggered: updated_at or validity_confirmed_at update resets to 1.0 (handled in service layer).
    """
    logger.info(f"Recalculating freshness for {'all workspaces' if not ws_id else f'workspace {ws_id}'}")
    
    # 1. Get stats before
    ws_filter = "AND workspace_id = %s" if ws_id else ""
    params = [ws_id] if ws_id else []
    
    cur.execute(f"SELECT AVG(dim_freshness) FROM memory_nodes WHERE status = 'active' {ws_filter}", params)
    avg_before = cur.fetchone()["avg"] or 0.0
    
    # 2. Perform update
    # Formula: 0.5 ^ (EXTRACT(DAY FROM (now() - GREATEST(updated_at, validity_confirmed_at))) / 180.0)
    update_sql = f"""
        UPDATE memory_nodes
        SET dim_freshness = POWER(0.5, EXTRACT(DAY FROM (now() - COALESCE(validity_confirmed_at, updated_at, created_at))) / 180.0)
        WHERE status = 'active' {ws_filter}
    """
    cur.execute(update_sql, params)
    nodes_updated = cur.rowcount
    
    # 3. Get stats after
    cur.execute(f"SELECT AVG(dim_freshness) FROM memory_nodes WHERE status = 'active' {ws_filter}", params)
    avg_after = cur.fetchone()["avg"] or 0.0
    
    # 4. Log to decay_logs
    cur.execute(
        """
        INSERT INTO decay_logs (date, workspace_id, nodes_updated, avg_freshness_before, avg_freshness_after)
        VALUES (CURRENT_DATE, %s, %s, %s, %s)
        """,
        (ws_id or "all", nodes_updated, avg_before, avg_after)
    )
    
    logger.info(f"Freshness recalculated: {nodes_updated} nodes. Avg {avg_before:.3f} -> {avg_after:.3f}")


def recalculate_author_rep(cur, ws_id: str | None = None):
    """
    S3-T03: Recalculate author reputation based on node quality (trust_score) in the last 90 days.
    """
    logger.info(f"Recalculating author reputation for {'all workspaces' if not ws_id else f'workspace {ws_id}'}")
    
    ws_filter = "AND workspace_id = %s" if ws_id else ""
    params = [ws_id] if ws_id else []
    
    # 1. Calculate avg trust per author for nodes updated in last 90 days
    # We only count active nodes.
    cur.execute(
        f"""
        WITH author_stats AS (
            SELECT 
                author,
                workspace_id,
                AVG(trust_score) as avg_trust
            FROM memory_nodes
            WHERE status = 'active' 
              AND (updated_at > now() - interval '90 days' OR created_at > now() - interval '90 days')
              {ws_filter}
            GROUP BY author, workspace_id
        )
        UPDATE memory_nodes n
        SET dim_author_rep = s.avg_trust
        FROM author_stats s
        WHERE n.author = s.author 
          AND n.workspace_id = s.workspace_id
          AND n.status = 'active'
        """,
        params
    )
    nodes_updated = cur.rowcount
    logger.info(f"Author reputation updated for {nodes_updated} nodes.")


async def ephemeral_decay_job():
    """Apply edge decay for ephemeral KBs."""
    try:
        with db_cursor(commit=True) as cur:
            cur.execute(
                """
                UPDATE edges e
                SET weight = GREATEST(
                    e.min_weight,
                    e.weight * POWER(0.5, EXTRACT(EPOCH FROM (now() - e.last_co_accessed)) / 86400.0 / e.half_life_days)
                )
                FROM workspaces w
                WHERE e.workspace_id = w.id AND w.kb_type = 'ephemeral'
                  AND e.status = 'active' AND e.pinned = FALSE
                """
            )
        logger.info("Ephemeral KB edge decay applied")
    except Exception as exc:
        logger.warning("Ephemeral decay skipped: %s", exc)


# Aliases for backward compatibility if needed during migration
_decay_loop = decay_job
_ephemeral_decay_loop = ephemeral_decay_job

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(decay_job())

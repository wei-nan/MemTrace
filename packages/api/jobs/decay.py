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

logger = logging.getLogger(__name__)

DECAY_INTERVAL_SECONDS          = 86400   # 24 hours
EPHEMERAL_DECAY_INTERVAL_SECONDS = 3600   # 1 hour


async def decay_job():
    """Apply edge weight decay and node archiving once."""
    try:
        with db_cursor(commit=True) as cur:
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
        logger.warning("Edge decay skipped: %s", exc)


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

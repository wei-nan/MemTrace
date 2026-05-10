"""
jobs/ingest.py — Stale ingestion job recovery background job.

Extracted from main.py (S4-5):
  - _stale_ingest_loop: auto-fail jobs stuck in processing/pending
  - recover_stale_on_startup: mark stale jobs failed at process start
"""
from __future__ import annotations

import asyncio
import logging

from core.database import db_cursor

logger = logging.getLogger(__name__)

STALE_INGEST_TIMEOUT_MINUTES        = 30
STALE_INGEST_CHECK_INTERVAL_SECONDS = 300   # check every 5 minutes


async def stale_ingest_job():
    """Auto-fail ingestion jobs that have been stuck in processing/pending for too long."""
    try:
        with db_cursor(commit=True) as cur:
            cur.execute(
                """
                UPDATE ingestion_logs
                SET status = 'failed',
                    error_msg = 'Job timed out after %s minutes with no progress.',
                    completed_at = NOW()
                WHERE status IN ('processing', 'pending')
                  AND created_at < NOW() - INTERVAL '%s minutes'
                """,
                (STALE_INGEST_TIMEOUT_MINUTES, STALE_INGEST_TIMEOUT_MINUTES),
            )
            count = cur.rowcount
        if count:
            logger.warning("Auto-failed %d timed-out ingestion job(s)", count)
    except Exception as exc:
        logger.warning("Stale ingest check failed: %s", exc)


# Aliases
_stale_ingest_loop = stale_ingest_job


def recover_stale_on_startup() -> None:
    """
    Called once at startup: mark any jobs that were left in processing/cancelling/pending
    state (from a previous server crash or restart) as failed.
    """
    try:
        with db_cursor(commit=True) as cur:
            cur.execute(
                """
                UPDATE ingestion_logs
                SET status = 'failed',
                    error_msg = 'Server restarted while job was in progress.',
                    completed_at = NOW()
                WHERE status IN ('processing', 'cancelling', 'pending')
                """
            )
            count = cur.rowcount
        if count:
            logger.warning("Marked %d stale ingestion job(s) as failed on startup", count)
    except Exception as exc:
        logger.warning("Could not clean up stale ingestion jobs: %s", exc)

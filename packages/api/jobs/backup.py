"""
jobs/backup.py — Automated database backup background job.

Extracted from main.py (S4-4).
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone

from core.backup import get_backup_config, run_backup_and_update_status

logger = logging.getLogger(__name__)

BACKUP_CHECK_INTERVAL_SECONDS = 3600   # re-check every hour


async def backup_job():
    """Check backup schedule and run pg_dump when interval has elapsed."""
    try:
        config = get_backup_config()
        if not config.get("enabled"):
            return
        interval_seconds = int(config.get("interval_hours", 24)) * 3600
        last_at = config.get("last_backup_at")
        if last_at:
            last_dt = datetime.fromisoformat(last_at)
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)
            elapsed = (datetime.now(timezone.utc) - last_dt).total_seconds()
            if elapsed < interval_seconds:
                return
        db_url = os.environ.get("DATABASE_URL", "")
        keep_count = int(config.get("keep_count", 7))
        await asyncio.to_thread(run_backup_and_update_status, config["path"], db_url, keep_count)
    except Exception as exc:
        logger.warning("Backup job error: %s", exc)


# Aliases
_backup_loop = backup_job

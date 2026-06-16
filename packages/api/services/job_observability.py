"""Persistent run history and heartbeat helpers for background jobs."""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

from core.database import db_cursor
from core.security import generate_id

logger = logging.getLogger(__name__)


def _json(data: Optional[dict[str, Any]]) -> str:
    return json.dumps(data or {})


def _duration_ms(started_at: float | None, finished_at: float | None) -> Optional[int]:
    if started_at is None or finished_at is None:
        return None
    return max(0, int((finished_at - started_at) * 1000))


def mark_job_started(
    job_name: str,
    *,
    run_id: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> None:
    """Best-effort heartbeat update. Observability must never break the job."""
    try:
        with db_cursor(commit=True) as cur:
            cur.execute(
                """
                INSERT INTO scheduler_heartbeats (
                    job_name, status, last_run_at, run_count, last_run_id, metadata, updated_at
                )
                VALUES (%s, 'running', now(), 1, %s, %s, now())
                ON CONFLICT (job_name) DO UPDATE SET
                    status = 'running',
                    last_run_at = now(),
                    run_count = scheduler_heartbeats.run_count + 1,
                    last_run_id = EXCLUDED.last_run_id,
                    metadata = EXCLUDED.metadata,
                    updated_at = now()
                """,
                (job_name, run_id, _json(metadata)),
            )
    except Exception as exc:
        logger.debug("Could not mark job heartbeat start for %s: %s", job_name, exc)


def mark_job_finished(
    job_name: str,
    *,
    status: str,
    duration_ms: Optional[int] = None,
    run_id: Optional[str] = None,
    error: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> None:
    try:
        with db_cursor(commit=True) as cur:
            cur.execute(
                """
                INSERT INTO scheduler_heartbeats (
                    job_name, status, last_run_at, last_success_at, last_failure_at,
                    duration_ms, run_count, failure_count, last_run_id, last_error,
                    metadata, updated_at
                )
                VALUES (
                    %s, %s, now(),
                    CASE WHEN %s = 'success' THEN now() ELSE NULL END,
                    CASE WHEN %s = 'failed' THEN now() ELSE NULL END,
                    %s, 1,
                    CASE WHEN %s = 'failed' THEN 1 ELSE 0 END,
                    %s, %s, %s, now()
                )
                ON CONFLICT (job_name) DO UPDATE SET
                    status = EXCLUDED.status,
                    last_success_at = CASE
                        WHEN EXCLUDED.status = 'success' THEN now()
                        ELSE scheduler_heartbeats.last_success_at
                    END,
                    last_failure_at = CASE
                        WHEN EXCLUDED.status = 'failed' THEN now()
                        ELSE scheduler_heartbeats.last_failure_at
                    END,
                    duration_ms = EXCLUDED.duration_ms,
                    failure_count = scheduler_heartbeats.failure_count +
                        CASE WHEN EXCLUDED.status = 'failed' THEN 1 ELSE 0 END,
                    last_run_id = COALESCE(EXCLUDED.last_run_id, scheduler_heartbeats.last_run_id),
                    last_error = EXCLUDED.last_error,
                    metadata = EXCLUDED.metadata,
                    updated_at = now()
                """,
                (
                    job_name,
                    status,
                    status,
                    status,
                    duration_ms,
                    status,
                    run_id,
                    error,
                    _json(metadata),
                ),
            )
    except Exception as exc:
        logger.debug("Could not mark job heartbeat finish for %s: %s", job_name, exc)


def start_job_run(
    job_name: str,
    *,
    workspace_id: Optional[str] = None,
    trigger: str = "scheduler",
    summary: Optional[dict[str, Any]] = None,
    update_heartbeat: bool = True,
) -> str:
    run_id = generate_id("jobrun")
    try:
        with db_cursor(commit=True) as cur:
            cur.execute(
                """
                INSERT INTO job_runs (id, job_name, workspace_id, trigger, status, summary)
                VALUES (%s, %s, %s, %s, 'running', %s)
                """,
                (run_id, job_name, workspace_id, trigger, _json(summary)),
            )
        if update_heartbeat:
            mark_job_started(job_name, run_id=run_id, metadata=summary)
    except Exception as exc:
        logger.debug("Could not start job run for %s: %s", job_name, exc)
    return run_id


def finish_job_run(
    run_id: Optional[str],
    job_name: str,
    *,
    status: str,
    duration_ms: Optional[int] = None,
    scanned_count: Optional[int] = None,
    processed_count: Optional[int] = None,
    created_count: Optional[int] = None,
    skipped_count: Optional[int] = None,
    failed_count: Optional[int] = None,
    error: Optional[str] = None,
    summary: Optional[dict[str, Any]] = None,
    update_heartbeat: bool = True,
) -> None:
    try:
        if run_id:
            with db_cursor(commit=True) as cur:
                cur.execute(
                    """
                    UPDATE job_runs
                    SET status = %s,
                        finished_at = now(),
                        duration_ms = %s,
                        scanned_count = %s,
                        processed_count = %s,
                        created_count = %s,
                        skipped_count = %s,
                        failed_count = %s,
                        error = %s,
                        summary = %s
                    WHERE id = %s
                    """,
                    (
                        status,
                        duration_ms,
                        scanned_count,
                        processed_count,
                        created_count,
                        skipped_count,
                        failed_count,
                        error,
                        _json(summary),
                        run_id,
                    ),
                )
        if update_heartbeat:
            mark_job_finished(
                job_name,
                status=status,
                duration_ms=duration_ms,
                run_id=run_id,
                error=error,
                metadata=summary,
            )
    except Exception as exc:
        logger.debug("Could not finish job run for %s: %s", job_name, exc)


def list_job_runs(
    cur,
    *,
    workspace_id: str,
    job_name: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    conditions = ["workspace_id = %s"]
    params: list[Any] = [workspace_id]
    if job_name:
        conditions.append("job_name = %s")
        params.append(job_name)
    if status:
        conditions.append("status = %s")
        params.append(status)
    params.extend([limit, offset])
    cur.execute(
        f"""
        SELECT *
        FROM job_runs
        WHERE {' AND '.join(conditions)}
        ORDER BY started_at DESC
        LIMIT %s OFFSET %s
        """,
        params,
    )
    return [dict(row) for row in cur.fetchall()]


def list_scheduler_heartbeats(cur) -> list[dict[str, Any]]:
    cur.execute(
        """
        SELECT *
        FROM scheduler_heartbeats
        ORDER BY updated_at DESC, job_name ASC
        """
    )
    return [dict(row) for row in cur.fetchall()]


__all__ = [
    "_duration_ms",
    "finish_job_run",
    "list_job_runs",
    "list_scheduler_heartbeats",
    "mark_job_finished",
    "mark_job_started",
    "start_job_run",
]

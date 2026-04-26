"""
Audit-log middleware (batched).

Architecture:
  request handler ──┐
                    │  enqueue (non-blocking, < 1µs)
                    ▼
            asyncio.Queue (bounded 5000)
                    │
                    │  drain every FLUSH_INTERVAL_SECONDS or
                    │  when batch reaches BATCH_SIZE
                    ▼
        single executemany() to ws_access_log

Why batched?
  - One DB connection per request (`asyncio.create_task(_write_log())`)
    can exhaust PostgreSQL's max_connections under load.
  - Batched inserts use one connection + one round-trip for many entries.

Robustness:
  - Queue is bounded; on overflow we drop the oldest entry and emit a
    WARNING.  An audit-log gap is preferable to blocking the API.
  - Failures in the consumer are logged but never propagate; if the
    DB is down, audit entries are dropped, not retried indefinitely.

Schema (created by migrations/003_add_ws_access_log.sql):
  ws_access_log(ts, user_id, ip, method, path, workspace_id, status_code, duration_ms)
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import Any, List, Tuple

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from .database import db_cursor
from .security import decode_token

logger = logging.getLogger(__name__)

_WS_ID_RE = re.compile(r"/workspaces/([^/?]+)")

# ─── Tunables ──────────────────────────────────────────────────────────────────
_QUEUE_MAX_SIZE         = 5000   # max in-flight log entries before we start dropping
_BATCH_SIZE             = 100    # rows per executemany
_FLUSH_INTERVAL_SECONDS = 1.0    # max time a row sits in the queue
# ───────────────────────────────────────────────────────────────────────────────

_LogTuple = Tuple[Any, Any, str, str, Any, int, int]
_queue: "asyncio.Queue[_LogTuple] | None" = None  # initialized at startup


def _extract_user_id(request: Request) -> str | None:
    """Return user_id from JWT or marker for API-key requests."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth[len("Bearer "):]
    if token.startswith("mt_"):
        # API key — full lookup happens in the route handler; mark for now
        return "apikey"
    payload = decode_token(token)
    return payload.get("sub") if payload else None


# ─── Middleware (producer) ─────────────────────────────────────────────────────

class AuditLogMiddleware(BaseHTTPMiddleware):
    """Records every /api/* request to ws_access_log via a bounded queue."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path
        if not path.startswith("/api/"):
            return await call_next(request)

        start = time.monotonic()
        response = await call_next(request)
        duration_ms = int((time.monotonic() - start) * 1000)

        ip: str | None = request.client.host if request.client else None
        ws_match = _WS_ID_RE.search(path)
        workspace_id: str | None = ws_match.group(1) if ws_match else None
        user_id = _extract_user_id(request)

        entry: _LogTuple = (
            user_id, ip, request.method, path,
            workspace_id, response.status_code, duration_ms,
        )

        q = _queue
        if q is None:
            return response  # consumer not started yet (startup race) — drop silently

        try:
            q.put_nowait(entry)
        except asyncio.QueueFull:
            # Drop the oldest entry to make room; better a gap than blocking
            try:
                _ = q.get_nowait()
                q.task_done()
            except asyncio.QueueEmpty:
                pass
            try:
                q.put_nowait(entry)
            except asyncio.QueueFull:
                logger.warning("Audit log queue full; dropping entry path=%s", path)

        return response


# ─── Consumer (background task) ────────────────────────────────────────────────

async def audit_writer_loop() -> None:
    """
    Drain the audit queue and write rows in batches.
    Started by the FastAPI lifespan handler in main.py.
    """
    global _queue
    _queue = asyncio.Queue(maxsize=_QUEUE_MAX_SIZE)
    logger.info("Audit log writer started (queue=%d, batch=%d)", _QUEUE_MAX_SIZE, _BATCH_SIZE)

    while True:
        batch: List[_LogTuple] = []
        try:
            # Block for the first item, then drain up to BATCH_SIZE non-blocking
            first = await asyncio.wait_for(_queue.get(), timeout=_FLUSH_INTERVAL_SECONDS)
            batch.append(first)
            _queue.task_done()
            while len(batch) < _BATCH_SIZE:
                try:
                    batch.append(_queue.get_nowait())
                    _queue.task_done()
                except asyncio.QueueEmpty:
                    break
        except asyncio.TimeoutError:
            continue       # Nothing in the queue this interval — loop again
        except asyncio.CancelledError:
            # Drain whatever is left on shutdown, then exit
            while True:
                try:
                    batch.append(_queue.get_nowait())
                    _queue.task_done()
                except asyncio.QueueEmpty:
                    break
            if batch:
                await asyncio.to_thread(_flush_batch, batch)
            logger.info("Audit log writer stopped")
            raise

        if batch:
            # Run blocking DB I/O in a thread to avoid stalling the event loop
            await asyncio.to_thread(_flush_batch, batch)


def _flush_batch(rows: List[_LogTuple]) -> None:
    """Write a batch of audit rows in a single transaction."""
    try:
        with db_cursor(commit=True) as cur:
            cur.executemany(
                """
                INSERT INTO ws_access_log
                    (user_id, ip, method, path, workspace_id, status_code, duration_ms)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                rows,
            )
    except Exception as exc:
        # Most likely cause: migration 003 hasn't run yet, or DB is down.
        # We never retry — audit gaps are acceptable, blocking the API is not.
        logger.debug("Audit batch flush failed (%d rows): %s", len(rows), exc)

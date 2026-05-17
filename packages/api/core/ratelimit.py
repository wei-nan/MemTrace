"""
Rate-limiting middleware using an in-memory sliding-window counter.

Tiers (per unique client key = IP + path-group):
  - search  :  30 requests / 60 s   (expensive vector/full-text queries)
  - write   :  60 requests / 60 s   (POST/PUT/PATCH/DELETE to API)
  - global  : 600 requests / 60 s   (everything else)

Client key is the remote IP address.  When the window is exceeded the
middleware returns HTTP 429 immediately — the request never reaches the
route handler.

Note: for multi-process deployments replace this with a Redis-backed
counter (e.g. slowapi + redis).
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from threading import Lock
from typing import DefaultDict, Deque, Tuple

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from fastapi import HTTPException

logger = logging.getLogger(__name__)

# ─── Limit definitions ─────────────────────────────────────────────────────────

_LIMITS: dict[str, tuple[int, int]] = {
    # group       window(s)  max_requests
    "search":    (60,  30),
    "write":     (60, 120),
    "global":    (60, 600),
}

# ─── Shared sliding-window state ───────────────────────────────────────────────

# Key: (client_ip, group)  →  deque of monotonic timestamps
_windows: DefaultDict[Tuple[str, str], Deque[float]] = defaultdict(deque)
_lock: Lock = Lock()

# Prevent unbounded growth: evict LRU entries when dict exceeds this size
_MAX_TRACKED = 50_000


def _evict_if_needed() -> None:
    """Remove the oldest (emptied) windows when the dict grows too large."""
    if len(_windows) < _MAX_TRACKED:
        return
    now = time.monotonic()
    to_del = [k for k, dq in _windows.items() if not dq or dq[-1] < now - 120]
    for k in to_del[:len(to_del) // 2 + 1]:
        del _windows[k]


def _classify_request(method: str, path: str) -> str:
    """Map a request to a rate-limit tier name."""
    if "search" in path or "semantic" in path or "traverse" in path:
        return "search"
    if method.upper() not in ("GET", "HEAD", "OPTIONS"):
        return "write"
    return "global"


# ─── Middleware ────────────────────────────────────────────────────────────────

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window rate limiter applied before every route handler."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip rate-limiting for static files and health checks
        path = request.url.path
        if path in ("/", "/health") or not path.startswith("/api/"):
            return await call_next(request)

        # Detect actual client IP (proxy-aware)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # X-Forwarded-For can be a comma-separated list; the first one is the original client
            ip = forwarded_for.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"

        group: str = _classify_request(request.method, path)
        window_s, max_req = _LIMITS[group]

        key: Tuple[str, str] = (ip, group)
        now = time.monotonic()

        with _lock:
            _evict_if_needed()
            dq = _windows[key]
            # Purge timestamps outside the sliding window
            cutoff = now - window_s
            while dq and dq[0] < cutoff:
                dq.popleft()

            current = len(dq)
            if current >= max_req:
                logger.warning(
                    "Rate limit: ip=%s group=%s count=%d/%d path=%s",
                    ip, group, current, max_req, path,
                )
                return Response(
                    content='{"detail":"Rate limit exceeded. Please slow down and try again."}',
                    status_code=429,
                    media_type="application/json",
                    headers={
                        "Retry-After": str(window_s),
                        "X-RateLimit-Limit": str(max_req),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Window": str(window_s),
                    },
                )
            dq.append(now)
            remaining = max_req - current - 1

        response = await call_next(request)
        # Inform callers of their remaining budget
        response.headers["X-RateLimit-Limit"] = str(max_req)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Window"] = str(window_s)
        return response


# ─── Traversal anomaly guard ───────────────────────────────────────────────────

_TRAVERSAL_SOFT_LIMIT = 500    # req / 10 min → HTTP 429
_TRAVERSAL_HARD_LIMIT = 2000   # req / 10 min → 1-hour suspend
_TRAVERSAL_WINDOW     = 600    # 10 minutes in seconds
_SUSPEND_DURATION     = 3600   # 1 hour in seconds

# user_id → deque of monotonic timestamps within the window
_traversal_windows: DefaultDict[str, Deque[float]] = defaultdict(deque)
# user_id → monotonic timestamp until which the user is suspended
_suspended_until: dict[str, float] = {}
_traversal_lock = Lock()


class TraversalGuard:
    """
    Per-user traversal anomaly detector.

    Call `check(user_id)` at the beginning of every traverse endpoint.
    Raises HTTPException(429) on soft limit or HTTPException(403) on hard
    suspension.  The guard is intentionally stateless across restarts
    (in-memory only); persistent tracking can be added later if needed.
    """

    @staticmethod
    def check(user_id: str) -> None:
        now = time.monotonic()
        with _traversal_lock:
            # Suspended?
            suspended = _suspended_until.get(user_id, 0)
            if now < suspended:
                remaining_s = int(suspended - now)
                raise HTTPException(
                    status_code=403,
                    detail=(
                        f"Your account has been temporarily suspended due to abnormal traversal activity. "
                        f"Please try again in {remaining_s // 60 + 1} minute(s)."
                    ),
                )

            dq = _traversal_windows[user_id]
            cutoff = now - _TRAVERSAL_WINDOW
            while dq and dq[0] < cutoff:
                dq.popleft()

            count = len(dq)

            if count >= _TRAVERSAL_HARD_LIMIT:
                _suspended_until[user_id] = now + _SUSPEND_DURATION
                logger.critical(
                    "Traversal HARD LIMIT: user=%s count=%d — suspended for 1 hour",
                    user_id, count,
                )
                raise HTTPException(
                    status_code=403,
                    detail=(
                        "Abnormal traversal activity detected. "
                        "Your account has been temporarily suspended for 1 hour."
                    ),
                )

            if count >= _TRAVERSAL_SOFT_LIMIT:
                logger.warning(
                    "Traversal SOFT LIMIT: user=%s count=%d/%d in %ds window",
                    user_id, count, _TRAVERSAL_SOFT_LIMIT, _TRAVERSAL_WINDOW,
                )
                raise HTTPException(
                    status_code=429,
                    detail="Traversal rate limit exceeded. Please slow down.",
                    headers={"Retry-After": "60"},
                )

            dq.append(now)

    @staticmethod
    def lift_suspension(user_id: str) -> bool:
        """Admin helper: manually lift a suspension. Returns True if one was active."""
        with _traversal_lock:
            was_suspended = _suspended_until.pop(user_id, 0) > time.monotonic()
            _traversal_windows.pop(user_id, None)
            return was_suspended

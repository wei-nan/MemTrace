"""
tests/test_traversal_guard.py — S5 TraversalGuard

涵蓋：
- 正常流量通過
- 超過 soft limit → 429
- 超過 hard limit → 403 + 帳號暫停
- 暫停期間的請求 → 403

Run: pytest tests/test_traversal_guard.py -v
"""
from __future__ import annotations

import time
from unittest.mock import patch

import pytest


def _reset_guard(user_id: str):
    """清除測試使用者的 guard 狀態（避免跨測試污染）。"""
    from core.ratelimit import _traversal_windows, _suspended_until
    _traversal_windows.pop(user_id, None)
    _suspended_until.pop(user_id, None)


# ─── 正常流量通過 ─────────────────────────────────────────────────────────────

def test_normal_traffic_passes():
    """少量請求不觸發任何限制。"""
    from core.ratelimit import TraversalGuard, _TRAVERSAL_SOFT_LIMIT

    uid = "usr_guard_normal"
    _reset_guard(uid)

    # 呼叫次數遠低於 soft limit
    for _ in range(min(3, _TRAVERSAL_SOFT_LIMIT - 1)):
        TraversalGuard.check(uid)  # should not raise


# ─── Soft limit 觸發 429 ──────────────────────────────────────────────────────

def test_soft_limit_raises_429():
    """達到 soft limit → HTTPException(429)。"""
    from fastapi import HTTPException
    from core.ratelimit import TraversalGuard, _TRAVERSAL_SOFT_LIMIT, _traversal_windows
    import collections

    uid = "usr_guard_soft"
    _reset_guard(uid)

    # 直接填入 soft limit 個時間戳（模擬近期請求）
    now = time.monotonic()
    _traversal_windows[uid] = collections.deque([now] * _TRAVERSAL_SOFT_LIMIT)

    with pytest.raises(HTTPException) as exc:
        TraversalGuard.check(uid)

    assert exc.value.status_code == 429
    _reset_guard(uid)


# ─── Hard limit 觸發 403 + 暫停 ──────────────────────────────────────────────

def test_hard_limit_raises_403_and_suspends():
    """達到 hard limit → HTTPException(403)，帳號被暫停。"""
    from fastapi import HTTPException
    from core.ratelimit import TraversalGuard, _TRAVERSAL_HARD_LIMIT, _traversal_windows, _suspended_until
    import collections

    uid = "usr_guard_hard"
    _reset_guard(uid)

    now = time.monotonic()
    _traversal_windows[uid] = collections.deque([now] * _TRAVERSAL_HARD_LIMIT)

    with pytest.raises(HTTPException) as exc:
        TraversalGuard.check(uid)

    assert exc.value.status_code == 403
    # 帳號應被寫入暫停記錄
    assert uid in _suspended_until
    assert _suspended_until[uid] > now
    _reset_guard(uid)


# ─── 暫停期間的請求 → 403 ────────────────────────────────────────────────────

def test_suspended_user_gets_403():
    """帳號暫停期間的任何請求 → 403，不管流量多少。"""
    from fastapi import HTTPException
    from core.ratelimit import TraversalGuard, _suspended_until

    uid = "usr_guard_suspended"
    _reset_guard(uid)

    # 手動設定暫停到未來 1 小時
    _suspended_until[uid] = time.monotonic() + 3600

    with pytest.raises(HTTPException) as exc:
        TraversalGuard.check(uid)

    assert exc.value.status_code == 403
    assert "suspended" in exc.value.detail.lower() or "minute" in exc.value.detail.lower()
    _reset_guard(uid)


# ─── 滑動視窗：舊請求過期後不計數 ───────────────────────────────────────────

def test_old_requests_expire_from_window():
    """視窗之外的舊請求不應計入 rate limit。"""
    from core.ratelimit import TraversalGuard, _TRAVERSAL_SOFT_LIMIT, _traversal_windows, _TRAVERSAL_WINDOW
    import collections

    uid = "usr_guard_window"
    _reset_guard(uid)

    # 填入 soft_limit 個過期時間戳（比 window 還舊）
    old_ts = time.monotonic() - _TRAVERSAL_WINDOW - 10
    _traversal_windows[uid] = collections.deque([old_ts] * _TRAVERSAL_SOFT_LIMIT)

    # 這次呼叫不應觸發 429（舊請求已過期）
    TraversalGuard.check(uid)  # should not raise
    _reset_guard(uid)

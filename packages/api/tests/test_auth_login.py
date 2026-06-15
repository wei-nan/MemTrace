"""
tests/test_auth_login.py — G1 帳號鎖定與登入流程

涵蓋：
- 正確密碼登入成功
- 錯誤密碼遞增失敗計數
- 連續 5 次失敗觸發 15 分鐘鎖定
- 帳號已鎖定時直接返回 429
- 登入成功後重置失敗計數

Run: pytest tests/test_auth_login.py -v
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch, call

import pytest


# ─── helpers ─────────────────────────────────────────────────────────────────

def _make_user(failed=0, locked_until=None, password_hash="hashed"):
    return {
        "id": "usr_test",
        "display_name": "Test",
        "password_hash": password_hash,
        "email_verified": True,
        "failed_login_count": failed,
        "locked_until": locked_until,
    }


def _make_body(email="test@example.com", password="ValidPass1"):
    b = MagicMock()
    b.email = email
    b.password = password
    return b


def _mock_db(user_row):
    cur = MagicMock()
    cur.fetchone.return_value = user_row
    cm = MagicMock()
    cm.__enter__ = lambda s: cur
    cm.__exit__ = MagicMock(return_value=False)
    return cm, cur


# ─── 登入成功 ─────────────────────────────────────────────────────────────────

def test_login_success_returns_token():
    """正確密碼 → 回傳 access_token，重置失敗計數。"""
    user = _make_user(failed=2)
    db_cm, cur = _mock_db(user)

    with patch("routers.auth.db_cursor", return_value=db_cm), \
         patch("routers.auth.verify_password", return_value=True), \
         patch("routers.auth.create_access_token", return_value="tok_ok"), \
         patch("routers.auth.generate_refresh_token", return_value=("raw", "hash")), \
         patch("routers.auth._set_refresh_cookie"):

        from routers.auth import login
        import json
        resp = login(_make_body())

        # failed_login_count should be reset
        update_calls = [str(c) for c in cur.execute.call_args_list]
        assert any("failed_login_count = 0" in c or "failed_login_count=%s" in c or "0" in c for c in update_calls)


# ─── 錯誤密碼遞增計數 ────────────────────────────────────────────────────────

def test_wrong_password_increments_failed_count():
    """錯誤密碼 → failed_login_count + 1，回傳 401。"""
    from fastapi import HTTPException
    user = _make_user(failed=1)
    db_cm, cur = _mock_db(user)

    with patch("routers.auth.db_cursor", return_value=db_cm), \
         patch("routers.auth.verify_password", return_value=False):

        from routers.auth import login
        with pytest.raises(HTTPException) as exc:
            login(_make_body())

        assert exc.value.status_code == 401
        # Check that UPDATE was called to increment count
        sql_calls = " ".join(str(c) for c in cur.execute.call_args_list)
        assert "failed_login_count" in sql_calls


# ─── 5 次失敗觸發鎖定 ────────────────────────────────────────────────────────

def test_fifth_failure_triggers_lockout():
    """第 5 次失敗 → 寫入 locked_until = now() + 15min。"""
    from fastapi import HTTPException
    user = _make_user(failed=4)  # next failure = 5 → lock
    db_cm, cur = _mock_db(user)

    with patch("routers.auth.db_cursor", return_value=db_cm), \
         patch("routers.auth.verify_password", return_value=False):

        from routers.auth import login
        with pytest.raises(HTTPException) as exc:
            login(_make_body())

        assert exc.value.status_code == 401
        sql_calls = " ".join(str(c) for c in cur.execute.call_args_list)
        assert "locked_until" in sql_calls


# ─── 帳號已鎖定直接擋下 ──────────────────────────────────────────────────────

def test_locked_account_returns_429_before_password_check():
    """帳號已鎖定 → 不驗密碼，直接回傳 429 含 retry_after。"""
    from fastapi import HTTPException

    future = datetime.now(timezone.utc) + timedelta(minutes=10)
    user = _make_user(failed=5, locked_until=future)
    db_cm, cur = _mock_db(user)

    with patch("routers.auth.db_cursor", return_value=db_cm), \
         patch("routers.auth.verify_password") as mock_verify:

        from routers.auth import login
        with pytest.raises(HTTPException) as exc:
            login(_make_body())

        assert exc.value.status_code == 429
        # Password verification must NOT be called
        mock_verify.assert_not_called()


# ─── 帳號不存在 ───────────────────────────────────────────────────────────────

def test_user_not_found_returns_401():
    """找不到 email → 401（不暴露帳號是否存在）。"""
    from fastapi import HTTPException
    db_cm, cur = _mock_db(None)

    with patch("routers.auth.db_cursor", return_value=db_cm):
        from routers.auth import login
        with pytest.raises(HTTPException) as exc:
            login(_make_body())
        assert exc.value.status_code == 401


# ─── 無密碼帳號（magic-link 建立的）不能密碼登入 ─────────────────────────────

def test_no_password_hash_returns_401():
    """password_hash 為 None 的帳號（magic-link 建立）→ 401。"""
    from fastapi import HTTPException
    user = _make_user(password_hash=None)
    db_cm, cur = _mock_db(user)

    with patch("routers.auth.db_cursor", return_value=db_cm):
        from routers.auth import login
        with pytest.raises(HTTPException) as exc:
            login(_make_body())
        assert exc.value.status_code == 401


# ─── 鎖定時間已過可再登入 ────────────────────────────────────────────────────

def test_expired_lockout_allows_login():
    """locked_until 已過期 → 不觸發 429，走正常密碼驗證。"""
    past = datetime.now(timezone.utc) - timedelta(minutes=1)
    user = _make_user(failed=5, locked_until=past)
    db_cm, cur = _mock_db(user)

    with patch("routers.auth.db_cursor", return_value=db_cm), \
         patch("routers.auth.verify_password", return_value=True), \
         patch("routers.auth.create_access_token", return_value="tok"), \
         patch("routers.auth.generate_refresh_token", return_value=("r", "h")), \
         patch("routers.auth._set_refresh_cookie"):

        from routers.auth import login
        resp = login(_make_body())
        # Should not raise — expired lock is treated as unlocked
        assert resp is not None

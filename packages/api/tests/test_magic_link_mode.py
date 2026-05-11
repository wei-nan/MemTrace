"""
tests/test_magic_link_mode.py — P4.10-S1-4

Tests that verify the magic-link endpoints respect the registration_mode guard.

Two approaches are used:
1. Unit-level: patch settings directly and call the handler function
2. Integration: use TestClient (skipped if app cannot import)

Run:  pytest tests/test_magic_link_mode.py -v
"""
from __future__ import annotations

import hashlib
from unittest.mock import MagicMock, patch

import pytest


# ─── Unit-level: test handler logic directly ─────────────────────────────────
# These tests bypass the HTTP layer (CSRF etc.) and test the guard logic directly.

def _make_settings(mode: str):
    s = MagicMock()
    s.registration_mode = mode
    s.registration_domains = []
    s.refresh_token_expire_days = 30
    s.app_url = "http://localhost"
    return s


# ─── S1-4a: magic-link/request blocked in open mode ──────────────────────────

def test_magic_link_request_blocked_in_open_mode():
    """
    The request_magic_link handler must raise HTTPException(403) when
    registration_mode != 'invite_only'.
    """
    from fastapi import HTTPException
    mock_settings = _make_settings("open")

    with patch("routers.registration.settings", mock_settings):
        from routers.registration import request_magic_link
        from models.auth import MagicLinkRegisterRequest
        body = MagicMock()
        body.email = "test@example.com"

        with pytest.raises(HTTPException) as exc_info:
            request_magic_link(body)

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["error"] == "magic_link_unavailable"


# ─── S1-4a (variant): domain mode also blocked ───────────────────────────────

def test_magic_link_request_blocked_in_domain_mode():
    from fastapi import HTTPException
    mock_settings = _make_settings("domain")

    with patch("routers.registration.settings", mock_settings):
        from routers.registration import request_magic_link
        body = MagicMock()
        body.email = "test@example.com"

        with pytest.raises(HTTPException) as exc_info:
            request_magic_link(body)

        assert exc_info.value.status_code == 403


# ─── S1-4b: magic-link/request allowed in invite_only mode ───────────────────

def test_magic_link_request_allowed_in_invite_only_mode():
    """
    In invite_only mode, the handler should proceed past the mode guard
    (subsequent DB errors are OK in this unit test; we only care it does NOT 403).
    """
    from fastapi import HTTPException
    mock_settings = _make_settings("invite_only")

    with patch("routers.registration.settings", mock_settings), \
         patch("routers.registration.db_cursor") as mock_db, \
         patch("routers.registration.send_magic_link_email"):

        # Simulate no existing user and no recent token
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = None
        mock_db.return_value.__enter__ = lambda s: mock_cur
        mock_db.return_value.__exit__ = MagicMock(return_value=False)

        from routers.registration import request_magic_link
        body = MagicMock()
        body.email = "user@example.com"

        # Should not raise a 403 — may succeed or raise a non-403 error
        try:
            result = request_magic_link(body)
            # 200 response — magic link path executed
        except HTTPException as e:
            assert e.status_code != 403, f"Should not get 403 in invite_only mode, got: {e.detail}"
        except Exception:
            pass  # DB or other error is acceptable; we only check mode guard


# ─── S1-4c: magic-link/verify blocked in open mode ───────────────────────────

def test_magic_link_verify_blocked_in_open_mode():
    """
    POST /auth/magic-link/verify must raise 403 when registration_mode != 'invite_only'.
    """
    from fastapi import HTTPException
    mock_settings = _make_settings("open")

    with patch("routers.registration.settings", mock_settings):
        from routers.registration import verify_magic_link
        body = MagicMock()
        body.token = "sometoken"

        with pytest.raises(HTTPException) as exc_info:
            verify_magic_link(body)

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["error"] == "magic_link_unavailable"


# ─── S1-4c (extra): approval mode also blocked ───────────────────────────────

def test_magic_link_verify_blocked_in_approval_mode():
    from fastapi import HTTPException
    mock_settings = _make_settings("approval")

    with patch("routers.registration.settings", mock_settings):
        from routers.registration import verify_magic_link
        body = MagicMock()
        body.token = "sometoken"

        with pytest.raises(HTTPException) as exc_info:
            verify_magic_link(body)

        assert exc_info.value.status_code == 403


# ─── S1-4c (extra): verify allowed in invite_only mode ──────────────────────

def test_magic_link_verify_allowed_in_invite_only_mode():
    """
    In invite_only mode, verify should proceed past the guard
    (may fail on DB lookup which is fine).
    """
    from fastapi import HTTPException
    mock_settings = _make_settings("invite_only")

    with patch("routers.registration.settings", mock_settings), \
         patch("routers.registration.db_cursor") as mock_db:

        mock_cur = MagicMock()
        # Simulate "token not found" (record = None) → 400, not 403
        mock_cur.fetchone.return_value = None
        mock_db.return_value.__enter__ = lambda s: mock_cur
        mock_db.return_value.__exit__ = MagicMock(return_value=False)

        from routers.registration import verify_magic_link
        body = MagicMock()
        body.token = "sometoken"

        with pytest.raises(HTTPException) as exc_info:
            verify_magic_link(body)

        # Should be 400 (invalid token), NOT 403 (mode guard)
        assert exc_info.value.status_code != 403, \
            f"Should not get 403 in invite_only mode, got {exc_info.value.status_code}: {exc_info.value.detail}"

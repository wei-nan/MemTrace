"""
tests/test_password_registration.py — R1–R7

Tests for POST /auth/register/password
Verifies password policy, mode guard, duplicate email, and happy path.

Run:  pytest tests/test_password_registration.py -v
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


def _make_settings(mode: str = "open"):
    s = MagicMock()
    s.registration_mode = mode
    s.registration_domains = []
    s.refresh_token_expire_days = 30
    s.app_url = "http://localhost"
    s.access_token_expire_minutes = 30
    return s


def _make_body(email: str = "new@example.com", password: str = "ValidPass1",
               display_name: str = "Test User"):
    b = MagicMock()
    b.email = email
    b.password = password
    b.display_name = display_name
    return b


def _mock_db(existing_user=None):
    """Return a patchable db_cursor context manager with optional existing user."""
    cur = MagicMock()
    cur.fetchone.return_value = existing_user
    cm = MagicMock()
    cm.__enter__ = lambda s: cur
    cm.__exit__ = MagicMock(return_value=False)
    return cm, cur


# ─── R1: happy path returns access_token ─────────────────────────────────────

def test_r1_successful_registration():
    """Valid email + strong password in open mode → 201 with access_token."""
    from fastapi import HTTPException

    mock_settings = _make_settings("open")
    db_cm, cur = _mock_db(existing_user=None)

    with patch("routers.registration.settings", mock_settings), \
         patch("routers.registration.db_cursor", return_value=db_cm), \
         patch("routers.registration.check_password_policy", return_value=None), \
         patch("routers.registration.hash_password", return_value="hashed"), \
         patch("routers.registration.generate_id", return_value="usr_newtest"), \
         patch("routers.registration.create_access_token", return_value="tok_abc"), \
         patch("routers.registration.generate_refresh_token", return_value=("raw", "hash")), \
         patch("routers.registration._set_refresh_cookie"):

        from routers.registration import register_with_password
        body = _make_body()

        from fastapi.responses import JSONResponse
        result = register_with_password(body)
        assert isinstance(result, JSONResponse)
        import json
        data = json.loads(result.body)
        assert data["access_token"] == "tok_abc"


# ─── R2: password too short ───────────────────────────────────────────────────

def test_r2_password_too_short():
    from fastapi import HTTPException
    from core.security import check_password_policy

    err = check_password_policy("abc")
    assert err is not None
    assert "8" in err  # mentions length


# ─── R3: password missing uppercase ──────────────────────────────────────────

def test_r3_no_uppercase():
    from core.security import check_password_policy

    err = check_password_policy("test1234")
    assert err is not None
    assert "uppercase" in err.lower()


# ─── R4: password missing digit ──────────────────────────────────────────────

def test_r4_no_digit():
    from core.security import check_password_policy

    err = check_password_policy("TestPass")
    assert err is not None
    assert "digit" in err.lower()


# ─── R5: HIBP leaked password blocked ────────────────────────────────────────

def test_r5_hibp_leaked_password():
    """Password1 variants appear in HIBP; check_password_policy should return an error.
    We mock the HIBP HTTP call to simulate a match."""
    import hashlib
    from unittest.mock import patch as _patch

    password = "Password1!"
    sha1 = hashlib.sha1(password.encode()).hexdigest().upper()
    suffix = sha1[5:]

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = f"{suffix}:10\nOTHER1:1\n"

    with _patch("httpx.get", return_value=mock_resp):
        from core.security import check_password_policy
        err = check_password_policy(password)
        assert err is not None
        assert "洩漏" in err or "leak" in err.lower() or "pwned" in err.lower() or "洩" in err


# ─── R6: duplicate email returns 409 ─────────────────────────────────────────

def test_r6_duplicate_email():
    from fastapi import HTTPException

    mock_settings = _make_settings("open")
    existing = {"id": "usr_existing"}
    db_cm, cur = _mock_db(existing_user=existing)

    with patch("routers.registration.settings", mock_settings), \
         patch("routers.registration.db_cursor", return_value=db_cm), \
         patch("routers.registration.check_password_policy", return_value=None):

        from routers.registration import register_with_password
        body = _make_body()

        with pytest.raises(HTTPException) as exc:
            register_with_password(body)

        assert exc.value.status_code == 409


# ─── R7: invite_only mode blocks password registration ───────────────────────

def test_r7_invite_only_blocks_password_register():
    from fastapi import HTTPException

    mock_settings = _make_settings("invite_only")

    with patch("routers.registration.settings", mock_settings):
        from routers.registration import register_with_password
        body = _make_body()

        with pytest.raises(HTTPException) as exc:
            register_with_password(body)

        assert exc.value.status_code == 403


# ─── R7b: closed mode also blocks ────────────────────────────────────────────

def test_r7b_closed_mode_blocks():
    from fastapi import HTTPException

    mock_settings = _make_settings("closed")

    with patch("routers.registration.settings", mock_settings):
        from routers.registration import register_with_password
        body = _make_body()

        with pytest.raises(HTTPException) as exc:
            register_with_password(body)

        assert exc.value.status_code == 403

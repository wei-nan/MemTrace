"""
tests/test_kb_access_control.py — A1–A6

Tests for workspace access control and description field.
Covers public KB anonymous read, private KB guards, and description PATCH.

Run:  pytest tests/test_kb_access_control.py -v
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


def _ws(visibility: str = "private", owner_id: str = "usr_owner") -> dict:
    return {
        "id": "ws_test_001",
        "name": "Test KB",
        "description": None,
        "visibility": visibility,
        "owner_id": owner_id,
        "kb_type": "evergreen",
        "language": "zh-TW",
        "status": "active",
        "deleted_at": None,
        "allow_anonymous_view": False,
        "linked_workspace_id": None,
        "embedding_model": "text-embedding-3-small",
        "embedding_dim": 1536,
        "embedding_provider": "openai",
        "migrating_to_provider": None,
        "migrating_to_model": None,
        "migration_status": "none",
        "archive_window_days": 90,
        "min_traversals": 1,
        "qa_archive_mode": "manual_review",
        "extraction_provider": None,
        "auto_split": False,
        "consult_trust_tier": "ask",
        "consult_provider": None,
        "agent_node_id": None,
        "settings": {},
        "schema_version": "1.0",
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }


def _mock_require_ws(ws_dict):
    """Patch require_ws_access to return the given workspace dict."""
    from unittest.mock import patch
    return patch("services.workspaces.require_ws_access", return_value=ws_dict)


# ─── A1: public KB anonymous read ────────────────────────────────────────────

def test_a1_public_kb_anonymous_accessible():
    """require_ws_access with user=None should not raise for a public workspace."""
    from services.workspaces import require_ws_access

    cur = MagicMock()
    cur.fetchone.return_value = _ws(visibility="public")

    # Should not raise
    ws = require_ws_access(cur, "ws_test_001", user=None)
    assert ws is not None


# ─── A2: private KB blocks anonymous ─────────────────────────────────────────

def test_a2_private_kb_anonymous_blocked():
    """require_ws_access with user=None on a private workspace → 403/404."""
    from fastapi import HTTPException
    from services.workspaces import require_ws_access

    cur = MagicMock()
    cur.fetchone.return_value = _ws(visibility="private")

    with pytest.raises(HTTPException) as exc:
        require_ws_access(cur, "ws_test_001", user=None)

    assert exc.value.status_code in (403, 404)


# ─── A3: private KB owner can read ───────────────────────────────────────────

def test_a3_private_kb_owner_accessible():
    """Owner of a private workspace should pass require_ws_access."""
    from services.workspaces import require_ws_access

    owner_id = "usr_owner"
    cur = MagicMock()
    cur.fetchone.side_effect = [
        _ws(visibility="private", owner_id=owner_id),  # workspace lookup
        None,  # membership lookup (not needed for owner)
    ]
    user = {"sub": owner_id}

    ws = require_ws_access(cur, "ws_test_001", user=user)
    assert ws is not None


# ─── A4: private KB non-member blocked ───────────────────────────────────────

def test_a4_private_kb_non_member_blocked():
    """A user who is neither owner nor member of a private workspace is blocked."""
    from fastapi import HTTPException
    from services.workspaces import require_ws_access

    cur = MagicMock()
    # First call: workspace fetch; second: membership check (not a member)
    cur.fetchone.side_effect = [
        _ws(visibility="private", owner_id="usr_owner"),
        None,  # no membership row
    ]
    user = {"sub": "usr_stranger"}

    with pytest.raises(HTTPException) as exc:
        require_ws_access(cur, "ws_test_001", user=user)

    assert exc.value.status_code in (403, 404)


# ─── A5: description can be saved ────────────────────────────────────────────

def test_a5_description_saved_in_update():
    """update_workspace_in_db must include 'description' in the SET clause."""
    from services.workspaces import update_workspace_in_db

    owner_id = "usr_owner"
    ws = _ws(visibility="private", owner_id=owner_id)
    ws["description"] = None

    cur = MagicMock()
    cur.fetchone.side_effect = [ws, {**ws, "description": "My KB about X"}]

    update_workspace_in_db(
        cur, "ws_test_001", owner_id,
        {"description": "My KB about X"}
    )

    sql: str = cur.execute.call_args_list[-1][0][0]
    assert "description" in sql


# ─── A6: description can be cleared ──────────────────────────────────────────

def test_a6_description_cleared_with_none():
    """Passing description=None should be included in the update (allows clearing)."""
    from services.workspaces import update_workspace_in_db

    owner_id = "usr_owner"
    ws = _ws(visibility="private", owner_id=owner_id)
    ws["description"] = "Old description"

    cur = MagicMock()
    cur.fetchone.side_effect = [ws, {**ws, "description": None}]

    # description=None means "clear it" — it should still appear in the SET clause
    update_workspace_in_db(
        cur, "ws_test_001", owner_id,
        {"description": None}
    )

    sql: str = cur.execute.call_args_list[-1][0][0]
    assert "description" in sql

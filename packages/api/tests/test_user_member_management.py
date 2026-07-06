from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from models.collaboration import MemberCreate
from routers import admin, collaboration


@contextmanager
def _fake_db_cursor(cur, *args, **kwargs):
    yield cur


def test_list_system_users_returns_page():
    cur = MagicMock()
    cur.fetchone.return_value = {"cnt": 1}
    cur.fetchall.return_value = [
        {
            "id": "user_1",
            "display_name": "Alice",
            "email": "alice@example.com",
            "email_verified": True,
            "is_platform_admin": False,
            "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "last_login_at": None,
            "workspace_count": 2,
        }
    ]

    with patch("routers.admin.db_cursor", new=lambda *a, **k: _fake_db_cursor(cur)):
        page = admin.list_system_users(q="alice", limit=10, offset=0, user={"sub": "admin"})

    assert page["total"] == 1
    assert page["users"][0]["email"] == "alice@example.com"
    assert page["users"][0]["workspace_count"] == 2
    assert "ILIKE" in cur.execute.call_args_list[0].args[0]


def test_add_existing_member_inserts_membership_and_notification():
    cur = MagicMock()
    joined_at = datetime(2026, 1, 2, tzinfo=timezone.utc)
    cur.fetchone.side_effect = [
        {"owner_id": "owner_1", "visibility": "restricted", "name": "Spec KB"},
        {"id": "user_2", "display_name": "Bob", "email": "bob@example.com"},
        None,
        {"user_id": "user_2", "role": "editor", "joined_at": joined_at},
    ]

    with patch("routers.collaboration.db_cursor", new=lambda *a, **k: _fake_db_cursor(cur)), patch(
        "routers.collaboration._get_effective_role", return_value="admin"
    ):
        member = collaboration.add_existing_member(
            "ws_1",
            MemberCreate(user_id="user_2", role="editor"),
            user={"sub": "owner_1", "email": "owner@example.com"},
        )

    assert member["user_id"] == "user_2"
    assert member["role"] == "editor"
    executed_sql = [call.args[0] for call in cur.execute.call_args_list]
    assert any("INSERT INTO workspace_members" in sql for sql in executed_sql)
    assert any("INSERT INTO notifications" in sql for sql in executed_sql)


def test_list_user_candidates_excludes_owner_and_existing_members():
    cur = MagicMock()
    cur.fetchone.return_value = {"owner_id": "owner_1", "visibility": "restricted", "name": "Spec KB"}
    cur.fetchall.return_value = [{"id": "user_2", "display_name": "Bob", "email": "bob@example.com"}]

    with patch("routers.collaboration.db_cursor", new=lambda *a, **k: _fake_db_cursor(cur)), patch(
        "routers.collaboration._get_effective_role", return_value="admin"
    ):
        rows = collaboration.list_user_candidates("ws_1", q="bo", limit=20, user={"sub": "owner_1"})

    assert rows[0]["id"] == "user_2"
    params = cur.execute.call_args.args[1]
    assert "owner_1" in params
    assert "ws_1" in params


def test_leave_workspace_deletes_current_user_membership():
    cur = MagicMock()
    cur.fetchone.side_effect = [{"owner_id": "owner_1"}, {"user_id": "user_2"}]

    with patch("routers.collaboration.db_cursor", new=lambda *a, **k: _fake_db_cursor(cur)):
        result = collaboration.leave_workspace("ws_1", user={"sub": "user_2"})

    assert result == {"message": "Left workspace"}
    assert "DELETE FROM workspace_members" in cur.execute.call_args_list[1].args[0]
    assert cur.execute.call_args_list[1].args[1] == ("ws_1", "user_2")


def test_workspace_owner_cannot_leave_workspace():
    cur = MagicMock()
    cur.fetchone.return_value = {"owner_id": "owner_1"}

    with patch("routers.collaboration.db_cursor", new=lambda *a, **k: _fake_db_cursor(cur)):
        with pytest.raises(HTTPException) as exc:
            collaboration.leave_workspace("ws_1", user={"sub": "owner_1"})

    assert exc.value.status_code == 400

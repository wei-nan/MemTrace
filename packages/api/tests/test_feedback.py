from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from services.feedback import (
    FEEDBACK_WORKSPACE_ID,
    create_feedback_node,
    list_all_feedback,
    list_my_feedback,
    feedback_type_from_tags,
)


@pytest.fixture
def mock_user():
    return {"sub": "user_123", "email": "test@example.com"}


@pytest.fixture
def other_user():
    return {"sub": "user_456", "email": "other@example.com"}


@pytest.fixture
def client():
    from main import app
    # Remove CsrfMiddleware for testing (same pattern as test_documents.py)
    app.user_middleware = [m for m in app.user_middleware if "CsrfMiddleware" not in str(m)]
    app.middleware_stack = app.build_middleware_stack()
    return TestClient(app)


@pytest.fixture
def override_auth(client, mock_user):
    from core.deps import get_current_user
    client.app.dependency_overrides[get_current_user] = lambda: mock_user
    yield
    client.app.dependency_overrides.clear()


@pytest.fixture
def mock_db():
    with patch("routers.feedback.db_cursor") as mock:
        yield mock


# ─── (a) authenticated user can submit → creates a node in ws_feedback ────────

def test_submit_feedback_creates_node_in_ws_feedback(client, override_auth, mock_db, mock_user):
    mock_cur = mock_db.return_value.__enter__.return_value
    # 1st fetchone: ensure_feedback_workspace's SELECT (workspace already exists)
    # 2nd fetchone: create_node_in_db's INSERT ... RETURNING
    mock_cur.fetchone.side_effect = [
        {"id": FEEDBACK_WORKSPACE_ID},
        {"id": "mem_fb1", "resolution_status": "open"},
    ]

    response = client.post(
        "/api/v1/feedback",
        json={"type": "bug-report", "title": "按鈕沒反應", "body": "點擊後畫面卡住"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data == {"id": "mem_fb1", "status": "open"}

    # The INSERT must target ws_feedback, tagged feedback+bug-report, authored by the caller.
    insert_call = next(
        c for c in mock_cur.execute.call_args_list if "INSERT INTO memory_nodes" in c.args[0]
    )
    sql, params = insert_call.args
    assert params[1] == FEEDBACK_WORKSPACE_ID          # workspace_id
    assert "inquiry" in params                          # content_type
    assert list(params[6]) == ["feedback", "bug-report"]  # tags
    assert mock_user["sub"] in params                    # author


def test_create_feedback_node_service_uses_inquiry_and_tags():
    cur = MagicMock()
    cur.fetchone.side_effect = [
        {"id": FEEDBACK_WORKSPACE_ID},
        {"id": "mem_fb2", "resolution_status": "open"},
    ]
    node = create_feedback_node(cur, "user_123", "feature-request", "希望能匯出 CSV", "詳細說明")
    assert node["id"] == "mem_fb2"

    insert_call = next(
        c for c in cur.execute.call_args_list if "INSERT INTO memory_nodes" in c.args[0]
    )
    _, params = insert_call.args
    assert list(params[6]) == ["feedback", "feature-request"]
    assert params[1] == FEEDBACK_WORKSPACE_ID


# ─── (b) unauthenticated request is rejected ──────────────────────────────────

def test_submit_feedback_requires_auth(client):
    response = client.post(
        "/api/v1/feedback",
        json={"type": "bug-report", "title": "x", "body": "y"},
    )
    assert response.status_code in (401, 403)


def test_get_my_feedback_requires_auth(client):
    response = client.get("/api/v1/feedback/mine")
    assert response.status_code in (401, 403)


# ─── (c) GET only returns the caller's own submissions ────────────────────────

def test_list_my_feedback_is_author_scoped():
    cur = MagicMock()
    cur.fetchall.return_value = [
        {"id": "mem_fb1", "tags": ["feedback", "bug-report"], "title": "t1",
         "resolution_status": "open", "created_at": "2026-09-01T00:00:00Z"},
    ]
    rows = list_my_feedback(cur, "user_123")
    assert len(rows) == 1

    sql, params = cur.execute.call_args.args
    assert "author = %s" in sql
    assert "'feedback' = ANY(tags)" in sql
    assert params == (FEEDBACK_WORKSPACE_ID, "user_123")


def test_get_my_feedback_endpoint_only_returns_caller_rows(client, override_auth, mock_db, mock_user):
    mock_cur = mock_db.return_value.__enter__.return_value
    # Simulate the DB already filtering by author=user_123 — another user's
    # row (user_456) must never be returned regardless of what's in the table.
    mock_cur.fetchall.return_value = [
        {"id": "mem_fb1", "tags": ["feedback", "bug-report"], "title": "我的回報",
         "resolution_status": "open", "created_at": "2026-09-01T00:00:00Z"},
    ]

    response = client.get("/api/v1/feedback/mine")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "mem_fb1"
    assert data[0]["type"] == "bug-report"

    sql, params = mock_cur.execute.call_args.args
    assert params == (FEEDBACK_WORKSPACE_ID, mock_user["sub"])


def test_feedback_type_from_tags():
    assert feedback_type_from_tags(["feedback", "bug-report"]) == "bug-report"
    assert feedback_type_from_tags(["feedback", "feature-request"]) == "feature-request"
    assert feedback_type_from_tags(["feedback"]) == "unknown"


# ─── admin listing: sees everyone's feedback, non-admin is rejected ───────────

@pytest.fixture
def admin_user():
    return {"sub": "user_admin", "email": "admin@example.com"}


def test_list_all_feedback_query_is_not_author_scoped():
    cur = MagicMock()
    cur.fetchall.return_value = [
        {"id": "mem_fb1", "tags": ["feedback", "bug-report"], "title": "t1", "body": "b1",
         "resolution_status": "open", "created_at": "2026-09-01T00:00:00Z",
         "author_id": "user_123", "author_name": "Alice", "author_email": "alice@example.com"},
        {"id": "mem_fb2", "tags": ["feedback", "feature-request"], "title": "t2", "body": "b2",
         "resolution_status": "open", "created_at": "2026-09-02T00:00:00Z",
         "author_id": "user_456", "author_name": "Bob", "author_email": "bob@example.com"},
    ]
    rows = list_all_feedback(cur)
    assert len(rows) == 2

    sql, params = cur.execute.call_args.args
    assert "author" not in sql.split("WHERE")[1].split("AND")[0]  # no author filter in WHERE
    assert params == (FEEDBACK_WORKSPACE_ID,)


def test_get_all_feedback_requires_system_admin(client):
    response = client.get("/api/v1/feedback/all")
    assert response.status_code in (401, 403)


def test_get_all_feedback_rejects_non_admin(client, override_auth):
    # override_auth logs in as a plain user (mock_user), not an admin — require_system_admin
    # must reject them even though they're authenticated.
    with patch("core.deps._admin_email_set", return_value=set()), \
         patch("core.deps.db_cursor") as mock_deps_db:
        mock_cur = mock_deps_db.return_value.__enter__.return_value
        mock_cur.fetchone.return_value = {"is_platform_admin": False}
        response = client.get("/api/v1/feedback/all")
    assert response.status_code == 403


def test_get_all_feedback_returns_rows_from_other_users(client, mock_db, admin_user):
    from core.deps import require_system_admin
    client.app.dependency_overrides[require_system_admin] = lambda: admin_user

    mock_cur = mock_db.return_value.__enter__.return_value
    mock_cur.fetchall.return_value = [
        {"id": "mem_fb1", "tags": ["feedback", "bug-report"], "title": "t1", "body": "b1",
         "resolution_status": "open", "created_at": "2026-09-01T00:00:00Z",
         "author_id": "user_123", "author_name": "Alice", "author_email": "alice@example.com"},
        {"id": "mem_fb2", "tags": ["feedback", "feature-request"], "title": "t2", "body": "b2",
         "resolution_status": "open", "created_at": "2026-09-02T00:00:00Z",
         "author_id": "user_456", "author_name": "Bob", "author_email": "bob@example.com"},
    ]

    response = client.get("/api/v1/feedback/all")
    client.app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert {row["author_id"] for row in data} == {"user_123", "user_456"}

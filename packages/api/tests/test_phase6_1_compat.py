import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

@pytest.fixture
def mock_user():
    return {"sub": "user_123", "email": "test@example.com"}

@pytest.fixture
def client():
    from main import app
    app.user_middleware = [m for m in app.user_middleware if "CsrfMiddleware" not in str(m)]
    app.middleware_stack = app.build_middleware_stack()
    from fastapi.testclient import TestClient
    return TestClient(app)

@pytest.fixture
def override_auth(client, mock_user):
    from core.deps import get_current_user
    client.app.dependency_overrides[get_current_user] = lambda: mock_user
    yield
    client.app.dependency_overrides.clear()

@pytest.fixture
def mock_db():
    with patch("routers.kb.db_cursor") as mock:
        with patch("core.ai.db_cursor", new=mock):
            yield mock

# ─── Workspace Validation Tests ───────────────────────────────────────────────

def test_create_workspace_legacy_rejected(client, override_auth, mock_db):
    # If legacy fields are present, it should fail with 422 before calling database
    response = client.post(
        "/api/v1/workspaces",
        json={"name_zh": "中文名稱", "language": "zh-TW"}
    )
    assert response.status_code == 422
    assert "Legacy fields" in response.text

    response = client.post(
        "/api/v1/workspaces",
        json={"name_en": "English Name", "language": "en"}
    )
    assert response.status_code == 422
    assert "Legacy fields" in response.text

def test_create_workspace_canonical_allowed(client, override_auth, mock_db):
    mock_cur = mock_db.return_value.__enter__.return_value
    mock_cur.fetchone.return_value = {
        "id": "ws_123",
        "name": "My Workspace",
        "language": "zh-TW",
        "visibility": "private",
        "kb_type": "evergreen",
        "owner_id": "user_123",
        "archive_window_days": 90,
        "min_traversals": 1,
        "embedding_model": "text-embedding-3-small",
        "embedding_dim": 1536,
        "qa_archive_mode": "manual_review",
        "created_at": "2026-05-26T00:00:00",
        "updated_at": "2026-05-26T00:00:00",
        "agent_node_id": "agent_123",
    }
    
    response = client.post(
        "/api/v1/workspaces",
        json={"name": "My Workspace", "language": "zh-TW"}
    )
    assert response.status_code == 201
    assert response.json()["name"] == "My Workspace"

def test_update_workspace_legacy_rejected(client, override_auth, mock_db):
    response = client.patch(
        "/api/v1/workspaces/ws_123",
        json={"name_zh": "新中文"}
    )
    assert response.status_code == 422
    assert "Legacy fields" in response.text

# ─── Node Validation Tests ────────────────────────────────────────────────────

def test_create_node_legacy_rejected(client, override_auth, mock_db):
    response = client.post(
        "/api/v1/workspaces/ws_123/nodes",
        json={"title_zh": "節點標題", "content_type": "factual", "body": "內容"}
    )
    assert response.status_code == 422
    assert "Legacy fields" in response.text

    response = client.post(
        "/api/v1/workspaces/ws_123/nodes",
        json={"title": "Title", "content_type": "factual", "body_en": "Legacy body"}
    )
    assert response.status_code == 422
    assert "Legacy fields" in response.text

def test_create_node_canonical_allowed(client, override_auth, mock_db):
    mock_cur = mock_db.return_value.__enter__.return_value
    node_mock = {
        "id": "mem_123",
        "schema_version": "1.0",
        "workspace_id": "ws_123",
        "title": "Clean Title",
        "content_type": "factual",
        "content_format": "plain",
        "body": "Clean Body",
        "tags": [],
        "visibility": "private",
        "author": "user_123",
        "created_at": "2026-05-26T00:00:00",
        "updated_at": "2026-05-26T00:00:00",
        "signature": "sig",
        "source_type": "human",
        "trust_score": 0.5,
        "dim_accuracy": 0.5,
        "dim_freshness": 1.0,
        "dim_utility": 0.5,
        "dim_author_rep": 0.8,
        "traversal_count": 0,
        "unique_traverser_count": 0,
        "status": "active",
        "archived_at": None,
        "copied_from_node": None,
        "copied_from_ws": None,
    }
    
    with patch("routers.kb._create_node_full_with_dedup", return_value=(node_mock, None, None)):
        with patch("routers.kb._trigger_node_background_jobs"):
            response = client.post(
                "/api/v1/workspaces/ws_123/nodes",
                json={"title": "Clean Title", "content_type": "factual", "body": "Clean Body"}
            )
            assert response.status_code == 201
            assert response.json()["title"] == "Clean Title"

def test_update_node_legacy_rejected(client, override_auth, mock_db):
    response = client.patch(
        "/api/v1/workspaces/ws_123/nodes/mem_123",
        json={"body_zh": "更新內容"}
    )
    assert response.status_code == 422
    assert "Legacy fields" in response.text

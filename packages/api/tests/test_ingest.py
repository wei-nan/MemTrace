import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
import os

@pytest.fixture
def mock_user():
    return {"sub": "user_123", "email": "test@example.com"}

# Use client from conftest or local override
@pytest.fixture
def client():
    from main import app
    # Remove CsrfMiddleware for testing
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
    with patch("routers.ingest.db_cursor") as mock:
        yield mock

def test_get_ingest_logs(client, override_auth, mock_db):
    mock_cur = mock_db.return_value.__enter__.return_value
    mock_cur.fetchall.return_value = [{"id": "ing_1", "status": "completed"}]
    
    with patch("routers.ingest.require_ws_access"):
        response = client.get("/api/v1/workspaces/ws_1/ingest/logs")
        assert response.status_code == 200
        assert response.json() == [{"id": "ing_1", "status": "completed"}]

def test_cancel_ingest(client, override_auth, mock_db):
    mock_cur = mock_db.return_value.__enter__.return_value
    mock_cur.rowcount = 1
    
    with patch("routers.ingest.require_ws_access"):
        # Bypass CSRF via headers if possible, or just mock the middleware
        with patch("core.csrf.CsrfMiddleware.dispatch", side_effect=lambda request, call_next: call_next(request)):
            response = client.post(
                "/api/v1/workspaces/ws_1/ingest/cancel/ing_1", 
                headers={"X-CSRF-Token": "test"},
                cookies={"mt_csrf": "test"}
            )
            assert response.status_code == 200

@pytest.mark.asyncio
async def test_process_ingestion_pipeline():
    from services.ingest.pipeline import process_ingestion
    
    mock_resolved = MagicMock()
    mock_resolved.provider.name = "test_provider"
    mock_resolved.model = "test_model"
    
    with patch("services.ingest.pipeline.db_cursor") as mock_db:
        mock_cur = mock_db.return_value.__enter__.return_value
        # 1. fetchone() for workspaces (extraction_provider)
        # 2. fetchone() for workspaces (embedding_model) in persist_nodes
        # 3. fetchone() for find_similar_node (None)
        mock_cur.fetchone.side_effect = [{"extraction_provider": "openai"}, {"embedding_model": "text-embedding-3-small", "embedding_provider": "openai"}, None]
        
        with patch("services.ingest.pipeline.resolve_provider", return_value=mock_resolved):
            with patch("services.ingest.pipeline.extract_nodes_structured", return_value=("[]", 100)):
                with patch("services.ingest.pipeline.persist_nodes", return_value=[]) as mock_persist:
                    await process_ingestion("job_1", "ws_1", "content", "user_1", "file.txt")
                    assert mock_cur.execute.called

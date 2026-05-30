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
            response = client.delete(
                "/api/v1/workspaces/ws_1/ingest/ing_1", 
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

@pytest.mark.asyncio
async def test_process_ingestion_failure_rollback():
    from services.ingest.pipeline import process_ingestion
    
    with patch("services.ingest.pipeline.db_cursor") as mock_db:
        mock_cur = mock_db.return_value.__enter__.return_value
        
        # 1. Update status to processing (rowcount=1)
        # 2. SELECT extraction_provider (raises exception to simulate failure)
        mock_cur.rowcount = 1
        mock_cur.fetchone.side_effect = Exception("Database connection lost")
        
        # We expect process_ingestion to handle the exception, log it, 
        # and update status to 'failed'
        await process_ingestion("job_1", "ws_1", "content", "user_1", "file.txt")
        
        # Verify that UPDATE ingestion_logs SET status = 'failed' was called
        # The last execute call should be setting status to failed
        calls = mock_cur.execute.call_args_list
        assert any("SET status = 'failed'" in call[0][0] for call in calls)
        assert any("Database connection lost" in str(call[0][1]) for call in calls)

def test_audit_source_success(client, override_auth, mock_db):
    mock_cur = mock_db.return_value.__enter__.return_value
    
    # 1. First fetch for import_sources
    # 2. Second fetch (fetchall) for memory_nodes refs
    mock_cur.fetchone.return_value = {
        "filename": "test.md",
        "raw_content": "# Heading 1\nContent 1\n\n# Heading 2\nContent 2"
    }
    mock_cur.fetchall.return_value = [
        {"source_paragraph_ref": "Chunk 1 (Heading 1)"}
    ]
    
    with patch("routers.ingest.require_ws_access"):
        response = client.get("/api/v1/workspaces/ws_1/audit/src_1")
        assert response.status_code == 200
        data = response.json()
        assert data["source_id"] == "src_1"
        assert data["filename"] == "test.md"
        assert data["coverage"] == 0.5
        assert data["total_headings"] == 2
        assert data["missing"] == ["Chunk 2 (Heading 2)"]

def test_retry_audit_missing_success(client, override_auth, mock_db):
    mock_cur = mock_db.return_value.__enter__.return_value
    mock_cur.fetchone.return_value = {
        "filename": "test.md",
        "doc_type": "generic",
        "raw_content": "# Heading 1\nContent 1\n\n# Heading 2\nContent 2"
    }
    
    with patch("routers.ingest.require_ws_access"):
        with patch("routers.ingest.process_ingestion") as mock_process:
            with patch("core.csrf.CsrfMiddleware.dispatch", side_effect=lambda request, call_next: call_next(request)):
                response = client.post(
                    "/api/v1/workspaces/ws_1/audit/src_1/retry",
                    json={"headings": ["Chunk 2 (Heading 2)"]},
                    headers={"X-CSRF-Token": "test"},
                    cookies={"mt_csrf": "test"}
                )
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "pending"
                assert data["job_id"].startswith("retry_ing")
                assert mock_process.called



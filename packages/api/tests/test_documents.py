import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
import os
from fastapi.responses import PlainTextResponse

@pytest.fixture
def mock_user():
    return {"sub": "user_123", "email": "test@example.com"}

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
    with patch("routers.documents.db_cursor") as mock:
        yield mock

def test_list_documents(client, override_auth, mock_db):
    mock_cur = mock_db.return_value.__enter__.return_value
    mock_cur.fetchall.return_value = [
        {"id": "doc_1", "workspace_id": "ws_1", "title": "Doc 1", "filename": "1.txt", "mime_type": "text/plain"}
    ]
    
    with patch("routers.documents.require_ws_access") as mock_ws_access:
        response = client.get("/api/v1/workspaces/ws_1/documents")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "doc_1"
        mock_ws_access.assert_called_once()

def test_get_document(client, override_auth, mock_db):
    mock_cur = mock_db.return_value.__enter__.return_value
    mock_cur.fetchone.return_value = {
        "id": "doc_1", "workspace_id": "ws_1", "title": "Doc 1", "filename": "1.txt", "mime_type": "text/plain", "storage_path": "/tmp/1.txt"
    }
    mock_cur.fetchall.return_value = [
        {"node_id": "node_1", "document_id": "doc_1", "paragraph_ref": ""}
    ]
    
    with patch("routers.documents.require_ws_access"):
        response = client.get("/api/v1/workspaces/ws_1/documents/doc_1")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "doc_1"
        assert len(data["linked_nodes"]) == 1

def test_download_document(client, override_auth, mock_db):
    mock_cur = mock_db.return_value.__enter__.return_value
    mock_cur.fetchone.return_value = {
        "id": "doc_1", "workspace_id": "ws_1", "title": "Doc 1", "filename": "1.txt", "mime_type": "text/plain", "storage_path": "fake_path_1.txt"
    }
    
    with patch("routers.documents.require_ws_access"):
        with patch("os.path.exists", return_value=True):
            with patch("routers.documents.FileResponse") as mock_file_response:
                mock_file_response.return_value = PlainTextResponse("fake file content")
                response = client.get("/api/v1/workspaces/ws_1/documents/doc_1/content")
                assert response.status_code == 200
                assert response.text == "fake file content"

def test_preview_document(client, override_auth, mock_db):
    mock_cur = mock_db.return_value.__enter__.return_value
    mock_cur.fetchone.return_value = {
        "id": "doc_1", "workspace_id": "ws_1", "title": "Doc 1", "filename": "1.txt", "mime_type": "text/plain", "storage_path": "fake_path_1.txt"
    }
    
    with patch("routers.documents.require_ws_access"):
        with patch("os.path.exists", return_value=True):
            from unittest.mock import mock_open
            with patch("builtins.open", mock_open(read_data=b"preview data here")):
                response = client.get("/api/v1/workspaces/ws_1/documents/doc_1/preview")
                assert response.status_code == 200
                assert response.text == "preview data here"

def test_update_document(client, override_auth, mock_db):
    mock_cur = mock_db.return_value.__enter__.return_value
    mock_cur.fetchone.side_effect = [
        {"id": "doc_1", "workspace_id": "ws_1", "title": "Doc 1", "filename": "1.txt"}, # check exist
        {"id": "doc_1", "workspace_id": "ws_1", "title": "Updated Doc", "filename": "1.txt"} # return updated
    ]
    
    with patch("routers.documents.require_ws_access"):
        response = client.patch(
            "/api/v1/workspaces/ws_1/documents/doc_1",
            json={"title": "Updated Doc"}
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Updated Doc"

def test_delete_document(client, override_auth, mock_db):
    mock_cur = mock_db.return_value.__enter__.return_value
    mock_cur.fetchone.side_effect = [
        {"id": "doc_1", "workspace_id": "ws_1", "title": "Doc 1", "storage_path": "fake_path_1.txt"}, # check exist
        {"id": "doc_1"} # delete_document_in_db return
    ]
    
    with patch("routers.documents.require_ws_access"):
        with patch("os.path.exists", return_value=True):
            with patch("os.remove") as mock_remove:
                response = client.delete("/api/v1/workspaces/ws_1/documents/doc_1")
                assert response.status_code == 204
                mock_remove.assert_called_once_with("fake_path_1.txt")

def test_get_node_source_docs(client, override_auth, mock_db):
    mock_cur = mock_db.return_value.__enter__.return_value
    mock_cur.fetchone.return_value = {"id": "node_1"} # check node exist
    mock_cur.fetchall.return_value = [
        {"id": "doc_1", "title": "Doc 1", "paragraph_ref": "p1"}
    ]
    
    with patch("routers.documents.require_ws_access"):
        response = client.get("/api/v1/workspaces/ws_1/nodes/node_1/sources")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "doc_1"

def test_attach_documents_to_node(client, override_auth, mock_db):
    mock_cur = mock_db.return_value.__enter__.return_value
    # 1. check node exist
    # 2. check document exist
    mock_cur.fetchone.side_effect = [
        {"id": "node_1"},
        {"id": "doc_1"}
    ]
    
    with patch("routers.documents.require_ws_access"):
        response = client.post(
            "/api/v1/workspaces/ws_1/nodes/node_1/document-links",
            json={"document_ids": ["doc_1"], "paragraph_ref": "p2"}
        )
        assert response.status_code == 201
        assert response.json()["created"] == 1
        assert response.json()["node_id"] == "node_1"

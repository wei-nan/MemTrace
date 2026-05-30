import sys
import os
import pytest
import json
import time
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import status

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import app

@pytest.fixture
def api_client():
    return TestClient(app)

@pytest.fixture
def mock_user() -> dict:
    return {
        "sub": "user_test_123",
        "email": "test@memtrace.com",
        "role": "admin"
    }

# Mock get_current_user dependency globally in tests
@pytest.fixture(autouse=True)
def override_auth(mock_user):
    from core.deps import get_current_user
    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield
    app.dependency_overrides.pop(get_current_user, None)

# --- Test /v1/models ---

@patch("routers.openai_compat.list_workspaces_in_db")
@patch("routers.openai_compat.db_cursor")
def test_list_models(mock_db_cursor, mock_list_workspaces, api_client):
    # Setup mock data for workspaces
    import datetime
    created_at = datetime.datetime(2026, 5, 30, 12, 0, 0, tzinfo=datetime.timezone.utc)
    mock_list_workspaces.return_value = [
        {"id": "ws_1", "name": "WorkSpace 1", "created_at": created_at},
        {"id": "ws_2", "name": "WorkSpace 2", "created_at": created_at}
    ]
    
    response = api_client.get("/v1/models", headers={"Authorization": "Bearer mt_mock_key"})
    assert response.status_code == 200
    data = response.json()
    assert data["object"] == "list"
    assert len(data["data"]) == 2
    assert data["data"][0]["id"] == "memtrace-ws_1"
    assert data["data"][0]["object"] == "model"
    assert data["data"][0]["created"] == int(created_at.timestamp())
    assert data["data"][0]["owned_by"] == "memtrace"
    assert data["data"][0]["display_name"] == "WorkSpace 1"

@patch("routers.openai_compat.db_cursor")
def test_get_model_not_found(mock_db_cursor, api_client):
    # Mock cursors return None
    cur = MagicMock()
    cur.fetchone.return_value = None
    
    mock_ctx = MagicMock()
    mock_ctx.__enter__.return_value = cur
    mock_db_cursor.return_value = mock_ctx
    
    # Non memtrace prefix
    response = api_client.get("/v1/models/ws_1", headers={"Authorization": "Bearer mt_mock_key"})
    assert response.status_code == 404
    assert "error" in response.json()
    
    # Valid prefix but not found in DB
    response = api_client.get("/v1/models/memtrace-ws_1", headers={"Authorization": "Bearer mt_mock_key"})
    assert response.status_code == 404
    assert "error" in response.json()
    assert response.json()["error"]["code"] == "model_not_found"

@patch("routers.openai_compat.db_cursor")
def test_get_model_success(mock_db_cursor, api_client):
    import datetime
    created_at = datetime.datetime(2026, 5, 30, 12, 0, 0, tzinfo=datetime.timezone.utc)
    
    cur = MagicMock()
    cur.fetchone.return_value = {
        "id": "ws_1",
        "name": "WorkSpace 1",
        "created_at": created_at
    }
    
    mock_ctx = MagicMock()
    mock_ctx.__enter__.return_value = cur
    mock_db_cursor.return_value = mock_ctx
    
    response = api_client.get("/v1/models/memtrace-ws_1", headers={"Authorization": "Bearer mt_mock_key"})
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "memtrace-ws_1"
    assert data["object"] == "model"
    assert data["display_name"] == "WorkSpace 1"

# --- Test /v1/chat/completions ---

@patch("routers.openai_compat.record_usage")
@patch("routers.openai_compat.chat_completion", new_callable=AsyncMock)
@patch("routers.openai_compat.resolve_provider")
@patch("routers.openai_compat.hybrid_retrieval_for_chat", new_callable=AsyncMock)
@patch("routers.openai_compat.db_cursor")
def test_chat_completions_sync(
    mock_db_cursor,
    mock_hybrid_retrieval,
    mock_resolve_provider,
    mock_chat_completion,
    mock_record_usage,
    api_client
):
    # Setup mock workspace row
    cur = MagicMock()
    cur.fetchone.side_effect = [
        {"id": "ws_1", "embedding_model": "text-embedding-3-small", "embedding_provider": "openai"}, # get workspace
        {"target_ws_id": "ws_associated"} # target associations
    ]
    cur.fetchall.return_value = [{"target_ws_id": "ws_associated"}]
    
    mock_ctx = MagicMock()
    mock_ctx.__enter__.return_value = cur
    mock_db_cursor.return_value = mock_ctx
    
    # Setup hybrid RAG search result
    mock_hybrid_retrieval.return_value = [
        {"id": "node_1", "title": "Citations rule", "body": "This is a source body."}
    ]
    
    # Mock resolved provider
    resolved_prov = MagicMock()
    resolved_prov.model = "gpt-4o-mini"
    resolved_prov.provider.name = "openai"
    mock_resolve_provider.return_value = resolved_prov
    
    # Mock AI response
    mock_chat_completion.return_value = ("Here is the answer based on sources.", 150)
    
    payload = {
        "model": "memtrace-ws_1",
        "messages": [
            {"role": "user", "content": "How are citations formatted?"}
        ],
        "temperature": 0.5,
        "max_tokens": 1000
    }
    
    response = api_client.post(
        "/v1/chat/completions",
        json=payload,
        headers={"Authorization": "Bearer mt_mock_key"}
    )
    assert response.status_code == 200
    
    data = response.json()
    assert data["object"] == "chat.completion"
    assert data["model"] == "memtrace-ws_1"
    assert "choices" in data
    assert len(data["choices"]) == 1
    assert "Here is the answer based on sources." in data["choices"][0]["message"]["content"]
    assert "**Sources:**" in data["choices"][0]["message"]["content"]
    assert "[1] Citations rule" in data["choices"][0]["message"]["content"]
    assert len(data["x_source_nodes"]) == 1
    assert data["x_source_nodes"][0]["id"] == "node_1"
    assert data["usage"]["total_tokens"] == 150
    assert "x-ratelimit-remaining-requests" in response.headers

@patch("routers.openai_compat.record_usage")
@patch("routers.openai_compat.chat_stream")
@patch("routers.openai_compat.resolve_provider")
@patch("routers.openai_compat.hybrid_retrieval_for_chat", new_callable=AsyncMock)
@patch("routers.openai_compat.db_cursor")
def test_chat_completions_streaming(
    mock_db_cursor,
    mock_hybrid_retrieval,
    mock_resolve_provider,
    mock_chat_stream,
    mock_record_usage,
    api_client
):
    # Setup mock workspace row
    cur = MagicMock()
    cur.fetchone.side_effect = [
        {"id": "ws_1", "embedding_model": "text-embedding-3-small", "embedding_provider": "openai"}, # get workspace
        {"target_ws_id": "ws_associated"} # target associations
    ]
    cur.fetchall.return_value = []
    
    mock_ctx = MagicMock()
    mock_ctx.__enter__.return_value = cur
    mock_db_cursor.return_value = mock_ctx
    
    # Setup hybrid RAG search result
    mock_hybrid_retrieval.return_value = [
        {"id": "node_1", "title": "Citations rule", "body": "This is a source body."}
    ]
    
    # Mock resolved provider
    resolved_prov = MagicMock()
    resolved_prov.model = "gpt-4o-mini"
    resolved_prov.provider.name = "openai"
    mock_resolve_provider.return_value = resolved_prov
    
    # Mock chat_stream generator
    async def dummy_stream(*args, **kwargs):
        yield "Chunk 1", 10
        yield " Chunk 2", 20
        
    mock_chat_stream.side_effect = dummy_stream
    
    payload = {
        "model": "memtrace-ws_1",
        "messages": [
            {"role": "user", "content": "How are citations formatted?"}
        ],
        "stream": True
    }
    
    response = api_client.post(
        "/v1/chat/completions",
        json=payload,
        headers={"Authorization": "Bearer mt_mock_key"}
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
    
    lines = response.text.split("\n\n")
    events = []
    for line in lines:
        if line.startswith("data: "):
            data_str = line[len("data: "):]
            if data_str == "[DONE]":
                events.append("[DONE]")
            else:
                events.append(json.loads(data_str))
                
    assert len(events) >= 4
    # Event 0: Chunk 1
    assert events[0]["choices"][0]["delta"]["content"] == "Chunk 1"
    # Event 1: Chunk 2
    assert events[1]["choices"][0]["delta"]["content"] == " Chunk 2"
    # Event 2: Inline sources text
    assert "**Sources:**" in events[2]["choices"][0]["delta"]["content"]
    assert "[1] Citations rule" in events[2]["choices"][0]["delta"]["content"]
    # Event 3: Top-level source nodes metadata & stop finish_reason
    assert events[3]["choices"][0]["finish_reason"] == "stop"
    assert events[3]["x_source_nodes"][0]["id"] == "node_1"
    # Event 4: DONE
    assert events[4] == "[DONE]"

@patch("routers.openai_compat.record_usage")
@patch("routers.openai_compat.chat_completion", new_callable=AsyncMock)
@patch("routers.openai_compat.resolve_provider")
@patch("routers.openai_compat.hybrid_retrieval_for_chat", new_callable=AsyncMock)
@patch("routers.openai_compat.db_cursor")
def test_system_override_workspace(
    mock_db_cursor,
    mock_hybrid_retrieval,
    mock_resolve_provider,
    mock_chat_completion,
    mock_record_usage,
    api_client
):
    # Setup mock workspace row
    cur = MagicMock()
    # We query ws_override from system override
    cur.fetchone.side_effect = [
        {"id": "ws_override", "embedding_model": "text-embedding-3-small", "embedding_provider": "openai"},
        {"target_ws_id": "ws_associated"}
    ]
    cur.fetchall.return_value = []
    
    mock_ctx = MagicMock()
    mock_ctx.__enter__.return_value = cur
    mock_db_cursor.return_value = mock_ctx
    
    mock_hybrid_retrieval.return_value = []
    
    resolved_prov = MagicMock()
    resolved_prov.model = "gpt-4o-mini"
    resolved_prov.provider.name = "openai"
    mock_resolve_provider.return_value = resolved_prov
    
    mock_chat_completion.return_value = ("Success", 50)
    
    payload = {
        "model": "memtrace-ws_normal",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant. workspace_id: ws_override"},
            {"role": "user", "content": "Hello"}
        ]
    }
    
    response = api_client.post(
        "/v1/chat/completions",
        json=payload,
        headers={"Authorization": "Bearer mt_mock_key"}
    )
    assert response.status_code == 200
    
    # Verify that the DB query used ws_override as workspace_id instead of ws_normal
    db_calls = cur.execute.call_args_list
    # The first call should select workspace details for ws_override
    first_query_args = db_calls[0][0][1]
    assert "ws_override" in first_query_args
    assert "ws_normal" not in first_query_args

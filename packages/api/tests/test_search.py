import sys
import os
import pytest
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.search import apply_text_search, perform_semantic_search
from core.ai import AIProviderUnavailable

def test_apply_text_search_postgres():
    filters = []
    params = []
    with patch("services.search._is_postgres", return_value=True):
        apply_text_search(filters, params, "hello world 測試")
    
    assert len(filters) == 1
    assert "search_vector @@ plainto_tsquery" in filters[0] or "ILIKE" in filters[0]
    assert len(params) > 0

def test_apply_text_search_sqlite():
    filters = []
    params = []
    with patch("services.search._is_postgres", return_value=False):
        apply_text_search(filters, params, "hello")
        
    assert len(filters) == 1
    assert "LIKE" in filters[0]
    assert len(params) == 4
    assert params[0] == "%hello%"

@pytest.mark.asyncio
@patch("services.search.embed")
@patch("services.search.resolve_provider")
@patch("services.search.record_usage")
async def test_perform_semantic_search(mock_record, mock_resolve, mock_embed):
    cur = MagicMock()
    cur.fetchone.return_value = {"embedding_model": "test-model"}
    cur.fetchall.return_value = [{"id": "mem_1", "similarity": 0.9}]
    
    # Mock context manager
    mock_db_cursor = MagicMock()
    mock_db_cursor.__enter__.return_value = cur
    
    mock_resolve.return_value = "provider_instance"
    mock_embed.return_value = ([0.1, 0.2], 10)
    
    with patch("services.search.db_cursor", return_value=mock_db_cursor):
        res = await perform_semantic_search(cur, "ws_test", "query", "user_1", limit=5)
        
    assert len(res) == 1
    assert res[0]["id"] == "mem_1"
    mock_embed.assert_called_once()
    mock_record.assert_called_once()

@pytest.mark.asyncio
@patch("services.search.resolve_provider")
async def test_perform_semantic_search_unavailable(mock_resolve):
    from core.ai import AIProviderUnavailable
    mock_resolve.side_effect = AIProviderUnavailable("No provider")
    
    cur = MagicMock()
    cur.fetchone.return_value = {"embedding_model": "test-model"}
    mock_db_cursor = MagicMock()
    mock_db_cursor.__enter__.return_value = cur
    
    from fastapi import HTTPException
    from core.ai import AIProviderUnavailable
    with patch("services.search.db_cursor", return_value=mock_db_cursor):
        with pytest.raises(AIProviderUnavailable):
            await perform_semantic_search(cur, "ws_test", "query", "user_1")
@pytest.mark.asyncio
@patch("core.ai.embed")
@patch("core.ai.resolve_provider")
async def test_hybrid_retrieval_for_chat_faq_hit(mock_resolve, mock_embed):
    cur = MagicMock()
    # Mock FAQ inquiry node
    cur.fetchone.return_value = {"id": "faq_node_id"}
    # Mock result nodes from FAQ
    cur.fetchall.return_value = [
        {"id": "result_node_1", "title_zh": "Ans", "title_en": "Ans", "body_zh": "...", "body_en": "...", "workspace_id": "ws_1"}
    ]
    
    from services.search import hybrid_retrieval_for_chat
    res = await hybrid_retrieval_for_chat(cur, ["ws_1"], "question", "user_1")
    
    assert len(res) == 1
    assert res[0]["id"] == "result_node_1"
    assert res[0]["_faq_hit_id"] == "faq_node_id"
    # Should skip embedding if FAQ hit
    mock_embed.assert_not_called()

@pytest.mark.asyncio
@patch("core.ai.embed")
@patch("core.ai.resolve_provider")
@patch("core.config.settings")
async def test_hybrid_retrieval_for_chat_vector_fallback(mock_settings, mock_resolve, mock_embed):
    mock_settings.database_url = "postgresql://..."
    cur = MagicMock()
    # 1. FAQ check (No hit)
    # 2. Vector search (Returns 1 node)
    # 3. Keyword fallback (Returns 1 node)
    
    # Configure cur.fetchone/fetchall to return different things on each call
    # 1. FAQ hit (fetchone returns None)
    cur.fetchone.return_value = None
    
    # 2. Vector search (fetchall returns 1 node)
    # 3. Keyword search (fetchall returns 1 node)
    cur.fetchall.side_effect = [
        [{"id": "vec_node", "title_zh": "V", "title_en": "V", "body_zh": "V", "body_en": "V", "workspace_id": "ws_1", "similarity": 0.8}],
        [{"id": "kw_node", "title_zh": "K", "title_en": "K", "body_zh": "K", "body_en": "K", "workspace_id": "ws_1", "similarity": 0.0}]
    ]
    
    mock_resolve.return_value = MagicMock()
    mock_embed.return_value = ([0.1], 10)
    
    from services.search import hybrid_retrieval_for_chat
    res = await hybrid_retrieval_for_chat(cur, ["ws_1"], "query", "user_1")
    
    assert len(res) == 2
    assert res[0]["id"] == "vec_node"
    assert res[1]["id"] == "kw_node"
    mock_embed.assert_called_once()




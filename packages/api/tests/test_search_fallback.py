"""
test_search_fallback.py — I-101 regression guard

Verifies that search_nodes_in_db degrades gracefully when no AI provider
key is configured (AIProviderUnavailable), returning keyword results instead
of propagating a 500-level error.

Also covers the system-key fallback in resolve_provider.
"""
import sys
import os
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.ai import AIProviderUnavailable


# ─── search_nodes_in_db: graceful degradation ─────────────────────────────────

@pytest.mark.asyncio
async def test_search_nodes_falls_back_to_keyword_when_no_ai_key():
    """
    When AIProviderUnavailable is raised by perform_semantic_search,
    search_nodes_in_db must still return keyword results (not raise).
    (Regression guard for I-101.)
    """
    from services.search import search_nodes_in_db

    keyword_hits = [
        {"id": "mem_g004", "title_en": "Trust Score", "title_zh": "Trust Score 四維評分",
         "content_type": "factual", "tags": [], "visibility": "public", "similarity": 1.0}
    ]

    cur = MagicMock()
    user = {"sub": "usr_test"}
    ws_row = {
        "id": "ws_spec0001", "visibility": "public", "owner_id": "usr_test",
        "kb_type": "evergreen", "embedding_model": "text-embedding-3-small",
        "embedding_provider": "openai",
    }

    cur.fetchall.return_value = keyword_hits

    with patch("services.search.require_ws_access", return_value=ws_row), \
         patch("services.search.perform_semantic_search",
               new_callable=AsyncMock,
               side_effect=AIProviderUnavailable("No key configured")):

        results = await search_nodes_in_db(cur, "ws_spec0001", "Trust", limit=5, user=user)

    # Must return keyword results, not raise
    assert len(results) >= 1
    assert results[0]["id"] == "mem_g004"


@pytest.mark.asyncio
async def test_search_nodes_uses_semantic_when_key_available():
    """When semantic search succeeds, results are merged with keyword results."""
    from services.search import search_nodes_in_db

    keyword_hits = [{"id": "mem_a", "title_en": "A", "title_zh": "", "content_type": "factual",
                     "tags": [], "visibility": "public", "similarity": 1.0}]
    semantic_hits = [{"id": "mem_b", "title_en": "B", "title_zh": "", "content_type": "factual",
                      "tags": [], "visibility": "public", "similarity": 0.88}]

    cur = MagicMock()
    cur.fetchall.return_value = keyword_hits
    user = {"sub": "usr_test"}
    ws_row = {
        "id": "ws_1", "visibility": "public", "owner_id": "usr_test",
        "kb_type": "evergreen", "embedding_model": "text-embedding-3-small",
        "embedding_provider": "openai",
    }

    with patch("services.search.require_ws_access", return_value=ws_row), \
         patch("services.search.perform_semantic_search",
               new_callable=AsyncMock, return_value=semantic_hits):

        results = await search_nodes_in_db(cur, "ws_1", "anything", limit=10, user=user)

    ids = [r["id"] for r in results]
    assert "mem_a" in ids
    assert "mem_b" in ids


# ─── resolve_provider: system key fallback ────────────────────────────────────

def test_resolve_provider_falls_back_to_system_key(monkeypatch):
    """
    When the caller user has no keys, resolve_provider must attempt
    user_id = 'system' before raising AIProviderUnavailable.
    """
    from core.ai import resolve_provider, PROVIDER_REGISTRY

    # Build a fake 'openai' provider entry
    system_key_row = {
        "provider": "openai",
        "key_enc": "enc_test",
        "base_url": None,
        "auth_mode": "bearer",
        "auth_token": None,
        "default_chat_model": "gpt-4o",
        "default_embedding_model": "text-embedding-3-small",
        "last_used_at": None,
    }

    call_count = {"n": 0}

    def fake_cursor_factory():
        class _CM:
            def __enter__(self_inner):
                return self_inner
            def __exit__(self_inner, *a): pass
            def execute(self_inner, q, p=None):
                call_count["n"] += 1
            def fetchall(self_inner):
                # First call (user keys): empty; second call (system keys): one row
                if call_count["n"] == 1:
                    return []
                return [system_key_row]
        return _CM()

    monkeypatch.setattr("core.ai.db_cursor", fake_cursor_factory)

    # Should not raise — system key found
    try:
        resolved = resolve_provider("usr_no_key", "embedding",
                                    preferred_provider="openai",
                                    preferred_model="text-embedding-3-small")
        # If we get here, the system key was used
        assert resolved is not None
    except AIProviderUnavailable:
        pytest.fail("resolve_provider raised AIProviderUnavailable even though system key exists")


def test_resolve_provider_raises_when_no_user_and_no_system_key(monkeypatch):
    """When neither user nor system has keys, AIProviderUnavailable must be raised."""
    from core.ai import resolve_provider

    call_count = {"n": 0}

    def fake_cursor_factory():
        class _CM:
            def __enter__(self_inner): return self_inner
            def __exit__(self_inner, *a): pass
            def execute(self_inner, q, p=None):
                call_count["n"] += 1
            def fetchall(self_inner): return []
        return _CM()

    monkeypatch.setattr("core.ai.db_cursor", fake_cursor_factory)

    with pytest.raises(AIProviderUnavailable):
        resolve_provider("usr_no_key", "chat")

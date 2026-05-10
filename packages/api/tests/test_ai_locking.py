import pytest
from unittest.mock import MagicMock, patch
from core.ai import resolve_provider, AIProviderUnavailable

@pytest.mark.asyncio
async def test_embedding_provider_locking():
    # Mock workspace settings
    mock_ws = {
        "id": "ws_123",
        "embedding_model": "text-embedding-004",
        "embedding_provider": "gemini"
    }
    
    user_id = "user_456"
    
    # 1. Test successful Gemini resolution in Gemini workspace
    # resolve_provider queries user_ai_keys
    with patch("core.ai.db_cursor") as mock_db:
        cur = mock_db.return_value.__enter__.return_value
        # Mock user_ai_keys rows
        cur.fetchall.return_value = [
            {
                "provider": "gemini",
                "key_enc": "enc_gemini",
                "base_url": None,
                "auth_mode": None,
                "auth_token": None,
                "default_chat_model": "gemini-2.0-flash",
                "default_embedding_model": "text-embedding-004",
                "last_used_at": None
            },
            {
                "provider": "openai",
                "key_enc": "enc_openai",
                "base_url": None,
                "auth_mode": None,
                "auth_token": None,
                "default_chat_model": "gpt-4o",
                "default_embedding_model": "text-embedding-3-small",
                "last_used_at": None
            }
        ]
        
        with patch("core.ai.decrypt_api_key", side_effect=lambda x: x.replace("enc_", "")):
            # Resolve with preferred provider
            resolved = resolve_provider(
                user_id, 
                "embedding", 
                preferred_provider=mock_ws["embedding_provider"], 
                preferred_model=mock_ws["embedding_model"]
            )
            
            assert resolved.provider.name == "gemini"
            assert resolved.model == "text-embedding-004"

    # 2. Test failure when Gemini is unavailable (but OpenAI is available)
    # The test wants to verify that if we ask for Gemini and it's NOT in the rows, it fails 
    # (or if preferred_provider is specified, it ONLY looks at that provider).
    # In the real resolve_provider, if preferred_provider is passed, the SQL includes "AND provider = %s".
    
    with patch("core.ai.db_cursor") as mock_db:
        cur = mock_db.return_value.__enter__.return_value
        # No rows for Gemini
        cur.fetchall.return_value = []
        
        with pytest.raises(AIProviderUnavailable):
            resolve_provider(
                user_id, 
                "embedding", 
                preferred_provider="gemini", 
                preferred_model="text-embedding-004"
            )

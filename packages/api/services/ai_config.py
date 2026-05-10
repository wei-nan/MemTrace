from datetime import datetime
from typing import Optional, List, Dict, Any
from core.database import db_cursor
from core.security import generate_id
from core.ai import encrypt_api_key

def list_user_ai_keys(cur, user_id: str) -> List[Dict[str, Any]]:
    cur.execute(
        "SELECT id, provider, key_hint, created_at, last_used_at, "
        "base_url, auth_mode, auth_token, default_chat_model, default_embedding_model "
        "FROM user_ai_keys WHERE user_id = %s ORDER BY created_at DESC",
        (user_id,),
    )
    return [dict(row) for row in cur.fetchall()]

def upsert_user_ai_key(
    cur, 
    user_id: str, 
    provider: str, 
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    auth_mode: str = "none",
    auth_token: Optional[str] = None,
    default_chat_model: Optional[str] = None,
    default_embedding_model: Optional[str] = None
) -> Dict[str, Any]:
    key_hint = api_key[-4:] if api_key else ""
    key_enc  = encrypt_api_key(api_key) if api_key else None
    key_id   = generate_id("uak")

    cur.execute(
        """
        INSERT INTO user_ai_keys (id, user_id, provider, key_enc, key_hint, base_url, auth_mode, auth_token, default_chat_model, default_embedding_model)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (user_id, provider) DO UPDATE
          SET key_enc               = COALESCE(EXCLUDED.key_enc, user_ai_keys.key_enc),
              key_hint              = COALESCE(NULLIF(EXCLUDED.key_hint, ''), user_ai_keys.key_hint),
              base_url              = EXCLUDED.base_url,
              auth_mode             = EXCLUDED.auth_mode,
              auth_token            = EXCLUDED.auth_token,
              default_chat_model    = EXCLUDED.default_chat_model,
              default_embedding_model = EXCLUDED.default_embedding_model,
              last_used_at          = NULL
        RETURNING id, provider, key_hint, created_at, last_used_at
        """,
        (
            key_id,
            user_id,
            provider,
            key_enc,
            key_hint,
            base_url,
            auth_mode,
            auth_token,
            default_chat_model,
            default_embedding_model
        ),
    )
    return dict(cur.fetchone())

def delete_user_ai_key(cur, user_id: str, provider: str) -> bool:
    cur.execute(
        "DELETE FROM user_ai_keys WHERE user_id = %s AND provider = %s",
        (user_id, provider),
    )
    return cur.rowcount > 0

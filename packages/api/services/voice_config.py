from typing import Optional, List, Dict, Any
from core.security import generate_id
from core.voice import encrypt_voice_credential

def list_user_voice_keys(cur, user_id: str) -> List[Dict[str, Any]]:
    cur.execute(
        "SELECT id, purpose, provider, credential_type, key_hint, created_at, last_used_at "
        "FROM user_voice_keys WHERE user_id = %s ORDER BY purpose",
        (user_id,),
    )
    return [dict(row) for row in cur.fetchall()]

def upsert_user_voice_key(
    cur,
    user_id: str,
    purpose: str,
    provider: str,
    credential: str,
    credential_type: str = "api_key",
) -> Dict[str, Any]:
    key_hint = credential[-4:] if credential_type == "api_key" else "(service account)"
    key_enc = encrypt_voice_credential(credential)
    key_id = generate_id("uvk")

    cur.execute(
        """
        INSERT INTO user_voice_keys (id, user_id, purpose, provider, credential_type, key_enc, key_hint)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (user_id, purpose) DO UPDATE
          SET provider        = EXCLUDED.provider,
              credential_type = EXCLUDED.credential_type,
              key_enc         = EXCLUDED.key_enc,
              key_hint        = EXCLUDED.key_hint,
              last_used_at    = NULL
        RETURNING id, purpose, provider, credential_type, key_hint, created_at, last_used_at
        """,
        (key_id, user_id, purpose, provider, credential_type, key_enc, key_hint),
    )
    return dict(cur.fetchone())

def delete_user_voice_key(cur, user_id: str, purpose: str) -> bool:
    cur.execute(
        "DELETE FROM user_voice_keys WHERE user_id = %s AND purpose = %s",
        (user_id, purpose),
    )
    return cur.rowcount > 0

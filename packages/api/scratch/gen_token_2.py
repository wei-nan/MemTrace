import secrets
import hashlib
from core.database import db_cursor
from core.security import generate_id

def create_temp_token(user_id):
    raw_key = "mt_" + secrets.token_hex(20)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    prefix = raw_key[:8]
    key_id = generate_id("apikey")
    
    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO api_keys (id, user_id, name, key_hash, prefix, scopes) VALUES (%s, %s, %s, %s, %s, %s)",
            (key_id, user_id, "CLI Dogfooding 2", key_hash, prefix, ["read", "write"])
        )
    return raw_key

token = create_temp_token('usr_6bc7b4c7')
print(f"TOKEN:{token}")

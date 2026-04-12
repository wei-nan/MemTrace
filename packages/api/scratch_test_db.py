import psycopg2
import os
from dotenv import load_dotenv

from psycopg2.extras import RealDictCursor

load_dotenv('../../.env')
DATABASE_URL = os.environ.get('DATABASE_URL')

conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
cur = conn.cursor()

try:
    print("Testing UPSERT...")
    cur.execute("""
        INSERT INTO user_ai_keys (id, user_id, provider, key_enc, key_hint)
        VALUES ('uak_test2', 'usr_6bc7b4c7', 'anthropic', 'enc_test', '5678')
        ON CONFLICT (user_id, provider) DO UPDATE
          SET key_enc = EXCLUDED.key_enc,
              key_hint = EXCLUDED.key_hint
        RETURNING id, provider, key_hint, created_at, last_used_at
    """)
    print("Success:", cur.fetchone())
    conn.commit()
except Exception as e:
    print("Error:", e)
    conn.rollback()
finally:
    conn.close()

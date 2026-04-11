import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

db_url = os.environ.get("DATABASE_URL", "postgresql://memtrace:memtrace_dev_secret@localhost:5432/memtrace")
print(f"Connecting to {db_url}...")
try:
    conn = psycopg2.connect(db_url)
    print("Connected!")
    cur = conn.cursor()
    cur.execute("SELECT version();")
    print(cur.fetchone())
    conn.close()
except Exception as e:
    print(f"Error: {e}")

import sqlite3

for db_path in ["test.db", "packages/api/test.db"]:
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT id, name, settings FROM workspaces")
        rows = cur.fetchall()
        print(f"--- SQLite DB: {db_path} ---")
        for row in rows:
            print(row)
        conn.close()
    except Exception as e:
        print(f"Failed to read {db_path}: {e}")

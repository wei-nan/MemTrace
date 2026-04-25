from core.database import db_cursor
with db_cursor() as cur:
    cur.execute('SELECT id, name_en FROM workspaces LIMIT 5')
    for r in cur.fetchall():
        print(f"{r['id']}: {r['name_en']}")

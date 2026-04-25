from core.database import db_cursor
with db_cursor() as cur:
    cur.execute("SELECT owner_id FROM workspaces WHERE id = 'ws_9804775a'")
    print(cur.fetchone())

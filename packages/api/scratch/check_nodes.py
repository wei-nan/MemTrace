from core.database import db_cursor
with db_cursor() as cur:
    cur.execute("SELECT id, title_en, content_type FROM memory_nodes WHERE workspace_id = 'ws_9804775a'")
    for r in cur.fetchall():
        print(f"{r['id']}: {r['title_en']} ({r['content_type']})")

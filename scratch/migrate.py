import os
import psycopg2
import psycopg2.extras
import glob

DATABASE_URL = "postgresql://memtrace:memtrace_dev_secret@localhost:5432/memtrace"

def get_conn():
    return psycopg2.connect(DATABASE_URL)

def apply_sql(conn, filepath):
    print(f"Applying {filepath}...")
    with open(filepath, 'r', encoding='utf-8') as f:
        sql = f.read()
    
    with conn.cursor() as cur:
        try:
            cur.execute(sql)
            conn.commit()
            print(f"Successfully applied {filepath}")
        except Exception as e:
            conn.rollback()
            print(f"Failed to apply {filepath}: {e}")

def check_and_migrate():
    conn = get_conn()
    
    # Create migration table if not exists
    with conn.cursor() as cur:
        cur.execute("CREATE TABLE IF NOT EXISTS migration_history (filename TEXT PRIMARY KEY, applied_at TIMESTAMPTZ DEFAULT NOW())")
        conn.commit()
        
        cur.execute("SELECT filename FROM migration_history")
        applied = {r[0] for r in cur.fetchall()}
    
    sql_files = sorted(glob.glob("schema/sql/*.sql"))
    
    for f in sql_files:
        filename = os.path.basename(f)
        if filename not in applied:
            apply_sql(conn, f)
            with conn.cursor() as cur:
                cur.execute("INSERT INTO migration_history (filename) VALUES (%s)", (filename,))
                conn.commit()
        else:
            print(f"Skipping {filename} (already applied)")
            
    conn.close()

if __name__ == "__main__":
    check_and_migrate()

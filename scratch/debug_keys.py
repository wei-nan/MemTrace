import psycopg2
db_url = 'postgresql://memtrace:memtrace_dev_secret@127.0.0.1:5432/memtrace'
try:
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    cur.execute("SELECT user_id, provider FROM user_ai_keys")
    rows = cur.fetchall()
    print('Entries in user_ai_keys:', rows)
    conn.close()
except Exception as e:
    print(f'Error: {e}')

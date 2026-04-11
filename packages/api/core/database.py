import os
import sqlite3
import psycopg2
import psycopg2.extras
from contextlib import contextmanager
from .config import settings


def get_conn():
    db_url = settings.database_url
    if db_url.startswith("sqlite"):
        # Extract path from sqlite:///./memtrace.db or sqlite:///memtrace.db
        db_path = db_url.replace("sqlite:///", "")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Similar to RealDictCursor
        return conn
    
    return psycopg2.connect(
        db_url,
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


@contextmanager
def db_cursor(commit: bool = False):
    conn = get_conn()
    try:
        # SQLite uses a different cursor object, but API is similar
        cur = conn.cursor()
        yield cur
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


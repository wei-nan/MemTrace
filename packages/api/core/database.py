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
    
    conn = psycopg2.connect(
        db_url,
        cursor_factory=psycopg2.extras.RealDictCursor,
    )
    conn.set_client_encoding('UTF8')
    return conn


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


from core.config import settings
def is_postgres() -> bool:
    return settings.database_url.startswith("postgresql")

def run_migrations():
    """Apply pending SQL migrations (PostgreSQL only; skipped for SQLite)."""
    import logging
    import pathlib
    logger = logging.getLogger(__name__)
    if not settings.database_url.startswith("postgresql"):
        return
    # Note: __file__ is in core/, so migrations are in ../migrations/
    migrations_dir = pathlib.Path(__file__).parent.parent / "migrations"
    if not migrations_dir.exists():
        logger.warning("Migrations directory not found at %s", migrations_dir)
        return
    with db_cursor(commit=True) as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
              filename TEXT PRIMARY KEY,
              applied_at TIMESTAMPTZ DEFAULT now()
            )
        """)
        for sql_file in sorted(migrations_dir.glob("*.sql")):
            cur.execute("SELECT 1 FROM schema_migrations WHERE filename = %s", (sql_file.name,))
            if cur.fetchone():
                continue
            logger.info("Applying migration: %s", sql_file.name)
            cur.execute(sql_file.read_text(encoding="utf-8"))
            cur.execute("INSERT INTO schema_migrations (filename) VALUES (%s)", (sql_file.name,))
            logger.info("Migration applied: %s", sql_file.name)

import psycopg2
import psycopg2.extras
from contextlib import contextmanager
from .config import settings


def get_conn():
    return psycopg2.connect(
        settings.database_url,
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


@contextmanager
def db_cursor(commit: bool = False):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            yield cur
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

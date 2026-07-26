import hashlib
import os
import pathlib
import sqlite3
import psycopg2
import psycopg2.extras
from contextlib import contextmanager
from .config import settings


MIGRATION_MANIFEST = "MANIFEST.txt"

# Schema version is independent of the app's semver — it's a monotonically
# increasing integer bumped only when a migration changes schema semantics
# (not on every file). 1 corresponds to the 2026-07-26 baseline recut
# (Trust removal + migration history consolidation). See
# ws_spec_plan/mem_d74aa763.
REQUIRED_SCHEMA_VERSION = 1


def _checksum(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


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


def load_migration_files(migrations_dir: pathlib.Path) -> list[pathlib.Path]:
    """Return the explicitly approved migrations in manifest order.

    Historical SQL files may exist beside the runtime migrations during local
    development. They must never be picked up implicitly.
    """
    manifest_path = migrations_dir / MIGRATION_MANIFEST
    if not manifest_path.exists():
        raise RuntimeError(f"Migration manifest not found: {manifest_path}")

    names = [
        line.strip()
        for line in manifest_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if len(names) != len(set(names)):
        raise RuntimeError("Migration manifest contains duplicate filenames")

    files: list[pathlib.Path] = []
    for name in names:
        if pathlib.Path(name).name != name or not name.endswith(".sql"):
            raise RuntimeError(f"Invalid migration manifest entry: {name}")
        sql_file = migrations_dir / name
        if not sql_file.is_file():
            raise RuntimeError(f"Manifest migration does not exist: {sql_file}")
        files.append(sql_file)
    return files


def run_migrations():
    """Apply pending SQL migrations (PostgreSQL only; skipped for SQLite)."""
    import logging
    logger = logging.getLogger(__name__)
    if not settings.database_url.startswith("postgresql"):
        return
    # Note: __file__ is in core/, so migrations are in ../migrations/
    migrations_dir = pathlib.Path(__file__).parent.parent / "migrations"
    if not migrations_dir.exists():
        logger.warning("Migrations directory not found at %s", migrations_dir)
        return

    migration_files = load_migration_files(migrations_dir)
    with db_cursor(commit=True) as cur:
        # A fresh database has no tracking table. The baseline dump creates
        # schema_migrations itself, so it must run before the normal tracker
        # bootstrap or PostgreSQL would see a duplicate CREATE TABLE.
        cur.execute("SELECT to_regclass('public.schema_migrations') AS table_name")
        tracking_row = cur.fetchone()
        tracking_exists = bool(
            tracking_row
            and (
                tracking_row.get("table_name")
                if hasattr(tracking_row, "get")
                else tracking_row[0]
            )
        )
        if not tracking_exists and migration_files and migration_files[0].name.startswith("000_baseline"):
            baseline = migration_files.pop(0)
            logger.info("Applying migration baseline: %s", baseline.name)
            # utf-8-sig strips the BOM the baseline dump carries (matches the
            # per-migration read below); plain utf-8 leaves it and Postgres errors.
            baseline_text = baseline.read_text(encoding="utf-8-sig")
            cur.execute(baseline_text)
            # The pg_dump baseline sets search_path='' for the session; restore it so
            # the tracking INSERT and the unqualified table names in later migrations resolve.
            cur.execute("SET search_path TO public")
            cur.execute(
                "INSERT INTO schema_migrations (filename, checksum) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (baseline.name, _checksum(baseline_text)),
            )
            cur.execute(
                "INSERT INTO system_state (key, value) VALUES ('schema_version', %s) ON CONFLICT DO NOTHING",
                (str(REQUIRED_SCHEMA_VERSION),),
            )
            logger.info("Migration applied: %s", baseline.name)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
              filename TEXT PRIMARY KEY,
              applied_at TIMESTAMPTZ DEFAULT now(),
              checksum TEXT
            )
        """)
        for sql_file in migration_files:
            sql_text = sql_file.read_text(encoding="utf-8-sig")
            checksum = _checksum(sql_text)
            cur.execute(
                "SELECT checksum FROM schema_migrations WHERE filename = %s", (sql_file.name,)
            )
            existing = cur.fetchone()
            if existing:
                stored = existing.get("checksum") if hasattr(existing, "get") else existing[0]
                if stored is not None and stored != checksum:
                    raise RuntimeError(
                        f"Applied migration {sql_file.name} has changed since it was run "
                        f"(checksum mismatch) — migrations must never be edited after being "
                        f"applied. Add a new migration instead."
                    )
                continue
            logger.info("Applying migration: %s", sql_file.name)
            cur.execute(sql_text)
            cur.execute(
                "INSERT INTO schema_migrations (filename, checksum) VALUES (%s, %s)",
                (sql_file.name, checksum),
            )
            logger.info("Migration applied: %s", sql_file.name)


def assert_schema_version(cur):
    """Fail closed if the live DB's schema_version doesn't match the code's
    REQUIRED_SCHEMA_VERSION. Call after run_migrations() on startup.
    """
    cur.execute("SELECT value FROM system_state WHERE key = 'schema_version'")
    row = cur.fetchone()
    if not row:
        raise RuntimeError(
            "system_state.schema_version is not set — the database has not been "
            "initialized from the current baseline. Run run_migrations() first."
        )
    live_version = row.get("value") if hasattr(row, "get") else row[0]
    if int(live_version) != REQUIRED_SCHEMA_VERSION:
        raise RuntimeError(
            f"Schema version mismatch: database is at {live_version}, code requires "
            f"{REQUIRED_SCHEMA_VERSION}. Refusing to start — this database does not "
            f"match this deployment's code."
        )

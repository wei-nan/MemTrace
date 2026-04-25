import gzip
import json
import logging
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .database import db_cursor

logger = logging.getLogger(__name__)


def get_backup_config() -> dict:
    with db_cursor() as cur:
        cur.execute("SELECT value FROM system_config WHERE key = 'backup'")
        row = cur.fetchone()
    if not row:
        return {"enabled": False, "path": "/backups", "interval_hours": 24, "keep_count": 7}
    return dict(row["value"])


def set_backup_config(updates: dict) -> dict:
    config = get_backup_config()
    config.update(updates)
    payload = json.dumps(config)
    with db_cursor(commit=True) as cur:
        cur.execute(
            """INSERT INTO system_config (key, value, updated_at)
               VALUES ('backup', %s::jsonb, NOW())
               ON CONFLICT (key) DO UPDATE SET value = %s::jsonb, updated_at = NOW()""",
            (payload, payload),
        )
    return config


def validate_path(path: str) -> str:
    if not path or not path.strip():
        raise ValueError("Path cannot be empty")
    if any(c in path for c in (';', '&', '|', '`', '$', '>', '<', '\n', '\r', '\x00')):
        raise ValueError("Invalid characters in backup path")
    normalized = os.path.normpath(path)
    if not os.path.isabs(normalized):
        raise ValueError("Backup path must be absolute")
    return normalized


def run_backup(path: str, db_url: str, keep_count: int = 7) -> str:
    safe_path = validate_path(path)
    Path(safe_path).mkdir(parents=True, exist_ok=True)

    m = re.match(r"postgresql(?:\+\w+)?://([^:]+):([^@]*)@([^:/]+)(?::(\d+))?/(.+)", db_url)
    if not m:
        raise RuntimeError("Cannot parse DATABASE_URL")
    user, password, host, port, dbname = m.groups()
    port = port or "5432"

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_file = os.path.join(safe_path, f"backup_{timestamp}.sql.gz")

    env = {**os.environ, "PGPASSWORD": password}
    cmd = ["pg_dump", "-h", host, "-p", port, "-U", user, "--format=plain", dbname]

    with gzip.open(out_file, "wb") as gz:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        assert proc.stdout is not None
        for chunk in iter(lambda: proc.stdout.read(65536), b""):
            gz.write(chunk)
        proc.wait()
        if proc.returncode != 0:
            Path(out_file).unlink(missing_ok=True)
            raise RuntimeError(f"pg_dump failed: {proc.stderr.read().decode()}")  # type: ignore[union-attr]

    _rotate(safe_path, keep_count)
    return out_file


def _rotate(path: str, keep_count: int) -> None:
    files = sorted(
        Path(path).glob("backup_*.sql.gz"),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    for f in files[keep_count:]:
        f.unlink(missing_ok=True)


def run_backup_and_update_status(path: str, db_url: str, keep_count: int) -> None:
    """Run backup and persist result to system_config. Safe to call from a thread pool."""
    try:
        out_file = run_backup(path, db_url, keep_count)
        set_backup_config({
            "last_backup_at": datetime.now(timezone.utc).isoformat(),
            "last_backup_file": out_file,
            "last_backup_status": "ok",
        })
        logger.info("Backup complete: %s", out_file)
    except Exception as exc:
        logger.error("Backup failed: %s", exc)
        set_backup_config({
            "last_backup_at": datetime.now(timezone.utc).isoformat(),
            "last_backup_status": f"error: {exc}",
        })

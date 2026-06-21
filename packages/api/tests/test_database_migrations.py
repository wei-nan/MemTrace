from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.database import load_migration_files, run_migrations


def test_load_migration_files_uses_manifest_order_and_ignores_extra_sql(tmp_path: Path):
    (tmp_path / "MANIFEST.txt").write_text(
        "# approved migrations\n002_second.sql\n001_first.sql\n",
        encoding="utf-8",
    )
    for name in ("001_first.sql", "002_second.sql", "999_scratch.sql"):
        (tmp_path / name).write_text(f"-- {name}", encoding="utf-8")

    result = load_migration_files(tmp_path)

    assert [path.name for path in result] == ["002_second.sql", "001_first.sql"]


def test_load_migration_files_rejects_missing_and_duplicate_entries(tmp_path: Path):
    (tmp_path / "MANIFEST.txt").write_text(
        "001_missing.sql\n001_missing.sql\n",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="duplicate"):
        load_migration_files(tmp_path)


def test_run_migrations_applies_baseline_before_creating_tracking_table(tmp_path: Path):
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    (migrations_dir / "MANIFEST.txt").write_text(
        "000_baseline.sql\n101_after.sql\n",
        encoding="utf-8",
    )
    (migrations_dir / "000_baseline.sql").write_text(
        "CREATE TABLE schema_migrations (filename TEXT PRIMARY KEY);",
        encoding="utf-8",
    )
    (migrations_dir / "101_after.sql").write_text(
        "CREATE TABLE after_baseline (id INTEGER);",
        encoding="utf-8",
    )

    cur = MagicMock()
    cur.fetchone.side_effect = [
        {"table_name": None},  # tracking table does not exist
        None,                  # 101_after.sql has not run
    ]
    cursor_context = MagicMock()
    cursor_context.__enter__.return_value = cur

    fake_database_file = tmp_path / "core" / "database.py"
    fake_database_file.parent.mkdir()
    fake_database_file.write_text("", encoding="utf-8")

    with (
        patch("core.database.__file__", str(fake_database_file)),
        patch("core.database.db_cursor", return_value=cursor_context),
        patch("core.database.settings.database_url", "postgresql://test"),
    ):
        run_migrations()

    statements = [call.args[0] for call in cur.execute.call_args_list]
    baseline_index = statements.index(
        "CREATE TABLE schema_migrations (filename TEXT PRIMARY KEY);"
    )
    tracker_bootstrap_index = next(
        index
        for index, statement in enumerate(statements)
        if "CREATE TABLE IF NOT EXISTS schema_migrations" in statement
    )
    assert baseline_index < tracker_bootstrap_index
    assert "CREATE TABLE after_baseline (id INTEGER);" in statements

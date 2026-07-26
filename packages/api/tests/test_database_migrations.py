from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.database import (
    assert_schema_version,
    load_migration_files,
    run_migrations,
    REQUIRED_SCHEMA_VERSION,
)


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


def test_run_migrations_rejects_changed_already_applied_migration(tmp_path: Path):
    """Migrations must never be edited after being applied — if the file content
    no longer matches the stored checksum, refuse to proceed silently."""
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    (migrations_dir / "MANIFEST.txt").write_text("101_after.sql\n", encoding="utf-8")
    (migrations_dir / "101_after.sql").write_text(
        "CREATE TABLE after_baseline (id INTEGER);", encoding="utf-8"
    )

    cur = MagicMock()
    cur.fetchone.side_effect = [
        {"table_name": "schema_migrations"},  # tracking table exists
        {"checksum": "stale-checksum-does-not-match"},
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
        pytest.raises(RuntimeError, match="checksum mismatch"),
    ):
        run_migrations()


def test_run_migrations_skips_already_applied_migration_with_matching_checksum(tmp_path: Path):
    from core.database import _checksum

    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    (migrations_dir / "MANIFEST.txt").write_text("101_after.sql\n", encoding="utf-8")
    sql_text = "CREATE TABLE after_baseline (id INTEGER);"
    (migrations_dir / "101_after.sql").write_text(sql_text, encoding="utf-8")

    cur = MagicMock()
    cur.fetchone.side_effect = [
        {"table_name": "schema_migrations"},
        {"checksum": _checksum(sql_text)},
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
    assert sql_text not in statements  # not re-applied


def test_assert_schema_version_passes_when_matching():
    cur = MagicMock()
    cur.fetchone.return_value = {"value": str(REQUIRED_SCHEMA_VERSION)}
    assert_schema_version(cur)  # does not raise


def test_assert_schema_version_raises_when_mismatched():
    cur = MagicMock()
    cur.fetchone.return_value = {"value": str(REQUIRED_SCHEMA_VERSION + 1)}
    with pytest.raises(RuntimeError, match="mismatch"):
        assert_schema_version(cur)


def test_assert_schema_version_raises_when_unset():
    cur = MagicMock()
    cur.fetchone.return_value = None
    with pytest.raises(RuntimeError, match="not set"):
        assert_schema_version(cur)

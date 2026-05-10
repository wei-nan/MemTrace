"""
conftest.py — Shared pytest fixtures for MemTrace API tests.

Test DB strategy:
  - Unit tests: use unittest.mock to avoid any real DB connections.
  - Integration tests: requires a running Postgres instance.
    Set TEST_DATABASE_URL env var, e.g.:
      TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/memtrace_test

  For Docker-based integration testing:
    docker compose up -d postgres
    TEST_DATABASE_URL=postgresql://... pytest tests/

  Each integration test that uses `db_conn` runs inside a transaction that is
  rolled back after the test, keeping the DB clean.
"""
from __future__ import annotations

import os
import sys
from typing import Generator
from unittest.mock import MagicMock

import pytest

# Ensure packages/api is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# ─── Lightweight mock cursor (used by pure unit tests) ───────────────────────

@pytest.fixture
def mock_cursor() -> MagicMock:
    """A simple MagicMock that mimics a psycopg2 RealDictCursor."""
    cur = MagicMock()
    cur.fetchone.return_value = None
    cur.fetchall.return_value = []
    cur.rowcount = 0
    return cur


# ─── Integration DB fixtures (skipped if TEST_DATABASE_URL not set) ──────────

def _get_test_db_url() -> str | None:
    return os.environ.get("TEST_DATABASE_URL")


@pytest.fixture(scope="session")
def db_conn():
    """
    Session-scoped real DB connection for integration tests.
    Skip automatically when TEST_DATABASE_URL is not configured.
    """
    url = _get_test_db_url()
    if not url:
        pytest.skip("TEST_DATABASE_URL not set — skipping integration tests")

    import psycopg2
    import psycopg2.extras

    conn = psycopg2.connect(url, cursor_factory=psycopg2.extras.RealDictCursor)
    conn.set_client_encoding("UTF8")
    yield conn
    conn.close()


@pytest.fixture
def db_transaction(db_conn) -> Generator:
    """
    Function-scoped transaction fixture.
    Each test runs inside a transaction that is rolled back on teardown,
    so tests are fully isolated without truncating tables.
    """
    db_conn.autocommit = False
    try:
        yield db_conn
    finally:
        db_conn.rollback()


# ─── FastAPI TestClient fixture ───────────────────────────────────────────────

@pytest.fixture(scope="session")
def client():
    """
    FastAPI TestClient backed by the real app.
    Requires the app to be importable (i.e., running in Docker or with venv).
    Skip if the app cannot be imported (e.g., missing DB connection at startup).
    """
    try:
        from fastapi.testclient import TestClient
        from main import app  # type: ignore[import]
        return TestClient(app)
    except Exception as exc:
        pytest.skip(f"Could not import app for TestClient: {exc}")


# ─── Factory fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def fake_user() -> dict:
    """A minimal user dict mimicking a decoded JWT payload."""
    return {
        "sub": "user_test_001",
        "email": "test@example.com",
    }


@pytest.fixture
def fake_admin_user() -> dict:
    return {
        "sub": "user_admin_001",
        "email": "admin@example.com",
        "role": "admin",
    }


@pytest.fixture
def fake_workspace_id() -> str:
    return "ws_test_fixture_001"

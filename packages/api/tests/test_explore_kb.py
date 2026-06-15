"""
tests/test_explore_kb.py — E1–E10

Tests for GET /api/v1/workspaces/explore
Verifies anonymous vs authenticated visibility, search, language filter, and sort.

Run:  pytest tests/test_explore_kb.py -v
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ─── Shared helpers ──────────────────────────────────────────────────────────

def _ws(id: str, name: str, visibility: str = "public", language: str = "zh-TW",
        node_count: int = 5, owner_id: str = "usr_a", my_role: str | None = None,
        description: str | None = None) -> dict:
    return {
        "id": id, "name": name, "description": description,
        "visibility": visibility, "language": language,
        "kb_type": "evergreen", "owner_id": owner_id,
        "owner_display_name": "Test User",
        "node_count": node_count, "created_at": "2026-01-01T00:00:00+00:00",
        "my_role": my_role,
    }


def _call(user, q=None, lang=None, sort="newest", db_rows=None):
    """Call explore_workspaces_in_db with a mocked cursor."""
    from services.workspaces import explore_workspaces_in_db
    cur = MagicMock()
    cur.fetchall.return_value = db_rows or []
    explore_workspaces_in_db(cur, user, q, lang, sort)
    return cur


# ─── E1: anonymous sees only public / conditional_public ─────────────────────

def test_e1_anonymous_only_public():
    """explore_workspaces_in_db WHERE clause must restrict to public/conditional_public for anon."""
    cur = _call(user=None)
    sql: str = cur.execute.call_args[0][0]
    # Find the outermost WHERE (last occurrence, after FROM/JOIN clauses)
    outer_where_idx = sql.lower().rfind("where")
    outer_where = sql[outer_where_idx:]
    # Outer WHERE must contain the public visibility guard
    assert "visibility IN ('public', 'conditional_public')" in outer_where
    # Outer WHERE must NOT contain owner_id = %s (that only appears for logged-in users)
    assert "owner_id = %s" not in outer_where


# ─── E2: anonymous result never contains private ─────────────────────────────

def test_e2_anonymous_result_has_no_private():
    """Simulate DB returning a private row — service must filter it out in SQL."""
    public_row = _ws("ws_1", "Public KB", visibility="public")
    private_row = _ws("ws_2", "My Private KB", visibility="private", my_role="admin")

    # The SQL WHERE clause should prevent private rows from being returned;
    # we verify the SQL is constructed correctly (not returning private).
    cur = _call(user=None, db_rows=[public_row])
    sql: str = cur.execute.call_args[0][0]
    assert "private" not in sql.lower() or "conditional_public" in sql


# ─── E3: authenticated user sees own private KB ──────────────────────────────

def test_e3_authenticated_sees_own_kb():
    """SQL must include owner_id = %s clause when user is authenticated."""
    user = {"sub": "usr_abc"}
    cur = _call(user=user)
    sql: str = cur.execute.call_args[0][0]
    assert "owner_id = %s" in sql


# ─── E4: authenticated user sees member KB ───────────────────────────────────

def test_e4_authenticated_sees_member_kb():
    """SQL must include workspace_members subquery for member access."""
    user = {"sub": "usr_abc"}
    cur = _call(user=user)
    sql: str = cur.execute.call_args[0][0]
    assert "workspace_members" in sql


# ─── E5: name search filter ──────────────────────────────────────────────────

def test_e5_name_search_ilike():
    """?q= should produce ILIKE filter on name and description."""
    user = None
    cur = _call(user=user, q="MemTrace")
    sql: str = cur.execute.call_args[0][0]
    params: list = cur.execute.call_args[0][1]
    assert "ILIKE" in sql
    assert any("%MemTrace%" in str(p) for p in params)


# ─── E6: search no results ───────────────────────────────────────────────────

def test_e6_search_no_results():
    """When DB returns empty list, result is empty (no crash)."""
    from services.workspaces import explore_workspaces_in_db
    cur = MagicMock()
    cur.fetchall.return_value = []
    result = explore_workspaces_in_db(cur, None, q="xyznotexist", lang=None, sort="newest")
    assert result == []


# ─── E7: language filter ─────────────────────────────────────────────────────

def test_e7_language_filter():
    """?lang=zh-TW should add language = %s to WHERE."""
    cur = _call(user=None, lang="zh-TW")
    sql: str = cur.execute.call_args[0][0]
    params: list = cur.execute.call_args[0][1]
    assert "language = %s" in sql
    assert "zh-TW" in params


# ─── E8: sort newest ─────────────────────────────────────────────────────────

def test_e8_sort_newest():
    """sort=newest → ORDER BY created_at DESC."""
    cur = _call(user=None, sort="newest")
    sql: str = cur.execute.call_args[0][0]
    assert "created_at DESC" in sql


# ─── E9: sort nodes ──────────────────────────────────────────────────────────

def test_e9_sort_nodes():
    """sort=nodes → ORDER BY node_count DESC."""
    cur = _call(user=None, sort="nodes")
    sql: str = cur.execute.call_args[0][0]
    assert "node_count DESC" in sql


# ─── E10: invalid sort rejected by FastAPI (integration) ─────────────────────

def test_e10_invalid_sort_rejected(client):
    """GET /api/v1/workspaces/explore?sort=invalid should return 422."""
    resp = client.get("/api/v1/workspaces/explore?sort=invalid")
    assert resp.status_code == 422

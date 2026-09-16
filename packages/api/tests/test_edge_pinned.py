"""
tests/test_edge_pinned.py
update_edge_in_db: the only way to set `pinned` on an already-created edge
without deleting and recreating it (services/edges.py::update_edge_in_db).
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from services.edges import update_edge_in_db


def test_update_edge_in_db_sets_pinned():
    cur = MagicMock()
    cur.fetchone.side_effect = [
        {"id": "edge_1"},  # existence check
        {"id": "edge_1", "from_id": "mem_a", "to_id": "mem_b", "relation": "related_to", "pinned": True},
    ]

    res = update_edge_in_db(cur, "ws_test", "edge_1", {"pinned": True})
    assert res["pinned"] is True

    update_sql, params = next(
        c.args for c in cur.execute.call_args_list if "UPDATE edges" in c.args[0]
    )
    assert "pinned = %s" in update_sql
    assert params[0] is True


def test_update_edge_in_db_missing_edge_raises_404():
    cur = MagicMock()
    cur.fetchone.return_value = None
    with pytest.raises(HTTPException) as exc:
        update_edge_in_db(cur, "ws_test", "edge_missing", {"pinned": True})
    assert exc.value.status_code == 404


def test_update_edge_in_db_requires_pinned_field():
    cur = MagicMock()
    cur.fetchone.return_value = {"id": "edge_1"}
    with pytest.raises(HTTPException) as exc:
        update_edge_in_db(cur, "ws_test", "edge_1", {})
    assert exc.value.status_code == 400

"""
tests/test_edge_governance.py
Write-governance: answered_by direction guard + resolution_status auto-sync + delete_edge.
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException
from services.edges import create_edge_in_db, delete_edge_in_db
from services.nodes import create_node_in_db


def _mk_node(cur, ws_id, content_type, title="t"):
    row = create_node_in_db(cur, ws_id, {
        "title": title,
        "content_type": content_type,
        "body": "body",
        "author": "tester",
        "visibility": "private",
    })
    return row["id"]


@pytest.mark.integration
class TestAnsweredByGovernance:

    def test_answered_by_auto_resolves_inquiry(self, db_transaction):
        conn = db_transaction
        ws_id = "ws_spec0001"
        with conn.cursor() as cur:
            inq = _mk_node(cur, ws_id, "inquiry", "q")
            ans = _mk_node(cur, ws_id, "factual", "a")
            create_edge_in_db(cur, ws_id, {"from_id": inq, "to_id": ans, "relation": "answered_by"})
            cur.execute("SELECT resolution_status FROM memory_nodes WHERE id = %s", (inq,))
            assert cur.fetchone()["resolution_status"] == "resolved"

    def test_answered_by_reversed_direction_rejected(self, db_transaction):
        conn = db_transaction
        ws_id = "ws_spec0001"
        with conn.cursor() as cur:
            inq = _mk_node(cur, ws_id, "inquiry", "q")
            ans = _mk_node(cur, ws_id, "factual", "a")
            with pytest.raises(HTTPException) as exc:
                create_edge_in_db(cur, ws_id, {"from_id": ans, "to_id": inq, "relation": "answered_by"})
            assert exc.value.status_code == 400


@pytest.mark.integration
class TestSymmetricRelationGovernance:
    """related_to / similar_to are direction-less: the reverse edge must be
    rejected so a pair is never stored as two mirrored edges."""

    @pytest.mark.parametrize("relation", ["related_to", "similar_to"])
    def test_reverse_direction_rejected(self, db_transaction, relation):
        conn = db_transaction
        ws_id = "ws_spec0001"
        with conn.cursor() as cur:
            a = _mk_node(cur, ws_id, "factual", "a")
            b = _mk_node(cur, ws_id, "factual", "b")
            create_edge_in_db(cur, ws_id, {"from_id": a, "to_id": b, "relation": relation})
            with pytest.raises(HTTPException) as exc:
                create_edge_in_db(cur, ws_id, {"from_id": b, "to_id": a, "relation": relation})
            assert exc.value.status_code == 409
            cur.execute(
                "SELECT count(*) AS n FROM edges WHERE workspace_id = %s AND relation = %s "
                "AND from_id IN (%s, %s) AND to_id IN (%s, %s)",
                (ws_id, relation, a, b, a, b),
            )
            assert cur.fetchone()["n"] == 1

    @pytest.mark.parametrize("relation", ["depends_on", "extends", "proceeds_to"])
    def test_directional_relations_allow_both_directions(self, db_transaction, relation):
        conn = db_transaction
        ws_id = "ws_spec0001"
        with conn.cursor() as cur:
            a = _mk_node(cur, ws_id, "factual", "a")
            b = _mk_node(cur, ws_id, "factual", "b")
            create_edge_in_db(cur, ws_id, {"from_id": a, "to_id": b, "relation": relation})
            create_edge_in_db(cur, ws_id, {"from_id": b, "to_id": a, "relation": relation})
            cur.execute(
                "SELECT count(*) AS n FROM edges WHERE workspace_id = %s AND relation = %s "
                "AND from_id IN (%s, %s) AND to_id IN (%s, %s)",
                (ws_id, relation, a, b, a, b),
            )
            assert cur.fetchone()["n"] == 2


@pytest.mark.integration
class TestRelatedToRedundancyGovernance:
    """P1: a generic related_to must not stack on a pair already joined by a
    specific relation; without one it is allowed."""

    def test_related_to_rejected_when_specific_relation_exists(self, db_transaction):
        conn = db_transaction
        ws_id = "ws_spec0001"
        with conn.cursor() as cur:
            a = _mk_node(cur, ws_id, "factual", "a")
            b = _mk_node(cur, ws_id, "factual", "b")
            create_edge_in_db(cur, ws_id, {"from_id": a, "to_id": b, "relation": "depends_on"})
            # related_to in either direction is now redundant → 409
            with pytest.raises(HTTPException) as exc:
                create_edge_in_db(cur, ws_id, {"from_id": b, "to_id": a, "relation": "related_to"})
            assert exc.value.status_code == 409

    def test_related_to_allowed_without_specific_relation(self, db_transaction):
        conn = db_transaction
        ws_id = "ws_spec0001"
        with conn.cursor() as cur:
            a = _mk_node(cur, ws_id, "factual", "a")
            b = _mk_node(cur, ws_id, "factual", "b")
            edge = create_edge_in_db(cur, ws_id, {"from_id": a, "to_id": b, "relation": "related_to"})
            assert edge["relation"] == "related_to"


@pytest.mark.integration
class TestDeleteEdge:

    def test_delete_edge_removes_edge(self, db_transaction):
        conn = db_transaction
        ws_id = "ws_spec0001"
        with conn.cursor() as cur:
            a = _mk_node(cur, ws_id, "factual", "a")
            b = _mk_node(cur, ws_id, "factual", "b")
            edge = create_edge_in_db(cur, ws_id, {"from_id": a, "to_id": b, "relation": "related_to"})
            res = delete_edge_in_db(cur, ws_id, edge["id"])
            assert res["deleted"] is True
            cur.execute("SELECT 1 FROM edges WHERE id = %s", (edge["id"],))
            assert cur.fetchone() is None

    def test_delete_edge_not_found(self, db_transaction):
        conn = db_transaction
        ws_id = "ws_spec0001"
        with conn.cursor() as cur:
            with pytest.raises(HTTPException) as exc:
                delete_edge_in_db(cur, ws_id, "edge_does_not_exist")
            assert exc.value.status_code == 404

"""
tests/test_contradiction.py — admission-time contradiction detection.

Verifies the generalized contradiction check (services/contradiction.py):
on a detected contradiction the NEW node is marked 'conflicted', a contradicts
edge is created, and an audit proposal is raised (high severity when the
contradicted node is established — human-confirmed or heavily traversed).
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch, AsyncMock

import pytest

from services.contradiction import detect_and_flag_contradictions

_VEC = "[" + ",".join(["0.02"] * 1536) + "]"


def _seed_pair(cur, ws_id, target_traversals=15):
    """Insert a target node and a new node with identical embeddings.

    target_traversals drives the severity path: >= HIGH_SEVERITY_TRAVERSAL_COUNT
    (10) makes the target 'established', so contradicting it is high severity.
    """
    cur.execute(
        """
        INSERT INTO memory_nodes (id, workspace_id, content_type, author, signature, title, body, traversal_count, embedding)
        VALUES ('contra_target', %s, 'factual', 'usr_seed', 'sig_t', 'Target', 'The sky is blue.', %s, %s::vector)
        ON CONFLICT (id) DO UPDATE SET embedding = EXCLUDED.embedding, traversal_count = EXCLUDED.traversal_count, status = 'active'
        """,
        (ws_id, target_traversals, _VEC),
    )
    cur.execute(
        """
        INSERT INTO memory_nodes (id, workspace_id, content_type, author, signature, title, body, embedding)
        VALUES ('contra_new', %s, 'factual', 'usr_seed', 'sig_n', 'New claim', 'The sky is green.', %s::vector)
        ON CONFLICT (id) DO UPDATE SET embedding = EXCLUDED.embedding, status = 'active'
        """,
        (ws_id, _VEC),
    )


@pytest.mark.integration
class TestContradictionDetection:

    @pytest.mark.asyncio
    async def test_contradiction_marks_conflicted_and_proposes(self, db_transaction):
        conn = db_transaction
        ws_id = "ws_spec0001"
        with conn.cursor() as cur:
            _seed_pair(cur, ws_id)

            with patch("services.contradiction.resolve_provider", return_value=MagicMock()), \
                 patch("services.contradiction.chat_completion",
                       new_callable=AsyncMock,
                       return_value=('{"contradicts": true, "reason": "sky colour conflict"}', 50)):
                summary = await detect_and_flag_contradictions(cur, ws_id, "contra_new")

            assert summary["status"] == "done"
            assert summary["flagged"] >= 1

            # New node marked conflicted
            cur.execute("SELECT status FROM memory_nodes WHERE id = 'contra_new'")
            assert cur.fetchone()["status"] == "conflicted"

            # contradicts edge new -> target
            cur.execute(
                "SELECT 1 FROM edges WHERE workspace_id = %s AND relation = 'contradicts' AND from_id = 'contra_new' AND to_id = 'contra_target'",
                (ws_id,),
            )
            assert cur.fetchone() is not None

            # high-severity proposal (target is established: 15 traversals)
            cur.execute(
                "SELECT severity, category FROM audit_proposals WHERE workspace_id = %s AND reviewer = 'contradiction_detector' AND 'contra_new' = ANY(target_ids)",
                (ws_id,),
            )
            prop = cur.fetchone()
            assert prop is not None
            assert prop["category"] == "contradiction"
            assert prop["severity"] == "high"

    @pytest.mark.asyncio
    async def test_no_contradiction_leaves_node_active(self, db_transaction):
        conn = db_transaction
        ws_id = "ws_spec0001"
        with conn.cursor() as cur:
            _seed_pair(cur, ws_id)

            with patch("services.contradiction.resolve_provider", return_value=MagicMock()), \
                 patch("services.contradiction.chat_completion",
                       new_callable=AsyncMock,
                       return_value=('{"contradicts": false, "reason": "compatible"}', 50)):
                summary = await detect_and_flag_contradictions(cur, ws_id, "contra_new")

            assert summary["status"] == "done"
            assert summary["flagged"] == 0
            cur.execute("SELECT status FROM memory_nodes WHERE id = 'contra_new'")
            assert cur.fetchone()["status"] == "active"

    @pytest.mark.asyncio
    async def test_provider_unavailable_returns_undetermined(self, db_transaction):
        from core.ai import AIProviderUnavailable
        conn = db_transaction
        ws_id = "ws_spec0001"
        with conn.cursor() as cur:
            _seed_pair(cur, ws_id)
            with patch("services.contradiction.resolve_provider", side_effect=AIProviderUnavailable("no key")):
                summary = await detect_and_flag_contradictions(cur, ws_id, "contra_new")
            assert summary["status"] == "undetermined"
            # node must remain active — we did not (and could not) judge it
            cur.execute("SELECT status FROM memory_nodes WHERE id = 'contra_new'")
            assert cur.fetchone()["status"] == "active"

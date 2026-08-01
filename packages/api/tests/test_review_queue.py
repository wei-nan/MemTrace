from unittest.mock import MagicMock, patch

import pytest

from core.database import db_cursor
from routers.review import _annotate_stale_edge, _fetch_active_node_ids, list_review_queue


def _pending_row(id_, change_type, node_data, workspace_id="ws_x"):
    return {
        "id": id_,
        "workspace_id": workspace_id,
        "change_type": change_type,
        "node_data": node_data,
        "before_snapshot": None,
        "diff_summary": {},
        "proposer_meta": {},
        "status": "pending",
    }


class TestReviewQueueStaleEdgeIsBatched:
    """mem_0b494395: _annotate_stale_edge used to issue a per-row memory_nodes
    query for every pending create_edge item (up to 2N queries for N rows).
    Asserts the fix collapses this to a single batched lookup query,
    regardless of how many create_edge rows are pending."""

    @patch("routers.review._get_effective_role", return_value="admin")
    @patch("routers.review._require_ws_access", return_value={"owner_id": "usr_owner"})
    @patch("routers.review.db_cursor")
    def test_stale_edge_check_issues_one_query_not_one_per_row(
        self, mock_db_cursor, mock_require_access, mock_role
    ):
        # 5 pending create_edge rows referencing only 2 distinct node ids, plus
        # one unrelated 'create' row that must be left untouched.
        pending_rows = [
            _pending_row(f"rev_edge_{i}", "create_edge", {"from_id": "node_a", "to_id": "node_stale"})
            for i in range(5)
        ]
        pending_rows.append(_pending_row("rev_create", "create", {}))

        cur = MagicMock()
        # 1st cur.fetchall(): the review_queue SELECT. 2nd: the batched
        # memory_nodes lookup — only node_a comes back as active, so
        # node_stale is treated as missing/archived.
        cur.fetchall.side_effect = [pending_rows, [{"id": "node_a"}]]
        mock_db_cursor.return_value.__enter__.return_value = cur

        result = list_review_queue("ws_x", status="pending", user={"sub": "usr_owner"})

        # Exactly 2 SQL statements total: one for review_queue, one batched
        # memory_nodes lookup shared across all 5 create_edge rows — not
        # 1 + 2*5 like the old per-row implementation.
        assert cur.execute.call_count == 2
        batch_query_params = cur.execute.call_args_list[1][0][1]
        assert batch_query_params[0] == "ws_x"
        assert set(batch_query_params[1]) == {"node_a", "node_stale"}

        by_id = {item["id"]: item for item in result}
        assert by_id["rev_create"]["proposer_meta"].get("stale_edge") is not True
        for i in range(5):
            item = by_id[f"rev_edge_{i}"]
            assert item["proposer_meta"]["stale_edge"] is True
            assert item["proposer_meta"]["missing_nodes"] == ["node_stale"]
            assert item["can_review"] is False


def _setup_workspace_and_nodes(cur, ws_id, user_id):
    cur.execute("SELECT 1 FROM users WHERE id = %s", (user_id,))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO users (id, display_name, email) VALUES (%s, %s, %s)",
            (user_id, user_id, f"{user_id}@example.com"),
        )
    cur.execute("SELECT 1 FROM workspaces WHERE id = %s", (ws_id,))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO workspaces (id, name, owner_id, language) VALUES (%s, %s, %s, 'zh-TW')",
            (ws_id, "Test Workspace", user_id),
        )
    for node_id, status in (("node_active_a", "active"), ("node_active_b", "active"), ("node_deleted_c", "archived")):
        cur.execute("SELECT 1 FROM memory_nodes WHERE id = %s", (node_id,))
        if not cur.fetchone():
            cur.execute(
                """
                INSERT INTO memory_nodes (id, workspace_id, title, content_type, author, signature, status)
                VALUES (%s, %s, 'Test Node', 'factual', %s, 'sig', %s)
                """,
                (node_id, ws_id, user_id, status),
            )


@pytest.mark.integration
class TestReviewQueueStaleEdgeAgainstRealDb:
    """Same fix, checked against a real Postgres connection so the ANY(%s)
    batch query and status filter are exercised for real, not just mocked."""

    def test_batched_lookup_flags_correct_nodes_across_mixed_rows(self, db_transaction):
        ws_id = "ws_test_review_queue_batch"
        user_id = "usr_review_queue_batch_owner"

        with db_transaction.cursor() as cur:
            _setup_workspace_and_nodes(cur, ws_id, user_id)

            active_ids = _fetch_active_node_ids(cur, ws_id, {"node_active_a", "node_active_b", "node_deleted_c"})
            assert active_ids == {"node_active_a", "node_active_b"}

            fresh_item = _annotate_stale_edge(
                {"change_type": "create_edge", "node_data": {"from_id": "node_active_a", "to_id": "node_active_b"}, "proposer_meta": {}},
                active_ids,
            )
            assert fresh_item.get("proposer_meta", {}).get("stale_edge") is not True

            for from_id in ("node_active_a", "node_active_b"):
                stale_item = _annotate_stale_edge(
                    {"change_type": "create_edge", "node_data": {"from_id": from_id, "to_id": "node_deleted_c"}, "proposer_meta": {}},
                    active_ids,
                )
                assert stale_item["proposer_meta"]["stale_edge"] is True
                assert stale_item["proposer_meta"]["missing_nodes"] == ["node_deleted_c"]
                assert stale_item["can_review"] is False

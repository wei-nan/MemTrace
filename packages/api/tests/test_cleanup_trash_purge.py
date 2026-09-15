"""
tests/test_cleanup_trash_purge.py — jobs/cleanup.py's 30-day trash purge
(ws_spec_plan/mem_bc15e46d): confirmed deletes sit in `trashed` for 30 days,
reversible, before this job runs the existing tombstone-delete path on them.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from jobs.cleanup import _purge_expired_trash


def test_purge_expired_trash_calls_delete_node_in_db_for_expired_nodes():
    cur = MagicMock()
    cur.fetchall.side_effect = [
        [{"id": "mem_1", "workspace_id": "ws_test", "trashed_by": "user_1",
          "trash_reason_category": "duplicate", "trash_reason_note": "dup of mem_2"}],
        [],  # no expired edges
    ]

    with patch("services.nodes.delete_node_in_db") as mock_delete_node:
        _purge_expired_trash(cur)

    mock_delete_node.assert_called_once_with(
        cur, "ws_test", "mem_1",
        deleted_by="user_1", reason_category="duplicate", reason_note="dup of mem_2",
    )


def test_purge_expired_trash_calls_delete_edge_in_db_for_expired_edges():
    cur = MagicMock()
    cur.fetchall.side_effect = [
        [],  # no expired nodes
        [{"id": "edge_1", "workspace_id": "ws_test", "trashed_by": "user_1",
          "trash_reason_category": "wrong_direction", "trash_reason_note": ""}],
    ]

    with patch("services.edges.delete_edge_in_db") as mock_delete_edge:
        _purge_expired_trash(cur)

    mock_delete_edge.assert_called_once_with(
        cur, "ws_test", "edge_1",
        deleted_by="user_1", reason_category="wrong_direction", reason_note="",
    )


def test_purge_expired_trash_defaults_missing_actor_and_reason():
    cur = MagicMock()
    cur.fetchall.side_effect = [
        [{"id": "mem_1", "workspace_id": "ws_test", "trashed_by": None,
          "trash_reason_category": None, "trash_reason_note": None}],
        [],
    ]

    with patch("services.nodes.delete_node_in_db") as mock_delete_node:
        _purge_expired_trash(cur)

    mock_delete_node.assert_called_once_with(
        cur, "ws_test", "mem_1",
        deleted_by="system", reason_category="other", reason_note="",
    )


def test_purge_expired_trash_one_failure_does_not_block_others():
    cur = MagicMock()
    cur.fetchall.side_effect = [
        [
            {"id": "mem_1", "workspace_id": "ws_test", "trashed_by": "u1",
             "trash_reason_category": "other", "trash_reason_note": ""},
            {"id": "mem_2", "workspace_id": "ws_test", "trashed_by": "u1",
             "trash_reason_category": "other", "trash_reason_note": ""},
        ],
        [],
    ]

    with patch("services.nodes.delete_node_in_db", side_effect=[Exception("boom"), None]) as mock_delete_node:
        _purge_expired_trash(cur)  # must not raise

    assert mock_delete_node.call_count == 2

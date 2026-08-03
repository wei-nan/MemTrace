"""
tests/test_submit_outcome.py
Regression coverage for the submit_outcome handler's record_path failure
handling (ws_6aa957c3/mem_5cad006f, ws_spec_plan/mem_532f310c).

record_path_in_db can raise (e.g. an embedding-dimension mismatch between the
resolved provider and the workspace's pinned vector column) *after* the
task's status/edge update has already committed in an earlier, separate
transaction. Before this fix, that exception propagated straight out of
submit_outcome, so the caller saw a generic MCP error for a call that had, in
fact, already partially succeeded. submit_outcome had no test coverage of
any kind prior to this file.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from services.mcp_tools import execute_tool

WS_ID = "ws_test"
TASK_ID = "mem_task1"
IMPL_ID = "mem_impl1"


def _mock_db_cursor(fetchone_side_effect):
    """fetchone_side_effect's first item is always the claim check
    (`_has_live_claim`'s SELECT) — callers that need a live claim must pass
    a truthy row (e.g. {"1": 1}) as the first element."""
    cur = MagicMock()
    cur.fetchone.side_effect = fetchone_side_effect
    mock_db_cursor = MagicMock()
    mock_db_cursor.__enter__.return_value = cur
    mock_db_cursor.__exit__.return_value = False
    return mock_db_cursor, cur


def _base_args(outcome="success"):
    return {
        "workspace_id": WS_ID,
        "task_node_id": TASK_ID,
        "outcome": outcome,
        "implementation_node_id": IMPL_ID,
        "node_sequence": [TASK_ID, IMPL_ID],
        "message": "done",
    }


@pytest.mark.asyncio
async def test_submit_outcome_record_path_failure_does_not_raise():
    """The core regression test: record_path_in_db raising must not propagate
    out of submit_outcome, and the response must say so via path_recorded."""
    user = {"sub": "u1"}

    # Three sequential cur.fetchone() calls inside the main transaction:
    # 1) the claim check (_has_live_claim — truthy = caller holds the claim),
    # 2) the task-existence check, 3) the C3 depends_on-parent lookup (None = skip).
    task_row = {"id": TASK_ID, "status": "active"}
    mock_db_cursor, cur = _mock_db_cursor([{"1": 1}, task_row, None])

    with patch("services.mcp_tools.require_ws_access", return_value={"my_role": "editor"}), \
         patch("services.mcp_tools.db_cursor", return_value=mock_db_cursor), \
         patch("services.edges.create_edge_in_db", return_value={"id": "edge_1"}), \
         patch("services.inquiry_paths.record_path_in_db", new_callable=AsyncMock) as mock_record_path, \
         patch("services.mcp_tools.log_mcp_interaction"):
        mock_record_path.side_effect = Exception("expected 1536 dimensions, not 3072")

        res = await execute_tool("submit_outcome", _base_args(), user, MagicMock())

    # Must NOT raise, and must still report the outcome as submitted.
    assert res["task_node_id"] == TASK_ID
    assert res["outcome"] == "success"
    assert res["implementation_node_id"] == IMPL_ID
    assert res["path_recorded"] is False
    mock_record_path.assert_awaited_once()


@pytest.mark.asyncio
async def test_submit_outcome_record_path_success_reports_true():
    user = {"sub": "u1"}

    task_row = {"id": TASK_ID, "status": "active"}
    mock_db_cursor, cur = _mock_db_cursor([{"1": 1}, task_row, None])

    with patch("services.mcp_tools.require_ws_access", return_value={"my_role": "editor"}), \
         patch("services.mcp_tools.db_cursor", return_value=mock_db_cursor), \
         patch("services.edges.create_edge_in_db", return_value={"id": "edge_1"}), \
         patch("services.inquiry_paths.record_path_in_db", new_callable=AsyncMock) as mock_record_path, \
         patch("services.mcp_tools.log_mcp_interaction"):
        mock_record_path.return_value = {"id": "path_1"}

        res = await execute_tool("submit_outcome", _base_args(), user, MagicMock())

    assert res["path_recorded"] is True
    mock_record_path.assert_awaited_once()


@pytest.mark.asyncio
async def test_submit_outcome_requires_claim():
    # Claim check (_has_live_claim) returns no row -> must fail before touching
    # record_path at all.
    user = {"sub": "u1"}
    mock_db_cursor, cur = _mock_db_cursor([None])

    with patch("services.mcp_tools.require_ws_access", return_value={"my_role": "editor"}), \
         patch("services.mcp_tools.db_cursor", return_value=mock_db_cursor):
        with pytest.raises(Exception):
            await execute_tool("submit_outcome", _base_args(), user, MagicMock())

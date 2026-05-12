"""
test_traverse.py — unit tests for graph traversal (bfs_neighborhood) and
the MCP traverse tool handler.

Covers:
  - bfs_neighborhood called with viewer_role (no viewer_id kwarg)
  - depth=1 returns neighbours
  - MCP execute_tool("traverse") does NOT pass viewer_id to bfs_neighborhood
  - Smoke: traverse result has "nodes" and "edges" keys
"""
import sys
import os
from unittest.mock import MagicMock, patch, call

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.search import bfs_neighborhood


# ─── bfs_neighborhood unit tests ──────────────────────────────────────────────

def _make_cur(edges, nodes):
    """Return a mock cursor whose fetchall() returns edges then nodes."""
    cur = MagicMock()
    cur.fetchall.side_effect = [edges, nodes]
    return cur


def test_bfs_depth1_returns_neighbour():
    """depth=1 should return root + one neighbour and the connecting edge."""
    cur = _make_cur(
        edges=[{
            "id": "edge_1",
            "from_id": "mem_root",
            "to_id": "mem_child",
            "relation": "extends",
            "weight": 0.9,
        }],
        nodes=[
            {"id": "mem_root",  "title_en": "Root",  "title_zh": "", "content_type": "factual", "tags": [], "visibility": "public"},
            {"id": "mem_child", "title_en": "Child", "title_zh": "", "content_type": "factual", "tags": [], "visibility": "public"},
        ],
    )
    result = bfs_neighborhood(cur, "ws_test", "mem_root", depth=1)
    assert "nodes" in result
    assert "edges" in result
    assert any(n["id"] == "mem_child" for n in result["nodes"])
    assert result["edges"][0]["id"] == "edge_1"


def test_bfs_accepts_viewer_role_kwarg():
    """bfs_neighborhood must accept viewer_role without raising TypeError."""
    cur = _make_cur(edges=[], nodes=[])
    # Should not raise
    result = bfs_neighborhood(cur, "ws_test", "mem_x", depth=1, viewer_role="viewer")
    assert result["nodes"] == []
    assert result["edges"] == []


def test_bfs_does_not_accept_viewer_id():
    """Passing viewer_id should raise TypeError — the signature has no such param."""
    cur = _make_cur(edges=[], nodes=[])
    with pytest.raises(TypeError, match="viewer_id"):
        bfs_neighborhood(cur, "ws_test", "mem_x", depth=1, viewer_id="usr_abc")


def test_bfs_empty_graph():
    """No edges → only root in nodes, no edges."""
    cur = _make_cur(edges=[], nodes=[
        {"id": "mem_root", "title_en": "Lone", "title_zh": "", "content_type": "factual", "tags": [], "visibility": "public"},
    ])
    result = bfs_neighborhood(cur, "ws_test", "mem_root", depth=2)
    assert result["edges"] == []


def test_bfs_relation_filter_passed_to_sql():
    """When relation= is given, the SQL execute call should include that relation."""
    cur = _make_cur(edges=[], nodes=[])
    bfs_neighborhood(cur, "ws_test", "mem_root", depth=1, relation="depends_on")
    # The first execute call should have 'depends_on' somewhere in its params
    first_call_params = cur.execute.call_args_list[0][0][1]
    assert "depends_on" in first_call_params


# ─── MCP traverse handler integration test ────────────────────────────────────

@pytest.mark.asyncio
async def test_mcp_traverse_no_viewer_id_kwarg():
    """
    execute_tool('traverse') must call bfs_neighborhood WITHOUT viewer_id.
    (Regression guard for I-102: the extra kwarg caused a TypeError in production.)
    """
    from services.mcp_tools import execute_tool

    user = {"sub": "usr_test"}
    args = {"workspace_id": "ws_spec0001", "node_id": "mem_g004", "depth": 1}
    mock_result = {"nodes": [{"id": "mem_g004"}], "edges": [], "truncated": False, "total_nodes": 1}
    background_tasks = MagicMock()

    with patch("services.mcp_tools.bfs_neighborhood", return_value=mock_result) as mock_bfs, \
         patch("services.mcp_tools.db_cursor"), \
         patch("services.mcp_tools.require_ws_access", return_value={"owner_id": "usr_test"}), \
         patch("services.mcp_tools.get_effective_role", return_value="admin"), \
         patch("services.mcp_tools.log_mcp_interaction"):

        result = await execute_tool("traverse", args, user, background_tasks)

    assert "nodes" in result
    assert "edges" in result

    # Critical: bfs_neighborhood must NOT have been called with viewer_id
    _, called_kwargs = mock_bfs.call_args
    assert "viewer_id" not in called_kwargs, (
        "viewer_id was passed to bfs_neighborhood — regression of I-102"
    )
    # Must have viewer_role instead
    assert "viewer_role" in called_kwargs


@pytest.mark.asyncio
async def test_mcp_traverse_smoke():
    """Smoke: traverse returns the expected dict shape."""
    from services.mcp_tools import execute_tool

    user = {"sub": "usr_test"}
    args = {"workspace_id": "ws_1", "node_id": "mem_1"}
    mock_result = {
        "nodes": [{"id": "mem_1"}, {"id": "mem_2"}],
        "edges": [{"id": "edge_1", "from_id": "mem_1", "to_id": "mem_2"}],
        "truncated": False,
        "total_nodes": 2,
    }
    background_tasks = MagicMock()

    with patch("services.mcp_tools.bfs_neighborhood", return_value=mock_result), \
         patch("services.mcp_tools.db_cursor"), \
         patch("services.mcp_tools.require_ws_access", return_value={"owner_id": "u1"}), \
         patch("services.mcp_tools.get_effective_role", return_value="viewer"), \
         patch("services.mcp_tools.log_mcp_interaction"):

        result = await execute_tool("traverse", args, user, background_tasks)

    assert len(result["nodes"]) == 2
    assert len(result["edges"]) == 1
    assert result["nodes"][0]["id"] == "mem_1"

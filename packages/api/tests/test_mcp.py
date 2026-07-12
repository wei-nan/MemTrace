import sys
import os
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import HTTPException

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.mcp_tools import execute_tool, TOOLS, dispatch

@pytest.mark.asyncio
async def test_execute_tool_list_workspaces():
    user = {"sub": "user_1"}
    cur = MagicMock()
    cur.fetchall.return_value = [{"id": "ws_1", "name_en": "WS 1"}]

    mock_db_cursor = MagicMock()
    mock_db_cursor.__enter__.return_value = cur

    with patch("services.mcp_tools.db_cursor", return_value=mock_db_cursor):
        res = await execute_tool("list_workspaces", {}, user, MagicMock())
        assert len(res) == 1
        assert res[0]["id"] == "ws_1"


@pytest.mark.asyncio
async def test_execute_tool_list_workspaces_projects_summary_fields_only():
    """2026-07-07 瘦身：list_workspaces 只回摘要欄位，不外洩 settings/schema_version 等內部欄位。"""
    user = {"sub": "user_1"}
    full_ws_row = {
        "id": "ws_1",
        "name": "WS 1",
        "description": "desc",
        "my_role": "admin",
        "visibility": "private",
        "language": "zh-TW",
        "node_count": 42,
        "settings": {"mcp_ingest_enabled": True},
        "schema_version": "1.0",
        "embedding_dim": 3072,
        "deleted_at": None,
    }

    with patch("services.mcp_tools.list_workspaces_in_db", return_value=[full_ws_row]):
        res = await execute_tool("list_workspaces", {}, user, MagicMock())

    assert res == [{
        "id": "ws_1",
        "name": "WS 1",
        "description": "desc",
        "my_role": "admin",
        "visibility": "private",
        "language": "zh-TW",
        "node_count": 42,
    }]
    assert "settings" not in res[0]
    assert "schema_version" not in res[0]


@pytest.mark.asyncio
async def test_execute_tool_create_edge_projects_response():
    """2026-07-07 瘦身：create_edge 只回精簡欄位，不外洩 rating_sum/co_access_count 等內部統計。"""
    user = {"sub": "user_1"}
    args = {"workspace_id": "ws_1", "from_id": "mem_a", "to_id": "mem_b", "relation": "related_to"}

    full_edge_row = {
        "id": "edge_1",
        "workspace_id": "ws_1",
        "from_id": "mem_a",
        "to_id": "mem_b",
        "relation": "related_to",
        "weight": 0.8,
        "status": "active",
        "half_life_days": 30,
        "updated_at": "2026-07-07T00:00:00Z",
        "rating_sum": 0,
        "rating_count": 0,
        "co_access_count": 5,
        "metadata": {},
        "pinned": False,
        "edge_class": "semantic",
    }

    with patch("services.mcp_tools.db_cursor"), \
         patch("services.mcp_tools.require_ws_access", return_value={"owner_id": "user_1"}), \
         patch("services.mcp_tools.create_edge_in_db", return_value=full_edge_row):
        res = await execute_tool("create_edge", args, user, MagicMock())

    assert res == {
        "id": "edge_1",
        "from_id": "mem_a",
        "to_id": "mem_b",
        "relation": "related_to",
        "weight": 0.8,
        "status": "active",
        "half_life_days": 30,
        "updated_at": "2026-07-07T00:00:00Z",
    }
    assert "rating_sum" not in res
    assert "co_access_count" not in res

@pytest.mark.asyncio
async def test_execute_tool_get_node():
    user = {"sub": "user_1"}
    args = {"workspace_id": "ws_1", "node_id": "mem_1"}
    cur = MagicMock()
    cur.fetchone.return_value = {"id": "mem_1", "title_en": "Node 1"}
    
    mock_db_cursor = MagicMock()
    mock_db_cursor.__enter__.return_value = cur
    
    # Mock require_ws_access to return a valid workspace row
    workspace_row = {"id": "ws_1", "visibility": "public", "owner_id": "user_1", "kb_type": "evergreen"}
    
    background_tasks = MagicMock()
    
    with patch("services.mcp_tools.db_cursor", return_value=mock_db_cursor):
        with patch("services.workspaces.require_ws_access", return_value=workspace_row):
            with patch("services.workspaces.get_effective_role", return_value="admin"):
                # We also need to mock cur.fetchone for get_node_in_db's internal call
                cur.fetchone.return_value = {"id": "mem_1", "title_en": "Node 1", "visibility": "public"}
                res = await execute_tool("get_node", args, user, background_tasks)
                assert res["id"] == "mem_1"
                assert background_tasks.add_task.call_count == 2

@pytest.mark.asyncio
async def test_execute_tool_search_nodes():
    user = {"sub": "user_1"}
    args = {"workspace_id": "ws_1", "query": "test", "include_archived": True}
    
    mock_results = [{"id": "mem_1", "title_en": "Test Node"}]
    
    background_tasks = MagicMock()
    
    with patch("services.mcp_tools.search_nodes_in_db", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = mock_results
        with patch("services.mcp_tools.db_cursor"):
            with patch("services.search.db_cursor"):
                with patch("services.search.resolve_provider"):
                    with patch("services.search.embed", side_effect=AsyncMock(return_value=([0.1]*1536, 10))):
                        res = await execute_tool("search_nodes", args, user, background_tasks)
            assert len(res) == 1
            assert res[0]["id"] == "mem_1"
            assert mock_search.await_args.kwargs["include_archived"] is True
            # Should have recorded interaction edges and logged query
            assert background_tasks.add_task.call_count >= 1

@pytest.mark.asyncio
async def test_execute_tool_create_node():
    user = {"sub": "user_1"}
    args = {"workspace_id": "ws_1", "title": "New Node", "body": "Content"}
    
    mock_node = {
        "id": "mem_new",
        "title": "New Node",
        "body": "Content",
        "status": "active",
        "created_at": "2026-07-07T07:10:00+08:00",
        "signature": "secret-signature",
        "dim_freshness": 1.0,
        "ask_count": 7,
        "workspace_id": "ws_1",
    }
    
    background_tasks = MagicMock()
    
    with patch("services.mcp_tools.create_node_full_with_dedup", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = (mock_node, None, None)
        with patch("services.mcp_tools.db_cursor"):
            with patch("services.mcp_tools.trigger_node_background_jobs") as mock_bg:
                res = await execute_tool("create_node", args, user, background_tasks)
                assert res == {
                    "id": "mem_new",
                    "title": "New Node",
                    "status": "active",
                    "created_at": "2026-07-07T07:10:00+08:00",
                }
                assert "body" not in res
                assert "signature" not in res
                assert "dim_freshness" not in res
                assert "ask_count" not in res
                assert "workspace_id" not in res
                mock_bg.assert_called_once()
                assert mock_bg.call_args.args[4] is mock_node

@pytest.mark.asyncio
async def test_execute_tool_create_node_duplicate():
    user = {"sub": "user_1"}
    args = {"workspace_id": "ws_1", "title_en": "Dup", "body_en": "Dup"}
    
    dup_info = {"action": "duplicate_found", "existing_node_id": "mem_old"}
    
    with patch("services.mcp_tools.create_node_full_with_dedup", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = (None, None, dup_info)
        with patch("services.mcp_tools.db_cursor"):
            res = await execute_tool("create_node", args, user, MagicMock())
            assert res["action"] == "duplicate_found"
            assert res["existing_node_id"] == "mem_old"


@pytest.mark.asyncio
async def test_execute_tool_create_node_pending_review_stays_compact():
    user = {"sub": "user_1"}
    args = {"workspace_id": "ws_1", "title": "Needs Review", "body": "Content"}

    background_tasks = MagicMock()

    with patch("services.mcp_tools.create_node_full_with_dedup", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = (None, "rev_1", None)
        with patch("services.mcp_tools.db_cursor"):
            res = await execute_tool("create_node", args, user, background_tasks)
            assert res == {"review_id": "rev_1", "status": "pending_review"}


@pytest.mark.asyncio
async def test_execute_tool_update_node_projects_success_response():
    user = {"sub": "user_1"}
    args = {"workspace_id": "ws_1", "node_id": "mem_1", "body": "Updated body"}
    mock_node = {
        "id": "mem_1",
        "title": "Updated Node",
        "body": "Updated body",
        "status": "active",
        "updated_at": "2026-07-07T07:12:00+08:00",
        "signature": "secret-signature",
        "dim_utility": 1.0,
        "miss_count": 3,
        "workspace_id": "ws_1",
    }

    with patch("services.mcp_tools.update_node_in_db", return_value=mock_node):
        with patch("services.mcp_tools.db_cursor"):
            res = await execute_tool("update_node", args, user, MagicMock())
            assert res == {
                "id": "mem_1",
                "title": "Updated Node",
                "status": "active",
                "updated_at": "2026-07-07T07:12:00+08:00",
            }
            assert "body" not in res
            assert "signature" not in res
            assert "dim_utility" not in res
            assert "miss_count" not in res
            assert "workspace_id" not in res

@pytest.mark.asyncio
async def test_execute_tool_traverse():
    user = {"sub": "user_1"}
    args = {"workspace_id": "ws_1", "node_id": "mem_1"}
    
    mock_result = {"nodes": [], "edges": []}
    
    background_tasks = MagicMock()
    
    with patch("services.mcp_tools.bfs_neighborhood", return_value=mock_result):
        with patch("services.mcp_tools.db_cursor"):
            with patch("services.mcp_tools.get_effective_role", return_value="admin"):
                with patch("services.mcp_tools.require_ws_access", return_value={"owner_id": "u1"}):
                    res = await execute_tool("traverse", args, user, background_tasks)
                    assert "nodes" in res
                    background_tasks.add_task.assert_called()

@pytest.mark.asyncio
async def test_dispatch_tools_list():
    payload = {"id": "1", "method": "tools/list"}
    res = await dispatch(payload, {"sub": "u1"}, MagicMock())
    assert res["id"] == "1"
    assert "tools" in res["result"]
    assert "jsonrpc" in res

@pytest.mark.asyncio
async def test_dispatch_tools_call():
    payload = {
        "id": "2", 
        "method": "tools/call", 
        "params": {"name": "list_workspaces", "arguments": {}}
    }
    
    with patch("services.mcp_tools.execute_tool", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = [{"id": "ws_1"}]
        res = await dispatch(payload, {"sub": "u1"}, MagicMock())
        assert res["id"] == "2"
        assert "result" in res
        content = res["result"]["content"][0]["text"]
        assert "ws_1" in content

@pytest.mark.asyncio
async def test_execute_tool_access_denied():
    user = {"sub": "user_1"}
    args = {"workspace_id": "ws_forbidden", "node_id": "mem_1"}
    
    with patch("services.workspaces.require_ws_access", side_effect=HTTPException(status_code=403, detail="Forbidden")):
        with patch("services.mcp_tools.db_cursor"):
            with pytest.raises(HTTPException):
                await execute_tool("get_node", args, user, MagicMock())


@pytest.mark.asyncio
async def test_get_next_task_excludes_answered_and_resolved_inquiries():
    user = {"sub": "user_1"}
    cur = MagicMock()
    cur.fetchall.return_value = []

    mock_db_cursor = MagicMock()
    mock_db_cursor.__enter__.return_value = cur

    with patch("services.mcp_tools.db_cursor", return_value=mock_db_cursor):
        with patch("services.mcp_tools.require_ws_access"):
            result = await execute_tool(
                "get_next_task",
                {"workspace_id": "ws_1"},
                user,
                MagicMock(),
            )

    assert result == {"tasks": [], "total": 0}
    task_query = cur.execute.call_args_list[0].args[0]
    assert "resolution_status" in task_query
    assert "answered_edges.relation = 'answered_by'" in task_query


# ─── log_mcp_interaction: node-level access → traversal_log (keep-alive) ───────
# ws_spec_plan/mem_ea840fad: retirement of the (Workspace Agent) node + telemetry
# edges. Only explicit-access tools (get_node/traverse/update_node) with a real
# actor_id feed traversal_log; search hits and create do not.

from fastapi import BackgroundTasks
from services.mcp_tools import log_mcp_interaction, record_traversal, log_mcp_query_internal


def _scheduled(bt):
    return [(t.func, t.args) for t in bt.tasks]


def test_log_mcp_interaction_keep_alive_tool_records_traversal():
    bt = BackgroundTasks()
    log_mcp_interaction(bt, "ws_1", "get_node", node_id="mem_1", actor_id="user_1")
    scheduled = _scheduled(bt)
    # analytics query log always scheduled
    assert any(func is log_mcp_query_internal for func, _ in scheduled)
    # node-level access recorded to traversal_log with the real actor_id
    assert (record_traversal, ("ws_1", "mem_1", "user_1")) in scheduled


def test_log_mcp_interaction_search_does_not_record_traversal():
    bt = BackgroundTasks()
    # search_nodes logs analytics only, with no node_id
    log_mcp_interaction(bt, "ws_1", "search_nodes", query_text="q", result_count=3)
    funcs = [func for func, _ in _scheduled(bt)]
    assert log_mcp_query_internal in funcs
    assert record_traversal not in funcs


def test_log_mcp_interaction_create_is_not_keep_alive():
    bt = BackgroundTasks()
    # create_node passes a node_id + actor but must NOT count as keep-alive
    log_mcp_interaction(bt, "ws_1", "create_node", node_id="mem_2", actor_id="user_1")
    funcs = [func for func, _ in _scheduled(bt)]
    assert record_traversal not in funcs


def test_log_mcp_interaction_requires_actor_id():
    bt = BackgroundTasks()
    # keep-alive tool but no actor_id → skip traversal write gracefully
    log_mcp_interaction(bt, "ws_1", "get_node", node_id="mem_1")
    funcs = [func for func, _ in _scheduled(bt)]
    assert record_traversal not in funcs

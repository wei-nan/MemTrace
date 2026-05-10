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
    args = {"workspace_id": "ws_1", "query": "test"}
    
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
            # Should have recorded interaction edges and logged query
            assert background_tasks.add_task.call_count >= 1

@pytest.mark.asyncio
async def test_execute_tool_create_node():
    user = {"sub": "user_1"}
    args = {"workspace_id": "ws_1", "title_en": "New Node", "body_en": "Content"}
    
    mock_node = {"id": "mem_new", "title_en": "New Node"}
    
    background_tasks = MagicMock()
    
    with patch("services.mcp_tools.create_node_full_with_dedup", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = (mock_node, None, None)
        with patch("services.mcp_tools.db_cursor"):
            with patch("services.mcp_tools.trigger_node_background_jobs") as mock_bg:
                res = await execute_tool("create_node", args, user, background_tasks)
                assert res["id"] == "mem_new"
                mock_bg.assert_called_once()

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

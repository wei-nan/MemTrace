import sys
import os
import pytest
from unittest.mock import MagicMock, patch, AsyncMock, ANY

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.mcp_tools import (
    resolve_profile_tools,
    dispatch,
    MCP_TOOL_PROFILES,
    TOOLS,
)

def test_resolve_profile_tools_default():
    # When no args and no env, it defaults to core+agent_loop
    with patch.dict(os.environ, {}, clear=True):
        tools = resolve_profile_tools()
        names = {t["name"] for t in tools}
        expected = MCP_TOOL_PROFILES["core"].union(MCP_TOOL_PROFILES["agent_loop"])
        assert names == expected
        assert len(tools) == 22


def test_resolve_profile_tools_env():
    # Respects MEMTRACE_MCP_TOOL_PROFILE env var
    with patch.dict(os.environ, {"MEMTRACE_MCP_TOOL_PROFILE": "ingest_docs"}):
        tools = resolve_profile_tools()
        names = {t["name"] for t in tools}
        assert names == MCP_TOOL_PROFILES["ingest_docs"]
        assert len(tools) == 10


def test_resolve_profile_tools_explicit():
    # Explicit arguments override env vars
    with patch.dict(os.environ, {"MEMTRACE_MCP_TOOL_PROFILE": "core"}):
        # Explicit full
        tools_full = resolve_profile_tools("full")
        assert len(tools_full) == len(TOOLS)

        # Explicit advanced_graph
        tools_graph = resolve_profile_tools("advanced_graph")
        names_graph = {t["name"] for t in tools_graph}
        assert names_graph == MCP_TOOL_PROFILES["advanced_graph"]

        # Multiple profiles combined with + or ,
        tools_multi = resolve_profile_tools("core+advanced_graph")
        names_multi = {t["name"] for t in tools_multi}
        assert names_multi == MCP_TOOL_PROFILES["core"].union(MCP_TOOL_PROFILES["advanced_graph"])


def test_resolve_profile_tools_invalid():
    # Unknown profiles raise ValueError
    with pytest.raises(ValueError) as excinfo:
        resolve_profile_tools("core+nonexistent")
    assert "Unknown MCP tool profile: 'nonexistent'" in str(excinfo.value)


@pytest.mark.asyncio
async def test_dispatch_with_profile_filtering():
    # Test tools/list filtering
    list_payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {}
    }
    user = {"sub": "u1"}
    
    # 1. With core profile
    res = await dispatch(list_payload, user, MagicMock(), tool_profile="core")
    assert "error" not in res
    tools = res["result"]["tools"]
    names = {t["name"] for t in tools}
    assert names == MCP_TOOL_PROFILES["core"]

    # 2. With core+agent_loop profile
    res = await dispatch(list_payload, user, MagicMock(), tool_profile="core+agent_loop")
    assert "error" not in res
    tools = res["result"]["tools"]
    names = {t["name"] for t in tools}
    assert names == MCP_TOOL_PROFILES["core"].union(MCP_TOOL_PROFILES["agent_loop"])


@pytest.mark.asyncio
async def test_dispatch_restrict_tool_call():
    user = {"sub": "u1"}
    
    # Try calling a tool that is not in the 'core' profile (e.g. get_next_task)
    call_payload = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "get_next_task",
            "arguments": {"workspace_id": "ws_1"}
        }
    }

    # Calling it with 'core' profile should fail with method not found
    res = await dispatch(call_payload, user, MagicMock(), tool_profile="core")
    assert "error" in res
    assert res["error"]["code"] == -32601
    assert "is not available in the active profile" in res["error"]["message"]

    # Calling it with 'agent_loop' profile should proceed to execute (mocked execution)
    with patch("services.mcp_tools.execute_tool", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = {"tasks": []}
        res = await dispatch(call_payload, user, MagicMock(), tool_profile="agent_loop")
        assert "error" not in res
        mock_exec.assert_called_once_with("get_next_task", {"workspace_id": "ws_1"}, user, ANY)


@pytest.mark.asyncio
async def test_dispatch_invalid_profile_error():
    # Dispatching with invalid profile should return JSON-RPC error -32602
    list_payload = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/list",
        "params": {}
    }
    user = {"sub": "u1"}
    res = await dispatch(list_payload, user, MagicMock(), tool_profile="invalid_profile_name")
    assert "error" in res
    assert res["error"]["code"] == -32602
    assert "Unknown MCP tool profile" in res["error"]["message"]

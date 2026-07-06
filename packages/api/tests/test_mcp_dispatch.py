import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from services.mcp_dispatch import UNHANDLED, dispatch_core_method


@pytest.mark.asyncio
async def test_initialize_records_client_capabilities():
    capabilities = {}
    result = await dispatch_core_method(
        {
            "id": 1,
            "method": "initialize",
            "params": {"capabilities": {"model_size": "large", "context_limit": 32000}},
        },
        {"sub": "user_1"},
        MagicMock(),
        tools=[],
        execute_tool=AsyncMock(),
        user_capabilities=capabilities,
        logger=MagicMock(),
    )

    assert result["result"]["serverInfo"]["name"] == "memtrace"
    assert capabilities["user_1"]["model_size"] == "large"
    assert capabilities["user_1"]["context_limit"] == 32000


@pytest.mark.asyncio
async def test_tools_call_serializes_domain_result():
    execute = AsyncMock(return_value={"created_at": "2026-06-19", "count": 2})
    result = await dispatch_core_method(
        {
            "id": 2,
            "method": "tools/call",
            "params": {"name": "list_workspaces", "arguments": {}},
        },
        {"sub": "user_1"},
        MagicMock(),
        tools=[{"name": "list_workspaces"}],
        execute_tool=execute,
        user_capabilities={},
        logger=MagicMock(),
    )

    content = json.loads(result["result"]["content"][0]["text"])
    assert content["count"] == 2
    execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_resource_method_is_left_for_resource_dispatch():
    result = await dispatch_core_method(
        {"id": 3, "method": "resources/read", "params": {}},
        {"sub": "user_1"},
        MagicMock(),
        tools=[],
        execute_tool=AsyncMock(),
        user_capabilities={},
        logger=MagicMock(),
    )

    assert result is UNHANDLED

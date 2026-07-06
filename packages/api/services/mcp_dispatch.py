"""JSON-RPC transport dispatch for MCP core methods."""
from __future__ import annotations

import dataclasses
import datetime
import decimal
import json
import uuid
from typing import Any, Awaitable, Callable

from core.constants import MCP_INSTRUCTIONS


UNHANDLED = object()


def _serialize(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
        return value.isoformat()
    if isinstance(value, (decimal.Decimal, uuid.UUID)):
        return str(value)
    if dataclasses.is_dataclass(value):
        return _serialize(dataclasses.asdict(value))
    if isinstance(value, dict):
        return {str(key): _serialize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_serialize(item) for item in value]
    return str(value)


def jsonrpc_ok(message_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": message_id, "result": result}


async def dispatch_core_method(
    payload: dict[str, Any],
    user: dict[str, Any],
    background_tasks: Any,
    *,
    tools: list[dict[str, Any]],
    execute_tool: Callable[[str, dict, dict, Any], Awaitable[Any]],
    user_capabilities: dict[str, dict[str, Any]],
    logger: Any,
) -> dict[str, Any] | object:
    """Handle initialize and tool methods, or return ``UNHANDLED``."""
    message_id = payload.get("id")
    method = payload.get("method")
    params = payload.get("params", {})

    if method == "initialize":
        user_sub = user.get("sub")
        if user_sub:
            capabilities = params.get("capabilities", {})
            user_capabilities[user_sub] = {
                "model_size": capabilities.get("model_size")
                or params.get("model_size")
                or "medium",
                "context_limit": capabilities.get("context_limit")
                or params.get("context_limit")
                or 8192,
                "prefer_format": capabilities.get("prefer_format")
                or params.get("prefer_format")
                or "json",
            }
        return jsonrpc_ok(
            message_id,
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}, "resources": {}},
                "serverInfo": {"name": "memtrace", "version": "1.0.0"},
                "instructions": MCP_INSTRUCTIONS,
            },
        )

    if method == "tools/list":
        return jsonrpc_ok(message_id, {"tools": tools})

    if method == "tools/call":
        tool_name = params.get("name")
        tool_args = params.get("arguments", {})
        logger.info("MCP tool call: %s", tool_name)
        allowed_tool_names = {t["name"] for t in tools}
        if tool_name not in allowed_tool_names:
            return {
                "jsonrpc": "2.0",
                "id": message_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: '{tool_name}' is not available in the active profile."
                }
            }
        result = await execute_tool(tool_name, tool_args, user, background_tasks)
        return jsonrpc_ok(
            message_id,
            {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            _serialize(result),
                            indent=2,
                            ensure_ascii=False,
                        ),
                    }
                ]
            },
        )

    return UNHANDLED

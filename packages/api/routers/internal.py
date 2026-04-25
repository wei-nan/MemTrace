from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from typing import Optional
from core.database import db_cursor
import os

router = APIRouter(prefix="/internal", tags=["Internal"])

INTERNAL_TOKEN = os.getenv("MEMTRACE_INTERNAL_TOKEN", "memtrace_internal_secret")

class McpLogRequest(BaseModel):
    workspace_id: str
    tool_name: str
    query_text: Optional[str] = None
    result_node_count: int
    estimated_tokens: int

@router.post("/mcp-log")
async def log_mcp_query(
    payload: McpLogRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Internal endpoint to log MCP tool usage for analytics.
    Requires a valid MEMTRACE_INTERNAL_TOKEN.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid internal token")
    
    token = authorization.replace("Bearer ", "")
    if token != INTERNAL_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden: Invalid internal token")

    with db_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO mcp_query_logs 
            (workspace_id, tool_name, query_text, result_node_count, estimated_tokens)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (payload.workspace_id, payload.tool_name, payload.query_text, payload.result_node_count, payload.estimated_tokens)
        )
    
    return {"status": "logged"}

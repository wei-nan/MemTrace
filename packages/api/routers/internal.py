from fastapi import APIRouter, Depends, Header, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from core.database import db_cursor
from core.security import generate_id
import os

router = APIRouter(prefix="/internal", tags=["Internal"])

INTERNAL_TOKEN = os.getenv("MEMTRACE_INTERNAL_TOKEN", "memtrace_internal_secret")

class McpLogRequest(BaseModel):
    id: Optional[str] = None
    workspace_id: str
    tool_name: str
    query_text: Optional[str] = None
    result_node_count: int
    estimated_tokens: int
    provider: Optional[str] = None

def _db_log_mcp(payload_dict: dict, log_id: str):
    with db_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO mcp_query_logs 
            (id, workspace_id, tool_name, query_text, result_node_count, estimated_tokens, provider)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                log_id,
                payload_dict["workspace_id"],
                payload_dict["tool_name"],
                payload_dict["query_text"],
                payload_dict["result_node_count"],
                payload_dict["estimated_tokens"],
                payload_dict["provider"]
            )
        )

@router.post("/mcp-log")
async def log_mcp_query(
    payload: McpLogRequest,
    background_tasks: BackgroundTasks,
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

    log_id = payload.id or generate_id("log")
    background_tasks.add_task(_db_log_mcp, payload.dict(), log_id)
    
    return {"status": "logged", "id": log_id}

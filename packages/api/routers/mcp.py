"""
MCP SSE Transport — Remote access to MemTrace knowledge graphs.

Protocol:
  GET  /sse          → SSE stream; first event tells client where to POST
  POST /messages     → JSON-RPC 2.0 messages; responses go back via SSE

Auth: Authorization: Bearer mt_<api_key>   (same key generated in WorkspaceSettings)

Claude Code config:
  {
    "mcpServers": {
      "memtrace": {
        "type": "sse",
        "url": "https://<your-host>/sse",
        "headers": { "Authorization": "Bearer mt_..." }
      }
    }
  }
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, BackgroundTasks
from fastapi.responses import StreamingResponse

from core.database import db_cursor
from core.deps import get_current_user

from services.workspaces import require_ws_access as _require_ws_access
from services.mcp_tools import TOOLS as _TOOLS, dispatch as _dispatch
from core.constants import SEARCH_MISS_DEDUP, VALID_RELATIONS, VALID_CONTENT_T

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/mcp", tags=["mcp"])

@router.get("/status")
async def mcp_status(user: dict = Depends(get_current_user)):
    """Return real-time MCP session status."""
    user_sub = user.get("sub")
    user_sessions = [
        {
            "session_id": sid,
            "created_at": s.get("created_at"),
            "last_accessed": s.get("last_accessed")
        }
        for sid, s in _sessions.items()
        if s.get("user_sub") == user_sub
    ]
    return {
        "active_sessions_total": len(_sessions),
        "user_sessions": user_sessions,
        "server_info": _SERVER_INFO
    }


# ── In-memory session map: session_id → dict ─────────────────────────
_sessions: Dict[str, dict] = {}

# ── MCP server metadata ────────────────────────────────────────────────────────
_SERVER_INFO = {
    "name":    "memtrace",
    "version": "1.0.0",
}
_PROTOCOL_VERSION = "2024-11-05"


# ═══════════════════════════════════════════════════════════════════════════════
# Tool definitions
# ═══════════════════════════════════════════════════════════════════════════════



# ═══════════════════════════════════════════════════════════════════════════════
# Tool execution
# ═══════════════════════════════════════════════════════════════════════════════




# SSE endpoint
# ═══════════════════════════════════════════════════════════════════════════════


import time


MAX_SESSIONS_PER_USER = 5
SESSION_TTL_SECONDS = 3600

@router.get("/sse")
async def mcp_sse(
    request: Request,
    user: dict = Depends(get_current_user),
):
    """
    MCP SSE stream endpoint.
    Sends an 'endpoint' event telling the client where to POST messages,
    then streams responses back as 'message' events.
    """
    user_sub = user.get("sub")
    
    # Prune expired sessions globally (optional but good practice)
    now = time.time()
    expired = [sid for sid, s in _sessions.items() if now - s.get("created_at", 0) > SESSION_TTL_SECONDS]
    for sid in expired:
        _sessions.pop(sid, None)
        
    # Enforce max sessions per user limit
    user_sessions = [sid for sid, s in _sessions.items() if s.get("user_sub") == user_sub]
    if len(user_sessions) >= MAX_SESSIONS_PER_USER:
        # Prune oldest session for this user
        oldest_sid = min(user_sessions, key=lambda sid: _sessions[sid].get("created_at", 0))
        _sessions.pop(oldest_sid, None)

    session_id = str(uuid.uuid4())
    queue: asyncio.Queue = asyncio.Queue()
    _sessions[session_id] = {
        "queue": queue,
        "user_sub": user_sub,
        "api_key_id": user.get("api_key_id"),
        "created_at": now,
        "last_accessed": now,
    }

    # Build the POST URL the client should use
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme
    host = request.headers.get("x-forwarded-host") or request.headers.get("host", "")
    base = f"{proto}://{host}"
    post_url = f"{base}/messages?sessionId={session_id}"

    async def event_stream():
        try:
            # 1 — Tell client where to POST
            yield f"event: endpoint\ndata: {json.dumps({'uri': post_url})}\n\n"

            # 2 — Relay responses from the queue
            while True:
                if await request.is_disconnected():
                    break
                try:
                    response = await asyncio.wait_for(queue.get(), timeout=20)
                    yield f"data: {json.dumps(response, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"   # keep connection alive
        finally:
            _sessions.pop(session_id, None)
            logger.debug("MCP session closed: %s", session_id)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":     "no-cache",
            "X-Accel-Buffering": "no",        # disable nginx buffering
            "Connection":        "keep-alive",
        },
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Message endpoint
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/messages")
async def mcp_messages(
    request: Request,
    sessionId: str = Query(...),
    user: dict = Depends(get_current_user),
    background_tasks: BackgroundTasks = None,
):
    """Receive a JSON-RPC 2.0 message and push the response to the SSE session."""
    session = _sessions.get(sessionId)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    
    if session.get("user_sub") != user.get("sub") or session.get("api_key_id") != user.get("api_key_id"):
        raise HTTPException(status_code=403, detail="Session owner mismatch")
        
    if time.time() - session.get("created_at", 0) > SESSION_TTL_SECONDS:
        _sessions.pop(sessionId, None)
        raise HTTPException(status_code=401, detail="Session expired")
        
    session["last_accessed"] = time.time()

    queue = session["queue"]

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    response = await _dispatch(body, user, background_tasks)
    await queue.put(response)
    return {"ok": True}

# ═══════════════════════════════════════════════════════════════════════════════
# Streamable HTTP transport (MCP spec 2025-03-26)
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/mcp")
async def mcp_streamable(
    request: Request,
    user: dict = Depends(get_current_user),
    background_tasks: BackgroundTasks = None,
):
    """
    Streamable HTTP transport — single POST endpoint for all JSON-RPC messages.
    Used by Cursor, Antigravity, and other modern MCP clients.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    response = await _dispatch(body, user, background_tasks)
    return response



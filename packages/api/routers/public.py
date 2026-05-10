from __future__ import annotations

import hashlib
import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from core.database import db_cursor
from core.auth import can_anonymous_view
from models.kb import (
    WorkspaceResponse,
    NodeResponse,
    EdgeResponse,
    GraphPreviewResponse
)

router = APIRouter(prefix="/public", tags=["public"])

_ANON_SALT = os.getenv("MEMTRACE_ANON_LOG_SALT", "")

def _hash_value(value: str) -> str:
    """Helper to hash IP/UA with a salt."""
    return hashlib.sha256(f"{value}{_ANON_SALT}".encode()).hexdigest()

def _log_access(request: Request, workspace_id: str, endpoint: str, node_id: Optional[str] = None):
    """Logic to insert a log record into anonymous_access_log."""
    # Ensure we don't log authenticated users in this table
    if hasattr(request.state, "user") and request.state.user and request.state.user.id != "anonymous":
        return

    ip = request.client.host if request.client else "unknown"
    ua = request.headers.get("user-agent", "unknown")
    
    with db_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO anonymous_access_log (workspace_id, node_id, ip_hash, user_agent_hash, endpoint)
            VALUES (%s, %s, %s, %s, %s)
        """, (workspace_id, node_id, _hash_value(ip), _hash_value(ua), endpoint))

async def _get_workspace_public(workspace_id: str):
    """Retrieve workspace and verify it is accessible to anonymous users."""
    from core.config import settings
    if not settings.allow_anonymous:
        raise HTTPException(status_code=404, detail="Not Found")

    with db_cursor() as cur:
        cur.execute("SELECT * FROM workspaces WHERE id = %s", (workspace_id,))
        ws = cur.fetchone()
    
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    if not can_anonymous_view(ws):
        raise HTTPException(
            status_code=403, 
            detail="This workspace is not public."
        )
    
    return ws

@router.get("/workspaces/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace_public(workspace_id: str, request: Request, background_tasks: BackgroundTasks):
    """Get basic workspace metadata for public display."""
    ws = await _get_workspace_public(workspace_id)
    background_tasks.add_task(_log_access, request, workspace_id, "metadata")
    return ws


@router.get("/workspaces/{workspace_id}/graph-preview", response_model=GraphPreviewResponse)
async def get_graph_preview_public(workspace_id: str, request: Request, background_tasks: BackgroundTasks):
    """Get nodes and edges for the initial graph visualization in visitor view."""
    await _get_workspace_public(workspace_id)
    background_tasks.add_task(_log_access, request, workspace_id, "graph")
    
    with db_cursor() as cur:
        # Fetch active nodes, excluding system agent nodes (source='mcp')
        cur.execute(
            """
            SELECT * FROM memory_nodes
            WHERE workspace_id = %s
              AND status = 'active'
              AND (visibility IS DISTINCT FROM 'private')
              AND (metadata->>'source' IS NULL OR metadata->>'source' <> 'mcp')
            LIMIT 1000
            """,
            (workspace_id,)
        )
        nodes = cur.fetchall()
        
        # Fetch edges
        cur.execute(
            "SELECT * FROM edges WHERE workspace_id = %s LIMIT 2000",
            (workspace_id,)
        )
        edges = cur.fetchall()
        
    return {
        "nodes": nodes,
        "edges": edges,
        "total_nodes": len(nodes),
        "total_edges": len(edges)
    }

@router.get("/workspaces/{workspace_id}/nodes/{node_id}", response_model=NodeResponse)
async def get_node_public(workspace_id: str, node_id: str, request: Request, background_tasks: BackgroundTasks):
    """Get detailed information for a single node in a public workspace."""
    await _get_workspace_public(workspace_id)
    background_tasks.add_task(_log_access, request, workspace_id, "node_detail", node_id)
    
    with db_cursor() as cur:
        cur.execute(
            """SELECT * FROM memory_nodes
               WHERE id = %s AND workspace_id = %s
                 AND status = 'active'
                 AND (visibility IS DISTINCT FROM 'private')""",
            (node_id, workspace_id)
        )
        node = cur.fetchone()
        
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    return node

@router.get("/workspaces/{workspace_id}/search", response_model=List[NodeResponse])
async def search_public(workspace_id: str, request: Request, background_tasks: BackgroundTasks, q: str = ""):
    """Basic text search for nodes in a public workspace."""
    if not q or len(q) < 2:
        return []
        
    await _get_workspace_public(workspace_id)
    background_tasks.add_task(_log_access, request, workspace_id, "search")
    
    # We use a simplified version of the search logic from kb.py
    filters = ["workspace_id = %s", "status = 'active'", "(visibility IS DISTINCT FROM 'private')"]
    params = [workspace_id]

    # Exclude system nodes
    filters.append("(metadata->>'source' IS NULL OR metadata->>'source' <> 'mcp')")
    
    from services.search import apply_text_search as _apply_text_search
    _apply_text_search(filters, params, q)
    
    query = f"SELECT * FROM memory_nodes WHERE {' AND '.join(filters)} ORDER BY created_at DESC LIMIT 50"
    
    with db_cursor() as cur:
        cur.execute(query, tuple(params))
        return cur.fetchall()

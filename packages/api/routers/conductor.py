"""Conductor hooks, inquiry scale, and async safety review controls."""
from __future__ import annotations

from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from core.database import db_cursor
from core.deps import get_current_user
from core.security import generate_id
from services.conductor import create_hook, list_deliveries, list_hooks, set_node_scale_in_db, update_hook
from services.safety_queue import enqueue_safety_review, list_safety_review_queue
from services.workspaces import require_ws_access

router = APIRouter(prefix="/api/v1", tags=["conductor"])


class NodeScaleUpdate(BaseModel):
    scale: Literal["minor", "major"]


class ConductorHookCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    url: str = Field(..., min_length=1, max_length=2000)
    secret: Optional[str] = Field(None, max_length=2000)
    enabled: bool = True
    event_filter: dict[str, Any] = Field(default_factory=dict)


class ConductorHookUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=120)
    url: Optional[str] = Field(None, min_length=1, max_length=2000)
    secret: Optional[str] = Field(None, max_length=2000)
    enabled: Optional[bool] = None
    event_filter: Optional[dict[str, Any]] = None


class SafetyReviewEnqueue(BaseModel):
    event_type: str = Field("manual", min_length=1, max_length=80)
    risk_hint: Optional[str] = Field(None, max_length=120)
    priority: int = Field(30, ge=1, le=100)


@router.patch("/workspaces/{ws_id}/nodes/{node_id}/scale")
def set_node_scale(
    ws_id: str,
    node_id: str,
    body: NodeScaleUpdate,
    user: dict = Depends(get_current_user),
):
    with db_cursor(commit=True) as cur:
        require_ws_access(cur, ws_id, user, write=True, required_role="editor")
        node = set_node_scale_in_db(cur, ws_id, node_id, body.scale)
    return {"node": node}


@router.get("/workspaces/{ws_id}/conductor/hooks")
def get_conductor_hooks(
    ws_id: str,
    user: dict = Depends(get_current_user),
):
    with db_cursor() as cur:
        require_ws_access(cur, ws_id, user, required_role="viewer")
        hooks = list_hooks(cur, ws_id)
    return {"hooks": hooks, "total": len(hooks)}


@router.post("/workspaces/{ws_id}/conductor/hooks", status_code=201)
def post_conductor_hook(
    ws_id: str,
    body: ConductorHookCreate,
    user: dict = Depends(get_current_user),
):
    with db_cursor(commit=True) as cur:
        require_ws_access(cur, ws_id, user, write=True, required_role="editor")
        hook = create_hook(cur, ws_id, body.model_dump())
    return {"hook": hook}


@router.patch("/workspaces/{ws_id}/conductor/hooks/{hook_id}")
def patch_conductor_hook(
    ws_id: str,
    hook_id: str,
    body: ConductorHookUpdate,
    user: dict = Depends(get_current_user),
):
    with db_cursor(commit=True) as cur:
        require_ws_access(cur, ws_id, user, write=True, required_role="editor")
        hook = update_hook(cur, ws_id, hook_id, body.model_dump(exclude_unset=True))
    return {"hook": hook}


@router.get("/workspaces/{ws_id}/conductor/deliveries")
def get_conductor_deliveries(
    ws_id: str,
    status: Optional[str] = Query(None, pattern="^(pending|delivered|failed|skipped)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: dict = Depends(get_current_user),
):
    with db_cursor() as cur:
        require_ws_access(cur, ws_id, user, required_role="viewer")
        deliveries = list_deliveries(cur, workspace_id=ws_id, status=status, limit=limit, offset=offset)
    return {"deliveries": deliveries, "total": len(deliveries), "offset": offset}


@router.get("/workspaces/{ws_id}/safety-review-queue")
def get_safety_review_queue(
    ws_id: str,
    status: Optional[str] = Query(None, pattern="^(queued|processing|done|failed|skipped)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: dict = Depends(get_current_user),
):
    with db_cursor() as cur:
        require_ws_access(cur, ws_id, user, required_role="viewer")
        items = list_safety_review_queue(cur, workspace_id=ws_id, status=status, limit=limit, offset=offset)
    return {"items": items, "total": len(items), "offset": offset}


@router.post("/workspaces/{ws_id}/nodes/{node_id}/safety-review", status_code=202)
def post_node_safety_review(
    ws_id: str,
    node_id: str,
    body: SafetyReviewEnqueue,
    user: dict = Depends(get_current_user),
):
    event_id = f"manual:{generate_id('safeevt')}"
    with db_cursor(commit=True) as cur:
        require_ws_access(cur, ws_id, user, write=True, required_role="editor")
        cur.execute(
            "SELECT 1 FROM memory_nodes WHERE id = %s AND workspace_id = %s",
            (node_id, ws_id),
        )
        if not cur.fetchone():
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Node not found")
        item = enqueue_safety_review(
            cur,
            workspace_id=ws_id,
            node_id=node_id,
            event_type=body.event_type,
            event_id=event_id,
            source="manual",
            risk_hint=body.risk_hint,
            priority=body.priority,
        )
    return {"queued": item is not None, "item": item}

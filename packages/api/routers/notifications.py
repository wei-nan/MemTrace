"""routers/notifications.py — in-app notification center endpoints (user-scoped)."""
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException

from core.deps import get_current_user
from core.database import db_cursor
from services.notifications import (
    list_notifications,
    unread_count,
    mark_notification_read,
    mark_all_read,
)

router = APIRouter(prefix="/api/v1", tags=["notifications"])


@router.get("/notifications")
def get_notifications(
    workspace_id: Optional[str] = Query(None),
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: dict = Depends(get_current_user),
):
    with db_cursor() as cur:
        items = list_notifications(
            cur, user["sub"],
            workspace_id=workspace_id, unread_only=unread_only, limit=limit, offset=offset,
        )
        count = unread_count(cur, user["sub"], workspace_id)
    return {"notifications": items, "unread_count": count, "offset": offset}


@router.get("/notifications/unread_count")
def get_unread_count(
    workspace_id: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
):
    with db_cursor() as cur:
        count = unread_count(cur, user["sub"], workspace_id)
    return {"unread_count": count}


@router.post("/notifications/{notification_id}/read")
def post_mark_read(notification_id: str, user: dict = Depends(get_current_user)):
    with db_cursor(commit=True) as cur:
        ok = mark_notification_read(cur, notification_id, user["sub"])
    if not ok:
        raise HTTPException(status_code=404, detail="Notification not found or already read")
    return {"status": "ok"}


@router.post("/notifications/read_all")
def post_mark_all_read(
    workspace_id: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
):
    with db_cursor(commit=True) as cur:
        n = mark_all_read(cur, user["sub"], workspace_id)
    return {"status": "ok", "updated": n}

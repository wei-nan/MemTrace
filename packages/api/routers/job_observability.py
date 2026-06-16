"""Read-only API for background job run history and scheduler heartbeats."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from core.database import db_cursor
from core.deps import get_current_user
from services.job_observability import list_job_runs, list_scheduler_heartbeats
from services.workspaces import require_ws_access

router = APIRouter(prefix="/api/v1", tags=["job-observability"])


@router.get("/workspaces/{ws_id}/job-runs")
def get_job_runs(
    ws_id: str,
    job_name: Optional[str] = None,
    status: Optional[str] = Query(None, pattern="^(running|success|failed|skipped)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: dict = Depends(get_current_user),
):
    with db_cursor() as cur:
        require_ws_access(cur, ws_id, user)
        runs = list_job_runs(
            cur,
            workspace_id=ws_id,
            job_name=job_name,
            status=status,
            limit=limit,
            offset=offset,
        )
    return {"runs": runs, "total": len(runs), "offset": offset}


@router.get("/workspaces/{ws_id}/scheduler-heartbeats")
def get_scheduler_heartbeats(
    ws_id: str,
    user: dict = Depends(get_current_user),
):
    with db_cursor() as cur:
        require_ws_access(cur, ws_id, user)
        heartbeats = list_scheduler_heartbeats(cur)
    return {"heartbeats": heartbeats, "total": len(heartbeats)}

import os
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from core.backup import (
    get_backup_config,
    run_backup_and_update_status,
    set_backup_config,
    validate_path,
)
from core.deps import require_system_admin
from core.database import db_cursor

router = APIRouter(prefix="/api/v1/system", tags=["admin"])


class BackupConfig(BaseModel):
    enabled: bool
    path: str
    interval_hours: int
    keep_count: int
    last_backup_at: Optional[str] = None
    last_backup_file: Optional[str] = None
    last_backup_status: Optional[str] = None


class BackupConfigUpdate(BaseModel):
    enabled: Optional[bool] = None
    path: Optional[str] = None
    interval_hours: Optional[int] = None
    keep_count: Optional[int] = None


@router.get("/backup-config", response_model=BackupConfig)
def get_backup_config_endpoint(user: dict = Depends(require_system_admin)):
    return get_backup_config()


@router.patch("/backup-config", response_model=BackupConfig)
def update_backup_config_endpoint(
    data: BackupConfigUpdate,
    user: dict = Depends(require_system_admin),
):
    updates = data.model_dump(exclude_none=True)
    if "path" in updates:
        try:
            validate_path(updates["path"])
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
    if "interval_hours" in updates and updates["interval_hours"] < 1:
        raise HTTPException(status_code=400, detail="interval_hours must be >= 1")
    if "keep_count" in updates and updates["keep_count"] < 1:
        raise HTTPException(status_code=400, detail="keep_count must be >= 1")
    return set_backup_config(updates)


@router.post("/backup/run", status_code=202)
def trigger_backup(
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_system_admin),
):
    config = get_backup_config()
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        raise HTTPException(status_code=503, detail="DATABASE_URL not configured")
    background_tasks.add_task(
        run_backup_and_update_status,
        config["path"],
        db_url,
        config.get("keep_count", 7),
    )
    return {"message": "Backup started"}


@router.get("/registrations")
def list_registrations(status: Optional[str] = "pending", user: dict = Depends(require_system_admin)):
    with db_cursor() as cur:
        query = "SELECT id, email, status, purpose_note, admin_note, reviewed_by, reviewed_at, created_at FROM user_registrations"
        params = []
        if status:
            query += " WHERE status = %s"
            params.append(status)
        query += " ORDER BY created_at DESC"
        cur.execute(query, tuple(params))
        return cur.fetchall()


@router.post("/registrations/{reg_id}/approve")
def approve_registration(reg_id: str, user: dict = Depends(require_system_admin)):
    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE user_registrations SET status = 'approved', reviewed_by = %s, reviewed_at = now() WHERE id = %s", (user["sub"], reg_id))
    return {"message": "Approved"}


@router.post("/registrations/{reg_id}/reject")
def reject_registration(reg_id: str, user: dict = Depends(require_system_admin)):
    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE user_registrations SET status = 'rejected', reviewed_by = %s, reviewed_at = now() WHERE id = %s", (user["sub"], reg_id))
    return {"message": "Rejected"}

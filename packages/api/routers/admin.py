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
from core.deps import get_current_user

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
def get_backup_config_endpoint(user: dict = Depends(get_current_user)):
    return get_backup_config()


@router.patch("/backup-config", response_model=BackupConfig)
def update_backup_config_endpoint(
    data: BackupConfigUpdate,
    user: dict = Depends(get_current_user),
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
    user: dict = Depends(get_current_user),
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

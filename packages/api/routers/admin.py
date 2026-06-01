import os
from typing import Optional, Literal

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
from services.ai_config import upsert_user_ai_key, delete_user_ai_key

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


class PromoteDemoteRequest(BaseModel):
    user_id: str


@router.post("/promote", status_code=200)
def promote_user(data: PromoteDemoteRequest, user: dict = Depends(require_system_admin)):
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT id FROM users WHERE id = %s", (data.user_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="User not found")
        cur.execute("UPDATE users SET is_platform_admin = TRUE WHERE id = %s", (data.user_id,))
    return {"message": f"User {data.user_id} promoted to platform admin"}


@router.post("/demote", status_code=200)
def demote_user(data: PromoteDemoteRequest, user: dict = Depends(require_system_admin)):
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT id FROM users WHERE id = %s", (data.user_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="User not found")
        cur.execute("UPDATE users SET is_platform_admin = FALSE WHERE id = %s", (data.user_id,))
    return {"message": f"User {data.user_id} demoted"}


# ── System AI Key Management ──────────────────────────────────────────────────

# target: "system" = shared keys for all users; "safety" = safety-review-only key
VALID_AI_TARGETS = {"system", "safety"}
TARGET_USER_MAP = {"system": "system", "safety": "system:safety"}

VALID_PROVIDERS = {"openai", "anthropic", "gemini", "ollama"}


class SystemAIKeyUpsert(BaseModel):
    target: Literal["system", "safety"]
    provider: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    auth_mode: str = "none"
    auth_token: Optional[str] = None
    default_chat_model: Optional[str] = None
    default_embedding_model: Optional[str] = None


class SystemAIKeyResponse(BaseModel):
    target: str
    provider: str
    key_hint: str
    base_url: Optional[str] = None
    auth_mode: Optional[str] = None
    default_chat_model: Optional[str] = None
    default_embedding_model: Optional[str] = None
    last_used_at: Optional[str] = None


@router.get("/ai-keys", response_model=list[SystemAIKeyResponse])
def list_system_ai_keys(user: dict = Depends(require_system_admin)):
    """List all system-level and safety AI keys."""
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT
                CASE WHEN user_id = 'system:safety' THEN 'safety' ELSE 'system' END AS target,
                provider, key_hint, base_url, auth_mode,
                default_chat_model, default_embedding_model, last_used_at
            FROM user_ai_keys
            WHERE user_id IN ('system', 'system:safety')
            ORDER BY user_id, provider
            """,
        )
        return [dict(r) for r in cur.fetchall()]


@router.post("/ai-keys", response_model=SystemAIKeyResponse, status_code=201)
def upsert_system_ai_key(body: SystemAIKeyUpsert, user: dict = Depends(require_system_admin)):
    """Create or update a system-level or safety AI key."""
    if body.provider not in VALID_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown provider '{body.provider}'")
    target_user = TARGET_USER_MAP[body.target]

    with db_cursor(commit=True) as cur:
        # Ensure the virtual system user exists
        cur.execute("SELECT id FROM users WHERE id = %s", (target_user,))
        if not cur.fetchone():
            label = "System Safety" if body.target == "safety" else "System"
            email = f"{body.target}@memtrace.local"
            cur.execute(
                "INSERT INTO users (id, display_name, email, email_verified) VALUES (%s, %s, %s, true)",
                (target_user, label, email),
            )
        row = upsert_user_ai_key(
            cur,
            user_id=target_user,
            provider=body.provider,
            api_key=body.api_key,
            base_url=body.base_url,
            auth_mode=body.auth_mode,
            auth_token=body.auth_token,
            default_chat_model=body.default_chat_model,
            default_embedding_model=body.default_embedding_model,
        )

    return {**row, "target": body.target}


@router.delete("/ai-keys/{target}/{provider}", status_code=204)
def delete_system_ai_key(
    target: str,
    provider: str,
    user: dict = Depends(require_system_admin),
):
    """Delete a system-level or safety AI key."""
    if target not in VALID_AI_TARGETS:
        raise HTTPException(status_code=400, detail="Invalid target")
    target_user = TARGET_USER_MAP[target]
    with db_cursor(commit=True) as cur:
        delete_user_ai_key(cur, target_user, provider)


@router.patch("/ai-keys/{target}/{provider}/model", status_code=200)
def update_system_ai_key_model(
    target: str,
    provider: str,
    body: dict,
    user: dict = Depends(require_system_admin),
):
    """Update only the default model fields for a system key (no re-entering the API key)."""
    if target not in VALID_AI_TARGETS:
        raise HTTPException(status_code=400, detail="Invalid target")
    target_user = TARGET_USER_MAP[target]
    allowed = {"default_chat_model", "default_embedding_model"}
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    set_clause = ", ".join(f"{k} = %s" for k in updates)
    with db_cursor(commit=True) as cur:
        cur.execute(
            f"UPDATE user_ai_keys SET {set_clause} WHERE user_id = %s AND provider = %s",
            (*updates.values(), target_user, provider),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Key not found")
    return {"message": "Updated"}

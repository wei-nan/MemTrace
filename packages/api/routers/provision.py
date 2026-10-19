"""
Provisioner keys: let an external harness create knowledge bases for its owner.

The owner signs in (a human session, not an API key) and creates a provisioner
key, stores it in the harness's secret store, and can revoke it at any time. The
harness calls POST /provision/workspaces with that key. The server creates a
workspace owned by the owner and mints a kb:write service token bound to it, in
one transaction, and returns the token once. The conversation layer never sees
the token, and neither does the owner.

A provisioner key can do nothing else: core.deps.get_current_user refuses it on
every other route, including /mcp. The token it mints is an ordinary workspace
service token (kb:write), which cannot mint keys or create workspaces.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from core.database import db_cursor
from core.deps import get_current_user
from core.security import generate_id

router = APIRouter(tags=["provisioning"])

MAX_PROVISIONER_DAYS = 90
MAX_PROVISIONED_WORKSPACES = 10
PROVISIONED_TOKEN_SCOPES = ["kb:write"]


def _new_key() -> tuple[str, str, str]:
    raw = "mt_" + secrets.token_hex(20)
    return raw, hashlib.sha256(raw.encode()).hexdigest(), raw[:8]


def _require_human_session(user: dict) -> dict:
    """Provisioner keys are issued by a signed-in person, never by another key."""
    if user.get("api_key_id"):
        raise HTTPException(
            status_code=403,
            detail={"error": "human_session_required", "message": "Sign in to manage provisioner keys; API keys cannot"},
        )
    return user


def _human_session(user: dict = Depends(get_current_user)) -> dict:
    return _require_human_session(user)


class ProvisionerKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    expires_in_days: int = Field(MAX_PROVISIONER_DAYS, ge=1, le=MAX_PROVISIONER_DAYS)
    max_workspaces: int = Field(MAX_PROVISIONED_WORKSPACES, ge=1, le=MAX_PROVISIONED_WORKSPACES)


class ProvisionerKeyResponse(BaseModel):
    id: str
    name: str
    prefix: str
    created_at: datetime
    expires_at: datetime
    max_workspaces: int
    last_used_at: Optional[datetime] = None
    workspaces_created: int = 0


class ProvisionerKeyCreateResponse(ProvisionerKeyResponse):
    key: str  # one-time plaintext


@router.post("/users/me/provisioner-keys", response_model=ProvisionerKeyCreateResponse, status_code=201)
def create_provisioner_key(data: ProvisionerKeyCreate, user: dict = Depends(_human_session)):
    raw, key_hash, prefix = _new_key()
    key_id = generate_id("apikey")
    with db_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO api_keys (id, user_id, name, key_hash, prefix, key_type, max_workspaces, expires_at)
            VALUES (%s, %s, %s, %s, %s, 'provisioner', %s, now() + make_interval(days => %s))
            RETURNING created_at, expires_at
            """,
            (key_id, user["sub"], data.name, key_hash, prefix, data.max_workspaces, data.expires_in_days),
        )
        row = cur.fetchone()
    return {
        "id": key_id, "name": data.name, "prefix": prefix, "created_at": row["created_at"],
        "expires_at": row["expires_at"], "max_workspaces": data.max_workspaces,
        "workspaces_created": 0, "key": raw,
    }


@router.get("/users/me/provisioner-keys", response_model=List[ProvisionerKeyResponse])
def list_provisioner_keys(user: dict = Depends(_human_session)):
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT k.id, k.name, k.prefix, k.created_at, k.expires_at, k.max_workspaces, k.last_used_at,
                   (SELECT count(*) FROM workspaces w WHERE w.provisioned_by_key_id = k.id) AS workspaces_created
            FROM api_keys k
            WHERE k.user_id = %s AND k.key_type = 'provisioner' AND k.revoked_at IS NULL
            ORDER BY k.created_at DESC
            """,
            (user["sub"],),
        )
        return cur.fetchall()


@router.delete("/users/me/provisioner-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_provisioner_key(key_id: str, user: dict = Depends(_human_session)):
    """Stops the key from provisioning more. Service tokens it already minted keep working;
    revoke those separately from the workspace's API keys."""
    with db_cursor(commit=True) as cur:
        cur.execute(
            """
            UPDATE api_keys SET revoked_at = now()
            WHERE id = %s AND user_id = %s AND key_type = 'provisioner' AND revoked_at IS NULL
            """,
            (key_id, user["sub"]),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Provisioner key not found")


class ProvisionWorkspace(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    language: Literal["zh-TW", "en"]
    description: Optional[str] = Field(None, max_length=2000)
    token_name: str = Field("harness", min_length=1, max_length=100)
    token_expires_in_days: Optional[int] = Field(None, ge=1, le=365)


class ProvisionedToken(BaseModel):
    id: str
    key: str  # one-time plaintext; the harness stores it, nobody else should see it
    prefix: str
    scopes: List[str]
    expires_at: Optional[datetime] = None


class ProvisionedWorkspace(BaseModel):
    workspace_id: str
    name: str
    language: str
    service_token: ProvisionedToken


@router.post("/provision/workspaces", response_model=ProvisionedWorkspace, status_code=201)
def provision_workspace(body: ProvisionWorkspace, user: dict = Depends(get_current_user)):
    """Create a knowledge base for the key's owner and mint a kb:write token bound to it.

    All or nothing: if any step fails, neither the workspace nor the token exists.
    """
    if user.get("key_type") != "provisioner":
        raise HTTPException(
            status_code=403,
            detail={"error": "provisioner_key_required", "message": "This endpoint needs a provisioner key"},
        )

    # Imported here to keep this module's import graph light for the auth path.
    from models.kb import WorkspaceCreate
    from services.mcp_tools import _MCP_INGEST_DAILY_QUOTA_DEFAULT
    from services.workspaces import create_workspace_in_db

    raw, key_hash, prefix = _new_key()
    token_id = generate_id("apikey")

    with db_cursor(commit=True) as cur:
        # Lock the key row: concurrent provisioning calls queue here, so the quota
        # below cannot be overrun by two requests racing.
        cur.execute(
            """
            SELECT user_id, max_workspaces FROM api_keys
            WHERE id = %s AND key_type = 'provisioner' AND revoked_at IS NULL
              AND (expires_at IS NULL OR expires_at > now())
            FOR UPDATE
            """,
            (user["api_key_id"],),
        )
        key = cur.fetchone()
        if not key:
            raise HTTPException(status_code=401, detail="Invalid or revoked API key")

        cur.execute("SELECT count(*) AS n FROM workspaces WHERE provisioned_by_key_id = %s", (user["api_key_id"],))
        if cur.fetchone()["n"] >= key["max_workspaces"]:
            raise HTTPException(
                status_code=403,
                detail={"error": "quota_exceeded", "max_workspaces": key["max_workspaces"]},
            )

        # Same defaults as the MCP create_workspace tool: private, manual-review Q&A archive,
        # MCP ingestion on. The harness's token cannot change qa_archive_mode afterwards.
        ws_body = WorkspaceCreate(
            name=body.name, description=body.description, language=body.language,
            visibility="private", kb_type="evergreen",
        ).model_dump()
        ws_body["qa_archive_mode"] = "manual_review"
        ws_body["auto_split"] = False
        ws_body["settings"] = {"mcp_ingest_enabled": True, "mcp_ingest_daily_quota": _MCP_INGEST_DAILY_QUOTA_DEFAULT}
        ws = create_workspace_in_db(cur, key["user_id"], ws_body)

        cur.execute("UPDATE workspaces SET provisioned_by_key_id = %s WHERE id = %s", (user["api_key_id"], ws["id"]))
        cur.execute(
            """
            INSERT INTO api_keys (id, user_id, name, key_hash, prefix, scopes, workspace_id, key_type,
                                  parent_key_id, expires_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'service', %s,
                    CASE WHEN %s::int IS NULL THEN NULL ELSE now() + make_interval(days => %s::int) END)
            RETURNING expires_at
            """,
            (token_id, key["user_id"], body.token_name, key_hash, prefix, PROVISIONED_TOKEN_SCOPES, ws["id"],
             user["api_key_id"], body.token_expires_in_days, body.token_expires_in_days),
        )
        token_row = cur.fetchone()

    return {
        "workspace_id": ws["id"],
        "name": ws["name"],
        "language": ws["language"],
        "service_token": {
            "id": token_id, "key": raw, "prefix": prefix,
            "scopes": PROVISIONED_TOKEN_SCOPES, "expires_at": token_row["expires_at"],
        },
    }

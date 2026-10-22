"""
Provisioner keys: let an external harness create (and manage) knowledge bases for its owner.

The owner signs in (a human session, not an API key) and creates a provisioner
key, stores it in the harness's secret store, and can revoke it at any time. The
harness calls POST /provision/workspaces with that key. The server creates a
workspace owned by the owner and mints a kb:write service token bound to it, in
one transaction, and returns the token once. The conversation layer never sees
the token, and neither does the owner.

A provisioner key can do nothing outside /api/v1/provision/*: core.deps.get_current_user
refuses it on every other route, including /mcp. The token it mints is an ordinary
workspace service token (kb:write), which cannot mint keys or create workspaces.

What a provisioner key may do, always and only to workspaces IT created:
  POST   /provision/workspaces               create one (Idempotency-Key makes retries safe)
  GET    /provision/workspaces               list them / look one up by Idempotency-Key
  GET    /provision/quota                    how many more it may create
  DELETE /provision/workspaces/{id}/token    revoke the tokens it minted for one
  DELETE /provision/workspaces/{id}          delete one (only if the owner enabled it for this key)
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import secrets
from datetime import datetime
from typing import List, Literal, Optional

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query, Response, status
from pydantic import BaseModel, Field, StrictBool, StrictInt, field_validator

from core.config import settings
from core.database import db_cursor
from core.deps import get_current_user
from core.security import generate_id

logger = logging.getLogger(__name__)

router = APIRouter(tags=["provisioning"])

MAX_PROVISIONER_DAYS = 90
PROVISIONED_TOKEN_SCOPES = ["kb:write"]
_IDEMPOTENCY_KEY = re.compile(r"^[A-Za-z0-9._:\-]{1,128}$")


def _cap() -> int:
    """The deployment's ceiling for one provisioner key's workspace count."""
    return max(1, int(settings.max_provisioned_workspaces))


def _new_key() -> tuple[str, str, str]:
    raw = "mt_" + secrets.token_hex(20)
    return raw, hashlib.sha256(raw.encode()).hexdigest(), raw[:8]


def _clean_text(value: Optional[str], *, allow_empty: bool = False) -> Optional[str]:
    if value is None:
        return None
    if "\x00" in value:
        raise ValueError("must not contain NUL characters")
    value = value.strip()
    if not value and not allow_empty:
        raise ValueError("must not be empty")
    return value


# ─── authorization helpers ───────────────────────────────────────────────────

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


def _provisioner(user: dict = Depends(get_current_user)) -> dict:
    if user.get("key_type") != "provisioner":
        raise HTTPException(
            status_code=403,
            detail={"error": "provisioner_key_required", "message": "This endpoint needs a provisioner key"},
        )
    return user


def _lock_key(cur, key_id: str) -> dict:
    """The provisioner key's row, locked: concurrent calls with the same key queue here, so a quota
    or an Idempotency-Key cannot be raced. 401 if it was revoked or expired in the meantime."""
    cur.execute(
        """
        SELECT user_id, max_workspaces, can_delete_workspaces, expires_at FROM api_keys
        WHERE id = %s AND key_type = 'provisioner' AND revoked_at IS NULL
          AND (expires_at IS NULL OR expires_at > now())
        FOR UPDATE
        """,
        (key_id,),
    )
    key = cur.fetchone()
    if not key:
        raise HTTPException(status_code=401, detail="Invalid or revoked API key")
    return key


def _effective_cap(key: dict) -> int:
    return min(int(key["max_workspaces"]), _cap())


def _own_workspace(cur, key_id: str, workspace_id: str) -> dict:
    cur.execute(
        "SELECT id, name FROM workspaces WHERE id = %s AND provisioned_by_key_id = %s",
        (workspace_id, key_id),
    )
    ws = cur.fetchone()
    if not ws:
        # The same answer for "does not exist" and "belongs to someone else".
        raise HTTPException(status_code=404, detail="Workspace not found")
    return ws


# ─── managing provisioner keys (a signed-in person) ──────────────────────────

class ProvisionerKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    expires_in_days: StrictInt = Field(MAX_PROVISIONER_DAYS, ge=1, le=MAX_PROVISIONER_DAYS)
    max_workspaces: Optional[StrictInt] = Field(None, ge=1)
    can_delete_workspaces: StrictBool = False

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        return _clean_text(v)  # type: ignore[return-value]


class ProvisionerKeyResponse(BaseModel):
    id: str
    name: str
    prefix: str
    created_at: datetime
    expires_at: datetime
    max_workspaces: int
    can_delete_workspaces: bool = False
    last_used_at: Optional[datetime] = None
    workspaces_created: int = 0


class ProvisionerKeyCreateResponse(ProvisionerKeyResponse):
    key: str  # one-time plaintext


@router.post("/users/me/provisioner-keys", response_model=ProvisionerKeyCreateResponse, status_code=201)
def create_provisioner_key(data: ProvisionerKeyCreate, user: dict = Depends(_human_session)):
    cap = _cap()
    max_workspaces = data.max_workspaces if data.max_workspaces is not None else cap
    if max_workspaces > cap:
        raise HTTPException(status_code=422, detail={"error": "max_workspaces_too_large", "max": cap})
    raw, key_hash, prefix = _new_key()
    key_id = generate_id("apikey")
    with db_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO api_keys (id, user_id, name, key_hash, prefix, key_type, max_workspaces,
                                  can_delete_workspaces, expires_at)
            VALUES (%s, %s, %s, %s, %s, 'provisioner', %s, %s, now() + make_interval(days => %s))
            RETURNING created_at, expires_at
            """,
            (key_id, user["sub"], data.name, key_hash, prefix, max_workspaces, data.can_delete_workspaces,
             data.expires_in_days),
        )
        row = cur.fetchone()
    return {
        "id": key_id, "name": data.name, "prefix": prefix, "created_at": row["created_at"],
        "expires_at": row["expires_at"], "max_workspaces": max_workspaces,
        "can_delete_workspaces": data.can_delete_workspaces, "workspaces_created": 0, "key": raw,
    }


@router.get("/users/me/provisioner-keys", response_model=List[ProvisionerKeyResponse])
def list_provisioner_keys(user: dict = Depends(_human_session)):
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT k.id, k.name, k.prefix, k.created_at, k.expires_at, k.max_workspaces,
                   k.can_delete_workspaces, k.last_used_at,
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


# ─── what a provisioner key does ─────────────────────────────────────────────

class ProvisionWorkspace(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    language: Literal["zh-TW", "en"]
    description: Optional[str] = Field(None, max_length=2000)
    token_name: str = Field("harness", min_length=1, max_length=100)
    token_expires_in_days: Optional[StrictInt] = Field(None, ge=1, le=365)

    @field_validator("name", "token_name")
    @classmethod
    def _required_text(cls, v: str) -> str:
        return _clean_text(v)  # type: ignore[return-value]

    @field_validator("description")
    @classmethod
    def _optional_text(cls, v: Optional[str]) -> Optional[str]:
        return _clean_text(v, allow_empty=True)


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
    idempotent_replay: bool = False


def _fingerprint(body: ProvisionWorkspace) -> str:
    """What an Idempotency-Key is bound to. The token options are deliberately left out: a replay
    mints a fresh token with whatever options the retry asks for."""
    canonical = json.dumps(
        {"name": body.name, "language": body.language, "description": body.description or ""},
        sort_keys=True, ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def _mint_token(cur, *, owner_id: str, workspace_id: str, provisioner_id: str, body: ProvisionWorkspace) -> dict:
    raw, key_hash, prefix = _new_key()
    token_id = generate_id("apikey")
    cur.execute(
        """
        INSERT INTO api_keys (id, user_id, name, key_hash, prefix, scopes, workspace_id, key_type,
                              parent_key_id, expires_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'service', %s,
                CASE WHEN %s::int IS NULL THEN NULL ELSE now() + make_interval(days => %s::int) END)
        RETURNING expires_at
        """,
        (token_id, owner_id, body.token_name, key_hash, prefix, PROVISIONED_TOKEN_SCOPES, workspace_id,
         provisioner_id, body.token_expires_in_days, body.token_expires_in_days),
    )
    row = cur.fetchone()
    return {"id": token_id, "key": raw, "prefix": prefix, "scopes": PROVISIONED_TOKEN_SCOPES,
            "expires_at": row["expires_at"]}


def _revoke_minted_tokens(cur, provisioner_id: str, workspace_id: str) -> int:
    cur.execute(
        """
        UPDATE api_keys SET revoked_at = now()
        WHERE parent_key_id = %s AND workspace_id = %s AND key_type = 'service' AND revoked_at IS NULL
        """,
        (provisioner_id, workspace_id),
    )
    return cur.rowcount


@router.post("/provision/workspaces", response_model=ProvisionedWorkspace, status_code=201)
def provision_workspace(
    body: ProvisionWorkspace,
    response: Response,
    idempotency_key: Optional[str] = Header(None),
    user: dict = Depends(_provisioner),
):
    """Create a knowledge base for the key's owner and mint a kb:write token bound to it.

    All or nothing: if any step fails, neither the workspace nor the token exists.

    With an Idempotency-Key, a retry of the same request returns the workspace it already created
    (200, idempotent_replay=true) with a freshly minted token, and revokes the tokens minted before:
    the server never stores a token, so a lost response cannot be replayed, only replaced.
    """
    if idempotency_key is not None and not _IDEMPOTENCY_KEY.match(idempotency_key):
        raise HTTPException(
            status_code=422,
            detail={"error": "invalid_idempotency_key", "message": "1-128 characters from A-Z a-z 0-9 . _ : -"},
        )

    # Imported here to keep this module's import graph light for the auth path.
    from models.kb import WorkspaceCreate
    from services.mcp_tools import _MCP_INGEST_DAILY_QUOTA_DEFAULT
    from services.workspaces import create_workspace_in_db

    fingerprint = _fingerprint(body)
    provisioner_id = user["api_key_id"]

    with db_cursor(commit=True) as cur:
        key = _lock_key(cur, provisioner_id)

        if idempotency_key is not None:
            cur.execute(
                """
                SELECT id, name, language, provision_request_hash FROM workspaces
                WHERE provisioned_by_key_id = %s AND provision_request_id = %s
                """,
                (provisioner_id, idempotency_key),
            )
            existing = cur.fetchone()
            if existing:
                if existing["provision_request_hash"] != fingerprint:
                    raise HTTPException(
                        status_code=409,
                        detail={"error": "idempotency_conflict",
                                "message": "This Idempotency-Key was used for a different request"},
                    )
                _revoke_minted_tokens(cur, provisioner_id, existing["id"])
                token = _mint_token(cur, owner_id=key["user_id"], workspace_id=existing["id"],
                                    provisioner_id=provisioner_id, body=body)
                response.status_code = 200
                return {"workspace_id": existing["id"], "name": existing["name"], "language": existing["language"],
                        "service_token": token, "idempotent_replay": True}

        cur.execute("SELECT count(*) AS n FROM workspaces WHERE provisioned_by_key_id = %s", (provisioner_id,))
        cap = _effective_cap(key)
        if cur.fetchone()["n"] >= cap:
            raise HTTPException(status_code=403, detail={"error": "quota_exceeded", "max_workspaces": cap})

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

        cur.execute(
            """
            UPDATE workspaces SET provisioned_by_key_id = %s, provision_request_id = %s, provision_request_hash = %s
            WHERE id = %s
            """,
            (provisioner_id, idempotency_key, fingerprint if idempotency_key is not None else None, ws["id"]),
        )
        token = _mint_token(cur, owner_id=key["user_id"], workspace_id=ws["id"],
                            provisioner_id=provisioner_id, body=body)

    return {"workspace_id": ws["id"], "name": ws["name"], "language": ws["language"], "service_token": token}


class ProvisionQuota(BaseModel):
    max_workspaces: int
    workspaces_created: int
    remaining: int
    expires_at: datetime


@router.get("/provision/quota", response_model=ProvisionQuota)
def provision_quota(user: dict = Depends(_provisioner)):
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT max_workspaces, expires_at FROM api_keys
            WHERE id = %s AND key_type = 'provisioner' AND revoked_at IS NULL
              AND (expires_at IS NULL OR expires_at > now())
            """,
            (user["api_key_id"],),
        )
        key = cur.fetchone()
        if not key:
            raise HTTPException(status_code=401, detail="Invalid or revoked API key")
        cur.execute("SELECT count(*) AS n FROM workspaces WHERE provisioned_by_key_id = %s", (user["api_key_id"],))
        created = cur.fetchone()["n"]
    cap = _effective_cap(key)
    return {"max_workspaces": cap, "workspaces_created": created, "remaining": max(0, cap - created),
            "expires_at": key["expires_at"]}


class ProvisionedWorkspaceToken(BaseModel):
    id: str
    prefix: str
    expires_at: Optional[datetime] = None


class ProvisionedWorkspaceInfo(BaseModel):
    workspace_id: str
    name: str
    language: str
    idempotency_key: Optional[str] = None
    created_at: datetime
    token: Optional[ProvisionedWorkspaceToken] = None  # the newest unrevoked token, never its plaintext


@router.get("/provision/workspaces", response_model=List[ProvisionedWorkspaceInfo])
def list_provisioned_workspaces(
    idempotency_key: Optional[str] = Query(None, max_length=128),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: dict = Depends(_provisioner),
):
    """The workspaces this key created, oldest first; filter by Idempotency-Key to look one up."""
    params: list = [user["api_key_id"], user["api_key_id"]]
    where = ""
    if idempotency_key is not None:
        where = "AND w.provision_request_id = %s"
        params.append(idempotency_key)
    params += [limit, offset]
    with db_cursor() as cur:
        cur.execute(
            f"""
            SELECT w.id AS workspace_id, w.name, w.language, w.provision_request_id AS idempotency_key,
                   w.created_at, t.id AS token_id, t.prefix AS token_prefix, t.expires_at AS token_expires_at
            FROM workspaces w
            LEFT JOIN LATERAL (
                SELECT id, prefix, expires_at FROM api_keys
                WHERE parent_key_id = %s AND workspace_id = w.id AND key_type = 'service' AND revoked_at IS NULL
                ORDER BY created_at DESC LIMIT 1
            ) t ON true
            WHERE w.provisioned_by_key_id = %s {where}
            ORDER BY w.created_at, w.id
            LIMIT %s OFFSET %s
            """,
            params,
        )
        rows = cur.fetchall()
    return [
        {
            "workspace_id": r["workspace_id"], "name": r["name"], "language": r["language"],
            "idempotency_key": r["idempotency_key"], "created_at": r["created_at"],
            "token": ({"id": r["token_id"], "prefix": r["token_prefix"], "expires_at": r["token_expires_at"]}
                      if r["token_id"] else None),
        }
        for r in rows
    ]


@router.delete("/provision/workspaces/{workspace_id}/token", status_code=status.HTTP_204_NO_CONTENT)
def revoke_workspace_token(workspace_id: str, user: dict = Depends(_provisioner)):
    """Revoke every token this key minted for one of its workspaces (disabling the harness).
    Repeating it is harmless; a workspace this key did not create is a 404."""
    with db_cursor(commit=True) as cur:
        _lock_key(cur, user["api_key_id"])
        _own_workspace(cur, user["api_key_id"], workspace_id)
        _revoke_minted_tokens(cur, user["api_key_id"], workspace_id)


class DeleteWorkspace(BaseModel):
    confirm_name: str


@router.delete("/provision/workspaces/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_provisioned_workspace(workspace_id: str, body: DeleteWorkspace = Body(...), user: dict = Depends(_provisioner)):
    """Delete a workspace this key created, with its nodes and service tokens. Three guards:
    the owner enabled deletion for this key, its minted tokens were revoked first, and the request
    names the workspace as it is called now."""
    with db_cursor(commit=True) as cur:
        key = _lock_key(cur, user["api_key_id"])
        if not key["can_delete_workspaces"]:
            raise HTTPException(
                status_code=403,
                detail={"error": "deletion_not_allowed",
                        "message": "The owner has not enabled workspace deletion for this provisioner key"},
            )
        ws = _own_workspace(cur, user["api_key_id"], workspace_id)
        if body.confirm_name != ws["name"]:
            raise HTTPException(status_code=409, detail={"error": "confirmation_mismatch"})
        cur.execute(
            """
            SELECT count(*) AS n FROM api_keys
            WHERE parent_key_id = %s AND workspace_id = %s AND key_type = 'service' AND revoked_at IS NULL
            """,
            (user["api_key_id"], workspace_id),
        )
        if cur.fetchone()["n"]:
            raise HTTPException(
                status_code=409,
                detail={"error": "tokens_still_active", "message": "Revoke the workspace's tokens first"},
            )
        cur.execute("DELETE FROM api_keys WHERE workspace_id = %s", (workspace_id,))
        cur.execute("DELETE FROM workspaces WHERE id = %s", (workspace_id,))
    logger.info("provisioner key %s deleted workspace %s", user["api_key_id"], workspace_id)

import secrets
import hashlib
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from core.database import db_cursor
from core.security import generate_id
from core.deps import get_current_user

router = APIRouter(tags=["api-keys"])

class ApiKeyCreate(BaseModel):
    name: str
    scopes: List[str]
    workspace_id: Optional[str] = None

class ApiKeyResponse(BaseModel):
    id: str
    name: str
    prefix: str
    scopes: List[str]
    workspace_id: Optional[str] = None
    created_at: datetime
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

class ApiKeyCreateResponse(ApiKeyResponse):
    key: str  # The one-time plaintext key

@router.post("/users/me/api-keys", response_model=ApiKeyCreateResponse)
def create_api_key(
    data: ApiKeyCreate,
    current_user: dict = Depends(get_current_user)
):
    raw_key = "mt_" + secrets.token_hex(20)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    prefix = raw_key[:8]
    key_id = generate_id("apikey")
    
    with db_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO api_keys (id, user_id, name, key_hash, prefix, scopes, workspace_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING created_at
            """,
            (key_id, current_user["sub"], data.name, key_hash, prefix, data.scopes, data.workspace_id)
        )
        row = cur.fetchone()
        
    return {
        "id": key_id,
        "name": data.name,
        "prefix": prefix,
        "scopes": data.scopes,
        "workspace_id": data.workspace_id,
        "created_at": row["created_at"],
        "key": raw_key
    }

@router.get("/users/me/api-keys", response_model=List[ApiKeyResponse])
def list_api_keys(
    current_user: dict = Depends(get_current_user)
):
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT id, name, prefix, scopes, workspace_id, created_at, last_used_at, expires_at
            FROM api_keys
            WHERE user_id = %s
            ORDER BY created_at DESC
            """,
            (current_user["sub"],)
        )
        return cur.fetchall()

@router.delete("/users/me/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_api_key(
    key_id: str,
    current_user: dict = Depends(get_current_user)
):
    with db_cursor(commit=True) as cur:
        cur.execute(
            "DELETE FROM api_keys WHERE id = %s AND user_id = %s",
            (key_id, current_user["sub"])
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="API key not found")


class RotateApiKeyResponse(ApiKeyCreateResponse):
    pass


@router.post("/users/me/api-keys/{key_id}/rotate", response_model=RotateApiKeyResponse)
def rotate_api_key(
    key_id: str,
    current_user: dict = Depends(get_current_user)
):
    """G3: Rotate an API key — revoke the old one and generate a new key with the same scopes."""
    with db_cursor(commit=True) as cur:
        cur.execute(
            "SELECT id, name, scopes, workspace_id FROM api_keys WHERE id = %s AND user_id = %s",
            (key_id, current_user["sub"])
        )
        old_key = cur.fetchone()
        if not old_key:
            raise HTTPException(status_code=404, detail="API key not found")

        # Revoke old key
        cur.execute(
            "DELETE FROM api_keys WHERE id = %s",
            (key_id,)
        )

        # Generate new key with the same name, scopes, workspace
        raw_key = "mt_" + secrets.token_hex(20)
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        prefix = raw_key[:8]
        new_id = generate_id("apikey")

        cur.execute(
            """
            INSERT INTO api_keys (id, user_id, name, key_hash, prefix, scopes, workspace_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING created_at
            """,
            (new_id, current_user["sub"], old_key["name"], key_hash, prefix, old_key["scopes"], old_key["workspace_id"])
        )
        row = cur.fetchone()

    return {
        "id": new_id,
        "name": old_key["name"],
        "prefix": prefix,
        "scopes": old_key["scopes"],
        "workspace_id": old_key["workspace_id"],
        "created_at": row["created_at"],
        "key": raw_key,
    }


# ── Workspace-specific API Keys ─────────────────────────────────────────────

@router.get("/workspaces/{ws_id}/api-keys", response_model=List[ApiKeyResponse])
def list_workspace_api_keys(
    ws_id: str,
    current_user: dict = Depends(get_current_user)
):
    with db_cursor() as cur:
        # Check ownership
        cur.execute("SELECT owner_id FROM workspaces WHERE id = %s", (ws_id,))
        ws = cur.fetchone()
        if not ws:
            raise HTTPException(status_code=404, detail="Workspace not found")
        if ws["owner_id"] != current_user["sub"]:
            raise HTTPException(status_code=403, detail="Only workspace owner can manage service tokens")

        cur.execute(
            """
            SELECT id, name, prefix, scopes, workspace_id, created_at, last_used_at, expires_at
            FROM api_keys
            WHERE workspace_id = %s
            ORDER BY created_at DESC
            """,
            (ws_id,)
        )
        return cur.fetchall()


@router.post("/workspaces/{ws_id}/api-keys", response_model=ApiKeyCreateResponse)
def create_workspace_api_key(
    ws_id: str,
    data: ApiKeyCreate,
    current_user: dict = Depends(get_current_user)
):
    with db_cursor(commit=True) as cur:
        # Check ownership
        cur.execute("SELECT owner_id FROM workspaces WHERE id = %s", (ws_id,))
        ws = cur.fetchone()
        if not ws:
            raise HTTPException(status_code=404, detail="Workspace not found")
        if ws["owner_id"] != current_user["sub"]:
            raise HTTPException(status_code=403, detail="Only workspace owner can manage service tokens")

        raw_key = "mt_" + secrets.token_hex(20)
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        prefix = raw_key[:8]
        key_id = generate_id("apikey")
        
        cur.execute(
            """
            INSERT INTO api_keys (id, user_id, name, key_hash, prefix, scopes, workspace_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING created_at
            """,
            (key_id, current_user["sub"], data.name, key_hash, prefix, data.scopes, ws_id)
        )
        row = cur.fetchone()
        
    return {
        "id": key_id,
        "name": data.name,
        "prefix": prefix,
        "scopes": data.scopes,
        "workspace_id": ws_id,
        "created_at": row["created_at"],
        "key": raw_key
    }


@router.post("/workspaces/{ws_id}/api-keys/{key_id}/rotate", response_model=RotateApiKeyResponse)
def rotate_workspace_api_key(
    ws_id: str,
    key_id: str,
    current_user: dict = Depends(get_current_user)
):
    with db_cursor(commit=True) as cur:
        # Check workspace ownership
        cur.execute("SELECT owner_id FROM workspaces WHERE id = %s", (ws_id,))
        ws = cur.fetchone()
        if not ws:
            raise HTTPException(status_code=404, detail="Workspace not found")
        if ws["owner_id"] != current_user["sub"]:
            raise HTTPException(status_code=403, detail="Only workspace owner can manage service tokens")

        cur.execute(
            "SELECT id, name, scopes, workspace_id FROM api_keys WHERE id = %s AND workspace_id = %s",
            (key_id, ws_id)
        )
        old_key = cur.fetchone()
        if not old_key:
            raise HTTPException(status_code=404, detail="API key not found")

        # Revoke old key
        cur.execute(
            "DELETE FROM api_keys WHERE id = %s",
            (key_id,)
        )

        # Generate new key
        raw_key = "mt_" + secrets.token_hex(20)
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        prefix = raw_key[:8]
        new_id = generate_id("apikey")

        cur.execute(
            """
            INSERT INTO api_keys (id, user_id, name, key_hash, prefix, scopes, workspace_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING created_at
            """,
            (new_id, current_user["sub"], old_key["name"], key_hash, prefix, old_key["scopes"], ws_id)
        )
        row = cur.fetchone()

    return {
        "id": new_id,
        "name": old_key["name"],
        "prefix": prefix,
        "scopes": old_key["scopes"],
        "workspace_id": ws_id,
        "created_at": row["created_at"],
        "key": raw_key,
    }


@router.delete("/workspaces/{ws_id}/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_workspace_api_key(
    ws_id: str,
    key_id: str,
    current_user: dict = Depends(get_current_user)
):
    with db_cursor(commit=True) as cur:
        # Check workspace ownership
        cur.execute("SELECT owner_id FROM workspaces WHERE id = %s", (ws_id,))
        ws = cur.fetchone()
        if not ws:
            raise HTTPException(status_code=404, detail="Workspace not found")
        if ws["owner_id"] != current_user["sub"]:
            raise HTTPException(status_code=403, detail="Only workspace owner can manage service tokens")

        cur.execute(
            "DELETE FROM api_keys WHERE id = %s AND workspace_id = %s",
            (key_id, ws_id)
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="API key not found")


@router.get("/resolved-models")
def get_resolved_models(type: str = "chat", user: dict = Depends(get_current_user)):
    """Return the currently resolved provider and model for a user's task type."""
    from core.ai import resolve_provider, AIProviderUnavailable
    try:
        resolved = resolve_provider(user["sub"], type)
        return {
            "provider": resolved.provider,
            "model":    resolved.model,
        }
    except AIProviderUnavailable:
        return {
            "provider": "openai",
            "model":    "gpt-4o-mini" if type == "chat" else "text-embedding-3-small",
        }

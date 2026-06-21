"""Personal connector accounts and explicit workspace bindings."""
from __future__ import annotations

from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field

from core.database import db_cursor
from core.deps import get_current_user
from services.connectors import (
    create_connector_account,
    create_connector_binding,
    delete_connector_binding,
    get_owned_connector_account,
    list_connector_accounts,
    list_connector_bindings,
    list_connector_runs,
    record_connector_event,
    revoke_connector_account,
    update_connector_binding,
)
from services.connector_framework import registry
from services.workspaces import require_ws_access

router = APIRouter(prefix="/api/v1", tags=["connectors"])


@router.get("/connectors/providers")
def get_connector_providers(user: dict = Depends(get_current_user)):
    del user
    return [provider.to_dict() for provider in registry.list()]


class ConnectorAccountCreate(BaseModel):
    provider: Literal["google_drive", "asana", "github", "gitlab"]
    provider_account_id: str = Field(..., min_length=1, max_length=500)
    provider_instance_url: str = Field("", max_length=2000)
    display_name: Optional[str] = Field(None, max_length=200)
    auth_type: Literal["oauth", "token", "app"] = "oauth"
    credential: Optional[str] = Field(None, min_length=1, max_length=10000)
    scopes: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConnectorBindingCreate(BaseModel):
    connector_account_id: str
    external_container_type: str = Field(..., min_length=1, max_length=100)
    external_container_id: str = Field(..., min_length=1, max_length=1000)
    external_container_name: Optional[str] = Field(None, max_length=500)
    sync_direction: Literal["inbound", "outbound", "bidirectional"] = "inbound"
    permissions: dict[str, Any] = Field(default_factory=dict)
    event_filters: dict[str, Any] = Field(default_factory=dict)


class ConnectorBindingUpdate(BaseModel):
    enabled: Optional[bool] = None
    sync_direction: Optional[Literal["inbound", "outbound", "bidirectional"]] = None
    permissions: Optional[dict[str, Any]] = None
    event_filters: Optional[dict[str, Any]] = None


class ConnectorEventCreate(BaseModel):
    provider_event_id: str = Field(..., min_length=1, max_length=1000)
    event_type: str = Field(..., min_length=1, max_length=200)
    binding_id: Optional[str] = None
    payload: dict[str, Any] = Field(default_factory=dict)


@router.get("/users/me/connector-accounts")
def get_connector_accounts(user: dict = Depends(get_current_user)):
    with db_cursor() as cur:
        return list_connector_accounts(cur, user["sub"])


@router.post("/users/me/connector-accounts", status_code=201)
def post_connector_account(
    body: ConnectorAccountCreate,
    user: dict = Depends(get_current_user),
):
    with db_cursor(commit=True) as cur:
        return create_connector_account(
            cur,
            owner_user_id=user["sub"],
            **body.model_dump(),
        )


@router.delete("/users/me/connector-accounts/{account_id}")
def delete_connector_account(
    account_id: str,
    user: dict = Depends(get_current_user),
):
    with db_cursor(commit=True) as cur:
        return revoke_connector_account(cur, account_id, user["sub"])


@router.get("/workspaces/{ws_id}/connector-bindings")
def get_connector_bindings(
    ws_id: str,
    user: dict = Depends(get_current_user),
):
    with db_cursor() as cur:
        require_ws_access(cur, ws_id, user, required_role="viewer")
        return list_connector_bindings(cur, ws_id)


@router.post("/workspaces/{ws_id}/connector-bindings", status_code=201)
def post_connector_binding(
    ws_id: str,
    body: ConnectorBindingCreate,
    user: dict = Depends(get_current_user),
):
    with db_cursor(commit=True) as cur:
        require_ws_access(cur, ws_id, user, write=True, required_role="editor")
        return create_connector_binding(
            cur,
            owner_user_id=user["sub"],
            workspace_id=ws_id,
            **body.model_dump(),
        )


@router.patch("/workspaces/{ws_id}/connector-bindings/{binding_id}")
def patch_connector_binding(
    ws_id: str,
    binding_id: str,
    body: ConnectorBindingUpdate,
    user: dict = Depends(get_current_user),
):
    with db_cursor(commit=True) as cur:
        require_ws_access(cur, ws_id, user, write=True, required_role="editor")
        return update_connector_binding(
            cur,
            workspace_id=ws_id,
            binding_id=binding_id,
            **body.model_dump(),
        )


@router.delete(
    "/workspaces/{ws_id}/connector-bindings/{binding_id}",
    status_code=204,
)
def remove_connector_binding(
    ws_id: str,
    binding_id: str,
    user: dict = Depends(get_current_user),
):
    with db_cursor(commit=True) as cur:
        require_ws_access(cur, ws_id, user, write=True, required_role="editor")
        delete_connector_binding(cur, ws_id, binding_id)
    return Response(status_code=204)


@router.get("/workspaces/{ws_id}/connector-runs")
def get_connector_runs(
    ws_id: str,
    limit: int = 50,
    user: dict = Depends(get_current_user),
):
    with db_cursor() as cur:
        require_ws_access(cur, ws_id, user, required_role="viewer")
        return list_connector_runs(cur, ws_id, min(max(limit, 1), 200))


@router.post("/users/me/connector-accounts/{account_id}/events")
def post_connector_event(
    account_id: str,
    body: ConnectorEventCreate,
    user: dict = Depends(get_current_user),
):
    with db_cursor(commit=True) as cur:
        get_owned_connector_account(cur, account_id, user["sub"])
        event, created = record_connector_event(
            cur,
            connector_account_id=account_id,
            **body.model_dump(),
        )
    return {"event": event, "created": created}

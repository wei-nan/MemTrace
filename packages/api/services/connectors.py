"""Persistence services for personal connector accounts and workspace bindings."""
from __future__ import annotations

import json
from typing import Any, Optional

from fastapi import HTTPException

from core.credentials import encrypt_secret
from core.security import generate_id
from services.connector_framework import registry


def _json(value: Optional[dict[str, Any]]) -> str:
    return json.dumps(value or {})


def list_connector_accounts(cur, owner_user_id: str) -> list[dict[str, Any]]:
    cur.execute(
        """
        SELECT id, owner_user_id, provider, provider_instance_url,
               provider_account_id, display_name, auth_type, scopes,
               status, metadata, created_at, updated_at
        FROM connector_accounts
        WHERE owner_user_id = %s
        ORDER BY provider, display_name NULLS LAST, created_at
        """,
        (owner_user_id,),
    )
    return [dict(row) for row in cur.fetchall()]


def get_owned_connector_account(cur, account_id: str, owner_user_id: str) -> dict[str, Any]:
    cur.execute(
        """
        SELECT *
        FROM connector_accounts
        WHERE id = %s AND owner_user_id = %s
        """,
        (account_id, owner_user_id),
    )
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Connector account not found")
    return dict(row)


def create_connector_account(
    cur,
    *,
    owner_user_id: str,
    provider: str,
    provider_account_id: str,
    provider_instance_url: str = "",
    display_name: Optional[str] = None,
    auth_type: str = "oauth",
    credential: Optional[str] = None,
    scopes: Optional[list[str]] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    registry.validate(provider, auth_type=auth_type)
    account_id = generate_id("connacct")
    cur.execute(
        """
        INSERT INTO connector_accounts (
            id, owner_user_id, provider, provider_instance_url,
            provider_account_id, display_name, auth_type,
            credentials_enc, scopes, metadata
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id, owner_user_id, provider, provider_instance_url,
                  provider_account_id, display_name, auth_type, scopes,
                  status, metadata, created_at, updated_at
        """,
        (
            account_id,
            owner_user_id,
            provider,
            provider_instance_url,
            provider_account_id,
            display_name,
            auth_type,
            encrypt_secret(credential) if credential else None,
            scopes or [],
            _json(metadata),
        ),
    )
    return dict(cur.fetchone())


def revoke_connector_account(cur, account_id: str, owner_user_id: str) -> dict[str, Any]:
    get_owned_connector_account(cur, account_id, owner_user_id)
    cur.execute(
        """
        UPDATE connector_accounts
        SET status = 'revoked', credentials_enc = NULL, updated_at = now()
        WHERE id = %s
        RETURNING id, status, updated_at
        """,
        (account_id,),
    )
    return dict(cur.fetchone())


def list_connector_bindings(cur, workspace_id: str) -> list[dict[str, Any]]:
    cur.execute(
        """
        SELECT b.*, a.provider, a.provider_instance_url,
               a.provider_account_id, a.display_name AS account_display_name,
               a.status AS account_status
        FROM connector_bindings b
        JOIN connector_accounts a ON a.id = b.connector_account_id
        WHERE b.workspace_id = %s
        ORDER BY a.provider, b.external_container_name NULLS LAST, b.created_at
        """,
        (workspace_id,),
    )
    return [dict(row) for row in cur.fetchall()]


def create_connector_binding(
    cur,
    *,
    owner_user_id: str,
    workspace_id: str,
    connector_account_id: str,
    external_container_type: str,
    external_container_id: str,
    external_container_name: Optional[str] = None,
    sync_direction: str = "inbound",
    permissions: Optional[dict[str, Any]] = None,
    event_filters: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    account = get_owned_connector_account(cur, connector_account_id, owner_user_id)
    if account["status"] != "active":
        raise HTTPException(status_code=409, detail="Connector account is not active")
    registry.validate(
        account["provider"],
        container_type=external_container_type,
        sync_direction=sync_direction,
    )

    binding_id = generate_id("connbind")
    cur.execute(
        """
        INSERT INTO connector_bindings (
            id, connector_account_id, workspace_id,
            external_container_type, external_container_id,
            external_container_name, sync_direction,
            permissions, event_filters, created_by
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING *
        """,
        (
            binding_id,
            connector_account_id,
            workspace_id,
            external_container_type,
            external_container_id,
            external_container_name,
            sync_direction,
            _json(permissions),
            _json(event_filters),
            owner_user_id,
        ),
    )
    return dict(cur.fetchone())


def update_connector_binding(
    cur,
    *,
    workspace_id: str,
    binding_id: str,
    enabled: Optional[bool] = None,
    sync_direction: Optional[str] = None,
    permissions: Optional[dict[str, Any]] = None,
    event_filters: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    updates: list[str] = []
    params: list[Any] = []
    for column, value in (
        ("enabled", enabled),
        ("sync_direction", sync_direction),
        ("permissions", _json(permissions) if permissions is not None else None),
        ("event_filters", _json(event_filters) if event_filters is not None else None),
    ):
        if value is not None:
            updates.append(f"{column} = %s")
            params.append(value)
    if not updates:
        raise HTTPException(status_code=422, detail="No connector binding changes supplied")
    params.extend([binding_id, workspace_id])
    cur.execute(
        f"""
        UPDATE connector_bindings
        SET {", ".join(updates)}, updated_at = now()
        WHERE id = %s AND workspace_id = %s
        RETURNING *
        """,
        params,
    )
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Connector binding not found")
    return dict(row)


def delete_connector_binding(cur, workspace_id: str, binding_id: str) -> None:
    cur.execute(
        "DELETE FROM connector_bindings WHERE id = %s AND workspace_id = %s",
        (binding_id, workspace_id),
    )
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Connector binding not found")


def record_connector_event(
    cur,
    *,
    connector_account_id: str,
    provider_event_id: str,
    event_type: str,
    payload: Optional[dict[str, Any]] = None,
    binding_id: Optional[str] = None,
) -> tuple[dict[str, Any], bool]:
    event_id = generate_id("connevt")
    cur.execute(
        """
        INSERT INTO connector_events (
            id, connector_account_id, binding_id,
            provider_event_id, event_type, payload
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (connector_account_id, provider_event_id) DO NOTHING
        RETURNING *
        """,
        (
            event_id,
            connector_account_id,
            binding_id,
            provider_event_id,
            event_type,
            _json(payload),
        ),
    )
    row = cur.fetchone()
    if row:
        return dict(row), True
    cur.execute(
        """
        SELECT *
        FROM connector_events
        WHERE connector_account_id = %s AND provider_event_id = %s
        """,
        (connector_account_id, provider_event_id),
    )
    return dict(cur.fetchone()), False


def list_connector_runs(cur, workspace_id: str, limit: int = 50) -> list[dict[str, Any]]:
    cur.execute(
        """
        SELECT r.*, b.workspace_id, a.provider
        FROM connector_runs r
        JOIN connector_bindings b ON b.id = r.binding_id
        JOIN connector_accounts a ON a.id = b.connector_account_id
        WHERE b.workspace_id = %s
        ORDER BY r.started_at DESC
        LIMIT %s
        """,
        (workspace_id, limit),
    )
    return [dict(row) for row in cur.fetchall()]

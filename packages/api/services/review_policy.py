"""Business logic for Workspace review policies, model bindings, and safe revocation."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import HTTPException

from core.database import db_cursor
from core.security import generate_id


def _json(val: Any) -> str:
    return json.dumps(val or {})


def get_review_policy(cur, workspace_id: str) -> dict[str, Any]:
    """Retrieve the review policy for a workspace. Auto-inserts a default if missing."""
    cur.execute(
        """
        SELECT * FROM workspace_review_policies WHERE workspace_id = %s
        """,
        (workspace_id,),
    )
    row = cur.fetchone()
    if row:
        return dict(row)

    # Insert default manual_only policy
    cur.execute(
        """
        INSERT INTO workspace_review_policies (
            workspace_id, inherit_system_default, mode, minimum_success, accept_rule, reject_rule, policy_version
        ) VALUES (%s, TRUE, 'manual_only', 1, '{}', '{}', 1)
        RETURNING *
        """,
        (workspace_id,),
    )
    return dict(cur.fetchone())


def update_review_policy(
    cur,
    workspace_id: str,
    *,
    mode: str,
    inherit_system_default: Optional[bool] = None,
    minimum_success: Optional[int] = None,
    accept_rule: Optional[dict[str, Any]] = None,
    reject_rule: Optional[dict[str, Any]] = None,
    updated_by: Optional[str] = None,
) -> dict[str, Any]:
    """Update review policy and increment policy_version."""
    old_policy = get_review_policy(cur, workspace_id)
    updates: list[str] = ["policy_version = policy_version + 1", "updated_at = now()"]
    params: list[Any] = []

    if mode not in ("manual_only", "fallback_advisory", "panel_advisory", "consensus_automatic"):
        raise HTTPException(status_code=400, detail="Invalid review policy mode")

    updates.append("mode = %s")
    params.append(mode)

    if inherit_system_default is not None:
        updates.append("inherit_system_default = %s")
        params.append(inherit_system_default)

    if minimum_success is not None:
        updates.append("minimum_success = %s")
        params.append(minimum_success)

    if accept_rule is not None:
        updates.append("accept_rule = %s")
        params.append(_json(accept_rule))

    if reject_rule is not None:
        updates.append("reject_rule = %s")
        params.append(_json(reject_rule))

    if updated_by is not None:
        updates.append("updated_by = %s")
        params.append(updated_by)

    params.append(workspace_id)
    cur.execute(
        f"""
        UPDATE workspace_review_policies
        SET {", ".join(updates)}
        WHERE workspace_id = %s
        RETURNING *
        """,
        params,
    )
    return dict(cur.fetchone())


def list_workspace_model_bindings(cur, workspace_id: str) -> list[dict[str, Any]]:
    """List all reviewer model bindings for a workspace, including credential details."""
    cur.execute(
        """
        SELECT b.*, k.provider, k.default_chat_model AS model, k.key_hint, u.display_name AS offered_by_name
        FROM workspace_model_bindings b
        JOIN user_ai_keys k ON k.id = b.model_account_id
        JOIN users u ON u.id = b.offered_by
        WHERE b.workspace_id = %s
        ORDER BY b.priority DESC, b.created_at
        """,
        (workspace_id,),
    )
    return [dict(row) for row in cur.fetchall()]


def create_workspace_model_binding(
    cur,
    *,
    workspace_id: str,
    model_account_id: str,
    offered_by: str,
    allowed_usages: list[str],
    priority: int = 0,
) -> dict[str, Any]:
    """Create a new model binding between a user key and a workspace."""
    # Check that key exists
    cur.execute("SELECT * FROM user_ai_keys WHERE id = %s", (model_account_id,))
    key = cur.fetchone()
    if not key:
        raise HTTPException(status_code=404, detail="AI key not found")

    # Determine source scope and billing
    source_scope = "system" if key["user_id"] == "system" else "user"
    billing_owner = key["user_id"]

    # Check if owner
    cur.execute("SELECT owner_id FROM workspaces WHERE id = %s", (workspace_id,))
    ws = cur.fetchone()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    is_ws_owner = ws["owner_id"] == offered_by

    # Consent and approval status
    consent_status = "approved" if offered_by == billing_owner else "pending"
    approval_status = "approved" if is_ws_owner else "pending"
    status = "active" if (consent_status == "approved" and approval_status == "approved") else "offered"

    binding_id = generate_id("wsmb")
    cur.execute(
        """
        INSERT INTO workspace_model_bindings (
            id, workspace_id, model_account_id, source_scope, offered_by,
            allowed_usages, billing_owner, consent_status, approval_status,
            status, priority
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING *
        """,
        (
            binding_id,
            workspace_id,
            model_account_id,
            source_scope,
            offered_by,
            allowed_usages,
            billing_owner,
            consent_status,
            approval_status,
            status,
            priority,
        ),
    )
    return dict(cur.fetchone())


def update_workspace_model_binding(
    cur,
    workspace_id: str,
    binding_id: str,
    *,
    status: Optional[str] = None,
    priority: Optional[int] = None,
    allowed_usages: Optional[list[str]] = None,
    approval_user_id: Optional[str] = None,
) -> dict[str, Any]:
    """Update a model binding's settings or approve/consent state."""
    cur.execute(
        "SELECT * FROM workspace_model_bindings WHERE id = %s AND workspace_id = %s",
        (binding_id, workspace_id),
    )
    binding = cur.fetchone()
    if not binding:
        raise HTTPException(status_code=404, detail="Model binding not found")

    updates = ["updated_at = now()"]
    params: list[Any] = []

    cur.execute("SELECT owner_id FROM workspaces WHERE id = %s", (workspace_id,))
    ws = cur.fetchone()
    is_ws_owner = approval_user_id == ws["owner_id"] if ws else False
    is_billing_owner = approval_user_id == binding["billing_owner"]

    next_consent = binding["consent_status"]
    next_approval = binding["approval_status"]

    if approval_user_id:
        if is_ws_owner:
            next_approval = "approved"
            updates.append("approval_status = 'approved'")
        if is_billing_owner:
            next_consent = "approved"
            updates.append("consent_status = 'approved'")

    # Calculate status update if consent/approval changes
    if status is not None:
        updates.append("status = %s")
        params.append(status)
        if status == "revoked":
            updates.append("revoked_at = now()")
            # Discard any active review attempts
            cur.execute(
                """
                UPDATE review_attempts
                SET status = 'discarded_after_revocation', finished_at = now()
                WHERE binding_id = %s AND status IN ('queued', 'running')
                """,
                (binding_id,),
            )
    elif approval_user_id:
        if next_consent == "approved" and next_approval == "approved" and binding["status"] == "offered":
            updates.append("status = 'active'")

    if priority is not None:
        updates.append("priority = %s")
        params.append(priority)

    if allowed_usages is not None:
        updates.append("allowed_usages = %s")
        params.append(allowed_usages)

    params.append(binding_id)
    cur.execute(
        f"""
        UPDATE workspace_model_bindings
        SET {", ".join(updates)}
        WHERE id = %s
        RETURNING *
        """,
        params,
    )
    return dict(cur.fetchone())


def revoke_workspace_model_binding(cur, workspace_id: str, binding_id: str, user_id: str) -> dict[str, Any]:
    """Explicitly revoke a model binding by its owner or workspace owner."""
    cur.execute(
        "SELECT * FROM workspace_model_bindings WHERE id = %s AND workspace_id = %s",
        (binding_id, workspace_id),
    )
    binding = cur.fetchone()
    if not binding:
        raise HTTPException(status_code=404, detail="Model binding not found")

    cur.execute("SELECT owner_id FROM workspaces WHERE id = %s", (workspace_id,))
    ws = cur.fetchone()
    is_ws_owner = user_id == ws["owner_id"] if ws else False
    is_billing_owner = user_id == binding["billing_owner"]

    if not (is_ws_owner or is_billing_owner):
        raise HTTPException(status_code=403, detail="Not authorized to revoke this binding")

    return update_workspace_model_binding(cur, workspace_id, binding_id, status="revoked")


def revoke_user_model_bindings(cur, user_id: str, provider: str) -> None:
    """Invoked when a user deletes/revokes their AI key. Mark all bindings as revoked."""
    # Find all bindings pointing to user_id's key for provider
    cur.execute(
        """
        SELECT b.id, b.workspace_id FROM workspace_model_bindings b
        JOIN user_ai_keys k ON k.id = b.model_account_id
        WHERE k.user_id = %s AND k.provider = %s AND b.status <> 'revoked'
        """,
        (user_id, provider),
    )
    bindings = cur.fetchall()
    for binding in bindings:
        update_workspace_model_binding(
            cur,
            binding["workspace_id"],
            binding["id"],
            status="revoked",
        )

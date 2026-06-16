"""Conductor hook subscriptions and major-inquiry dispatch."""
from __future__ import annotations

import hashlib
import ipaddress
import json
import logging
from typing import Any, Optional
from urllib.parse import urlparse

from core.database import db_cursor
from core.security import generate_id
from services.job_observability import finish_job_run, start_job_run
from services.notifications import deliver_webhook

logger = logging.getLogger(__name__)

VALID_SCALES = {"minor", "major"}
LOCAL_WEBHOOK_HOSTS = {"localhost"}


def _json(data: Optional[dict[str, Any]]) -> str:
    return json.dumps(data or {})


def _load_json(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return {}
    return {}


def _is_loopback_host(hostname: str) -> bool:
    normalized = hostname.lower().rstrip(".")
    if normalized in LOCAL_WEBHOOK_HOSTS:
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


def validate_webhook_url(url: str) -> str:
    from fastapi import HTTPException

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise HTTPException(status_code=400, detail="Webhook URL must be an http or https URL")

    hostname = parsed.hostname.lower().rstrip(".")
    is_loopback = _is_loopback_host(hostname)
    if parsed.scheme == "http" and not is_loopback:
        raise HTTPException(status_code=400, detail="HTTP webhook URLs are allowed only for localhost or loopback hosts")

    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        ip = None
    if ip and (ip.is_private or ip.is_link_local or ip.is_multicast or ip.is_reserved) and not ip.is_loopback:
        raise HTTPException(status_code=400, detail="Webhook URL must not target private or link-local IP ranges")

    return url


def get_node_scale(node: dict[str, Any]) -> str:
    metadata = _load_json(node.get("metadata"))
    scale = metadata.get("scale") or "minor"
    return scale if scale in VALID_SCALES else "minor"


def set_node_scale_in_db(cur, ws_id: str, node_id: str, scale: str) -> dict[str, Any]:
    if scale not in VALID_SCALES:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="scale must be 'minor' or 'major'")
    cur.execute(
        """
        UPDATE memory_nodes
        SET metadata = jsonb_set(COALESCE(metadata, '{}'::jsonb), '{scale}', to_jsonb(%s::text), true),
            updated_at = now()
        WHERE id = %s AND workspace_id = %s
        RETURNING id, workspace_id, title, content_type, status, metadata
        """,
        (scale, node_id, ws_id),
    )
    row = cur.fetchone()
    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Node not found")
    return dict(row)


def list_hooks(cur, ws_id: str) -> list[dict[str, Any]]:
    cur.execute(
        """
        SELECT id, workspace_id, name, url, enabled, event_filter, created_at, updated_at
        FROM conductor_hook_subscriptions
        WHERE workspace_id = %s
        ORDER BY created_at ASC
        """,
        (ws_id,),
    )
    return [dict(row) for row in cur.fetchall()]


def list_deliveries(
    cur,
    *,
    workspace_id: str,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    conditions = ["d.workspace_id = %s"]
    params: list[Any] = [workspace_id]
    if status:
        conditions.append("d.status = %s")
        params.append(status)
    params.extend([limit, offset])
    cur.execute(
        f"""
        SELECT d.id, d.workspace_id, d.hook_id, h.name AS hook_name,
               d.node_id, d.event_id, d.correlation_id, d.status,
               d.attempts, d.last_error, d.payload, d.created_at, d.delivered_at
        FROM conductor_deliveries d
        LEFT JOIN conductor_hook_subscriptions h ON h.id = d.hook_id
        WHERE {' AND '.join(conditions)}
        ORDER BY d.created_at DESC
        LIMIT %s OFFSET %s
        """,
        params,
    )
    return [dict(row) for row in cur.fetchall()]


def create_hook(cur, ws_id: str, data: dict[str, Any]) -> dict[str, Any]:
    hook_id = generate_id("hook")
    url = validate_webhook_url(data["url"])
    cur.execute(
        """
        INSERT INTO conductor_hook_subscriptions (id, workspace_id, name, url, secret, enabled, event_filter)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id, workspace_id, name, url, enabled, event_filter, created_at, updated_at
        """,
        (
            hook_id,
            ws_id,
            data["name"],
            url,
            data.get("secret"),
            data.get("enabled", True),
            _json(data.get("event_filter")),
        ),
    )
    return dict(cur.fetchone())


def update_hook(cur, ws_id: str, hook_id: str, data: dict[str, Any]) -> dict[str, Any]:
    allowed = ["name", "url", "secret", "enabled", "event_filter"]
    updates = {key: value for key, value in data.items() if key in allowed and value is not None}
    if not updates:
        cur.execute(
            """
            SELECT id, workspace_id, name, url, enabled, event_filter, created_at, updated_at
            FROM conductor_hook_subscriptions
            WHERE workspace_id = %s AND id = %s
            """,
            (ws_id, hook_id),
        )
        row = cur.fetchone()
        if not row:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Hook not found")
        return dict(row)
    parts = []
    params: list[Any] = []
    for key, value in updates.items():
        parts.append(f"{key} = %s")
        if key == "url":
            value = validate_webhook_url(value)
        params.append(_json(value) if key == "event_filter" else value)
    params.extend([ws_id, hook_id])
    cur.execute(
        f"""
        UPDATE conductor_hook_subscriptions
        SET {', '.join(parts)}, updated_at = now()
        WHERE workspace_id = %s AND id = %s
        RETURNING id, workspace_id, name, url, enabled, event_filter, created_at, updated_at
        """,
        params,
    )
    row = cur.fetchone()
    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Hook not found")
    return dict(row)


def _hook_allows_node(hook: dict[str, Any], node: dict[str, Any], scale: str) -> bool:
    event_filter = _load_json(hook.get("event_filter"))
    if event_filter.get("scale") and event_filter["scale"] != scale:
        return False
    if event_filter.get("content_type") and event_filter["content_type"] != node.get("content_type"):
        return False
    tag_filter = event_filter.get("tags") or []
    if tag_filter and not set(tag_filter).intersection(set(node.get("tags") or [])):
        return False
    return True


def _event_id(ws_id: str, node: dict[str, Any]) -> str:
    basis = f"{ws_id}:{node['id']}:{node.get('updated_at')}:{get_node_scale(node)}"
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()


def _delivery_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in result.items() if key != "_deliveries"}


def prepare_major_inquiry_hook_deliveries(cur, ws_id: str, node_id: str, trigger_reason: str) -> dict[str, Any]:
    cur.execute(
        """
        SELECT id, workspace_id, title, body, tags, content_type, status, updated_at, metadata
        FROM memory_nodes
        WHERE id = %s AND workspace_id = %s AND status = 'active'
        """,
        (node_id, ws_id),
    )
    node = cur.fetchone()
    if not node:
        return {"status": "skipped", "reason": "node_not_active"}
    node = dict(node)
    scale = get_node_scale(node)
    if node["content_type"] != "inquiry" or scale != "major":
        return {"status": "skipped", "reason": "not_major_inquiry", "scale": scale}
    cur.execute(
        """
        SELECT 1 FROM edges
        WHERE workspace_id = %s AND from_id = %s AND relation = 'answered_by' AND status = 'active'
        LIMIT 1
        """,
        (ws_id, node_id),
    )
    if cur.fetchone():
        return {"status": "skipped", "reason": "already_answered"}
    cur.execute(
        """
        SELECT * FROM conductor_hook_subscriptions
        WHERE workspace_id = %s AND enabled = TRUE
        ORDER BY created_at ASC
        """,
        (ws_id,),
    )
    hooks = [dict(row) for row in cur.fetchall()]
    event_id = _event_id(ws_id, node)
    correlation_id = f"conductor:{event_id[:16]}"
    payload = {
        "event": "major_inquiry",
        "event_id": event_id,
        "correlation_id": correlation_id,
        "workspace_id": ws_id,
        "task_node_id": node_id,
        "scale": scale,
        "trigger_reason": trigger_reason,
        "title": node["title"],
        "body": node["body"],
        "tags": node.get("tags") or [],
    }
    delivered = 0
    skipped = 0
    pending = 0
    deliveries: list[dict[str, Any]] = []
    for hook in hooks:
        if not _hook_allows_node(hook, node, scale):
            skipped += 1
            continue
        delivery_id = generate_id("hookd")
        try:
            cur.execute(
                """
                INSERT INTO conductor_deliveries (
                    id, workspace_id, hook_id, node_id, event_id, correlation_id, payload
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (hook_id, event_id) DO NOTHING
                RETURNING id
                """,
                (delivery_id, ws_id, hook["id"], node_id, event_id, correlation_id, _json(payload)),
            )
            inserted = cur.fetchone()
            if not inserted:
                skipped += 1
                continue
            deliveries.append({
                "id": delivery_id,
                "hook_id": hook["id"],
                "url": hook["url"],
                "secret": hook.get("secret"),
                "payload": payload,
            })
            pending += 1
        except Exception as exc:
            logger.warning("Conductor hook delivery failed: hook=%s node=%s error=%s", hook["id"], node_id, exc)
            cur.execute(
                """
                UPDATE conductor_deliveries
                SET status = 'failed', attempts = attempts + 1, last_error = %s
                WHERE id = %s
                """,
                (str(exc), delivery_id),
            )
            skipped += 1
    return {
        "status": "processed",
        "event_id": event_id,
        "correlation_id": correlation_id,
        "hook_count": len(hooks),
        "delivered": delivered,
        "pending": pending,
        "skipped": skipped,
        "failed": 0,
        "_deliveries": deliveries,
    }


async def _deliver_prepared_deliveries(result: dict[str, Any]) -> dict[str, Any]:
    deliveries = result.get("_deliveries") or []
    delivered = 0
    failed = 0
    for delivery in deliveries:
        try:
            ok = await deliver_webhook(delivery["url"], delivery.get("secret"), delivery["payload"])
            if not ok:
                raise RuntimeError("webhook delivery failed after retries")
            with db_cursor(commit=True) as cur:
                cur.execute(
                    """
                    UPDATE conductor_deliveries
                    SET status = 'delivered', attempts = attempts + 1, delivered_at = now()
                    WHERE id = %s
                    """,
                    (delivery["id"],),
                )
            delivered += 1
        except Exception as exc:
            logger.warning(
                "Conductor hook delivery failed: hook=%s delivery=%s error=%s",
                delivery.get("hook_id"),
                delivery["id"],
                exc,
            )
            with db_cursor(commit=True) as cur:
                cur.execute(
                    """
                    UPDATE conductor_deliveries
                    SET status = 'failed', attempts = attempts + 1, last_error = %s
                    WHERE id = %s
                    """,
                    (str(exc), delivery["id"]),
                )
            failed += 1
    result["delivered"] = delivered
    result["failed"] = failed
    result["pending"] = 0
    return result


async def dispatch_major_inquiry_hooks(ws_id: str, node_id: str, trigger_reason: str) -> dict[str, Any]:
    with db_cursor(commit=True) as cur:
        result = prepare_major_inquiry_hook_deliveries(cur, ws_id, node_id, trigger_reason)
    if result.get("status") == "processed":
        result = await _deliver_prepared_deliveries(result)
    return _delivery_summary(result)


async def record_conductor_run(ws_id: str, node_id: str, trigger_reason: str) -> dict[str, Any]:
    run_id = start_job_run(
        "conductor_dispatch",
        workspace_id=ws_id,
        trigger="node_event",
        summary={"node_id": node_id, "trigger_reason": trigger_reason},
    )
    try:
        result = await dispatch_major_inquiry_hooks(ws_id, node_id, trigger_reason)
        status = "success" if result.get("status") == "processed" else "skipped"
        finish_job_run(
            run_id,
            "conductor_dispatch",
            status=status,
            scanned_count=1,
            processed_count=1 if status == "success" else 0,
            skipped_count=1 if status == "skipped" else result.get("skipped"),
            failed_count=result.get("failed"),
            summary=result,
        )
        return result
    except Exception as exc:
        finish_job_run(
            run_id,
            "conductor_dispatch",
            status="failed",
            scanned_count=1,
            failed_count=1,
            error=str(exc),
            summary={"node_id": node_id, "trigger_reason": trigger_reason},
        )
        raise

import hmac
import hashlib
import json
import logging
import asyncio
from typing import Optional, Dict, Any
import httpx

from core.config import settings
from core.database import db_cursor
from core.email import _dispatch
from core.security import generate_id

logger = logging.getLogger(__name__)

def list_notifications(
    cur,
    recipient_id: str,
    *,
    workspace_id: Optional[str] = None,
    unread_only: bool = False,
    severity: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Dict[str, Any]]:
    """List a user's in-app notifications, newest first."""
    conditions = ["recipient_id = %s"]
    params: list[Any] = [recipient_id]
    if workspace_id:
        conditions.append("workspace_id = %s")
        params.append(workspace_id)
    if unread_only:
        conditions.append("read_at IS NULL")
    if severity:
        conditions.append("severity = %s")
        params.append(severity)
    params.extend([limit, offset])
    cur.execute(
        f"""
        SELECT id, workspace_id, recipient_id, source_type, source_id,
               category, severity, title, body, target_node_id, read_at, created_at
        FROM notifications
        WHERE {' AND '.join(conditions)}
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
        """,
        params,
    )
    return [dict(r) for r in cur.fetchall()]


def unread_count(cur, recipient_id: str, workspace_id: Optional[str] = None) -> int:
    """Count a user's unread notifications (optionally scoped to one workspace)."""
    conditions = ["recipient_id = %s", "read_at IS NULL"]
    params: list[Any] = [recipient_id]
    if workspace_id:
        conditions.append("workspace_id = %s")
        params.append(workspace_id)
    cur.execute(
        f"SELECT count(*) AS cnt FROM notifications WHERE {' AND '.join(conditions)}",
        params,
    )
    row = cur.fetchone()
    return int(row["cnt"] if row else 0)


def mark_notification_read(cur, notification_id: str, recipient_id: str) -> bool:
    """Mark one notification read. Scoped to the owner to prevent cross-user reads."""
    cur.execute(
        """
        UPDATE notifications
        SET read_at = now()
        WHERE id = %s AND recipient_id = %s AND read_at IS NULL
        RETURNING id
        """,
        (notification_id, recipient_id),
    )
    return cur.fetchone() is not None


def mark_all_read(cur, recipient_id: str, workspace_id: Optional[str] = None) -> int:
    """Mark all of a user's unread notifications read; returns the number updated."""
    conditions = ["recipient_id = %s", "read_at IS NULL"]
    params: list[Any] = [recipient_id]
    if workspace_id:
        conditions.append("workspace_id = %s")
        params.append(workspace_id)
    cur.execute(
        f"UPDATE notifications SET read_at = now() WHERE {' AND '.join(conditions)} RETURNING id",
        params,
    )
    return len(cur.fetchall())


def dismiss_notification(cur, notification_id: str, recipient_id: str) -> bool:
    """Permanently remove one notification. Scoped to the owner."""
    cur.execute(
        "DELETE FROM notifications WHERE id = %s AND recipient_id = %s RETURNING id",
        (notification_id, recipient_id),
    )
    return cur.fetchone() is not None


def dismiss_notifications(
    cur,
    recipient_id: str,
    *,
    workspace_id: Optional[str] = None,
    read_only: bool = False,
    severity: Optional[str] = None,
) -> int:
    """Bulk-remove a user's notifications (optionally only read ones / one workspace /
    one severity). Returns the number deleted."""
    conditions = ["recipient_id = %s"]
    params: list[Any] = [recipient_id]
    if workspace_id:
        conditions.append("workspace_id = %s")
        params.append(workspace_id)
    if read_only:
        conditions.append("read_at IS NOT NULL")
    if severity:
        conditions.append("severity = %s")
        params.append(severity)
    cur.execute(
        f"DELETE FROM notifications WHERE {' AND '.join(conditions)} RETURNING id",
        params,
    )
    return len(cur.fetchall())


def get_workspace_admins(ws_id: str) -> list[str]:
    """Retrieve emails of workspace owner and administrators."""
    with db_cursor() as cur:
        # Owner email
        cur.execute(
            """
            SELECT u.email FROM users u 
            JOIN workspaces w ON w.owner_id = u.id 
            WHERE w.id = %s
            """
            , (ws_id,)
        )
        owner = cur.fetchone()
        
        # Admin members email
        cur.execute(
            """
            SELECT u.email FROM users u
            JOIN workspace_members wm ON wm.user_id = u.id
            WHERE wm.workspace_id = %s AND wm.role = 'admin'
            """,
            (ws_id,)
        )
        admins = [r["email"] for r in cur.fetchall()]
        
        emails = []
        if owner and owner["email"]:
            emails.append(owner["email"])
        emails.extend(admins)
        return list(set(emails))

def _resolve_inapp_recipients(cur, ws_id: str) -> list[str]:
    """Owner + admins/editors — mirrors the 115/116 fan-out triggers."""
    cur.execute(
        """
        SELECT owner_id AS uid FROM workspaces WHERE id = %s
        UNION
        SELECT user_id FROM workspace_members
        WHERE workspace_id = %s AND role::text IN ('admin', 'editor')
        """,
        (ws_id, ws_id),
    )
    return [r["uid"] for r in cur.fetchall() if r and r["uid"]]


def emit_notification(
    cur,
    *,
    workspace_id: str,
    category: str,
    severity: str,
    title: str,
    source_type: str,
    source_id: str,
    body: Optional[str] = None,
    target_node_id: Optional[str] = None,
    group: Optional[str] = None,
) -> int:
    """Write an in-app notification to workspace owner + admins/editors, honoring each
    recipient's per-user opt-out (``users.notification_preferences[group] is False``).

    This is the Python-side counterpart to the 115/116 DB triggers (which fire for
    audit_proposals / review_queue inserts). Use it for notification sources that do
    not flow through those tables — e.g. consult / degradation events, and the
    safety "passed" trace — so every finding can still reach the inbox while letting
    users mute noisy groups. ``group`` defaults to ``category``.

    Returns the number of rows inserted. Does not swallow errors itself; callers in
    best-effort paths should wrap the call in try/except.
    """
    grp = group or category
    recipients = _resolve_inapp_recipients(cur, workspace_id)
    if not recipients:
        return 0
    cur.execute(
        "SELECT id, notification_preferences FROM users WHERE id = ANY(%s)",
        (recipients,),
    )
    pref_rows = cur.fetchall()
    inserted = 0
    for row in pref_rows:
        prefs = row["notification_preferences"] or {}
        if isinstance(prefs, str):
            try:
                prefs = json.loads(prefs)
            except Exception:
                prefs = {}
        if prefs.get(grp) is False:
            continue  # recipient muted this notification group
        cur.execute(
            """
            INSERT INTO notifications
                (id, workspace_id, recipient_id, source_type, source_id,
                 category, severity, title, body, target_node_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                generate_id("ntf"),
                workspace_id,
                row["id"],
                source_type,
                source_id,
                category,
                severity,
                title,
                body,
                target_node_id,
            ),
        )
        inserted += 1
    return inserted


async def deliver_webhook(webhook_url: str, webhook_secret: Optional[str], payload: dict) -> bool:
    """Deliver webhook POST request with exponential backoff retry.

    Returns True only when the remote endpoint acknowledges the delivery.
    Failures are still swallowed for backwards-compatible notification decoupling.
    """
    data = json.dumps(payload)
    headers = {"Content-Type": "application/json"}
    
    if webhook_secret:
        signature = hmac.new(
            webhook_secret.encode("utf-8"),
            data.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        headers["X-MemTrace-Signature"] = signature

    async with httpx.AsyncClient() as client:
        backoff = 1.0
        for attempt in range(3):
            try:
                response = await client.post(webhook_url, content=data, headers=headers, timeout=5.0)
                if 200 <= response.status_code < 300:
                    logger.info(f"Webhook delivered successfully to {webhook_url}")
                    return True
                else:
                    logger.warning(f"Webhook delivered returned status {response.status_code} (attempt {attempt+1})")
            except Exception as e:
                logger.warning(f"Webhook delivery failed to {webhook_url}: {e} (attempt {attempt+1})")
            
            await asyncio.sleep(backoff)
            backoff *= 2.0
        logger.error(f"Failed to deliver webhook to {webhook_url} after 3 attempts.")
        return False

def send_consult_notification(
    ws_id: str,
    session_id: str,
    classification: str,
    action_taken: str,
    proposal: dict,
    proposal_id: Optional[str] = None
):
    """
    Push notifications to workspace admins and dispatch webhooks.
    Decoupled: errors here do not affect database transactions.
    """
    try:
        # Load workspace name & settings
        with db_cursor() as cur:
            cur.execute("SELECT name, settings FROM workspaces WHERE id = %s", (ws_id,))
            ws = cur.fetchone()
            if not ws:
                return
            ws_name = ws["name"]
            ws_settings = ws["settings"] or {}
            if isinstance(ws_settings, str):
                try:
                    ws_settings = json.loads(ws_settings)
                except Exception:
                    ws_settings = {}

        # 1. Dispatch Webhook
        webhook_url = ws_settings.get("webhook_url")
        webhook_secret = ws_settings.get("webhook_secret")
        if webhook_url:
            webhook_payload = {
                "event": "consultation",
                "workspace_id": ws_id,
                "workspace_name": ws_name,
                "session_id": session_id,
                "classification": classification,
                "action_taken": action_taken,
                "proposal_id": proposal_id,
                "proposal": proposal
            }
            # Run webhook in background task
            asyncio.create_task(deliver_webhook(webhook_url, webhook_secret, webhook_payload))

        # 2. In-app notification center (independent of email/webhook availability).
        _consult_severity = {"blocked": "high", "escalated": "mid", "auto_merged": "low"}.get(action_taken)
        if _consult_severity is not None:
            node_title = (proposal.get("new_node") or {}).get("title") or "診斷節點"
            _consult_titles = {
                "blocked": f"⚠️ 危險操作已攔截：{node_title}",
                "escalated": f"新診斷提案待審核：{node_title}",
                "auto_merged": f"已自動合入診斷節點：{node_title}",
            }
            try:
                with db_cursor(commit=True) as ncur:
                    emit_notification(
                        ncur,
                        workspace_id=ws_id,
                        category="consultation",
                        severity=_consult_severity,
                        title=_consult_titles[action_taken],
                        body=f"classification={classification}, action={action_taken}",
                        source_type="consult",
                        source_id=proposal_id or session_id,
                        group="consultation",
                    )
            except Exception as e:
                logger.warning(f"consult in-app notification failed: {e}")

        # 3. Dispatch Emails
        recipients = get_workspace_admins(ws_id)
        if not recipients:
            return
            
        # Select template and subject based on action_taken
        if action_taken == "auto_merged":
            subject = f"[MemTrace] 知識庫「{ws_name}」已自動新增故障診斷節點"
            html = (
                f"<p>您好，</p>"
                f"<p>我們在知識庫 <strong>{ws_name}</strong> 中偵測到死路，AI 已透過「完全信任制」自動合入新節點：</p>"
                f"<blockquote><strong>{proposal.get('new_node', {}).get('title')}</strong></blockquote>"
                f"<p>這是一個<strong>安全 (safe)</strong>的操作，不需您手動干預。</p>"
            )
            text = f"您好，我們在知識庫 {ws_name} 中自動新增了新節點：{proposal.get('new_node', {}).get('title')}。"
        elif action_taken == "escalated":
            subject = f"[MemTrace] 知識庫「{ws_name}」有新的故障診斷提案待核准"
            review_url = f"{settings.app_url}/workspaces/{ws_id}/audit"
            html = (
                f"<p>您好，</p>"
                f"<p>知識庫 <strong>{ws_name}</strong> 的 AI 診斷產生了一筆新提案（分類為 <strong>{classification}</strong>），正在等待您的審核：</p>"
                f"<blockquote><strong>{proposal.get('new_node', {}).get('title', '新診斷節點')}</strong></blockquote>"
                f"<p>請前往審核佇列進行決議：</p>"
                f'<a href="{review_url}" class="btn">前往審核 &rarr;</a>'
                f'<p class="link-fallback">{review_url}</p>'
            )
            text = f"您好，知識庫 {ws_name} 有新的提案等待審核：{review_url}"
        elif action_taken == "blocked":
            subject = f"[MemTrace] ⚠️ 安全警告：知識庫「{ws_name}」危險操作已被攔截阻斷"
            html = (
                f"<p>您好，</p>"
                f"<p><strong>安全審查警告：</strong>AI 診斷在處理死路時，產生了被判定為<strong>危險 (dangerous)</strong>的操作，已被系統自動硬攔截阻斷：</p>"
                f"<blockquote><strong>{proposal.get('new_node', {}).get('title')}</strong></blockquote>"
                f"<p>此提案已被拒絕，且不會合入圖中。</p>"
            )
            text = f"警告：知識庫 {ws_name} 的 AI 診斷產生了危險操作，已被自動攔截阻斷。"
        else:
            return
            
        for to_email in recipients:
            _dispatch(to_email, subject, html, text)
            
    except Exception as e:
        logger.error(f"Failed to send consult notification: {e}")


def send_degradation_notification(ws_id: str, reason: str):
    """Notify workspace admins about AI reviewer policy degradation."""
    try:
        with db_cursor() as cur:
            cur.execute("SELECT name, settings FROM workspaces WHERE id = %s", (ws_id,))
            ws = cur.fetchone()
            if not ws:
                return
            ws_name = ws["name"]
            ws_settings = ws["settings"] or {}
            if isinstance(ws_settings, str):
                try:
                    ws_settings = json.loads(ws_settings)
                except Exception:
                    ws_settings = {}

        # 1. Webhook
        webhook_url = ws_settings.get("webhook_url")
        webhook_secret = ws_settings.get("webhook_secret")
        if webhook_url:
            payload = {
                "event": "review_policy_degradation",
                "workspace_id": ws_id,
                "workspace_name": ws_name,
                "reason": reason,
            }
            asyncio.create_task(deliver_webhook(webhook_url, webhook_secret, payload))

        # 2. In-app notification center (independent of email availability).
        try:
            with db_cursor(commit=True) as ncur:
                emit_notification(
                    ncur,
                    workspace_id=ws_id,
                    category="review_degradation",
                    severity="high",
                    title="⚠️ AI 審核已安全降級為人工審查",
                    body=reason,
                    source_type="review_policy",
                    source_id=ws_id,
                    group="review_degradation",
                )
        except Exception as e:
            logger.warning(f"degradation in-app notification failed: {e}")

        # 3. Email
        recipients = get_workspace_admins(ws_id)
        if not recipients:
            return

        subject = f"[MemTrace] ⚠️ 警告：知識庫「{ws_name}」AI 審核已安全降級為人工審查"
        html = (
            f"<p>您好，</p>"
            f"<p>知識庫 <strong>{ws_name}</strong> 的 AI 自動審核政策已發生<strong>安全降級 (degradation)</strong>：</p>"
            f"<p>有效模式已改為 <strong>僅限人工審核 (manual_only)</strong>。</p>"
            f"<p><strong>降級原因：</strong>{reason}</p>"
            f"<p>系統已暫停自動審查，所有新提案將保持 Pending 直到人工完成審查。當您重新綁定可用模型後，審查政策將自動恢復運作。</p>"
        )
        text = f"警告：知識庫 {ws_name} 的 AI 自動審核已降級為 manual_only。原因：{reason}"

        for to_email in recipients:
            _dispatch(to_email, subject, html, text)
    except Exception as e:
        logger.error(f"Failed to send degradation notification: {e}")


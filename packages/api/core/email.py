"""
core/email.py — Provider-agnostic email sending for MemTrace.

Supported providers (controlled by settings.email_provider):
  "resend"   — Resend API (default, recommended)
  "smtp"     — Generic SMTP (fallback / self-hosted)
  "disabled" — All sends are no-ops; tokens printed to console (dev mode)

To add a new provider later, implement _send_via_<name>() and add a branch
in _dispatch().  The rest of the codebase never changes.
"""
from __future__ import annotations

import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from core.config import settings

logger = logging.getLogger(__name__)

# ── Internal dispatch ──────────────────────────────────────────────────────────

def _dispatch(to: str, subject: str, html: str, text: str) -> None:
    """Route to the configured provider. Never raises — logs on failure."""
    provider = settings.email_provider.lower()
    try:
        if provider == "resend":
            _send_via_resend(to, subject, html, text)
        elif provider == "smtp":
            _send_via_smtp(to, subject, html, text)
        else:
            # "disabled" or unknown — print to console (dev mode)
            logger.info("[email:disabled] TO=%s  SUBJECT=%s", to, subject)
    except Exception as exc:
        logger.error("Email send failed (provider=%s, to=%s): %s", provider, to, exc)


def _send_via_resend(to: str, subject: str, html: str, text: str) -> None:
    import resend  # type: ignore
    resend.api_key = settings.email_api_key
    resend.Emails.send({
        "from":    f"{settings.email_from_name} <{settings.email_from}>",
        "to":      [to],
        "subject": subject,
        "html":    html,
        "text":    text,
    })
    logger.info("Email sent via Resend: to=%s subject=%s", to, subject)


def _send_via_smtp(to: str, subject: str, html: str, text: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"{settings.email_from_name} <{settings.email_from}>"
    msg["To"]      = to
    msg.attach(MIMEText(text, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html",  "utf-8"))

    ctx = ssl.create_default_context()
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.ehlo()
        server.starttls(context=ctx)
        server.login(settings.smtp_user, settings.smtp_password)
        server.sendmail(settings.email_from, to, msg.as_string())
    logger.info("Email sent via SMTP: to=%s subject=%s", to, subject)


# ── Public API ─────────────────────────────────────────────────────────────────

def send_verification_email(to: str, token: str) -> None:
    """Send the email address verification link after registration."""
    url   = f"{settings.app_url}/verify-email?token={token}"
    subject = "驗證您的 MemTrace 帳號 / Verify your MemTrace account"
    html  = _tpl_verification(url)
    text  = (
        f"請點擊以下連結驗證您的 Email（24 小時內有效）：\n{url}\n\n"
        f"Please verify your email address (valid for 24 hours):\n{url}"
    )
    _dispatch(to, subject, html, text)


def send_password_reset_email(to: str, token: str) -> None:
    """Send the password reset link."""
    url   = f"{settings.app_url}/reset-password?token={token}"
    subject = "重設您的 MemTrace 密碼 / Reset your MemTrace password"
    html  = _tpl_password_reset(url)
    text  = (
        f"請點擊以下連結重設密碼（1 小時內有效）：\n{url}\n\n"
        f"Please click the link below to reset your password (valid for 1 hour):\n{url}"
    )
    _dispatch(to, subject, html, text)


def send_workspace_deletion_notice(
    to: str,
    ws_name: str,
    days_left: int,
    restore_url: Optional[str] = None,
) -> None:
    """
    Notify the workspace owner about upcoming deletion.
    days_left: 30 (initial), 5 (warning), 0 (final / purged).
    """
    if days_left == 0:
        subject = f"[MemTrace] 知識庫「{ws_name}」已永久刪除"
        html    = _tpl_ws_deleted(ws_name)
        text    = f"您的知識庫「{ws_name}」已於今日從 MemTrace 永久刪除。"
    elif days_left <= 5:
        subject = f"[MemTrace] 知識庫「{ws_name}」將在 {days_left} 天後永久刪除"
        html    = _tpl_ws_deletion_warning(ws_name, days_left, restore_url)
        text    = (
            f"您的知識庫「{ws_name}」將在 {days_left} 天後永久刪除。\n"
            f"如需還原，請前往：{restore_url}"
        )
    else:
        subject = f"[MemTrace] 知識庫「{ws_name}」已進入 30 天刪除寬限期"
        html    = _tpl_ws_deletion_warning(ws_name, days_left, restore_url)
        text    = (
            f"您的知識庫「{ws_name}」已進入 30 天刪除寬限期。\n"
            f"如需還原，請前往：{restore_url}"
        )
    _dispatch(to, subject, html, text)


# ── Email templates ────────────────────────────────────────────────────────────
#
# Intentionally minimal inline HTML — no external dependencies, no CDN links.
# Uses the MemTrace primary colour (#4F46E5) from the design system.

_BASE = """<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  body{{margin:0;padding:0;background:#f5f5f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#1a1a1a}}
  .wrap{{max-width:560px;margin:40px auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08)}}
  .header{{background:#4F46E5;padding:32px 40px}}
  .header h1{{margin:0;color:#fff;font-size:20px;font-weight:600;letter-spacing:-.3px}}
  .body{{padding:36px 40px}}
  .body p{{margin:0 0 16px;line-height:1.6;font-size:15px;color:#374151}}
  .body p.sub{{font-size:13px;color:#6b7280}}
  .btn{{display:inline-block;margin:8px 0 24px;padding:13px 28px;background:#4F46E5;color:#fff !important;text-decoration:none;border-radius:8px;font-size:15px;font-weight:600}}
  .divider{{border:none;border-top:1px solid #e5e7eb;margin:24px 0}}
  .footer{{padding:20px 40px;background:#f9fafb;font-size:12px;color:#9ca3af;line-height:1.5}}
  .link-fallback{{word-break:break-all;color:#4F46E5;font-size:13px}}
</style>
</head>
<body>
<div class="wrap">
  <div class="header"><h1>MemTrace</h1></div>
  <div class="body">{content}</div>
  <div class="footer">{footer}</div>
</div>
</body>
</html>"""

_FOOTER_DEFAULT = (
    "此郵件由 MemTrace 系統自動發送，請勿回覆。<br>"
    "This is an automated message from MemTrace. Please do not reply."
)


def _tpl_verification(url: str) -> str:
    content = f"""
<p>您好，感謝您建立 MemTrace 帳號。</p>
<p>請點擊下方按鈕驗證您的 Email 地址，連結將在 <strong>24 小時</strong>後失效。</p>
<a href="{url}" class="btn">驗證 Email &rarr;</a>
<hr class="divider">
<p class="sub">Hi, thanks for creating a MemTrace account.<br>
Click the button above to verify your email address. The link expires in <strong>24 hours</strong>.</p>
<p class="sub">如果按鈕無法點擊，請複製以下連結貼入瀏覽器：<br>
If the button doesn't work, copy this link into your browser:</p>
<p class="link-fallback">{url}</p>"""
    return _BASE.format(content=content, footer=_FOOTER_DEFAULT)


def _tpl_password_reset(url: str) -> str:
    content = f"""
<p>我們收到了重設您 MemTrace 帳號密碼的請求。</p>
<p>請點擊下方按鈕設定新密碼，連結將在 <strong>1 小時</strong>後失效。</p>
<a href="{url}" class="btn">重設密碼 &rarr;</a>
<hr class="divider">
<p class="sub">We received a request to reset your MemTrace password.<br>
Click the button above to set a new password. The link expires in <strong>1 hour</strong>.</p>
<p class="sub">如果您沒有提出此請求，可以忽略本郵件，您的密碼不會有任何變更。<br>
If you didn't request this, you can safely ignore this email — your password won't change.</p>
<p class="link-fallback">{url}</p>"""
    return _BASE.format(content=content, footer=_FOOTER_DEFAULT)


def _tpl_ws_deletion_warning(ws_name: str, days_left: int, restore_url: Optional[str]) -> str:
    urgency = "⚠️ 緊急：" if days_left <= 5 else ""
    restore_block = ""
    if restore_url:
        restore_block = f'<a href="{restore_url}" class="btn">還原知識庫 &rarr;</a>'
    content = f"""
<p>{urgency}您的知識庫「<strong>{ws_name}</strong>」已進入刪除流程。</p>
<p>若未在 <strong>{days_left} 天</strong>內還原，該知識庫及其所有節點、邊與對話紀錄將被<strong>永久刪除</strong>，無法復原。</p>
{restore_block}
<hr class="divider">
<p class="sub">{urgency}Your workspace "<strong>{ws_name}</strong>" is scheduled for deletion.<br>
If not restored within <strong>{days_left} day(s)</strong>, all nodes, edges, and chat history will be <strong>permanently deleted</strong>.</p>"""
    footer = (
        f"如有疑問請聯絡支援團隊。{_FOOTER_DEFAULT}"
    )
    return _BASE.format(content=content, footer=footer)


def _tpl_ws_deleted(ws_name: str) -> str:
    content = f"""
<p>您的知識庫「<strong>{ws_name}</strong>」已於今日從 MemTrace 系統中永久刪除。</p>
<p>所有節點、邊及對話紀錄均已移除，此操作無法復原。</p>
<hr class="divider">
<p class="sub">Your workspace "<strong>{ws_name}</strong>" has been permanently deleted from MemTrace today.<br>
All nodes, edges, and chat history have been removed. This action cannot be undone.</p>"""
    return _BASE.format(content=content, footer=_FOOTER_DEFAULT)

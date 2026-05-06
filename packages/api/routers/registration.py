import hashlib
import secrets
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from core.config import settings
from core.database import db_cursor
from core.email import send_magic_link_email
from core.security import generate_id, create_access_token, generate_refresh_token
from models.auth import MagicLinkRegisterRequest, MagicLinkVerifyRequest, TokenResponse
from routers.auth import _set_refresh_cookie

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

def _validate_email_domain(email: str):
    if not settings.registration_domains:
        logger.warning("MEMTRACE_REGISTRATION_MODE=domain but MEMTRACE_REGISTRATION_DOMAINS not set")
        raise HTTPException(
            status_code=500,
            detail="系統配置錯誤：網域模式已開啟但未設定允許網域。",
        )
    domain = email.split("@")[-1].lower()
    allowed = [d.lower() for d in settings.registration_domains]
    if domain not in allowed:
        raise HTTPException(
            status_code=403,
            detail="此 email 網域不在允許清單中。請使用公司 email 或聯絡管理員。",
        )

@router.post("/register", status_code=200)
def register(body: MagicLinkRegisterRequest):
    """
    Unified entrance for open, domain, and approval registration modes.
    Sends a magic link for validation.
    """
    mode = settings.registration_mode
    if mode == "closed":
        raise HTTPException(status_code=403, detail="此知識庫目前不開放公開註冊，請聯絡管理員")

    if mode == "invite_only":
        raise HTTPException(status_code=403, detail="此知識庫僅限受邀者註冊。")

    email = body.email.lower().strip()

    if mode == "domain":
        _validate_email_domain(email)

    if mode in ("open", "domain", "approval"):
        with db_cursor() as cur:
            cur.execute("SELECT id FROM users WHERE email = %s", (email,))
            user = cur.fetchone()
            
            if mode == "approval" and not user:
                # Check if already requested
                with db_cursor() as cur:
                    cur.execute("SELECT id, status FROM user_registrations WHERE email = %s", (email,))
                    existing = cur.fetchone()
                
                if existing:
                    if existing["status"] == "pending":
                        return {"message": "您的申請正在審核中，請耐心等候。"}
                    elif existing["status"] == "rejected":
                        raise HTTPException(status_code=403, detail="您的註冊申請已被拒絕，請聯絡管理員。")
                    # If approved, they should already have a user account, so we shouldn't reach here if 'user' is None
                
                # Create registration request
                reg_id = generate_id("reg")
                with db_cursor(commit=True) as cur:
                    cur.execute("""
                        INSERT INTO user_registrations (id, email, status, purpose_note, created_at)
                        VALUES (%s, %s, 'pending', %s, now())
                    """, (reg_id, email, body.purpose_note))
                
                return {"message": "申請已送出，管理員審核通過後將透過 email 通知您。"}
            
            purpose = "login" if user else "registration"

        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

        with db_cursor(commit=True) as cur:
            # Rate guard: Prevent flooding (max 1 email per minute)
            cur.execute("""
                SELECT created_at FROM magic_link_tokens 
                WHERE email = %s AND created_at > now() - INTERVAL '1 minute'
                LIMIT 1
            """, (email,))
            if cur.fetchone():
                return {"message": "已寄送連結至您的信箱，請於 15 分鐘內完成"}

            cur.execute("""
                INSERT INTO magic_link_tokens (email, token_hash, purpose, expires_at)
                VALUES (%s, %s, %s, %s)
            """, (email, token_hash, purpose, expires_at))

        send_magic_link_email(email, token, purpose)
        return {"message": "已寄送連結至您的信箱，請於 15 分鐘內完成"}

    return {"message": "Success"}

@router.post("/magic-link/verify", response_model=TokenResponse)
def verify_magic_link(body: MagicLinkVerifyRequest):
    """
    Verifies the magic link token and creates a session.
    If purpose is registration and user doesn't exist, it creates the user.
    """
    token_hash = hashlib.sha256(body.token.encode()).hexdigest()

    with db_cursor(commit=True) as cur:
        cur.execute("""
            SELECT email, purpose, used_at, expires_at, workspace_id, invitation_id
            FROM magic_link_tokens
            WHERE token_hash = %s
        """, (token_hash,))
        record = cur.fetchone()

        if not record or record["used_at"] or record["expires_at"] < datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="連結已過期或無效，請重新申請")

        email = record["email"]
        
        # Mark as used
        cur.execute("UPDATE magic_link_tokens SET used_at = now() WHERE token_hash = %s", (token_hash,))

        # Find or create user
        cur.execute("SELECT id, display_name, email FROM users WHERE email = %s", (email,))
        user = cur.fetchone()

        if record["purpose"] == "registration":
            if not user:
                user_id = generate_id("usr")
                display_name = email.split("@")[0]
                cur.execute("""
                    INSERT INTO users (id, display_name, email, email_verified, created_at)
                    VALUES (%s, %s, %s, true, now())
                """, (user_id, display_name, email))
                user = {"id": user_id, "display_name": display_name, "email": email}
        else: # login
            if not user:
                raise HTTPException(status_code=400, detail="帳號不存在")

        # Create session tokens
        access_token = create_access_token(user["id"], user["email"], user["display_name"])
        raw_refresh, refresh_hash = generate_refresh_token()
        refresh_expires = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
        
        cur.execute(
            "INSERT INTO refresh_tokens (token_hash, user_id, expires_at) VALUES (%s, %s, %s)",
            (refresh_hash, user["id"], refresh_expires),
        )

        # Handle invitation logic
        if record["workspace_id"]:
            # Default role for invitations is 'viewer' unless specified otherwise
            # In Phase 4.6 simplified invite, we use 'viewer'
            cur.execute("""
                INSERT INTO workspace_members (workspace_id, user_id, role)
                VALUES (%s, %s, 'viewer')
                ON CONFLICT (workspace_id, user_id) DO NOTHING
            """, (record["workspace_id"], user["id"]))
        
    response = JSONResponse(
        content={"access_token": access_token, "token_type": "bearer"},
        status_code=200,
    )
    _set_refresh_cookie(response, raw_refresh)
    return response
@router.post("/register/invite/{invite_token}")
def register_with_invite(invite_token: str, body: MagicLinkRegisterRequest):
    """
    Registration flow for invite_only mode.
    Validates the invitation token before sending a magic link.
    """
    token_hash = hashlib.sha256(invite_token.encode()).hexdigest()
    
    with db_cursor(commit=True) as cur:
        cur.execute("""
            SELECT id, workspace_id, expires_at, max_uses, use_count
            FROM invitations
            WHERE token_hash = %s
        """, (token_hash,))
        inv = cur.fetchone()
        
        if not inv:
            raise HTTPException(status_code=410, detail="邀請連結無效或已過期。")
        
        if inv["expires_at"] and inv["expires_at"] < datetime.now():
            raise HTTPException(status_code=410, detail="邀請連結已過期。")
        
        if inv["max_uses"] is not None and inv["use_count"] >= inv["max_uses"]:
            raise HTTPException(status_code=410, detail="邀請連結使用次數已達上限。")
            
        # Increment use count
        cur.execute("UPDATE invitations SET use_count = use_count + 1 WHERE id = %s", (inv["id"],))
        
    # Standard magic link flow
    email = body.email.lower().strip()
    
    # Check if user already exists
    with db_cursor() as cur:
        cur.execute("SELECT id FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        purpose = "login" if user else "registration"
    
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
    
    with db_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO magic_link_tokens (email, token_hash, purpose, expires_at, workspace_id, invitation_id)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (email, token_hash, purpose, expires_at, inv["workspace_id"], inv["id"]))
        
    send_magic_link_email(email, token, purpose)
    return {"message": "已寄送連結至您的信箱，請透過連結完成註冊或登入。"}

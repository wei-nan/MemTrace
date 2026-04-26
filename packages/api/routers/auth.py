import secrets
import json
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse

from core.config import settings
from core.database import db_cursor
from core.deps import bearer, get_current_user
from core.email import send_password_reset_email, send_verification_email
from core.security import (
    check_password_policy,
    compute_signature,
    create_access_token,
    decode_token,
    generate_id,
    hash_password,
    verify_password,
)
from models.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
)
from fastapi.security import HTTPAuthorizationCredentials

router = APIRouter(prefix="/auth", tags=["auth"])

# ─── Register ─────────────────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=201)
def register(body: RegisterRequest):
    err = check_password_policy(body.password)
    if err:
        raise HTTPException(status_code=400, detail=err)

    with db_cursor(commit=True) as cur:
        cur.execute("SELECT id FROM users WHERE email = %s", (body.email,))
        if cur.fetchone():
            raise HTTPException(status_code=409, detail="Email already registered")

        user_id   = generate_id("usr")
        pw_hash   = hash_password(body.password)
        now       = datetime.now(timezone.utc)

        cur.execute("""
            INSERT INTO users (id, display_name, email, password_hash, email_verified, created_at)
            VALUES (%s, %s, %s, %s, false, %s)
        """, (user_id, body.display_name, body.email, pw_hash, now))

        # No default workspace creation — rely on onboarding or manual creation
        pass

        # generate verification token
        verify_token = secrets.token_urlsafe(32)
        cur.execute(
            "INSERT INTO email_verification_tokens (token, user_id, expires_at) VALUES (%s, %s, %s)",
            (verify_token, user_id, now + timedelta(hours=24))
        )
        send_verification_email(body.email, verify_token)

    token = create_access_token(user_id, body.email, body.display_name)
    return TokenResponse(access_token=token)


# ─── Login ────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest):
    with db_cursor(commit=True) as cur:
        cur.execute(
            "SELECT id, display_name, password_hash, email_verified, failed_login_count, locked_until FROM users WHERE email = %s",
            (body.email,)
        )
        user = cur.fetchone()

        if not user or not user["password_hash"]:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # G1: Check lockout before verifying password
        if user["locked_until"] and user["locked_until"] > datetime.now(timezone.utc):
            retry_after = int((user["locked_until"] - datetime.now(timezone.utc)).total_seconds())
            raise HTTPException(
                status_code=429,
                detail={"error": "account_locked", "retry_after": str(retry_after)},
            )

        if not verify_password(body.password, user["password_hash"]):
            # G1: Increment failed login count and maybe lock the account
            new_count = (user["failed_login_count"] or 0) + 1
            if new_count >= 5:
                cur.execute(
                    "UPDATE users SET failed_login_count = %s, locked_until = now() + INTERVAL '15 minutes' WHERE id = %s",
                    (new_count, user["id"]),
                )
            else:
                cur.execute(
                    "UPDATE users SET failed_login_count = %s WHERE id = %s",
                    (new_count, user["id"]),
                )
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # G1: Reset failure counters on successful login
        cur.execute(
            "UPDATE users SET last_login_at = now(), failed_login_count = 0, locked_until = NULL WHERE id = %s",
            (user["id"],)
        )

    token = create_access_token(user["id"], body.email, user["display_name"])
    return TokenResponse(access_token=token)


# ─── Logout ───────────────────────────────────────────────────────────────────

@router.post("/logout", status_code=204)
def logout(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    _user: dict = Depends(get_current_user),
):
    payload = decode_token(credentials.credentials)
    if payload and payload.get("jti"):
        with db_cursor(commit=True) as cur:
            cur.execute("""
                INSERT INTO session_blocklist (jti, expires_at)
                VALUES (%s, %s)
                ON CONFLICT (jti) DO NOTHING
            """, (payload["jti"], datetime.fromtimestamp(payload["exp"], tz=timezone.utc)))


# ─── Refresh ──────────────────────────────────────────────────────────────────

@router.post("/refresh", response_model=TokenResponse)
def refresh(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    token = create_access_token(payload["sub"], payload["email"], payload["display_name"])
    return TokenResponse(access_token=token)


# ─── Forgot password ──────────────────────────────────────────────────────────

@router.post("/forgot-password", status_code=204)
def forgot_password(body: ForgotPasswordRequest):
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT id FROM users WHERE email = %s", (body.email,))
        user = cur.fetchone()
        if user:
            token  = secrets.token_urlsafe(32)
            expires = datetime.now(timezone.utc) + timedelta(hours=1)
            cur.execute("""
                INSERT INTO password_reset_tokens (token, user_id, expires_at)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET token = EXCLUDED.token, expires_at = EXCLUDED.expires_at
            """, (token, user["id"], expires))
            send_password_reset_email(body.email, token)
    # Always return 204 — no user enumeration


@router.post("/reset-password", status_code=204)
def reset_password(body: ResetPasswordRequest):
    err = check_password_policy(body.new_password)
    if err:
        raise HTTPException(status_code=400, detail=err)

    with db_cursor(commit=True) as cur:
        cur.execute("""
            SELECT user_id FROM password_reset_tokens
            WHERE token = %s AND expires_at > now()
        """, (body.token,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=400, detail="Invalid or expired reset token")

        cur.execute(
            "UPDATE users SET password_hash = %s WHERE id = %s",
            (hash_password(body.new_password), row["user_id"])
        )
        cur.execute("DELETE FROM password_reset_tokens WHERE token = %s", (body.token,))

        # Invalidate all existing sessions for this user by inserting their JTIs into blocklist
        # (simplified: in production, store JTIs per user)


# ─── Current user ─────────────────────────────────────────────────────────────

@router.get("/me", response_model=UserResponse)
def me(current_user: dict = Depends(get_current_user)):
    with db_cursor() as cur:
        cur.execute(
            "SELECT id, display_name, email, password_hash, email_verified, avatar_url FROM users WHERE id = %s",
            (current_user["sub"],)
        )
        user = cur.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if user.get("password_hash"):
            providers = ["password"]
        else:
            providers = []

    return UserResponse(
        id=user["id"],
        display_name=user["display_name"],
        email=user["email"],
        email_verified=user["email_verified"],
        avatar_url=user["avatar_url"],
        auth_providers=providers,
    )



@router.get("/me/onboarding")
def get_onboarding(user: dict = Depends(get_current_user)):
    with db_cursor() as cur:
        cur.execute("SELECT onboarding FROM users WHERE id = %s", (user["sub"],))
        return cur.fetchone()["onboarding"]

@router.patch("/me/onboarding")
def update_onboarding(body: dict, user: dict = Depends(get_current_user)):
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT onboarding FROM users WHERE id = %s", (user["sub"],))
        current = cur.fetchone()["onboarding"]
        
        # Merge shallowly
        new_state = {**current, **body}
        
        cur.execute("UPDATE users SET onboarding = %s WHERE id = %s", (json.dumps(new_state), user["sub"]))
        return new_state
@router.post("/verify-email/{token}")
def verify_email(token: str):
    with db_cursor(commit=True) as cur:
        cur.execute(
            "SELECT user_id, expires_at FROM email_verification_tokens WHERE token = %s",
            (token,)
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Invalid or expired token")
        
        if row["expires_at"] < datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="Token has expired")
            
        cur.execute("UPDATE users SET email_verified = true WHERE id = %s", (row["user_id"],))
        cur.execute("DELETE FROM email_verification_tokens WHERE token = %s", (token,))
        
        return {"message": "Email verified successfully"}

@router.post("/resend-verification-email")
def resend_verification_email(user: dict = Depends(get_current_user)):
    with db_cursor(commit=True) as cur:
        # Check if already verified
        cur.execute("SELECT email, email_verified FROM users WHERE id = %s", (user["sub"],))
        u = cur.fetchone()
        if u and u["email_verified"]:
            return {"message": "Email already verified"}
            
        verify_token = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        cur.execute(
            "INSERT INTO email_verification_tokens (token, user_id, expires_at) VALUES (%s, %s, %s)",
            (verify_token, user["sub"], now + timedelta(hours=24))
        )
        send_verification_email(u["email"], verify_token)
        
        return {"message": "Verification email resent"}

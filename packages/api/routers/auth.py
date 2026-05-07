import secrets
import json
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse, RedirectResponse

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
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
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

_REFRESH_COOKIE = "mt_refresh"
_COOKIE_SECURE  = settings.app_url.startswith("https://")


def _set_refresh_cookie(response: Response, raw_token: str) -> None:
    """Plant the refresh-token httpOnly cookie."""
    response.set_cookie(
        key=_REFRESH_COOKIE,
        value=raw_token,
        httponly=True,                  # JS cannot read this cookie
        samesite="lax",
        secure=_COOKIE_SECURE,
        path="/auth/refresh",           # Only sent to the refresh endpoint
        max_age=settings.refresh_token_expire_days * 86400,
    )


def _clear_refresh_cookie(response: Response) -> None:
    """Remove the refresh-token cookie on logout."""
    response.delete_cookie(key=_REFRESH_COOKIE, path="/auth/refresh")

router = APIRouter(prefix="/auth", tags=["auth"])

# ─── Register ─────────────────────────────────────────────────────────────────

# Legacy registration disabled in Phase 4.6 (logic moved to registration.py)
# @router.post("/register", response_model=TokenResponse, status_code=201)
# def register(body: RegisterRequest):
#     ...


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

    access_token = create_access_token(user["id"], body.email, user["display_name"])

    # Issue a refresh token and store its hash in the DB
    raw_refresh, refresh_hash = generate_refresh_token()
    refresh_expires = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    with db_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO refresh_tokens (token_hash, user_id, expires_at)
            VALUES (%s, %s, %s)
            """,
            (refresh_hash, user["id"], refresh_expires),
        )

    response = JSONResponse(
        content={"access_token": access_token, "token_type": "bearer"},
        status_code=200,
    )
    _set_refresh_cookie(response, raw_refresh)
    return response


# ─── Logout ───────────────────────────────────────────────────────────────────

@router.post("/logout", status_code=204)
def logout(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    _user: dict = Depends(get_current_user),
):
    # Blocklist the current JWT
    payload = decode_token(credentials.credentials)
    if payload and payload.get("jti"):
        with db_cursor(commit=True) as cur:
            cur.execute(
                """
                INSERT INTO session_blocklist (jti, expires_at)
                VALUES (%s, %s)
                ON CONFLICT (jti) DO NOTHING
                """,
                (payload["jti"], datetime.fromtimestamp(payload["exp"], tz=timezone.utc)),
            )

    # Revoke the refresh token stored in the httpOnly cookie
    raw_refresh = request.cookies.get(_REFRESH_COOKIE)
    if raw_refresh:
        token_hash = hash_refresh_token(raw_refresh)
        with db_cursor(commit=True) as cur:
            cur.execute(
                "UPDATE refresh_tokens SET revoked_at = now() WHERE token_hash = %s",
                (token_hash,),
            )

    response = Response(status_code=204)
    _clear_refresh_cookie(response)
    return response


# ─── Refresh ──────────────────────────────────────────────────────────────────

@router.post("/refresh", response_model=TokenResponse)
def refresh(request: Request):
    """
    Exchange a valid refresh-token cookie for a new short-lived access token.
    The refresh token is rotated on every successful call (one-time-use pattern).
    """
    raw_refresh = request.cookies.get(_REFRESH_COOKIE)
    if not raw_refresh:
        raise HTTPException(status_code=401, detail="No refresh token")

    token_hash = hash_refresh_token(raw_refresh)
    with db_cursor(commit=True) as cur:
        cur.execute(
            """
            SELECT rt.user_id, rt.expires_at, u.email, u.display_name
            FROM refresh_tokens rt
            JOIN users u ON u.id = rt.user_id
            WHERE rt.token_hash = %s
              AND rt.revoked_at IS NULL
              AND rt.expires_at > now()
            """,
            (token_hash,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

        # Rotate: revoke old token and issue a new one
        cur.execute(
            "UPDATE refresh_tokens SET revoked_at = now() WHERE token_hash = %s",
            (token_hash,),
        )
        raw_new, new_hash = generate_refresh_token()
        new_expires = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
        cur.execute(
            "INSERT INTO refresh_tokens (token_hash, user_id, expires_at) VALUES (%s, %s, %s)",
            (new_hash, row["user_id"], new_expires),
        )

    access_token = create_access_token(row["user_id"], row["email"], row["display_name"])
    response = JSONResponse(
        content={"access_token": access_token, "token_type": "bearer"},
        status_code=200,
    )
    _set_refresh_cookie(response, raw_new)
    return response


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

@router.post("/me/password", status_code=204)
def update_password(body: dict, user: dict = Depends(get_current_user)):
    new_password = body.get("new_password")
    if not new_password:
        raise HTTPException(status_code=400, detail="New password required")
        
    err = check_password_policy(new_password)
    if err:
        raise HTTPException(status_code=400, detail=err)

    with db_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE users SET password_hash = %s WHERE id = %s",
            (hash_password(new_password), user["sub"])
        )

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

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from core.config import settings
from core.database import db_cursor
from core.deps import bearer, get_current_user
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

        # TODO: send verification email

    token = create_access_token(user_id, body.email, body.display_name)
    return TokenResponse(access_token=token)


# ─── Login ────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest):
    with db_cursor(commit=True) as cur:
        cur.execute(
            "SELECT id, display_name, password_hash, email_verified FROM users WHERE email = %s",
            (body.email,)
        )
        user = cur.fetchone()

        if not user or not user["password_hash"]:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        if not verify_password(body.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        cur.execute(
            "UPDATE users SET last_login_at = now() WHERE id = %s",
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
            # TODO: send reset email
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
            "SELECT id, display_name, email, email_verified, avatar_url FROM users WHERE id = %s",
            (current_user["sub"],)
        )
        user = cur.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        cur.execute(
            "SELECT provider FROM oauth_identities WHERE user_id = %s",
            (user["id"],)
        )
        providers = [r["provider"] for r in cur.fetchall()]
        if user["password_hash"] if "password_hash" in user else False:
            providers.append("password")

    return UserResponse(
        id=user["id"],
        display_name=user["display_name"],
        email=user["email"],
        email_verified=user["email_verified"],
        avatar_url=user["avatar_url"],
        auth_providers=providers,
    )


# ─── Google OAuth ─────────────────────────────────────────────────────────────

_oauth_state_store: dict[str, datetime] = {}   # in-memory; replace with Redis in production

GOOGLE_AUTH_URL   = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL  = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO   = "https://openidconnect.googleapis.com/v1/userinfo"


@router.get("/google")
def google_login():
    if not settings.google_client_id:
        raise HTTPException(status_code=501, detail="Google OAuth not configured")

    state = secrets.token_urlsafe(16)
    _oauth_state_store[state] = datetime.now(timezone.utc) + timedelta(minutes=10)

    params = {
        "client_id":     settings.google_client_id,
        "redirect_uri":  settings.google_redirect_uri,
        "response_type": "code",
        "scope":         "openid email profile",
        "state":         state,
        "access_type":   "online",
    }
    from urllib.parse import urlencode
    return RedirectResponse(f"{GOOGLE_AUTH_URL}?{urlencode(params)}")


@router.get("/google/callback", response_model=TokenResponse)
def google_callback(code: str, state: str):
    # Validate state
    expiry = _oauth_state_store.pop(state, None)
    if not expiry or datetime.now(timezone.utc) > expiry:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")

    # Exchange code for tokens
    with httpx.Client() as client:
        token_resp = client.post(GOOGLE_TOKEN_URL, data={
            "code":          code,
            "client_id":     settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri":  settings.google_redirect_uri,
            "grant_type":    "authorization_code",
        })
        token_resp.raise_for_status()
        id_token = token_resp.json().get("access_token")

        user_resp = client.get(
            GOOGLE_USERINFO,
            headers={"Authorization": f"Bearer {id_token}"},
        )
        user_resp.raise_for_status()
        guser = user_resp.json()

    google_sub  = guser["sub"]
    email       = guser["email"]
    display_name = guser.get("name", email)
    avatar_url  = guser.get("picture")

    with db_cursor(commit=True) as cur:
        # 1. Check existing OAuth identity
        cur.execute(
            "SELECT user_id FROM oauth_identities WHERE provider = 'google' AND subject = %s",
            (google_sub,)
        )
        row = cur.fetchone()
        if row:
            user_id = row["user_id"]
            cur.execute(
                "UPDATE users SET avatar_url = %s, display_name = %s, last_login_at = now() WHERE id = %s",
                (avatar_url, display_name, user_id)
            )
        else:
            # 2. Check email match with existing password account
            cur.execute("SELECT id FROM users WHERE email = %s", (email,))
            existing = cur.fetchone()
            if existing:
                user_id = existing["id"]
            else:
                # 3. Create new account
                user_id = generate_id("usr")
                cur.execute("""
                    INSERT INTO users (id, display_name, email, email_verified, avatar_url, created_at)
                    VALUES (%s, %s, %s, true, %s, now())
                """, (user_id, display_name, email, avatar_url))

            # Link Google identity
            cur.execute("""
                INSERT INTO oauth_identities (id, user_id, provider, subject)
                VALUES (%s, %s, 'google', %s)
                ON CONFLICT (provider, subject) DO NOTHING
            """, (generate_id("oid"), user_id, google_sub))

            cur.execute("UPDATE users SET last_login_at = now() WHERE id = %s", (user_id,))

    cur_display = display_name
    token = create_access_token(user_id, email, cur_display)
    return TokenResponse(access_token=token)

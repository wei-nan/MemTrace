from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import hashlib
import logging
import re

from .security import decode_token
from .database import db_cursor
from .config import settings

logger = logging.getLogger(__name__)

bearer = HTTPBearer(auto_error=False)

# S3-4a: Role hierarchy for RequireRole
ROLE_HIERARCHY = {"viewer": 0, "contributor": 1, "editor": 1, "admin": 2}

_WS_ID_PATTERN = re.compile(r"/workspaces/([^/]+)")


def _admin_email_set() -> set[str]:
    """Parse settings.admin_emails (comma-separated) into a normalized set."""
    return {e.strip().lower() for e in (settings.admin_emails or "").split(",") if e.strip()}


def _extract_workspace_id(request: Request) -> Optional[str]:
    """S3-3a: Parse workspace_id from the request path, if present."""
    m = _WS_ID_PATTERN.search(request.url.path)
    return m.group(1) if m else None


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
):
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    token = credentials.credentials

    if token.startswith("mt_"):
        key_hash = hashlib.sha256(token.encode()).hexdigest()
        ip = request.client.host if request.client else None
        ws_id = _extract_workspace_id(request)

        with db_cursor(commit=True) as cur:
            cur.execute(
                """SELECT ak.*, u.email, u.display_name
                   FROM api_keys ak JOIN users u ON u.id = ak.user_id
                   WHERE ak.key_hash = %s
                     AND ak.revoked_at IS NULL
                     AND (ak.expires_at IS NULL OR ak.expires_at > now())""",
                (key_hash,)
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=401, detail="Invalid or revoked API key")
            cur.execute(
                "UPDATE api_keys SET last_used_at = now(), last_used_ip = %s WHERE id = %s",
                (ip, row["id"])
            )

            # Option D (P4.10): branch on key_type
            if row["key_type"] == "service":
                # §29 workspace service token — fixed scopes, no dynamic role resolution
                return {
                    "sub": row["user_id"],
                    "email": row["email"],
                    "api_key_id": row["id"],
                    "role": None,
                    "scopes": row["scopes"] or [],
                    "workspace_id": row["workspace_id"],
                }

            # Account-level key — resolve role dynamically from workspace_members
            role: Optional[str] = None
            if ws_id:
                cur.execute(
                    "SELECT role FROM workspace_members WHERE user_id = %s AND workspace_id = %s",
                    (row["user_id"], ws_id),
                )
                member = cur.fetchone()
                if member:
                    role = member["role"]
                else:
                    cur.execute(
                        "SELECT id FROM workspaces WHERE id = %s AND owner_id = %s",
                        (ws_id, row["user_id"]),
                    )
                    if cur.fetchone():
                        role = "admin"

        return {
            "sub": row["user_id"],
            "email": row["email"],
            "api_key_id": row["id"],
            "role": role,
            "scopes": [],
            "workspace_id": None,
        }

    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    # Check blocklist
    jti = payload.get("jti")
    if jti:
        with db_cursor() as cur:
            cur.execute("SELECT 1 FROM session_blocklist WHERE jti = %s", (jti,))
            if cur.fetchone():
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked")

    # S3-3a: For JWT users, also resolve role from workspace_members
    ws_id = _extract_workspace_id(request)
    if ws_id and payload.get("sub"):
        with db_cursor() as cur:
            # Check owner
            cur.execute(
                "SELECT id FROM workspaces WHERE id = %s AND owner_id = %s",
                (ws_id, payload["sub"]),
            )
            if cur.fetchone():
                payload = {**payload, "role": "admin"}
            else:
                cur.execute(
                    "SELECT role FROM workspace_members WHERE user_id = %s AND workspace_id = %s",
                    (payload["sub"], ws_id),
                )
                member = cur.fetchone()
                payload = {**payload, "role": member["role"] if member else None}
    else:
        payload = {**payload, "role": None}

    return payload


# S3-4a: RequireRole — replaces RequireScope for workspace-aware role checks
def RequireRole(min_role: str):
    def _check(user: dict = Depends(get_current_user)):
        # JWT users: role already injected by get_current_user
        # API key users: role resolved via workspace_members in get_current_user
        if not user.get("role"):
            raise HTTPException(403, detail={"error": "no_membership", "message": "No membership in this workspace"})
        if ROLE_HIERARCHY.get(user["role"], -1) < ROLE_HIERARCHY.get(min_role, 0):
            raise HTTPException(403, detail={"error": "insufficient_role", "required": min_role, "actual": user["role"]})
        return user
    return _check


# DEPRECATED: 僅供 §29 workspace service token 使用
def RequireScope(required_scope: str):
    """DEPRECATED — only used by workspace service tokens (§29). Use RequireRole for all new endpoints."""
    def _require_scope(user: dict = Depends(get_current_user)):
        # only API keys have 'scopes'. jwt payload usually doesn't have it,
        # or we treat missing 'scopes' as full access (web UI)
        if "api_key_id" in user:
            scopes = user.get("scopes") or []
            if "*" not in scopes and required_scope not in scopes:
                raise HTTPException(status_code=403, detail={"error": "insufficient_scope", "required": required_scope})
        return user
    return _require_scope


def get_current_user_optional(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
):
    """Returns the payload dict if authenticated, else None."""
    if not credentials:
        return None
    token = credentials.credentials
    if token.startswith("mt_"):
        try:
            return get_current_user(request, credentials)
        except Exception:
            return None

    payload = decode_token(token)
    return payload


def require_system_admin(user: dict = Depends(get_current_user)) -> dict:
    """
    Dependency that gates an endpoint behind a system-admin check.

    A user is considered admin if their email (case-insensitive) appears in
    the ADMIN_EMAILS env var (comma-separated).

    Reject API keys outright — admin actions must come from a verified
    interactive session, not a stored credential.
    """
    if "api_key_id" in user:
        raise HTTPException(
            status_code=403,
            detail="System admin operations cannot be performed with an API key",
        )

    admin_emails = _admin_email_set()
    if not admin_emails:
        # No admin emails configured → lock down completely (fail closed)
        logger.critical(
            "SECURITY: ADMIN_EMAILS is not set — all admin endpoints are denied. "
            "Set ADMIN_EMAILS=user@example.com in your .env to enable admin operations."
        )
        raise HTTPException(
            status_code=403,
            detail="System admin not configured. Set ADMIN_EMAILS in environment.",
        )

    email = (user.get("email") or "").lower()
    if email not in admin_emails:
        raise HTTPException(status_code=403, detail="System admin access required")

    return user

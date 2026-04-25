from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import hashlib

from .security import decode_token
from .database import db_cursor

bearer = HTTPBearer(auto_error=False)


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
        return {"sub": row["user_id"], "email": row["email"],
                "scopes": row["scopes"], "api_key_id": row["id"]}

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

    return payload

def RequireScope(required_scope: str):
    def _require_scope(user: dict = Depends(get_current_user)):
        # only API keys have 'scopes'. jwt payload usually doesn't have it, or we treat missing 'scopes' as full access (web UI)
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

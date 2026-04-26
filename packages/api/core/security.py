from datetime import datetime, timedelta, timezone
from typing import Optional
import hashlib
import hmac
import logging
import secrets

import httpx
from jose import jwt, JWTError
from passlib.context import CryptContext

from .config import settings

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

ALGORITHM = "HS256"


# ── Password ──────────────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def check_password_policy(password: str) -> Optional[str]:
    """Returns an error message, or None if the password is valid."""
    if len(password) < 8:
        return "Password must be at least 8 characters."
    if len(password) > 128:
        return "Password must be at most 128 characters."
    if not any(c.isupper() for c in password):
        return "Password must contain at least one uppercase letter."
    if not any(c.islower() for c in password):
        return "Password must contain at least one lowercase letter."
    if not any(c.isdigit() for c in password):
        return "Password must contain at least one digit."

    # G2: HaveIBeenPwned k-Anonymity check
    try:
        sha1 = hashlib.sha1(password.encode()).hexdigest().upper()
        prefix, suffix = sha1[:5], sha1[5:]
        resp = httpx.get(f"https://api.pwnedpasswords.com/range/{prefix}", timeout=3.0)
        if resp.status_code == 200:
            for line in resp.text.splitlines():
                line_suffix, _ = line.split(":")
                if line_suffix.upper() == suffix:
                    return "此密碼已出現在已知洩漏資料庫中，請更換。"
    except Exception as exc:
        logger.warning("HIBP check failed (skipped): %s", exc)

    return None


# ── JWT ───────────────────────────────────────────────────────────────────────

def create_access_token(user_id: str, email: str, display_name: str) -> str:
    jti = secrets.token_hex(16)
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": user_id,
        "email": email,
        "display_name": display_name,
        "jti": jti,
        "iat": datetime.now(timezone.utc),
        "exp": expire,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except JWTError:
        return None


# ── Refresh tokens ─────────────────────────────────────────────────────────────

def generate_refresh_token() -> tuple[str, str]:
    """
    Create a new opaque refresh token.

    Returns (raw_token, token_hash) where:
    - raw_token  → sent to the client as an httpOnly cookie (one-time, never stored plaintext)
    - token_hash → stored in the DB for lookup and revocation
    """
    raw = secrets.token_urlsafe(48)   # 48 bytes → 64-char base64url string
    h = hashlib.sha256(raw.encode()).hexdigest()
    return raw, h


def hash_refresh_token(raw: str) -> str:
    """Re-derive the stored hash from a raw refresh token string."""
    return hashlib.sha256(raw.encode()).hexdigest()


# ── ID generation ─────────────────────────────────────────────────────────────

def generate_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(4)}"


# ── Content signature ─────────────────────────────────────────────────────────

def compute_signature(title: dict, content: dict, tags: list, author: str) -> str:
    import json
    payload = json.dumps({
        "title":   title,
        "content": content,
        "tags":    sorted(tags),
        "author":  author,
    }, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()

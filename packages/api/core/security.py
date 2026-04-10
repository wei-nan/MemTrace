from datetime import datetime, timedelta, timezone
from typing import Optional
import secrets
import hashlib

from jose import jwt, JWTError
from passlib.context import CryptContext

from .config import settings

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
    return None


# ── JWT ───────────────────────────────────────────────────────────────────────

def create_access_token(user_id: str, email: str, display_name: str) -> str:
    jti = secrets.token_hex(16)
    expire = datetime.now(timezone.utc) + timedelta(days=settings.access_token_expire_days)
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

"""Shared encryption helpers for provider credentials and OAuth secrets.

The encrypted payload format intentionally matches the legacy helpers that
lived in ``core.ai`` so existing AI keys remain decryptable.
"""
from __future__ import annotations

import base64

from cryptography.fernet import Fernet, InvalidToken

from core.config import settings


def _fernet() -> Fernet:
    raw = settings.secret_key.encode()[:32].ljust(32, b"0")
    return Fernet(base64.urlsafe_b64encode(raw))


def encrypt_secret(raw_value: str) -> str:
    """Encrypt a credential for storage."""
    return _fernet().encrypt(raw_value.encode()).decode()


def decrypt_secret(encrypted_value: str) -> str:
    """Decrypt a stored credential."""
    try:
        return _fernet().decrypt(encrypted_value.encode()).decode()
    except InvalidToken as exc:
        raise ValueError(
            "Failed to decrypt credential; the server secret key may have changed."
        ) from exc


__all__ = ["decrypt_secret", "encrypt_secret"]

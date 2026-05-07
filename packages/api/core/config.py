import os
import logging

from pydantic import model_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

# Known weak / default keys that must never be used in production
_WEAK_KEYS = {
    "1234567890abcdef1234567890abcdef",
    "changeme",
    "secret",
    "your-secret-key",
    "supersecretkey",
}


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    # Short-lived access token (default 60 min).
    # Set ACCESS_TOKEN_EXPIRE_MINUTES in .env to override.
    access_token_expire_minutes: int = 60
    # Long-lived refresh token (default 30 days, stored server-side).
    refresh_token_expire_days: int = 30
    # Kept for backward compatibility; ignored when access_token_expire_minutes is set.
    access_token_expire_days: int = 7

    # G4: AI usage retention (months)
    ai_usage_retention_months: int = 6

    # ── Email ──────────────────────────────────────────────────────────────────
    # Provider: "resend" (default) | "smtp" | "disabled"
    email_provider:   str = "disabled"
    email_api_key:    str = ""           # Resend API key (re_xxx...)
    email_from:       str = "noreply@memtrace.app"
    email_from_name:  str = "MemTrace"
    # SMTP fallback (only used when email_provider = "smtp")
    smtp_host:        str = "smtp.gmail.com"
    smtp_port:        int = 587
    smtp_user:        str = ""
    smtp_password:    str = ""
    # App base URL — used in email link generation
    app_url:          str = "http://localhost:5173"
    internal_service_token: str = ""

    # ── System admin (comma-separated emails) ─────────────────────────────────
    # Users whose email matches one of these are treated as system administrators.
    # Required for backup configuration and other privileged operations.
    admin_emails: str = ""
    registration_mode: str = "invite_only"  # "open" | "domain" | "approval" | "invite_only" | "closed"
    registration_domains: list[str] = []    # ["example.com"]
    allow_anonymous: bool = False           # Whether to allow guest view for public workspaces
    allowed_origins: list[str] = ["http://localhost:5173"]  # CORS allowed origins

    class Config:
        env_file = "../../.env"
        extra = "ignore"

    @model_validator(mode="after")
    def _validate_secret_key(self) -> "Settings":
        key = self.secret_key
        is_weak = key in _WEAK_KEYS or len(key) < 32

        if is_weak:
            # Allow bypass only when explicitly opted-in (dev convenience)
            if os.environ.get("ALLOW_WEAK_SECRET_KEY") == "1":
                logger.warning(
                    "⚠️  SECRET_KEY is weak or a known default. "
                    "This is permitted because ALLOW_WEAK_SECRET_KEY=1 is set, "
                    "but MUST NOT be used in production."
                )
            else:
                raise ValueError(
                    "SECRET_KEY is too short or is a known insecure default. "
                    "Set a strong random value (≥ 32 characters) in your .env file. "
                    "Generate one with:  python -c \"import secrets; print(secrets.token_hex(32))\"\n"
                    "To bypass in local development only, set ALLOW_WEAK_SECRET_KEY=1."
                )
        return self


settings = Settings()

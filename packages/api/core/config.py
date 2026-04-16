from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    access_token_expire_days: int = 7

    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"

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

    class Config:
        env_file = "../../.env"
        extra = "ignore"


settings = Settings()

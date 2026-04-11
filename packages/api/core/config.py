from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    access_token_expire_days: int = 7

    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"

    # Managed AI credits — server-level keys used when user has no own key
    openai_api_key:    str = ""
    anthropic_api_key: str = ""

    # Free tier token limit per user per month (default 50 000)
    ai_free_token_limit: int = 50_000

    class Config:
        env_file = "../../.env"
        extra = "ignore"


settings = Settings()

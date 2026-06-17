import os
import logging
from typing import Optional

from core.database import db_cursor, is_postgres
from core.ai import encrypt_api_key

logger = logging.getLogger(__name__)

def provision_safety_key(api_key: str, provider: Optional[str] = None) -> bool:
    """
    Idempotently provision the API key for system:safety.
    Detects provider if not provided.
    """
    if not api_key:
        return False
        
    # Auto-detect provider based on key prefix if not specified
    if not provider:
        if api_key.startswith("AIzaSy"):
            provider = "gemini"
        elif api_key.startswith("sk-ant-"):
            provider = "anthropic"
        elif api_key.startswith("sk-") or api_key.startswith("org-"):
            provider = "openai"
        else:
            # Fallback
            provider = "gemini"
            
    # Validate provider against schema constraints (lowercase check)
    provider = provider.lower()
    
    # Generate hint (last 4 chars)
    hint = api_key[-4:] if len(api_key) >= 4 else "****"
    
    # Encrypt the API key
    key_enc = encrypt_api_key(api_key)
    
    placeholder = "%s" if is_postgres() else "?"
    with db_cursor(commit=True) as cur:
        # 1. Ensure system:safety user exists
        cur.execute("SELECT id FROM users WHERE id = 'system:safety'")
        if not cur.fetchone():
            logger.info("Provisioning 'system:safety' system user...")
            cur.execute(
                """
                INSERT INTO users (id, display_name, email, email_verified)
                VALUES ('system:safety', 'System Safety', 'safety@memtrace.local', true)
                """
            )
            
        # 2. Idempotent key insertion (IF NOT EXISTS / ON CONFLICT)
        from core.security import generate_id
        
        # Check if key already exists for this provider and user
        cur.execute(
            f"SELECT id FROM user_ai_keys WHERE user_id = 'system:safety' AND provider = {placeholder}",
            (provider,)
        )
        existing = cur.fetchone()
        
        if existing:
            logger.info(f"Safety key already configured for provider '{provider}' (no-op).")
            return False
            
        key_id = generate_id("uak")
        cur.execute(
            f"""
            INSERT INTO user_ai_keys (id, user_id, provider, key_enc, key_hint)
            VALUES ({placeholder}, 'system:safety', {placeholder}, {placeholder}, {placeholder})
            ON CONFLICT (user_id, provider) DO NOTHING
            """,
            (key_id, provider, key_enc, hint)
        )
        logger.info(f"Successfully provisioned safety key for provider '{provider}'.")
        return True

def bootstrap_safety_from_env() -> None:
    """
    Check environment for MEMTRACE_SAFETY_API_KEY and trigger provisioning.
    Called on application startup.
    """
    env_key = os.environ.get("MEMTRACE_SAFETY_API_KEY")
    env_provider = os.environ.get("MEMTRACE_SAFETY_PROVIDER")
    
    if env_key:
        try:
            provision_safety_key(env_key, env_provider)
        except Exception as e:
            logger.error(f"Failed to bootstrap safety key from environment: {e}")

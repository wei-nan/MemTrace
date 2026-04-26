-- Migration 004: refresh token storage
-- Access tokens are now short-lived (60 min).
-- Refresh tokens live 30 days and are stored server-side so they can be
-- individually revoked (e.g. on logout or suspicious activity).

CREATE TABLE IF NOT EXISTS refresh_tokens (
    token_hash  TEXT        PRIMARY KEY,           -- SHA-256 of the raw token
    user_id     TEXT        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at  TIMESTAMPTZ NOT NULL,
    revoked_at  TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS refresh_tokens_user_idx    ON refresh_tokens (user_id);
CREATE INDEX IF NOT EXISTS refresh_tokens_expires_idx ON refresh_tokens (expires_at);

-- Purge expired / revoked refresh tokens (called from nightly cleanup)
CREATE OR REPLACE FUNCTION purge_old_refresh_tokens() RETURNS void LANGUAGE sql AS $$
  DELETE FROM refresh_tokens
  WHERE expires_at < now() - INTERVAL '1 day'
     OR revoked_at IS NOT NULL;
$$;

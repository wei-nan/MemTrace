-- Phase 4.6 Schema changes
-- P4.6-F1-1: Add allow_anonymous_view to workspaces
ALTER TABLE workspaces
    ADD COLUMN IF NOT EXISTS allow_anonymous_view BOOLEAN NOT NULL DEFAULT FALSE;

-- P4.6-F4-open-1: Magic link tokens table
CREATE TABLE IF NOT EXISTS magic_link_tokens (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       VARCHAR(320) NOT NULL,
    token_hash  CHAR(64) NOT NULL UNIQUE,   -- SHA-256(raw_token)
    purpose     VARCHAR(32) NOT NULL,       -- 'registration' | 'login'
    expires_at  TIMESTAMP NOT NULL,
    used_at     TIMESTAMP,
    workspace_id VARCHAR(64),              -- invite_only mode
    invitation_id UUID,                    -- related to invitations (Sprint 5)
    created_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_magic_token_hash ON magic_link_tokens (token_hash);
CREATE INDEX IF NOT EXISTS idx_magic_token_email ON magic_link_tokens (email, purpose);

-- P4.6-F4-approval-1: User registrations for approval mode
CREATE TABLE IF NOT EXISTS user_registrations (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       VARCHAR(320) NOT NULL UNIQUE,
    reason      TEXT,
    status      VARCHAR(20) NOT NULL DEFAULT 'pending', -- 'pending' | 'approved' | 'rejected'
    reviewer_id TEXT REFERENCES users(id),
    reviewed_at TIMESTAMP,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

-- P4.6-F6-1: Anonymous access log
CREATE TABLE IF NOT EXISTS anonymous_access_log (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    ip_address   VARCHAR(45) NOT NULL,
    user_agent   TEXT,
    path         TEXT NOT NULL,
    method       VARCHAR(10) NOT NULL,
    created_at   TIMESTAMP NOT NULL DEFAULT NOW()
);

-- P4.6-F4-invite-1: Invitations table
CREATE TABLE IF NOT EXISTS invitations (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    email        VARCHAR(320), -- Optional: if target email is known
    token        VARCHAR(64) NOT NULL UNIQUE,
    expires_at   TIMESTAMP,
    max_uses     INTEGER,
    use_count    INTEGER NOT NULL DEFAULT 0,
    created_by   TEXT REFERENCES users(id),
    created_at   TIMESTAMP NOT NULL DEFAULT NOW()
);

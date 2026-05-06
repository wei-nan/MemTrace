-- Sprint 5 Schema Updates: Aligning anonymous_access_log and invitations
-- Ref: P4.6-F6-1, P4.6-F4-invite-1

-- 1. Align anonymous_access_log
-- We drop the old structure and use the one specified in Sprint 5 requirements
DROP TABLE IF EXISTS anonymous_access_log;

CREATE TABLE anonymous_access_log (
    id           BIGSERIAL PRIMARY KEY,
    workspace_id VARCHAR(64) NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    node_id      VARCHAR(64),
    ip_hash      CHAR(64) NOT NULL,      -- SHA-256(IP + ANON_LOG_SALT)
    user_agent_hash CHAR(64),            -- SHA-256(User-Agent + ANON_LOG_SALT)
    endpoint     VARCHAR(64) NOT NULL,   -- e.g. 'metadata', 'graph', 'node_detail', 'search'
    accessed_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_anon_access_ws_time ON anonymous_access_log (workspace_id, accessed_at DESC);

-- 2. Hardening invitations (P4.6-F4-invite-1)
-- 036 already added token_hash, but let's ensure the structure matches Sprint 5 requirements
-- We'll keep the table from 035 but ensure it's clean
ALTER TABLE invitations DROP COLUMN IF EXISTS token; -- Ensure plaintext token is gone
ALTER TABLE invitations ALTER COLUMN token_hash SET NOT NULL;
ALTER TABLE invitations ADD COLUMN IF NOT EXISTS max_uses INTEGER DEFAULT NULL;
ALTER TABLE invitations ADD COLUMN IF NOT EXISTS use_count INTEGER NOT NULL DEFAULT 0;

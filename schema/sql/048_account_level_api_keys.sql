SET client_encoding = 'UTF8';
-- P4.10 Migration: Account-level API keys (Option D — key_type discriminator)
-- Rather than dropping scopes/workspace_id, we add a key_type column so both
-- account-level keys and workspace service tokens can coexist in the same table.
--
-- key_type = 'account'  → personal key, no fixed scope, role resolved dynamically
--                          from workspace_members on every request.
-- key_type = 'service'  → §29 workspace service token, fixed scopes, workspace-bound.

ALTER TABLE api_keys
  ADD COLUMN IF NOT EXISTS key_type VARCHAR(20) NOT NULL DEFAULT 'account'
    CHECK (key_type IN ('account', 'service'));

-- Backfill: existing workspace-scoped keys are service tokens
UPDATE api_keys SET key_type = 'service' WHERE workspace_id IS NOT NULL;

-- Ensure a user-first index on workspace_members for per-request role lookups
CREATE INDEX IF NOT EXISTS idx_wsm_user ON workspace_members(user_id);

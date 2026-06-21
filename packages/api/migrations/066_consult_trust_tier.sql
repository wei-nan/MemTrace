-- Migration 066: consult_trust_tier, consult_provider on workspaces & is_platform_admin on users (Phase 6.4)

ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS consult_trust_tier TEXT DEFAULT 'ask' CHECK (consult_trust_tier IN ('ask', 'full_trust'));
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS consult_provider TEXT;

ALTER TABLE users ADD COLUMN IF NOT EXISTS is_platform_admin BOOLEAN DEFAULT FALSE;

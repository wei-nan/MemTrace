-- ─────────────────────────────────────────────────────────────────
--  MemTrace — Migration 002: AI Provider & Credit System
-- ─────────────────────────────────────────────────────────────────

-- ─── ENUM ─────────────────────────────────────────────────────────

CREATE TYPE ai_provider AS ENUM ('openai', 'anthropic');

CREATE TYPE ai_feature AS ENUM (
  'extraction',    -- document → nodes
  'embedding',     -- semantic search vector
  'restructure'    -- node restructuring
);

-- ─── USER-SUPPLIED API KEYS ───────────────────────────────────────
-- Users may store their own provider API keys server-side (encrypted).
-- The key is AES-256-GCM encrypted with the server SECRET_KEY before storage.
-- The raw key is never logged or returned after creation.

CREATE TABLE user_ai_keys (
  id           TEXT PRIMARY KEY,           -- uak_<hex8>
  user_id      TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  provider     ai_provider NOT NULL,
  key_enc      TEXT NOT NULL,              -- AES-256-GCM ciphertext (base64)
  key_hint     TEXT NOT NULL,              -- last 4 chars of raw key, shown in UI
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_used_at TIMESTAMPTZ,
  UNIQUE (user_id, provider)               -- one key per provider per user
);

CREATE INDEX idx_user_ai_keys_user ON user_ai_keys (user_id);

-- ─── MANAGED CREDIT LEDGER ────────────────────────────────────────
-- Each row records one AI call against the managed credit pool.
-- tokens_used = prompt_tokens + completion_tokens as reported by the provider.

CREATE TABLE ai_credit_ledger (
  id           TEXT PRIMARY KEY,           -- ledger_<hex8>
  user_id      TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  feature      ai_feature NOT NULL,
  provider     ai_provider NOT NULL,
  model        TEXT NOT NULL,              -- e.g. 'gpt-4o-mini', 'claude-haiku-4-5'
  tokens_used  INTEGER NOT NULL CHECK (tokens_used >= 0),
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  workspace_id TEXT REFERENCES workspaces(id) ON DELETE SET NULL,
  node_id      TEXT                        -- optional, for extraction traceability
);

CREATE INDEX idx_ledger_user     ON ai_credit_ledger (user_id);
CREATE INDEX idx_ledger_user_ts  ON ai_credit_ledger (user_id, created_at DESC);

-- ─── FREE TIER QUOTA ──────────────────────────────────────────────
-- Tracks the monthly free-tier token allowance per user.
-- Reset on the 1st of each calendar month by a scheduled job.

CREATE TABLE ai_credit_quota (
  user_id          TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  free_tokens_used INTEGER NOT NULL DEFAULT 0,
  quota_month      DATE    NOT NULL DEFAULT date_trunc('month', now()),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ─── HELPER: get remaining free tokens for a user this month ───────

CREATE OR REPLACE FUNCTION ai_free_tokens_remaining(
  p_user_id TEXT,
  p_free_limit INTEGER DEFAULT 50000
)
RETURNS INTEGER AS $$
DECLARE
  v_used INTEGER;
  v_month DATE := date_trunc('month', now());
BEGIN
  SELECT COALESCE(free_tokens_used, 0) INTO v_used
  FROM ai_credit_quota
  WHERE user_id = p_user_id AND quota_month = v_month;

  IF NOT FOUND THEN
    -- Auto-provision quota row on first access
    INSERT INTO ai_credit_quota (user_id, free_tokens_used, quota_month)
    VALUES (p_user_id, 0, v_month)
    ON CONFLICT (user_id) DO UPDATE
      SET free_tokens_used = 0, quota_month = v_month, updated_at = now()
      WHERE ai_credit_quota.quota_month < v_month;

    RETURN p_free_limit;
  END IF;

  RETURN GREATEST(0, p_free_limit - v_used);
END;
$$ LANGUAGE plpgsql;

-- ─── HELPER: deduct tokens from free quota ────────────────────────

CREATE OR REPLACE FUNCTION ai_deduct_free_tokens(
  p_user_id TEXT,
  p_tokens  INTEGER
)
RETURNS VOID AS $$
DECLARE
  v_month DATE := date_trunc('month', now());
BEGIN
  INSERT INTO ai_credit_quota (user_id, free_tokens_used, quota_month, updated_at)
  VALUES (p_user_id, p_tokens, v_month, now())
  ON CONFLICT (user_id) DO UPDATE
    SET free_tokens_used = ai_credit_quota.free_tokens_used + p_tokens,
        updated_at       = now();
END;
$$ LANGUAGE plpgsql;

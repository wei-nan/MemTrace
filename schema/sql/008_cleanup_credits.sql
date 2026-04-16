-- ─────────────────────────────────────────────────────────────────
--  MemTrace — Migration 008: Cleanup Credit System
-- ─────────────────────────────────────────────────────────────────

-- Cleanup tables related to managed credits and free tier
DROP TABLE IF EXISTS ai_credit_quota CASCADE;

-- Drop helper functions
DROP FUNCTION IF EXISTS ai_free_tokens_remaining(TEXT, INTEGER);
DROP FUNCTION IF EXISTS ai_deduct_free_tokens(TEXT, INTEGER);

-- Note: we keep ai_credit_ledger as it remains the authoritative record
-- for all AI calls (regardless of key origin) per updated SPEC §21.

-- ─────────────────────────────────────────────────────────────────
--  MemTrace — Migration 006: Add Gemini to AI Provider Enum
-- ─────────────────────────────────────────────────────────────────

ALTER TYPE ai_provider ADD VALUE 'gemini';

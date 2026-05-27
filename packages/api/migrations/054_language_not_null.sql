-- 054_language_not_null.sql
-- Phase 6 S2-T08: Enforce NOT NULL on workspaces.language.
-- 
-- PREREQUISITE: ALL workspaces must have language set before applying this migration.
-- Run scripts/phase6/split_bilingual.py first and verify with:
--   SELECT count(*) FROM workspaces WHERE language IS NULL;  -- must be 0
--
-- Also makes workspaces.name NOT NULL (after consolidate_fields.py has run).
--
-- IMPORTANT: Apply this migration only after Stage 2 audit passes (M5 + M7).

-- Backfill language and name for existing workspaces before enforcing NOT NULL
UPDATE workspaces SET language = 'zh-TW' WHERE language IS NULL;
UPDATE workspaces SET name = coalesce(name_zh, name_en, 'Workspace') WHERE name IS NULL;

ALTER TABLE workspaces
  ALTER COLUMN language SET NOT NULL;

-- Make name NOT NULL now that all workspaces have it populated
ALTER TABLE workspaces
  ALTER COLUMN name SET NOT NULL;


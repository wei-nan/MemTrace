-- 054_language_not_null.sql
-- Phase 6 S2-T08: Enforce NOT NULL on workspaces.language and name.
-- Idempotent: safe to run on fresh DBs (adds columns if missing).

-- Add columns if they don't exist yet (guards for fresh / CI databases)
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS language TEXT;
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS name     TEXT;

-- Backfill language
UPDATE workspaces SET language = 'zh-TW' WHERE language IS NULL;

-- Backfill name from bilingual columns when they still exist
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'workspaces' AND column_name = 'name_zh'
    ) THEN
        UPDATE workspaces
        SET name = coalesce(name_zh, name_en, 'Workspace')
        WHERE name IS NULL;
    END IF;
END;
$$;
-- Final fallback: any remaining NULLs get a default
UPDATE workspaces SET name = 'Workspace' WHERE name IS NULL;

ALTER TABLE workspaces ALTER COLUMN language SET NOT NULL;
ALTER TABLE workspaces ALTER COLUMN name     SET NOT NULL;


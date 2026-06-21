-- 050_workspace_language.sql
-- Phase 6: Add language field and linked_workspace_id to workspaces.
-- language is nullable at this stage; NOT NULL enforcement comes in 054_language_not_null.sql
-- after all existing workspaces have been classified and split.

DO $$ BEGIN
  CREATE TYPE workspace_language AS ENUM ('zh-TW', 'en');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

ALTER TABLE workspaces
  ADD COLUMN IF NOT EXISTS language workspace_language,
  ADD COLUMN IF NOT EXISTS linked_workspace_id TEXT
    REFERENCES workspaces(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_ws_language ON workspaces (language);
CREATE INDEX IF NOT EXISTS idx_ws_linked   ON workspaces (linked_workspace_id);

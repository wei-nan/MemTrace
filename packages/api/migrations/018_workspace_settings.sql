SET client_encoding = 'UTF8';
-- C5: Workspace settings for reviewer profile
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS settings JSONB DEFAULT '{}'::jsonb;

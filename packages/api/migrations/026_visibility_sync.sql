-- Migration: 026_visibility_sync.sql
-- Description: Ensure kb_visibility enum is correct and remove accidental 'evergreen' value.
-- Note: 'evergreen' is a kb_type, not a visibility level.

-- 1. Add missing values if they don't exist
ALTER TYPE kb_visibility ADD VALUE IF NOT EXISTS 'restricted';
ALTER TYPE kb_visibility ADD VALUE IF NOT EXISTS 'conditional_public';

-- 2. Cleanup: We cannot easily drop enum values in Postgres without recreation, 
-- but since no data uses 'evergreen' for visibility, it's just a cosmetic issue.
-- However, we can ensure existing workspaces are migrated if they were somehow set to it.
UPDATE workspaces SET visibility = 'private' WHERE visibility::text = 'evergreen';

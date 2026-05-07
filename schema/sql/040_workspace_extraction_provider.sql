-- Add per-workspace extraction provider preference.
-- NULL = fall back to user's default provider selection.
ALTER TABLE workspaces
  ADD COLUMN IF NOT EXISTS extraction_provider TEXT;

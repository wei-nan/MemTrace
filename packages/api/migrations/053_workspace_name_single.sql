-- 053_workspace_name_single.sql
-- Phase 6 S2-T07: Add single-language 'name' column to workspaces.
-- Filled by scripts/phase6/consolidate_fields.py after language is set on all workspaces.
-- NOT NULL enforcement happens after the consolidation script completes.

ALTER TABLE workspaces
  ADD COLUMN IF NOT EXISTS name TEXT;

CREATE INDEX IF NOT EXISTS idx_workspaces_name ON workspaces (name);

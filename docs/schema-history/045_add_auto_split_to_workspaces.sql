-- Migration: 045_add_auto_split_to_workspaces.sql
-- Description: Add auto_split boolean to workspaces to enable automated node decomposition.
-- Phase 4.8: S9-5a

ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS auto_split BOOLEAN DEFAULT FALSE;

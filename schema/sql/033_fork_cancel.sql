-- Migration: 033_fork_cancel.sql
-- Description: Add fork flag and cancellation support to workspace_clone_jobs.
--   is_fork      : TRUE when the job was triggered by a public KB fork (vs. own workspace clone)
--   cancelled_at : timestamp set when the job is cancelled by the user

ALTER TABLE workspace_clone_jobs
  ADD COLUMN IF NOT EXISTS is_fork      BOOLEAN    NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS cancelled_at TIMESTAMPTZ;

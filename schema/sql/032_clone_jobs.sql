-- Migration: 032_clone_jobs.sql
-- Description: Add workspace clone/rebuild job tracking table.

CREATE TABLE IF NOT EXISTS workspace_clone_jobs (
    id              TEXT PRIMARY KEY,
    source_ws_id    TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    target_ws_id    TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    status          TEXT NOT NULL DEFAULT 'pending',
    total_nodes     INTEGER NOT NULL DEFAULT 0,
    processed_nodes INTEGER NOT NULL DEFAULT 0,
    error_msg       TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE OR REPLACE FUNCTION update_clone_job_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER trg_update_clone_job_timestamp
    BEFORE UPDATE ON workspace_clone_jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_clone_job_timestamp();

-- Migration 110: persistent job observability for scheduler and review jobs.

CREATE TABLE IF NOT EXISTS scheduler_heartbeats (
    job_name         TEXT PRIMARY KEY,
    status           TEXT NOT NULL DEFAULT 'unknown'
                     CHECK (status IN ('running', 'success', 'failed', 'skipped', 'unknown')),
    last_run_at      TIMESTAMPTZ,
    last_success_at  TIMESTAMPTZ,
    last_failure_at  TIMESTAMPTZ,
    duration_ms      INTEGER,
    run_count        INTEGER NOT NULL DEFAULT 0,
    failure_count    INTEGER NOT NULL DEFAULT 0,
    last_run_id      TEXT,
    last_error       TEXT,
    metadata         JSONB NOT NULL DEFAULT '{}',
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS job_runs (
    id              TEXT PRIMARY KEY,
    job_name        TEXT NOT NULL,
    workspace_id    TEXT REFERENCES workspaces(id) ON DELETE SET NULL,
    trigger         TEXT NOT NULL DEFAULT 'scheduler',
    status          TEXT NOT NULL DEFAULT 'running'
                    CHECK (status IN ('running', 'success', 'failed', 'skipped')),
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at     TIMESTAMPTZ,
    duration_ms     INTEGER,
    scanned_count   INTEGER,
    processed_count INTEGER,
    created_count   INTEGER,
    skipped_count   INTEGER,
    failed_count    INTEGER,
    error           TEXT,
    summary         JSONB NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_job_runs_workspace_started
    ON job_runs(workspace_id, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_job_runs_job_started
    ON job_runs(job_name, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_job_runs_status_started
    ON job_runs(status, started_at DESC);

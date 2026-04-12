-- ─────────────────────────────────────────────────────────────────
--  MemTrace — Migration 004: Ingestion Tracking
-- ─────────────────────────────────────────────────────────────────

CREATE TYPE ingestion_status AS ENUM ('processing', 'completed', 'failed');

CREATE TABLE ingestion_logs (
    id           TEXT PRIMARY KEY,           -- ing_<hex8>
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id      TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    filename     TEXT NOT NULL,
    status       ingestion_status NOT NULL DEFAULT 'processing',
    error_msg    TEXT,                       -- Capture API errors here
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_ingestion_logs_ws ON ingestion_logs (workspace_id, created_at DESC);

-- Migration 115: conductor hooks, node scale metadata, and async safety queue.
-- Canonical twin of packages/api/migrations/111_conductor_safety_queue.sql.

ALTER TABLE memory_nodes
    ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}';

CREATE TABLE IF NOT EXISTS conductor_hook_subscriptions (
    id              TEXT PRIMARY KEY,
    workspace_id    TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    url             TEXT NOT NULL,
    secret          TEXT,
    enabled         BOOLEAN NOT NULL DEFAULT TRUE,
    event_filter    JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (workspace_id, name)
);

CREATE INDEX IF NOT EXISTS idx_conductor_hooks_workspace
    ON conductor_hook_subscriptions(workspace_id, enabled);

CREATE TABLE IF NOT EXISTS conductor_deliveries (
    id              TEXT PRIMARY KEY,
    workspace_id    TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    hook_id         TEXT NOT NULL REFERENCES conductor_hook_subscriptions(id) ON DELETE CASCADE,
    node_id         TEXT REFERENCES memory_nodes(id) ON DELETE SET NULL,
    event_id        TEXT NOT NULL,
    correlation_id  TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'delivered', 'failed', 'skipped')),
    attempts        INTEGER NOT NULL DEFAULT 0,
    last_error      TEXT,
    payload         JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    delivered_at    TIMESTAMPTZ,
    UNIQUE (hook_id, event_id)
);

CREATE INDEX IF NOT EXISTS idx_conductor_deliveries_workspace_created
    ON conductor_deliveries(workspace_id, created_at DESC);

CREATE TABLE IF NOT EXISTS safety_review_queue (
    id              TEXT PRIMARY KEY,
    event_id        TEXT NOT NULL UNIQUE,
    workspace_id    TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    node_id         TEXT REFERENCES memory_nodes(id) ON DELETE CASCADE,
    event_type      TEXT NOT NULL,
    source          TEXT NOT NULL DEFAULT 'node_event',
    risk_hint       TEXT,
    status          TEXT NOT NULL DEFAULT 'queued'
                    CHECK (status IN ('queued', 'processing', 'done', 'failed', 'skipped')),
    priority        INTEGER NOT NULL DEFAULT 50,
    attempts        INTEGER NOT NULL DEFAULT 0,
    max_attempts    INTEGER NOT NULL DEFAULT 3,
    next_run_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    lease_until     TIMESTAMPTZ,
    last_error      TEXT,
    result          JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_safety_review_queue_ready
    ON safety_review_queue(priority ASC, next_run_at ASC, created_at ASC)
    WHERE status IN ('queued', 'failed');

CREATE INDEX IF NOT EXISTS idx_safety_review_queue_processing_lease
    ON safety_review_queue(lease_until ASC)
    WHERE status = 'processing';

CREATE INDEX IF NOT EXISTS idx_safety_review_queue_workspace_created
    ON safety_review_queue(workspace_id, created_at DESC);

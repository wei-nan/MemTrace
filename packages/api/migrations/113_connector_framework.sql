-- Migration 113: personal connector accounts with explicit workspace bindings.

CREATE TABLE IF NOT EXISTS connector_accounts (
    id                    TEXT PRIMARY KEY,
    owner_user_id         TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider              TEXT NOT NULL,
    provider_instance_url TEXT NOT NULL DEFAULT '',
    provider_account_id   TEXT NOT NULL,
    display_name          TEXT,
    auth_type             TEXT NOT NULL DEFAULT 'oauth',
    credentials_enc       TEXT,
    scopes                TEXT[] NOT NULL DEFAULT '{}',
    status                TEXT NOT NULL DEFAULT 'active'
                          CHECK (status IN ('active', 'expired', 'revoked', 'error')),
    metadata              JSONB NOT NULL DEFAULT '{}',
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (owner_user_id, provider, provider_instance_url, provider_account_id)
);

CREATE TABLE IF NOT EXISTS connector_bindings (
    id                      TEXT PRIMARY KEY,
    connector_account_id    TEXT NOT NULL REFERENCES connector_accounts(id) ON DELETE CASCADE,
    workspace_id            TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    external_container_type TEXT NOT NULL,
    external_container_id   TEXT NOT NULL,
    external_container_name TEXT,
    sync_direction          TEXT NOT NULL DEFAULT 'inbound'
                            CHECK (sync_direction IN ('inbound', 'outbound', 'bidirectional')),
    permissions             JSONB NOT NULL DEFAULT '{}',
    event_filters           JSONB NOT NULL DEFAULT '{}',
    enabled                 BOOLEAN NOT NULL DEFAULT TRUE,
    created_by              TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (
        connector_account_id,
        workspace_id,
        external_container_type,
        external_container_id
    )
);

CREATE TABLE IF NOT EXISTS connector_external_objects (
    id                    TEXT PRIMARY KEY,
    binding_id            TEXT NOT NULL REFERENCES connector_bindings(id) ON DELETE CASCADE,
    provider_object_type  TEXT NOT NULL,
    provider_object_id    TEXT NOT NULL,
    memtrace_object_type  TEXT NOT NULL,
    memtrace_object_id    TEXT NOT NULL,
    source_url            TEXT,
    external_version      TEXT,
    metadata              JSONB NOT NULL DEFAULT '{}',
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (
        binding_id,
        provider_object_type,
        provider_object_id,
        memtrace_object_type,
        memtrace_object_id
    )
);

CREATE TABLE IF NOT EXISTS connector_events (
    id                TEXT PRIMARY KEY,
    connector_account_id TEXT NOT NULL REFERENCES connector_accounts(id) ON DELETE CASCADE,
    binding_id        TEXT REFERENCES connector_bindings(id) ON DELETE SET NULL,
    provider_event_id TEXT NOT NULL,
    event_type        TEXT NOT NULL,
    payload           JSONB NOT NULL DEFAULT '{}',
    status            TEXT NOT NULL DEFAULT 'pending'
                      CHECK (status IN ('pending', 'processing', 'processed', 'failed', 'ignored')),
    attempts          INTEGER NOT NULL DEFAULT 0,
    last_error        TEXT,
    received_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed_at      TIMESTAMPTZ,
    UNIQUE (connector_account_id, provider_event_id)
);

CREATE TABLE IF NOT EXISTS connector_sync_cursors (
    binding_id          TEXT PRIMARY KEY REFERENCES connector_bindings(id) ON DELETE CASCADE,
    cursor_value        TEXT,
    last_synced_at      TIMESTAMPTZ,
    last_success_at     TIMESTAMPTZ,
    last_error          TEXT,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS connector_runs (
    id                TEXT PRIMARY KEY,
    binding_id        TEXT NOT NULL REFERENCES connector_bindings(id) ON DELETE CASCADE,
    trigger           TEXT NOT NULL DEFAULT 'manual',
    status            TEXT NOT NULL DEFAULT 'running'
                      CHECK (status IN ('running', 'success', 'failed', 'skipped')),
    started_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at       TIMESTAMPTZ,
    scanned_count     INTEGER,
    created_count     INTEGER,
    updated_count     INTEGER,
    skipped_count     INTEGER,
    failed_count      INTEGER,
    error             TEXT,
    summary           JSONB NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_connector_accounts_owner
    ON connector_accounts(owner_user_id, provider);
CREATE INDEX IF NOT EXISTS idx_connector_bindings_workspace
    ON connector_bindings(workspace_id, enabled);
CREATE INDEX IF NOT EXISTS idx_connector_events_pending
    ON connector_events(status, received_at);
CREATE INDEX IF NOT EXISTS idx_connector_runs_binding_time
    ON connector_runs(binding_id, started_at DESC);

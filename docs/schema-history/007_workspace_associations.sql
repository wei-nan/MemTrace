SET client_encoding = 'UTF8';
CREATE TABLE IF NOT EXISTS workspace_associations (
    id            TEXT PRIMARY KEY,
    source_ws_id  TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    target_ws_id  TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(source_ws_id, target_ws_id)
);

CREATE INDEX idx_ws_assoc_source ON workspace_associations(source_ws_id);

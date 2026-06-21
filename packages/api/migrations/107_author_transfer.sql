-- S3-T03: Author departure and authorship transfer
CREATE TABLE IF NOT EXISTS author_tombstones (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    left_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    transferred_to TEXT REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE (user_id, workspace_id)
);

CREATE INDEX IF NOT EXISTS idx_author_tombstones_ws ON author_tombstones(workspace_id);

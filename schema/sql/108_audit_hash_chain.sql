-- S3-T05: Audit Trail with Hash Chain
CREATE TABLE IF NOT EXISTS audit_trail (
    id SERIAL PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    action TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    metadata JSONB,
    prev_hash TEXT,
    curr_hash TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_workspace ON audit_trail(workspace_id);
CREATE INDEX IF NOT EXISTS idx_audit_target ON audit_trail(target_type, target_id);

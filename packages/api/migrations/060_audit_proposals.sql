-- Migration 060: audit_proposals table for AI reviewer framework (Phase 6.2 B4-T12)

CREATE TABLE IF NOT EXISTS audit_proposals (
    id              TEXT PRIMARY KEY,
    workspace_id    TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    reviewer        TEXT NOT NULL,               -- e.g. 'deduper', 'tag_normalizer', etc.
    category        TEXT NOT NULL,               -- e.g. 'duplicate', 'tag_orphan', 'edge_conflict'
    target_ids      TEXT[] NOT NULL DEFAULT '{}',-- node/edge IDs affected
    reasoning       TEXT,                        -- human-readable explanation
    evidence        JSONB DEFAULT '{}',          -- structured data (scores, diffs, etc.)
    suggested_action JSONB DEFAULT '{}',         -- what action the reviewer suggests
    severity        TEXT NOT NULL DEFAULT 'low' CHECK (severity IN ('low', 'mid', 'high')),
    status          TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'dismissed', 'expired')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at     TIMESTAMPTZ,
    resolved_by     TEXT
);

CREATE INDEX IF NOT EXISTS idx_audit_proposals_workspace ON audit_proposals(workspace_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_proposals_reviewer  ON audit_proposals(reviewer, workspace_id, status);
CREATE INDEX IF NOT EXISTS idx_audit_proposals_severity  ON audit_proposals(workspace_id, severity, status);

-- proposal_reads: tracks per-user read history for badge pulse animation
CREATE TABLE IF NOT EXISTS proposal_reads (
    proposal_id TEXT NOT NULL REFERENCES audit_proposals(id) ON DELETE CASCADE,
    user_id     TEXT NOT NULL,
    read_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (proposal_id, user_id)
);

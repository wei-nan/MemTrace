-- Migration: 006_node_trust_votes.sql
-- Description: Adds a table to track individual trust votes for nodes.

CREATE TABLE IF NOT EXISTS node_trust_votes (
    id              TEXT PRIMARY KEY,
    workspace_id    TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    node_id         TEXT NOT NULL REFERENCES memory_nodes(id) ON DELETE CASCADE,
    user_id         TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    accuracy        SMALLINT NOT NULL CHECK (accuracy BETWEEN 1 AND 5),
    utility         SMALLINT NOT NULL CHECK (utility BETWEEN 1 AND 5),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (node_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_node_trust_votes_node ON node_trust_votes (node_id);
CREATE INDEX IF NOT EXISTS idx_node_trust_votes_ws ON node_trust_votes (workspace_id);

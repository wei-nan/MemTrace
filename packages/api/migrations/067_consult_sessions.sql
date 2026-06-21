-- Migration 067: consult_sessions table for tracking consult history, multi-model outputs and budget gating (Phase 6.4)

CREATE TABLE IF NOT EXISTS consult_sessions (
    id                  TEXT PRIMARY KEY,
    workspace_id        TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    stuck_node_id       TEXT REFERENCES memory_nodes(id) ON DELETE SET NULL,
    problem_context     TEXT,
    mode                TEXT NOT NULL,                       -- 'interpret' | 'generate'
    synthesis_result    TEXT NOT NULL DEFAULT 'consensus',   -- 'consensus' | 'divergent' | 'safe' | 'risky' | 'dangerous' | 'budget_limit'
    inquiry_path_id     TEXT REFERENCES inquiry_paths(id) ON DELETE SET NULL,
    audit_proposal_id   TEXT REFERENCES audit_proposals(id) ON DELETE SET NULL,
    metadata            JSONB DEFAULT '{}'::jsonb,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_consult_sessions_workspace ON consult_sessions(workspace_id, created_at DESC);

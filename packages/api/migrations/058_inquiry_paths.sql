-- Migration: 058_inquiry_paths.sql
-- Create table for tracking agent inquiry paths

CREATE TABLE inquiry_paths (
  id            TEXT PRIMARY KEY,
  workspace_id  TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  agent_id      TEXT NOT NULL,
  query_text    TEXT NOT NULL,
  query_emb     vector(1536),
  node_sequence TEXT[] NOT NULL DEFAULT '{}',
  outcome       TEXT NOT NULL CHECK (outcome IN ('success', 'partial', 'failed', 'gap')),
  started_at    TIMESTAMPTZ NOT NULL,
  ended_at      TIMESTAMPTZ NOT NULL,
  token_used    INTEGER,
  rating        INTEGER,
  archived_at   TIMESTAMPTZ,
  metadata      JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_inquiry_paths_ws_ended ON inquiry_paths (workspace_id, ended_at DESC);
CREATE INDEX idx_inquiry_paths_emb ON inquiry_paths USING ivfflat (query_emb vector_cosine_ops);

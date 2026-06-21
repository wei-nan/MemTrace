-- Migration 062: Embedding migration state machine (C2-T27)

BEGIN;

-- Add provider and model tracking to workspaces
ALTER TABLE workspaces 
  ADD COLUMN IF NOT EXISTS embedding_provider TEXT NOT NULL DEFAULT 'openai',
  ADD COLUMN IF NOT EXISTS embedding_model TEXT NOT NULL DEFAULT 'text-embedding-3-small',
  ADD COLUMN IF NOT EXISTS migrating_to_provider TEXT,
  ADD COLUMN IF NOT EXISTS migrating_to_model TEXT,
  ADD COLUMN IF NOT EXISTS migration_status TEXT NOT NULL DEFAULT 'none'
  CHECK (migration_status IN ('none', 'in_progress', 'paused', 'completed'));

-- Add node secondary embedding columns for dual-index search during migration (C2-T28 setup)
ALTER TABLE memory_nodes
  ADD COLUMN IF NOT EXISTS secondary_embedding vector(1536), -- Dimension varies, default vector type handles any dimension safely via typmod or we can omit typmod. We use pgvector.
  ADD COLUMN IF NOT EXISTS secondary_embedding_model TEXT,
  ADD COLUMN IF NOT EXISTS secondary_embedding_provider TEXT;

-- Since dimension can vary by model, we remove typmod from secondary_embedding and let pgvector handle it
ALTER TABLE memory_nodes 
  ALTER COLUMN secondary_embedding TYPE vector;

-- Migration history table
CREATE TABLE IF NOT EXISTS workspace_migrations (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    target_provider TEXT NOT NULL,
    target_model TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('in_progress', 'paused', 'completed', 'failed')),
    error TEXT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_ws_migrations_ws_id ON workspace_migrations(workspace_id);

COMMIT;

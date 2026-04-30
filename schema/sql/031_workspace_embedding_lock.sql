-- Migration: 031_workspace_embedding_lock.sql
-- Description: Add embedding model and dimension tracking to workspaces.

ALTER TABLE workspaces
  ADD COLUMN IF NOT EXISTS embedding_model TEXT NOT NULL DEFAULT 'text-embedding-3-small',
  ADD COLUMN IF NOT EXISTS embedding_dim   INT  NOT NULL DEFAULT 1536;

DROP INDEX IF EXISTS idx_nodes_embedding;

ALTER TABLE memory_nodes
  ALTER COLUMN embedding TYPE vector
  USING embedding::vector;

CREATE INDEX IF NOT EXISTS idx_nodes_embedding
  ON memory_nodes
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

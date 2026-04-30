-- Migration: 013_workspace_embedding_lock.sql
-- Description: Add embedding model and dimension tracking to workspaces.
--   Also converts memory_nodes.embedding to flexible vector type.

-- 1. Add embedding tracking columns to workspaces
ALTER TABLE workspaces
  ADD COLUMN IF NOT EXISTS embedding_model TEXT NOT NULL DEFAULT 'text-embedding-3-small',
  ADD COLUMN IF NOT EXISTS embedding_dim   INT  NOT NULL DEFAULT 1536;

-- 2. Convert memory_nodes.embedding to flexible vector type
-- Note: We must drop the index first as it relies on the fixed dimension
DROP INDEX IF EXISTS idx_nodes_embedding;

-- Alter column to generic vector (unconstrained dimension)
-- Note: Generic vector type (without dimensions) does not support HNSW/IVFFlat indexing.
-- However, for typical workspace sizes, sequential scan with workspace_id filtering is efficient.
ALTER TABLE memory_nodes
  ALTER COLUMN embedding TYPE vector
  USING embedding::vector;

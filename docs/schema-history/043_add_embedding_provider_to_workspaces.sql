-- Migration: Add embedding_provider to workspaces for strict locking
-- Phase 4.8: S8-1

ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS embedding_provider TEXT;

-- Backfill existing workspaces based on embedding_model
UPDATE workspaces SET embedding_provider = 'openai' 
WHERE embedding_provider IS NULL 
  AND (embedding_model LIKE 'text-embedding-3-%' OR embedding_model LIKE 'text-embedding-ada-%');

UPDATE workspaces SET embedding_provider = 'gemini' 
WHERE embedding_provider IS NULL 
  AND (embedding_model LIKE 'text-embedding-004' OR embedding_model LIKE 'text-embedding-005');

UPDATE workspaces SET embedding_provider = 'ollama' 
WHERE embedding_provider IS NULL 
  AND (embedding_model IN ('nomic-embed-text', 'mxbai-embed-large', 'bge-m3'));

-- Default to 'openai' for others if unknown but model exists
UPDATE workspaces SET embedding_provider = 'openai' 
WHERE embedding_provider IS NULL AND embedding_model IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_workspaces_embed_prov ON workspaces(embedding_provider);

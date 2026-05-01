-- Migration: Add import_sources table for better traceability
-- Phase 4.2: D-1

CREATE TABLE IF NOT EXISTS import_sources (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    doc_type TEXT NOT NULL DEFAULT 'generic',
    raw_content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Add source_id to review_queue for strict tracking
ALTER TABLE review_queue ADD COLUMN IF NOT EXISTS source_id TEXT REFERENCES import_sources(id) ON DELETE SET NULL;

-- Index for faster lookup
CREATE INDEX IF NOT EXISTS idx_import_sources_ws ON import_sources(workspace_id);

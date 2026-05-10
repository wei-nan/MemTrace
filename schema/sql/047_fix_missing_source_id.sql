-- Migration: 047_fix_missing_source_id.sql
-- Description: Add missing source_id to memory_nodes and source_type/proposer to edges.
-- Phase 4.8 Traceability Fix

DO $$
BEGIN
    -- 1. Add source_id to memory_nodes
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'memory_nodes' AND column_name = 'source_id') THEN
        ALTER TABLE memory_nodes ADD COLUMN source_id TEXT REFERENCES import_sources(id) ON DELETE SET NULL;
        CREATE INDEX IF NOT EXISTS idx_memory_nodes_source_id ON memory_nodes(source_id);
    END IF;

    -- 2. Add source_tracing fields to edges (missing in some migrations)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'edges' AND column_name = 'source_type') THEN
        ALTER TABLE edges ADD COLUMN source_type source_type NOT NULL DEFAULT 'human';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'edges' AND column_name = 'proposer') THEN
        ALTER TABLE edges ADD COLUMN proposer TEXT;
    END IF;

    -- 3. Ensure source_id exists in review_queue (it should, but just in case)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'review_queue' AND column_name = 'source_id') THEN
        ALTER TABLE review_queue ADD COLUMN source_id TEXT REFERENCES import_sources(id) ON DELETE SET NULL;
    END IF;
END $$;

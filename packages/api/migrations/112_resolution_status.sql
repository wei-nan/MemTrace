-- Migration 112: resolution_status for memory_nodes.

ALTER TABLE memory_nodes
    ADD COLUMN IF NOT EXISTS resolution_status VARCHAR(50) NOT NULL DEFAULT 'open';

ALTER TABLE memory_nodes DROP CONSTRAINT IF EXISTS chk_resolution_status;
ALTER TABLE memory_nodes ADD CONSTRAINT chk_resolution_status 
    CHECK (resolution_status IN ('open', 'resolved', 'superseded'));

CREATE INDEX IF NOT EXISTS idx_memory_nodes_resolution_status
    ON memory_nodes(resolution_status);

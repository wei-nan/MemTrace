-- S5-T01: Optimistic Locking for memory_nodes
ALTER TABLE memory_nodes ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1;

-- Also add conflict_status and conflict_detail as defined in SPEC §17.4.2
ALTER TABLE memory_nodes ADD COLUMN IF NOT EXISTS conflict_status TEXT CHECK (conflict_status IN (NULL, 'flagged', 'resolved'));
ALTER TABLE memory_nodes ADD COLUMN IF NOT EXISTS conflict_detail JSONB;

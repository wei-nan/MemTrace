ALTER TYPE relation_type ADD VALUE IF NOT EXISTS 'answered_by';
ALTER TYPE relation_type ADD VALUE IF NOT EXISTS 'similar_to';
ALTER TYPE relation_type ADD VALUE IF NOT EXISTS 'queried_via_mcp';

ALTER TYPE node_status ADD VALUE IF NOT EXISTS 'gap';
ALTER TYPE node_status ADD VALUE IF NOT EXISTS 'answered';
ALTER TYPE node_status ADD VALUE IF NOT EXISTS 'answered-low-trust';
ALTER TYPE node_status ADD VALUE IF NOT EXISTS 'conflicted';

ALTER TYPE content_type ADD VALUE IF NOT EXISTS 'inquiry';

ALTER TABLE memory_nodes ADD COLUMN IF NOT EXISTS miss_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE memory_nodes ADD COLUMN IF NOT EXISTS ask_count INTEGER NOT NULL DEFAULT 0;

ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS
    qa_archive_mode VARCHAR(20) NOT NULL DEFAULT 'manual_review'
    CHECK (qa_archive_mode IN ('manual_review', 'auto_active'));
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS agent_node_id VARCHAR(64);

ALTER TYPE source_type ADD VALUE IF NOT EXISTS 'document';
ALTER TYPE source_type ADD VALUE IF NOT EXISTS 'qa_conversation';
ALTER TYPE source_type ADD VALUE IF NOT EXISTS 'mcp';

-- P4.5-3A-8: Fix existing gap node content_type
UPDATE memory_nodes SET content_type = 'inquiry' WHERE status = 'gap' AND content_type != 'inquiry';
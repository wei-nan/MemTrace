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

-- P4.5-3A-9: Add workspace status for lifecycle management
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'pending_deletion', 'deleted'));
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

-- P4.5-1B-2: Add metadata column for interaction tracking on edges
ALTER TABLE edges ADD COLUMN IF NOT EXISTS metadata JSONB;

-- P4.5-1B-1: MCP query logging for observability
CREATE TABLE IF NOT EXISTS mcp_query_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    tool_name TEXT NOT NULL,
    query_text TEXT,
    result_node_count INTEGER NOT NULL,
    estimated_tokens INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    provider TEXT
);
CREATE INDEX IF NOT EXISTS idx_mcp_query_logs_ws ON mcp_query_logs(workspace_id, created_at);

-- P4.5-3A-10: Fix ambiguous status reference in decay function
CREATE OR REPLACE FUNCTION apply_edge_decay()
RETURNS INTEGER AS $$
DECLARE
  updated_count INTEGER;
BEGIN
  -- 1. Time-based decay for 'ephemeral' workspaces
  UPDATE edges
  SET 
    weight = GREATEST(
      min_weight,
      weight * POWER(0.5, EXTRACT(EPOCH FROM (now() - last_co_accessed)) / 86400.0 / half_life_days)
    ),
    status = CASE 
      WHEN (weight * POWER(0.5, EXTRACT(EPOCH FROM (now() - last_co_accessed)) / 86400.0 / half_life_days)) < min_weight 
      THEN 'faded'::edge_status 
      ELSE edges.status 
    END
  FROM workspaces ws
  WHERE edges.workspace_id = ws.id
    AND ws.kb_type = 'ephemeral'
    AND edges.status = 'active'
    AND edges.pinned = FALSE
    AND edges.last_co_accessed < now() - INTERVAL '1 hour';

  GET DIAGNOSTICS updated_count = ROW_COUNT;

  -- 2. Traversal-based archiving for 'evergreen' workspaces
  UPDATE edges
  SET status = 'faded'::edge_status
  FROM workspaces ws
  WHERE edges.workspace_id = ws.id
    AND ws.kb_type = 'evergreen'
    AND edges.status = 'active'
    AND edges.pinned = FALSE
    AND edges.traversal_count = 0
    AND edges.last_co_accessed < now() - (ws.archive_window_days || ' days')::INTERVAL;

  RETURN updated_count;
END;
$$ LANGUAGE plpgsql;

ALTER TYPE source_type ADD VALUE IF NOT EXISTS 'document';
ALTER TYPE source_type ADD VALUE IF NOT EXISTS 'qa_conversation';
ALTER TYPE source_type ADD VALUE IF NOT EXISTS 'mcp';

-- P4.5-3A-8: Fix existing gap node content_type
UPDATE memory_nodes SET content_type = 'inquiry' WHERE status = 'gap' AND content_type != 'inquiry';
-- Add provider column to mcp_query_logs for Phase 4 analytics
-- Also ensure created_at has NOT NULL constraint as per spec

ALTER TABLE mcp_query_logs ADD COLUMN IF NOT EXISTS provider TEXT;
ALTER TABLE mcp_query_logs ALTER COLUMN created_at SET NOT NULL;
ALTER TABLE mcp_query_logs ALTER COLUMN created_at SET DEFAULT NOW();

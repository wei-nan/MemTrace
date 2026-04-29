-- Migration: 005_mcp_query_logs.sql
-- Description: Add provider column to mcp_query_logs for Phase 4 analytics

ALTER TABLE mcp_query_logs ADD COLUMN IF NOT EXISTS provider TEXT;
ALTER TABLE mcp_query_logs ALTER COLUMN created_at SET NOT NULL;
ALTER TABLE mcp_query_logs ALTER COLUMN created_at SET DEFAULT NOW();

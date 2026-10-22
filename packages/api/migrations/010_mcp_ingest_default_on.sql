-- 010_mcp_ingest_default_on.sql
-- MCP remote ingestion is no longer a user-facing toggle (hidden from the UI);
-- new workspaces default to enabled (services/workspaces.py). Backfill existing
-- workspaces so agents are not blocked by a setting nobody can reach anymore.
-- Only mcp_ingest_enabled is touched; other settings keys and the daily quota
-- are preserved (jsonb || merges at the top level).
UPDATE workspaces
SET settings = COALESCE(settings, '{}'::jsonb) || '{"mcp_ingest_enabled": true}'::jsonb
WHERE COALESCE(settings->>'mcp_ingest_enabled', '') <> 'true';

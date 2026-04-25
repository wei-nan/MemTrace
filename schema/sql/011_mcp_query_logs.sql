SET client_encoding = 'UTF8';
CREATE TABLE IF NOT EXISTS mcp_query_logs (
  id TEXT PRIMARY KEY,
  workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  tool_name TEXT NOT NULL,
  query_text TEXT,
  result_node_count INT DEFAULT 0,
  estimated_tokens INT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mcp_query_logs_ws
  ON mcp_query_logs(workspace_id, created_at);

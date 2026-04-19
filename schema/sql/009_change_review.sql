ALTER TABLE review_queue
  ADD COLUMN IF NOT EXISTS change_type TEXT NOT NULL DEFAULT 'create',
  ADD COLUMN IF NOT EXISTS target_node_id TEXT REFERENCES memory_nodes(id) ON DELETE CASCADE,
  ADD COLUMN IF NOT EXISTS before_snapshot JSONB,
  ADD COLUMN IF NOT EXISTS diff_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS proposer_type TEXT NOT NULL DEFAULT 'human',
  ADD COLUMN IF NOT EXISTS proposer_id TEXT,
  ADD COLUMN IF NOT EXISTS proposer_meta JSONB,
  ADD COLUMN IF NOT EXISTS reviewer_type TEXT,
  ADD COLUMN IF NOT EXISTS ai_review JSONB,
  ADD COLUMN IF NOT EXISTS review_notes TEXT;

CREATE INDEX IF NOT EXISTS idx_review_workspace_status_created
  ON review_queue (workspace_id, status, created_at);
CREATE INDEX IF NOT EXISTS idx_review_target_node
  ON review_queue (target_node_id);

CREATE TABLE IF NOT EXISTS node_revisions (
  id TEXT PRIMARY KEY,
  node_id TEXT NOT NULL REFERENCES memory_nodes(id) ON DELETE CASCADE,
  workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  revision_no INTEGER NOT NULL,
  snapshot JSONB NOT NULL,
  signature TEXT NOT NULL,
  proposer_type TEXT NOT NULL DEFAULT 'human',
  proposer_id TEXT,
  review_id TEXT REFERENCES review_queue(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (node_id, revision_no)
);

CREATE INDEX IF NOT EXISTS idx_node_revisions_node_rev_desc
  ON node_revisions (node_id, revision_no DESC);

CREATE TABLE IF NOT EXISTS ai_reviewers (
  id TEXT PRIMARY KEY,
  workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  provider TEXT NOT NULL,
  model TEXT NOT NULL,
  system_prompt TEXT NOT NULL,
  auto_accept_threshold NUMERIC(4,3) NOT NULL DEFAULT 0.95,
  auto_reject_threshold NUMERIC(4,3) NOT NULL DEFAULT 0.10,
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (workspace_id, name)
);


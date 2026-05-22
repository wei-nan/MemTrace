-- 057_cluster_single_name.sql
-- Phase 6: Consolidate node_clusters.name_zh / name_en → single name column.
-- Uses the workspace language to pick the preferred name; falls back to whichever
-- non-empty value is available.

ALTER TABLE node_clusters
  ADD COLUMN IF NOT EXISTS name TEXT;

-- Populate from existing bilingual columns based on workspace language
UPDATE node_clusters nc
SET name = CASE
    WHEN w.language = 'en' THEN COALESCE(NULLIF(nc.name_en, ''), nc.name_zh, nc.name_en)
    ELSE COALESCE(NULLIF(nc.name_zh, ''), nc.name_en, nc.name_zh)
  END
FROM workspaces w
WHERE w.id = nc.workspace_id
  AND nc.name IS NULL;

-- Fallback for any clusters whose workspace has no language yet
UPDATE node_clusters
SET name = COALESCE(NULLIF(name_en, ''), name_zh, 'Unnamed')
WHERE name IS NULL;

-- Enforce NOT NULL
ALTER TABLE node_clusters
  ALTER COLUMN name SET NOT NULL;

-- Drop old bilingual columns
ALTER TABLE node_clusters
  DROP COLUMN IF EXISTS name_zh,
  DROP COLUMN IF EXISTS name_en;

CREATE INDEX IF NOT EXISTS idx_node_clusters_name ON node_clusters (workspace_id, name);

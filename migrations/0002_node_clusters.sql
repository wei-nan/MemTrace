-- 0002_node_clusters.sql
-- Per-workspace dynamic cluster taxonomy for memory nodes.

CREATE TABLE node_clusters (
    id           text PRIMARY KEY,
    workspace_id text NOT NULL,
    name_zh      text NOT NULL,
    name_en      text NOT NULL,
    color        text NOT NULL DEFAULT 'blue',
    created_at   timestamptz DEFAULT now(),
    updated_at   timestamptz DEFAULT now()
);

CREATE INDEX idx_node_clusters_ws ON node_clusters(workspace_id);

ALTER TABLE memory_nodes
    ADD COLUMN IF NOT EXISTS cluster_id text REFERENCES node_clusters(id) ON DELETE SET NULL;

CREATE INDEX idx_memory_nodes_cluster ON memory_nodes(cluster_id);

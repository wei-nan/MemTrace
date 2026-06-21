-- 063_embed_retry_queue.sql
-- Create a queue for failed node embeddings to retry with exponential backoff.

CREATE TABLE IF NOT EXISTS embed_retry_queue (
    node_id VARCHAR(50) NOT NULL REFERENCES memory_nodes(id) ON DELETE CASCADE,
    workspace_id VARCHAR(50) NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    retry_count INTEGER NOT NULL DEFAULT 0,
    next_retry_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_error TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now()),
    PRIMARY KEY (node_id)
);

CREATE INDEX idx_embed_retry_queue_next_retry ON embed_retry_queue (next_retry_at);
CREATE INDEX idx_embed_retry_queue_ws ON embed_retry_queue (workspace_id);

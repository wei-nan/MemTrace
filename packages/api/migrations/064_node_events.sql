-- 064_node_events.sql
-- Create an event queue for node updates to process background tasks (like bg_suggest_edges) asynchronously.

CREATE TABLE IF NOT EXISTS node_events (
    id BIGSERIAL PRIMARY KEY,
    workspace_id VARCHAR(50) NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    node_id VARCHAR(50) NOT NULL REFERENCES memory_nodes(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL, -- e.g. 'created', 'updated', 'embedding_updated'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now()),
    processed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_node_events_unprocessed ON node_events (created_at) WHERE processed_at IS NULL;

-- Trigger to log node events
CREATE OR REPLACE FUNCTION log_node_event()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO node_events (workspace_id, node_id, event_type)
        VALUES (NEW.workspace_id, NEW.id, 'created');
    ELSIF TG_OP = 'UPDATE' THEN
        IF NEW.embedding IS DISTINCT FROM OLD.embedding THEN
            INSERT INTO node_events (workspace_id, node_id, event_type)
            VALUES (NEW.workspace_id, NEW.id, 'embedding_updated');
        ELSIF NEW.title IS DISTINCT FROM OLD.title OR NEW.body IS DISTINCT FROM OLD.body THEN
            INSERT INTO node_events (workspace_id, node_id, event_type)
            VALUES (NEW.workspace_id, NEW.id, 'updated');
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_log_node_event ON memory_nodes;
CREATE TRIGGER trigger_log_node_event
AFTER INSERT OR UPDATE ON memory_nodes
FOR EACH ROW
EXECUTE FUNCTION log_node_event();

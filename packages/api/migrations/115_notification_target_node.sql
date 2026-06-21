-- 115_notification_target_node.sql
-- Carry the target node id into notifications so the UI can focus the exact node
-- when a notification is clicked (audit_proposal -> the flagged node; review_queue
-- -> its target node). Re-defines the two fan-out functions (added in 114) to also
-- populate target_node_id. Idempotent.

ALTER TABLE notifications ADD COLUMN IF NOT EXISTS target_node_id text;

-- audit proposals: first element of target_ids is the primary node for node-level
-- findings (edge-level categories will simply not resolve to a node on the client).
CREATE OR REPLACE FUNCTION notify_on_audit_proposal() RETURNS trigger AS $$
BEGIN
    INSERT INTO notifications (id, workspace_id, recipient_id, source_type, source_id, category, severity, title, body, target_node_id)
    SELECT 'ntf_' || replace(gen_random_uuid()::text, '-', ''),
           NEW.workspace_id, r.uid, 'audit_proposal', NEW.id, NEW.category, NEW.severity,
           '[' || NEW.severity || '] ' || NEW.category,
           left(coalesce(NEW.reasoning, ''), 500),
           NEW.target_ids[1]
    FROM (
        SELECT owner_id AS uid FROM workspaces WHERE id = NEW.workspace_id
        UNION
        SELECT user_id FROM workspace_members
        WHERE workspace_id = NEW.workspace_id AND role::text IN ('admin', 'editor')
    ) r
    WHERE r.uid IS NOT NULL;
    RETURN NEW;
EXCEPTION WHEN OTHERS THEN
    RAISE WARNING 'notify_on_audit_proposal failed: %', SQLERRM;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION notify_on_review_queue() RETURNS trigger AS $$
BEGIN
    INSERT INTO notifications (id, workspace_id, recipient_id, source_type, source_id, category, severity, title, body, target_node_id)
    SELECT 'ntf_' || replace(gen_random_uuid()::text, '-', ''),
           NEW.workspace_id, r.uid, 'review_queue', NEW.id, NEW.change_type, 'review',
           'Review: ' || NEW.change_type,
           left(coalesce(NEW.source_info, ''), 500),
           NEW.target_node_id
    FROM (
        SELECT owner_id AS uid FROM workspaces WHERE id = NEW.workspace_id
        UNION
        SELECT user_id FROM workspace_members
        WHERE workspace_id = NEW.workspace_id AND role::text IN ('admin', 'editor')
    ) r
    WHERE r.uid IS NOT NULL;
    RETURN NEW;
EXCEPTION WHEN OTHERS THEN
    RAISE WARNING 'notify_on_review_queue failed: %', SQLERRM;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

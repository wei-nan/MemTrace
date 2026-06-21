-- 115_notification_center.sql
-- In-app notification center: a persistent, per-recipient inbox with read state.
-- Every audit/review finding must reach workspace owner + admins instead of waiting
-- to be discovered by pulling the audit page.
--
-- Coverage is achieved at the common sinks: all AI reviewers / safety / contradiction
-- / secret findings flow through audit_proposals; human-gated proposals flow through
-- review_queue. AFTER INSERT triggers fan a notification out to each recipient.
-- The fan-out is best-effort (EXCEPTION -> RETURN NEW) so a notification failure can
-- never block the underlying audit/review insert.
-- Idempotent: safe to re-run.

CREATE TABLE IF NOT EXISTS notifications (
    id            text PRIMARY KEY,
    workspace_id  text NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    recipient_id  text NOT NULL,
    source_type   text NOT NULL,          -- 'audit_proposal' | 'review_queue'
    source_id     text NOT NULL,
    category      text,
    severity      text,
    title         text NOT NULL,
    body          text,
    read_at       timestamp with time zone,
    created_at    timestamp with time zone NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_notifications_recipient_unread
    ON notifications(recipient_id, created_at DESC) WHERE read_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_notifications_recipient
    ON notifications(recipient_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notifications_workspace
    ON notifications(workspace_id, created_at DESC);

-- Fan-out for AI audit proposals (9 reviewers + safety queue + contradiction + secret).
CREATE OR REPLACE FUNCTION notify_on_audit_proposal() RETURNS trigger AS $$
BEGIN
    INSERT INTO notifications (id, workspace_id, recipient_id, source_type, source_id, category, severity, title, body)
    SELECT 'ntf_' || replace(gen_random_uuid()::text, '-', ''),
           NEW.workspace_id, r.uid, 'audit_proposal', NEW.id, NEW.category, NEW.severity,
           '[' || NEW.severity || '] ' || NEW.category,
           left(coalesce(NEW.reasoning, ''), 500)
    FROM (
        SELECT owner_id AS uid FROM workspaces WHERE id = NEW.workspace_id
        UNION
        -- role is an enum (viewer/editor); ::text keeps this robust if labels change.
        SELECT user_id FROM workspace_members
        WHERE workspace_id = NEW.workspace_id AND role::text IN ('admin', 'editor')
    ) r
    WHERE r.uid IS NOT NULL;
    RETURN NEW;
EXCEPTION WHEN OTHERS THEN
    RAISE WARNING 'notify_on_audit_proposal failed: %', SQLERRM;  -- best-effort: never block the insert
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Fan-out for human-gated review queue items.
CREATE OR REPLACE FUNCTION notify_on_review_queue() RETURNS trigger AS $$
BEGIN
    INSERT INTO notifications (id, workspace_id, recipient_id, source_type, source_id, category, severity, title, body)
    SELECT 'ntf_' || replace(gen_random_uuid()::text, '-', ''),
           NEW.workspace_id, r.uid, 'review_queue', NEW.id, NEW.change_type, 'review',
           'Review: ' || NEW.change_type,
           left(coalesce(NEW.source_info, ''), 500)
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

DROP TRIGGER IF EXISTS trg_notify_audit_proposal ON audit_proposals;
CREATE TRIGGER trg_notify_audit_proposal
    AFTER INSERT ON audit_proposals
    FOR EACH ROW EXECUTE FUNCTION notify_on_audit_proposal();

DROP TRIGGER IF EXISTS trg_notify_review_queue ON review_queue;
CREATE TRIGGER trg_notify_review_queue
    AFTER INSERT ON review_queue
    FOR EACH ROW EXECUTE FUNCTION notify_on_review_queue();

ALTER TABLE review_queue ADD COLUMN IF NOT EXISTS assigned_to text;
ALTER TABLE review_queue ADD COLUMN IF NOT EXISTS due_at timestamptz;

CREATE INDEX IF NOT EXISTS idx_review_queue_assigned ON review_queue(assigned_to) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_review_queue_due ON review_queue(due_at) WHERE status = 'pending';

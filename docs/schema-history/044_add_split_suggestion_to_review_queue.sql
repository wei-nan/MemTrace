-- Migration: 044_add_split_suggestion_to_review_queue.sql
-- Description: Add split_suggestion JSONB field to review_queue to store node decomposition proposals.
-- Phase 4.8: S9-3a

ALTER TABLE review_queue ADD COLUMN IF NOT EXISTS split_suggestion JSONB;

-- Add index for efficient querying of pending split suggestions
CREATE INDEX IF NOT EXISTS idx_review_queue_split ON review_queue((split_suggestion IS NOT NULL)) WHERE status = 'pending';

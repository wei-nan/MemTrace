-- Migration: 039_ingest_cancel.sql
-- Enables multi-file batch ingestion and cancellation support

-- 1. Extend the ingestion_status enum
-- Note: In some Postgres versions, this cannot run in a transaction block.
ALTER TYPE ingestion_status ADD VALUE 'pending';
ALTER TYPE ingestion_status ADD VALUE 'cancelling';
ALTER TYPE ingestion_status ADD VALUE 'cancelled';

-- 2. Add columns to ingestion_logs for batch management
ALTER TABLE ingestion_logs ADD COLUMN cancelled_at TIMESTAMPTZ;
ALTER TABLE ingestion_logs ADD COLUMN queue_position INTEGER DEFAULT 0;
ALTER TABLE ingestion_logs ADD COLUMN batch_id TEXT;

-- 3. Index for batch lookup
CREATE INDEX idx_ingestion_logs_batch ON ingestion_logs (batch_id);

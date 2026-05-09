-- 041_ingestion_log_stats.sql
-- Add started_at, nodes_created, nodes_skipped to ingestion_logs.

ALTER TABLE ingestion_logs
  ADD COLUMN IF NOT EXISTS started_at    timestamptz,
  ADD COLUMN IF NOT EXISTS nodes_created integer NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS nodes_skipped integer NOT NULL DEFAULT 0;

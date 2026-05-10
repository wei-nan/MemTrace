-- Migration: 046_add_source_to_ingestion_logs.sql
-- Description: Add source column to ingestion_logs to distinguish between file, MCP, and other ingestion sources.
-- Phase 4.8: S9-7a

ALTER TABLE ingestion_logs ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'file';

-- Update existing logs
UPDATE ingestion_logs SET source = 'file' WHERE source IS NULL;

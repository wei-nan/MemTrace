-- Migration: 007_usage_summary.sql
-- Description: P4-D8: AI Usage Monthly Summary

CREATE TABLE IF NOT EXISTS ai_usage_summary (
    id SERIAL PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    year_month TEXT NOT NULL, -- e.g. "2024-03"
    token_count BIGINT DEFAULT 0,
    last_updated TIMESTAMPTZ DEFAULT now(),
    UNIQUE(workspace_id, year_month)
);

CREATE INDEX IF NOT EXISTS idx_ai_usage_summary_ws ON ai_usage_summary(workspace_id);

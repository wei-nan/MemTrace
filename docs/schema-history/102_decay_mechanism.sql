-- Migration: S1-T02. Decay Mechanism
-- Goal: Track decay operations and add necessary fields if missing.

CREATE TABLE IF NOT EXISTS decay_logs (
  id                bigserial PRIMARY KEY,
  date              date NOT NULL DEFAULT CURRENT_DATE,
  workspace_id      text,
  nodes_updated     int,
  avg_freshness_before float,
  avg_freshness_after  float,
  created_at        timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_decay_logs_date ON decay_logs(date DESC);

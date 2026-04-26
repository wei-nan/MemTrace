-- Migration 003: workspace access audit log
-- Records every API call for security monitoring and anomaly detection.

CREATE TABLE IF NOT EXISTS ws_access_log (
    id           BIGSERIAL    PRIMARY KEY,
    ts           TIMESTAMPTZ  NOT NULL DEFAULT now(),
    user_id      TEXT,
    ip           TEXT,
    method       TEXT         NOT NULL,
    path         TEXT         NOT NULL,
    workspace_id TEXT,
    status_code  INTEGER,
    duration_ms  INTEGER
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS ws_access_log_ts_idx   ON ws_access_log (ts DESC);
CREATE INDEX IF NOT EXISTS ws_access_log_ws_idx   ON ws_access_log (workspace_id, ts DESC);
CREATE INDEX IF NOT EXISTS ws_access_log_user_idx ON ws_access_log (user_id, ts DESC);
CREATE INDEX IF NOT EXISTS ws_access_log_ip_idx   ON ws_access_log (ip, ts DESC);

-- Auto-purge entries older than 90 days to bound table growth.
-- Call this from the nightly cleanup job; it's safe to run repeatedly.
CREATE OR REPLACE FUNCTION purge_old_access_logs() RETURNS void LANGUAGE sql AS $$
  DELETE FROM ws_access_log WHERE ts < now() - INTERVAL '90 days';
$$;

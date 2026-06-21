-- S1-T02: Decay Mechanism — decay_logs table
-- Records daily freshness recalculation runs for audit and continuity verification.

CREATE TABLE IF NOT EXISTS decay_logs (
    id                    bigserial   PRIMARY KEY,
    date                  date        NOT NULL DEFAULT CURRENT_DATE,
    workspace_id          text        NOT NULL,   -- 'all' for global runs
    nodes_updated         int         NOT NULL DEFAULT 0,
    avg_freshness_before  float,
    avg_freshness_after   float,
    created_at            timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_decay_logs_date_ws
    ON decay_logs (date DESC, workspace_id);

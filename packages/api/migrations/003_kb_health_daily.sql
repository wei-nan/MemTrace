-- S1-T08: KB Health Dashboard — kb_health_daily table
-- Daily snapshot of all Stage 1 north-star metrics per workspace.

CREATE TABLE IF NOT EXISTS kb_health_daily (
    date                        date    NOT NULL,
    workspace_id                text    NOT NULL,
    token_savings_ratio         float   DEFAULT 0.0,
    retrieval_recall_at_5       float   DEFAULT 0.0,
    retrieval_mrr               float   DEFAULT 0.0,
    decay_runs_last_14d         int     DEFAULT 0,
    duplicate_pairs_unlinked    int     DEFAULT 0,
    avg_trust_active            float   DEFAULT 0.0,
    active_users_7d             int     DEFAULT 0,
    review_queue_depth          int     DEFAULT 0,
    ai_nodes_unverified_ratio   float   DEFAULT 0.0,
    created_at                  timestamptz DEFAULT now(),

    PRIMARY KEY (date, workspace_id)
);

CREATE INDEX IF NOT EXISTS idx_kb_health_daily_ws_date
    ON kb_health_daily (workspace_id, date DESC);

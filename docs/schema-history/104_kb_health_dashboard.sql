CREATE TABLE kb_health_daily (
    id           bigserial PRIMARY KEY,
    date         date NOT NULL,
    workspace_id text NOT NULL,
    
    token_savings_ratio     float,
    retrieval_recall_at_5   float,
    retrieval_mrr           float,
    decay_runs_last_14d     int,
    duplicate_pairs_unlinked int,
    avg_trust_active        float,
    active_users_7d         int,
    review_queue_depth      int,
    ai_nodes_unverified_ratio float,
    
    created_at   timestamptz DEFAULT now(),
    UNIQUE (date, workspace_id)
);

CREATE INDEX idx_kb_health_ws_date ON kb_health_daily(workspace_id, date DESC);

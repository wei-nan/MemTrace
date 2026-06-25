-- S1-T01: Token Telemetry — retrieval_logs table
-- Tracks every search/chat/traverse call for token measurement and retrieval quality evaluation.

CREATE TABLE IF NOT EXISTS retrieval_logs (
    id              bigserial       PRIMARY KEY,
    workspace_id    text            NOT NULL,
    user_id         text,
    mode            text            NOT NULL,   -- 'search' | 'chat' | 'traverse'
    query           text,
    top_k           int,
    hit_node_ids    text[],
    similarities    float[],
    tokens_query    int,
    tokens_context  int,
    tokens_answer   int,
    answer_useful   boolean,                    -- written back by user vote
    trace_id        text,                       -- links to chat session
    created_at      timestamptz     DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_retrieval_logs_ws_time
    ON retrieval_logs (workspace_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_retrieval_logs_mode
    ON retrieval_logs (workspace_id, mode, created_at DESC);

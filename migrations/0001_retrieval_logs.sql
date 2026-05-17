CREATE TABLE retrieval_logs (
    id bigserial PRIMARY KEY,
    workspace_id text NOT NULL,
    user_id text,
    mode text NOT NULL, -- 'search' | 'chat' | 'traverse'
    query text,
    top_k int,
    hit_node_ids text[],
    similarities float[],
    tokens_query int,
    tokens_context int,
    tokens_answer int,
    answer_useful boolean, -- 後續由 vote 寫回
    trace_id text, -- 串接 chat session
    created_at timestamptz DEFAULT now()
);
CREATE INDEX idx_retrieval_logs_ws_time ON retrieval_logs(workspace_id, created_at DESC);
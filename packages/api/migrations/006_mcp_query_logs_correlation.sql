-- 006_mcp_query_logs_correlation.sql
-- Adds optional run_id/task_id/stage correlation columns to mcp_query_logs,
-- closing the first (and broadest-coverage) piece of gap #4 in
-- ws_8c553f98/mem_ddd0e284 ("三組資料缺少共同的 run_id + task_id + stage
-- correlation"). mcp_query_logs is the one table every MCP tool call already
-- writes to (via services/mcp_tools.py::log_mcp_interaction ->
-- services/analytics.py::log_mcp_query_internal), so it is the natural first
-- table to carry the correlation id — retrieval_logs and inquiry_paths are
-- deliberately deferred (see ws_spec_plan/mem_22e5d5cf: those are narrower
-- and should follow this table, not be done in parallel).
--
-- All three columns are nullable and populated only when the caller (an
-- external harness) supplies them on the tool call — MemTrace does not
-- generate run_id/task_id/stage itself; per ws_spec_plan/mem_f2e46f6a this is
-- a passive ingest, not an executor. Existing rows and callers that never
-- pass these fields are unaffected (all NULL, same as before this migration).
--
-- No explicit BEGIN/COMMIT — run_migrations() applies each file inside its
-- own transaction (core/database.py::db_cursor(commit=True)).

ALTER TABLE mcp_query_logs
    ADD COLUMN run_id text,
    ADD COLUMN task_id text,
    ADD COLUMN stage text;

-- Speeds up "all calls for this run" / "all calls for this task" lookups,
-- the primary query shape a Run Usage Ledger aggregation would need.
CREATE INDEX idx_mcp_query_logs_run_id ON mcp_query_logs (run_id) WHERE run_id IS NOT NULL;
CREATE INDEX idx_mcp_query_logs_task_id ON mcp_query_logs (task_id) WHERE task_id IS NOT NULL;

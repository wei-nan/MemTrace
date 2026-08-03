-- 004_task_claims_table.sql
-- Replaces the per-process in-memory `_TASK_CLAIMS` dict in
-- packages/api/services/mcp_tools.py with a DB-backed claim lease shared
-- across all API processes/workers. The old dict let two processes each
-- believe they held the same claim (each has its own private copy), so
-- claim_task/release_task/get_next_task(exclusive)/submit_outcome could
-- double-claim under more than one process serving the same workspace.
-- See ws_6aa957c3/mem_f819c71c and the public gap this closes,
-- ws_spec0001/mem_inq002.
--
-- Deliberately a dedicated run-state table, not a memory_nodes column or
-- field: task claim leases are Agent Loop coordination state, not
-- knowledge graph content (A7 boundary; see ws_spec_plan/mem_f2e46f6a,
-- "允許的最小 Coordination" — task lifecycle/claim lease may live in
-- MemTrace but must not be folded into memory_nodes.status).
--
-- No explicit BEGIN/COMMIT — run_migrations() applies each file inside its
-- own transaction (core/database.py::db_cursor(commit=True)).

CREATE TABLE task_claims (
    workspace_id text NOT NULL,
    task_node_id text NOT NULL,
    agent_sub    text NOT NULL,
    claimed_at   timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_id, task_node_id)
);

-- Speeds up the TTL-cutoff scan in get_next_task's exclusive-mode filter
-- (_claimed_task_ids), which reads all live claims for a workspace.
CREATE INDEX idx_task_claims_claimed_at ON task_claims (claimed_at);

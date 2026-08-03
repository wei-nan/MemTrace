-- 005_workspace_pins.sql
-- Per-user workspace pinning for the Sidebar workspace switcher: users can
-- pin frequently-used workspaces so they surface at the top of the (now
-- capped) dropdown list. See ws_6aa957c3/mem_b0de24d8.
--
-- Dedicated table, not a memory_nodes/workspaces column: a pin is per-user
-- UI/coordination state, not knowledge graph content or a workspace-global
-- property (same A7 boundary reasoning as 004_task_claims_table.sql).
--
-- No explicit BEGIN/COMMIT — run_migrations() applies each file inside its
-- own transaction (core/database.py::db_cursor(commit=True)).

CREATE TABLE workspace_pins (
    user_id      text NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    workspace_id text NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    pinned_at    timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, workspace_id)
);

-- Speeds up the per-user pin lookup joined into list_workspaces_in_db /
-- explore_workspaces_in_db.
CREATE INDEX idx_workspace_pins_user ON workspace_pins (user_id);

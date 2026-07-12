-- 122_retire_workspace_agent_telemetry.sql
-- Retire the per-workspace "(Workspace Agent)" system-actor node and the
-- queried_via_mcp retrieval-telemetry edges it anchored. Node-level MCP access
-- now lives in traversal_log keyed by the real actor_id (see services/edges.py
-- record_traversal + services/mcp_tools.py log_mcp_interaction KEEP_ALIVE_TOOLS).
--
-- Design: ws_spec_plan/mem_ea840fad — supersedes the actor-table (mem_819815b4)
-- and retrieval_trace (mem_3e224fa2) endgame with a simpler consolidation:
-- telemetry keyed by existing actor identity, no new tables.
--
-- Backward compatibility: queried_via_mcp is retained as a deprecated
-- relation_type enum value (Postgres enum values are not dropped); it is simply
-- no longer written. Existing telemetry edges carry no knowledge, so they are
-- removed in bulk here rather than through per-edge tombstones — this migration
-- file is the record of removal.
--
-- Idempotent: safe to re-run on already-migrated databases.

-- 1. Remove all queried_via_mcp telemetry edges.
DELETE FROM edges WHERE relation = 'queried_via_mcp';

-- 2. Detach and remove the (Workspace Agent) system-actor nodes. Guard the
--    agent_node_id references so a re-run after the column is dropped is a no-op.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'workspaces' AND column_name = 'agent_node_id'
    ) THEN
        -- Any remaining edges anchored on an agent node (should be none after step 1).
        DELETE FROM edges
         WHERE from_id IN (SELECT agent_node_id FROM workspaces WHERE agent_node_id IS NOT NULL)
            OR to_id   IN (SELECT agent_node_id FROM workspaces WHERE agent_node_id IS NOT NULL);
        UPDATE workspaces SET agent_node_id = NULL WHERE agent_node_id IS NOT NULL;
    END IF;
END $$;

-- All system_actor nodes are (Workspace Agent) anchors (migration 117 set this
-- class only for agent nodes). They are actors, not knowledge — remove them.
DELETE FROM memory_nodes WHERE node_class = 'system_actor';

-- 3. Drop the now-unused workspace pointer column.
ALTER TABLE workspaces DROP COLUMN IF EXISTS agent_node_id;

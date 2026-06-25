-- 117_node_edge_class_and_tombstones.sql
-- Decouple system actors and retrieval telemetry from the knowledge graph, and
-- make hard-deletes auditable.
--
-- Root cause (mem_f2314f73): a workspace's "(Workspace Agent)" node is a system
-- actor / telemetry anchor, not knowledge. The evergreen cleanup job archived it
-- (no exclusion), which then made every queried_via_mcp edge it anchors look
-- "dangling" to the edge_auditor and suggested deleting them. queried_via_mcp is
-- retrieval telemetry, not a knowledge semantic edge, yet (weight 1.0) it also
-- dominated top_edges and default traversal.
--
-- Design conclusions: mem_819815b4 (agent = system actor), mem_3e224fa2
-- (queried_via_mcp = telemetry / edge_class), mem_347895c4 (mis-created data may
-- be hard-deleted, but the fact of removal must remain auditable — tombstones).
--
-- Idempotent: safe to re-run on already-migrated databases.

-- 1. node_class: separate system actors from knowledge nodes.
--    Decay governs knowledge visibility, never actor identity.
ALTER TABLE memory_nodes
    ADD COLUMN IF NOT EXISTS node_class text NOT NULL DEFAULT 'knowledge';
DO $$ BEGIN
    ALTER TABLE memory_nodes
        ADD CONSTRAINT memory_nodes_node_class_check
        CHECK (node_class IN ('knowledge', 'system_actor'));
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- 2. edge_class: separate semantic / system / telemetry edges.
ALTER TABLE edges
    ADD COLUMN IF NOT EXISTS edge_class text NOT NULL DEFAULT 'semantic';
DO $$ BEGIN
    ALTER TABLE edges
        ADD CONSTRAINT edges_edge_class_check
        CHECK (edge_class IN ('semantic', 'system', 'telemetry'));
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- 3. Backfill: each workspace's agent node is a system actor.
UPDATE memory_nodes
   SET node_class = 'system_actor'
 WHERE id IN (SELECT agent_node_id FROM workspaces WHERE agent_node_id IS NOT NULL)
   AND node_class <> 'system_actor';

-- 4. Backfill: queried_via_mcp is retrieval telemetry.
UPDATE edges
   SET edge_class = 'telemetry'
 WHERE relation = 'queried_via_mcp'
   AND edge_class <> 'telemetry';

-- 5. Restore agent nodes the cleanup job mis-archived. Archiving a system actor
--    was a category error (actor identity is outside Decay's domain).
UPDATE memory_nodes
   SET status = 'active', archived_at = NULL
 WHERE node_class = 'system_actor'
   AND status = 'archived';

-- 6. Tombstones ledger. Hard-deletes remove content but never the fact of
--    removal: 帳本不說謊，連對刪除也不說謊.
CREATE TABLE IF NOT EXISTS tombstones (
    id              text PRIMARY KEY,
    workspace_id    text NOT NULL,
    object_type     text NOT NULL CHECK (object_type IN ('node', 'edge')),
    object_id       text NOT NULL,
    relation        text,            -- edges only
    from_id         text,            -- edges only
    to_id           text,            -- edges only
    title           text,            -- nodes only (last known title)
    deleted_by      text,
    deleted_at      timestamptz NOT NULL DEFAULT now(),
    reason_category text NOT NULL DEFAULT 'other'
        CHECK (reason_category IN ('hallucination', 'wrong_direction', 'duplicate', 'pii', 'orphaned', 'other')),
    reason_note     text,
    source_context  jsonb
);
CREATE INDEX IF NOT EXISTS idx_tombstones_ws ON tombstones (workspace_id, deleted_at DESC);
CREATE INDEX IF NOT EXISTS idx_tombstones_object ON tombstones (object_id);

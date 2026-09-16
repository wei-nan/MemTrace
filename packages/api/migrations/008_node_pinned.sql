-- 008_node_pinned.sql
-- Adds node-level pinning, mirroring the pinned flag edges already have
-- (edges.pinned, checked by apply_edge_decay() in 000_baseline_v1.sql).
-- Nodes had no equivalent: apply_node_archiving() could auto-archive any
-- node purely on traversal-count/age, with no way to exempt a structurally
-- important "hub" node (see ws_spec_plan discussion — a platform-overview
-- node with 35 historical edges had every neighbor archived out from under
-- it, fragmenting the graph, because nothing could protect it or them).
--
-- No explicit BEGIN/COMMIT here — run_migrations() applies each file inside
-- its own transaction (core/database.py::db_cursor(commit=True)).

ALTER TABLE memory_nodes ADD COLUMN IF NOT EXISTS pinned boolean NOT NULL DEFAULT false;

CREATE OR REPLACE FUNCTION public.apply_node_archiving() RETURNS integer
    LANGUAGE plpgsql
    AS $function$
DECLARE
  archived_count INTEGER;
BEGIN
  -- 1. Evergreen: traversal-count based
  UPDATE memory_nodes
  SET
    status = 'archived'::node_status,
    archived_at = now()
  FROM workspaces ws
  WHERE memory_nodes.workspace_id = ws.id
    AND ws.kb_type = 'evergreen'
    AND memory_nodes.status = 'active'
    AND memory_nodes.pinned = FALSE
    AND memory_nodes.metadata->>'spec_status' IS DISTINCT FROM 'draft'
    AND memory_nodes.created_at < now() - (ws.archive_window_days || ' days')::INTERVAL
    AND memory_nodes.traversal_count < ws.min_traversals;

  GET DIAGNOSTICS archived_count = ROW_COUNT;

  -- 2. Ephemeral: all-edges-faded based
  UPDATE memory_nodes
  SET
    status = 'archived'::node_status,
    archived_at = now()
  FROM workspaces ws
  WHERE memory_nodes.workspace_id = ws.id
    AND ws.kb_type = 'ephemeral'
    AND memory_nodes.status = 'active'
    AND memory_nodes.pinned = FALSE
    AND memory_nodes.metadata->>'spec_status' IS DISTINCT FROM 'draft'
    -- All edges are either faded or non-existent
    AND NOT EXISTS (
      SELECT 1 FROM edges
      WHERE (from_id = memory_nodes.id OR to_id = memory_nodes.id)
        AND status = 'active'
    )
    -- Node without edges: archive after 60 days of inactivity
    AND (
      memory_nodes.traversal_count = 0
      OR memory_nodes.created_at < now() - INTERVAL '60 days'
    );

  RETURN archived_count + archived_count; -- rough estimation
END;
$function$;

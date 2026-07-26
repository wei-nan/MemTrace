-- 001_spec_validity.sql
-- Phase B of the spec-validity mechanism. See ws_spec_plan/mem_310a1c2d.
--
-- 1. Adds 'superseded_by' to relation_type: an old node points at the node
--    that replaced it, symmetric to how answered_by points inquiry -> answer.
--    (No separate 'supersedes' value — same pattern as answered_by, which
--    has no reverse-named counterpart either.)
-- 2. apply_node_archiving() gains an exclusion: nodes with
--    metadata->>'spec_status' = 'draft' are never auto-archived by
--    traversal-count or edge-fade rules. A draft is "awaiting review," not
--    "unused" — the two ideas must not collapse into the same signal.
--
-- No explicit BEGIN/COMMIT here — run_migrations() applies each file inside
-- its own transaction (core/database.py::db_cursor(commit=True)). Embedding
-- transaction control in the file body is redundant and, worse, makes any
-- ad-hoc "dry run" that calls cur.execute() directly commit for real the
-- moment it hits the file's own COMMIT — bit us once already.

ALTER TYPE relation_type ADD VALUE IF NOT EXISTS 'superseded_by';

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

-- 009_evergreen_no_decay.sql
-- Evergreen KBs are never auto-archived or edge-faded (ws_spec_plan, 2026-09-16).
--
-- Root cause: traversal_count / edges.traversal_count only credit explicit
-- get_node/traverse access (services/edges.py::record_traversal); a search
-- hit deliberately does NOT count (ws_spec_plan/mem_98300428 — "showing up
-- in search results != being accessed"). But the normal way reference
-- content in a spec/evergreen KB actually gets used IS search, not
-- one-at-a-time get_node calls. The old evergreen rules ("archive if never
-- traversed within N days" / "fade the edge if traversal_count = 0") were
-- silently archiving/fading valid, actively-searched content, contradicting
-- the product's own "Evergreen: memory never fades by time" positioning
-- (packages/ui/src/components/CreateWorkspaceModal.tsx). Concretely: 219 of
-- 275 non-trashed nodes in the public spec KB (ws_spec0001, evergreen) had
-- been auto-archived this way.
--
-- This does not change ephemeral-KB behavior (task logs, troubleshooting —
-- time/usage decay is the intended, useful behavior there) or the
-- node/edge-level `pinned` escape hatch, which still applies to ephemeral.
--
-- No explicit BEGIN/COMMIT here — run_migrations() applies each file inside
-- its own transaction (core/database.py::db_cursor(commit=True)).

CREATE OR REPLACE FUNCTION public.apply_node_archiving() RETURNS integer
    LANGUAGE plpgsql
    AS $function$
DECLARE
  archived_count INTEGER;
BEGIN
  -- Evergreen: no automatic archiving (see migration header).

  -- Ephemeral: all-edges-faded based
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

  GET DIAGNOSTICS archived_count = ROW_COUNT;

  RETURN archived_count;
END;
$function$;

CREATE OR REPLACE FUNCTION public.apply_edge_decay() RETURNS integer
    LANGUAGE plpgsql
    AS $$
DECLARE
  updated_count INTEGER;
BEGIN
  -- 1. Time-based decay for 'ephemeral' workspaces
  UPDATE edges
  SET
    weight = GREATEST(
      min_weight,
      weight * POWER(0.5, EXTRACT(EPOCH FROM (now() - last_co_accessed)) / 86400.0 / half_life_days)
    ),
    status = CASE
      WHEN (weight * POWER(0.5, EXTRACT(EPOCH FROM (now() - last_co_accessed)) / 86400.0 / half_life_days)) < min_weight
      THEN 'faded'::edge_status
      ELSE edges.status
    END
  FROM workspaces ws
  WHERE edges.workspace_id = ws.id
    AND ws.kb_type = 'ephemeral'
    AND edges.status = 'active'
    AND edges.pinned = FALSE
    AND edges.last_co_accessed < now() - INTERVAL '1 hour';

  GET DIAGNOSTICS updated_count = ROW_COUNT;

  -- 2. Evergreen: no automatic fading (see migration header) — was
  --    "fade if traversal_count = 0 and past archive_window_days", removed.

  RETURN updated_count;
END;
$$;

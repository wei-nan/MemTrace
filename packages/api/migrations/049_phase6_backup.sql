-- 049_phase6_backup.sql
-- Phase 6 pre-migration snapshots of critical tables.
-- Purpose: Full rollback capability before any schema changes.
-- Note: Can be safely re-run (IF NOT EXISTS guards).

CREATE TABLE IF NOT EXISTS _migration_backup_workspaces_v6 AS
  SELECT *, now() AS _snapshot_at FROM workspaces WHERE FALSE;

INSERT INTO _migration_backup_workspaces_v6
  SELECT *, now() AS _snapshot_at FROM workspaces
  ON CONFLICT DO NOTHING;

ALTER TABLE _migration_backup_workspaces_v6
  ADD COLUMN IF NOT EXISTS _snapshot_at TIMESTAMPTZ DEFAULT now();

CREATE TABLE IF NOT EXISTS _migration_backup_nodes_v6 AS
  SELECT * FROM memory_nodes WHERE FALSE;

INSERT INTO _migration_backup_nodes_v6
  SELECT * FROM memory_nodes;

CREATE INDEX IF NOT EXISTS idx_bk_nodes_v6_ws
  ON _migration_backup_nodes_v6 (workspace_id);

CREATE TABLE IF NOT EXISTS _migration_backup_edges_v6 AS
  SELECT * FROM edges WHERE FALSE;

INSERT INTO _migration_backup_edges_v6
  SELECT * FROM edges;

CREATE INDEX IF NOT EXISTS idx_bk_edges_v6_ws
  ON _migration_backup_edges_v6 (workspace_id);

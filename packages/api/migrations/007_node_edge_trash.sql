-- 007_node_edge_trash.sql
--
-- Adds a time-boxed soft-delete ("trash") state for nodes and edges, sitting
-- between the existing archive (indefinite fade, mem_3bbdf4dc) and
-- tombstone-delete (immediate, irreversible, mem_347895c4) tracks.
--
-- Decision: ws_spec_plan/mem_bc15e46d (2026-09-10). Confirmed items are moved
-- to `trashed` status; a daily job (jobs/cleanup.py) purges anything past
-- trashed_at + 30 days via the existing tombstone-delete path, so the final
-- terminal state is unchanged — this only adds a reversible buffer before it.
--
-- Note: the new enum values are added and committed as part of this
-- migration's single transaction (see core/database.py: run_migrations()
-- runs all migration files in one transaction). Application code only
-- references 'trashed' in later, separately-committed request transactions,
-- so the "can't use a new enum value in the same transaction it was added
-- in" Postgres restriction does not apply here — no need to split this into
-- two migration files.

ALTER TYPE node_status ADD VALUE IF NOT EXISTS 'trashed';
ALTER TYPE edge_status ADD VALUE IF NOT EXISTS 'trashed';

ALTER TABLE memory_nodes
    ADD COLUMN IF NOT EXISTS trashed_at timestamptz,
    ADD COLUMN IF NOT EXISTS trashed_by text,
    ADD COLUMN IF NOT EXISTS trash_reason_category text,
    ADD COLUMN IF NOT EXISTS trash_reason_note text;

ALTER TABLE edges
    ADD COLUMN IF NOT EXISTS trashed_at timestamptz,
    ADD COLUMN IF NOT EXISTS trashed_by text,
    ADD COLUMN IF NOT EXISTS trash_reason_category text,
    ADD COLUMN IF NOT EXISTS trash_reason_note text;

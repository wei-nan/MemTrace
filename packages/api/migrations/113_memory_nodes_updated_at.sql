-- 113_memory_nodes_updated_at.sql
-- Root-cause fix: memory_nodes.updated_at was nullable with no DEFAULT and no trigger,
-- unlike created_at (DEFAULT now() NOT NULL). Any write path that omitted updated_at
-- (including direct DB edits) left a NULL, which then crashed result sorting in
-- services/search.py ("NoneType vs datetime"), disabling search_nodes — and with it
-- the create-time de-duplication guard — for the whole workspace.
--
-- Defense in depth: backfill existing NULLs, then make the column structurally
-- symmetric with created_at, and wire the existing update_timestamp() trigger so
-- INSERT/UPDATE always refresh it (mirrors trg_workspaces_updated_at).
-- Idempotent: safe to re-run on already-migrated databases.

-- 1. Backfill existing NULLs (fall back to created_at, which is NOT NULL).
UPDATE public.memory_nodes
   SET updated_at = created_at
 WHERE updated_at IS NULL;

-- 2. Give the column a default so any insert path is covered even if triggers are off.
ALTER TABLE public.memory_nodes
    ALTER COLUMN updated_at SET DEFAULT now();

-- 3. Enforce the invariant at the DB level (symmetric with created_at).
ALTER TABLE public.memory_nodes
    ALTER COLUMN updated_at SET NOT NULL;

-- 4. Keep updated_at fresh on every INSERT/UPDATE via the existing trigger function.
DROP TRIGGER IF EXISTS trg_memory_nodes_updated_at ON public.memory_nodes;
CREATE TRIGGER trg_memory_nodes_updated_at
    BEFORE INSERT OR UPDATE ON public.memory_nodes
    FOR EACH ROW EXECUTE FUNCTION public.update_timestamp();

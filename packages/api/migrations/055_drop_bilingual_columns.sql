-- 055_drop_bilingual_columns.sql
-- Phase 6 S3-T11: Drop the legacy bilingual columns.
--
-- PREREQUISITES (all must be complete before applying this migration):
--   1. All code references to title_zh/title_en/body_zh/body_en removed (S3-T11 grep check)
--   2. memory_nodes.title column fully populated (NOT NULL) — via 052 + consolidate_fields.py
--   3. workspaces.name column fully populated (NOT NULL) — via 053 + consolidate_fields.py
--   4. search_vector trigger updated to use single columns (done in this file)
--   5. Stage 2 audit passed (M5=100%, M7=100%)
--   6. Integration tests passing against new single-column schema
--
-- IMPORTANT: The _migration_backup_*_v6 tables must remain for 30 days post-migration.

-- ── 1. Drop search_vector (GENERATED ALWAYS AS — must drop before dropping source columns)
-- The column was created in 022_search_vector.sql as GENERATED ALWAYS.
ALTER TABLE memory_nodes DROP COLUMN IF EXISTS search_vector;

-- Backfill single-language title and body from bilingual columns if they still exist
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'memory_nodes' AND column_name = 'title_zh'
    ) THEN
        UPDATE memory_nodes SET title = coalesce(title_zh, title_en, 'Untitled') WHERE title IS NULL;
        UPDATE memory_nodes SET body = coalesce(body_zh, body_en, '') WHERE body = '';
    END IF;
END;
$$;

-- ── 2. Drop bilingual node columns
ALTER TABLE memory_nodes
  DROP COLUMN IF EXISTS title_zh,
  DROP COLUMN IF EXISTS title_en,
  DROP COLUMN IF EXISTS body_zh,
  DROP COLUMN IF EXISTS body_en;


-- ── 3. Drop bilingual workspace columns
ALTER TABLE workspaces
  DROP COLUMN IF EXISTS name_zh,
  DROP COLUMN IF EXISTS name_en;

-- ── 4. Re-create search_vector as a regular tsvector column + trigger
--       (cannot use GENERATED ALWAYS after dropping the source columns)
ALTER TABLE memory_nodes
  ADD COLUMN IF NOT EXISTS search_vector tsvector;

-- Back-fill existing rows
UPDATE memory_nodes
SET search_vector = to_tsvector('simple', coalesce(title, '') || ' ' || coalesce(body, ''));

-- Trigger for future updates
CREATE OR REPLACE FUNCTION nodes_search_vector_update()
RETURNS trigger AS $$
BEGIN
  NEW.search_vector := to_tsvector(
    'simple',
    coalesce(NEW.title, '') || ' ' || coalesce(NEW.body, '')
  );
  RETURN NEW;
END
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_nodes_search_vector ON memory_nodes;
CREATE TRIGGER trg_nodes_search_vector
  BEFORE INSERT OR UPDATE OF title, body
  ON memory_nodes
  FOR EACH ROW
  EXECUTE FUNCTION nodes_search_vector_update();

CREATE INDEX IF NOT EXISTS idx_nodes_search_vector
  ON memory_nodes USING GIN (search_vector);

-- ── 5. Enforce NOT NULL on memory_nodes.title (should already be NOT NULL after consolidation)
ALTER TABLE memory_nodes
  ALTER COLUMN title SET NOT NULL;

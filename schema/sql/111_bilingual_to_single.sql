-- Migration: Consolidate bilingual columns into single-language title/body
-- Idempotent: safe to run on DBs that already have single-language columns.
-- For fresh installs, this runs after 001_init.sql (bilingual) and seed files.

-- ── Step 1: Add single-language columns if they don't exist ─────────────────
ALTER TABLE memory_nodes ADD COLUMN IF NOT EXISTS title TEXT;
ALTER TABLE memory_nodes ADD COLUMN IF NOT EXISTS body  TEXT NOT NULL DEFAULT '';

-- ── Step 2: Populate from bilingual columns (only when they still exist) ────
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'memory_nodes' AND column_name = 'title_zh'
    ) THEN
        -- Collapse zh → en for title
        UPDATE memory_nodes
        SET title = COALESCE(NULLIF(title_zh, ''), NULLIF(title_en, ''), 'untitled')
        WHERE title IS NULL;

        -- Collapse zh → en for body
        UPDATE memory_nodes
        SET body = COALESCE(NULLIF(body_zh, ''), body_en, '')
        WHERE body = '' AND (COALESCE(body_zh,'') != '' OR COALESCE(body_en,'') != '');
    END IF;
END;
$$;

-- ── Step 3: Ensure title is NOT NULL ────────────────────────────────────────
UPDATE memory_nodes SET title = 'untitled' WHERE title IS NULL OR title = '';
ALTER TABLE memory_nodes ALTER COLUMN title SET NOT NULL;

-- ── Step 4: Replace GENERATED search_vector (from bilingual) with regular ──
-- A GENERATED ALWAYS column cannot be dropped independently; we must drop the
-- whole column first, then re-add as a plain column driven by a trigger.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'memory_nodes' AND column_name = 'search_vector'
          AND is_generated = 'ALWAYS'
    ) THEN
        ALTER TABLE memory_nodes DROP COLUMN search_vector;
    END IF;
END;
$$;

ALTER TABLE memory_nodes ADD COLUMN IF NOT EXISTS search_vector tsvector;

-- ── Step 5: Create / replace trigger function ────────────────────────────────
CREATE OR REPLACE FUNCTION nodes_search_vector_update()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    NEW.search_vector := to_tsvector(
        'simple',
        coalesce(NEW.title, '') || ' ' || coalesce(NEW.body, '')
    );
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_nodes_search_vector ON memory_nodes;
CREATE TRIGGER trg_nodes_search_vector
    BEFORE INSERT OR UPDATE OF title, body ON memory_nodes
    FOR EACH ROW EXECUTE FUNCTION nodes_search_vector_update();

-- ── Step 6: GIN indexes ──────────────────────────────────────────────────────
DROP INDEX IF EXISTS idx_nodes_search;
CREATE INDEX IF NOT EXISTS idx_nodes_search_vector ON memory_nodes USING GIN(search_vector);
CREATE INDEX IF NOT EXISTS idx_nodes_title
    ON memory_nodes USING GIN(to_tsvector('simple', COALESCE(title, '')));

-- ── Step 7: Drop bilingual columns ──────────────────────────────────────────
ALTER TABLE memory_nodes DROP COLUMN IF EXISTS title_zh;
ALTER TABLE memory_nodes DROP COLUMN IF EXISTS title_en;
ALTER TABLE memory_nodes DROP COLUMN IF EXISTS body_zh;
ALTER TABLE memory_nodes DROP COLUMN IF EXISTS body_en;

-- ── Step 8: Backfill search_vector for existing rows ────────────────────────
UPDATE memory_nodes
SET search_vector = to_tsvector('simple', coalesce(title, '') || ' ' || coalesce(body, ''))
WHERE search_vector IS NULL;

-- ── Step 9: Add proceeds_to and extracted_from to relation_type if missing ──
ALTER TYPE relation_type ADD VALUE IF NOT EXISTS 'proceeds_to';
ALTER TYPE relation_type ADD VALUE IF NOT EXISTS 'extracted_from';

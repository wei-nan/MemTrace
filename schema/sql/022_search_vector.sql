-- schema/sql/022_search_vector.sql
-- NOTE: This file adds a plain search_vector column for fresh installs.
-- The column is populated by trigger trg_nodes_search_vector (created in 111_bilingual_to_single.sql).
-- For installs upgrading from the old GENERATED ALWAYS approach, 111_ handles the conversion.
ALTER TABLE memory_nodes ADD COLUMN IF NOT EXISTS search_vector tsvector;

CREATE INDEX IF NOT EXISTS idx_nodes_search_vector ON memory_nodes USING GIN(search_vector);

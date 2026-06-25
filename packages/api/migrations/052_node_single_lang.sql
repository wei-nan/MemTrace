-- 052_node_single_lang.sql
-- Phase 6 S2-T07: Add single-language title and body columns to memory_nodes.
-- These columns are filled by scripts/phase6/consolidate_fields.py
-- and set NOT NULL only AFTER all data has been migrated.
-- The old title_zh/en and body_zh/en columns are dropped in 055_drop_bilingual_columns.sql.

ALTER TABLE memory_nodes
  ADD COLUMN IF NOT EXISTS title TEXT,
  ADD COLUMN IF NOT EXISTS body  TEXT NOT NULL DEFAULT '';

CREATE INDEX IF NOT EXISTS idx_nodes_title ON memory_nodes USING GIN (to_tsvector('simple', coalesce(title, '')));

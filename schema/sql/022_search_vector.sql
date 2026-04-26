-- schema/sql/022_search_vector.sql
ALTER TABLE memory_nodes
  ADD COLUMN IF NOT EXISTS search_vector tsvector
  GENERATED ALWAYS AS (
    to_tsvector('simple',
      coalesce(title_zh,'') || ' ' || coalesce(title_en,'') || ' ' ||
      coalesce(body_zh,'')  || ' ' || coalesce(body_en,''))
  ) STORED;

CREATE INDEX IF NOT EXISTS idx_nodes_search ON memory_nodes USING GIN(search_vector);

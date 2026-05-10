-- 042_add_source_tracing_fields.sql
-- Phase 4.8: S5-6, P4.9: I-002
-- Link nodes back to their source document node and specific paragraph.

ALTER TABLE memory_nodes
  ADD COLUMN IF NOT EXISTS source_doc_node_id  TEXT REFERENCES memory_nodes(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS source_paragraph_ref TEXT;

CREATE INDEX IF NOT EXISTS idx_memory_nodes_source_doc ON memory_nodes(source_doc_node_id);

-- 057_p61_doc_nodes.sql
-- Phase 6.1 T01: Document-as-node + extracted_from edge architecture
--
-- Changes:
--   1. Add 'extracted_from' to relation_type enum
--   2. Add 'document' to content_type enum
--   3. Add documents.node_id FK → memory_nodes

-- 1. Extend relation_type enum
ALTER TYPE relation_type ADD VALUE IF NOT EXISTS 'extracted_from';

-- 2. Extend content_type enum
ALTER TYPE content_type ADD VALUE IF NOT EXISTS 'document';

-- 3. Add node_id FK on documents (nullable; filled by ingestion + migration script)
ALTER TABLE documents
  ADD COLUMN IF NOT EXISTS node_id TEXT REFERENCES memory_nodes(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_docs_node_id ON documents (node_id);

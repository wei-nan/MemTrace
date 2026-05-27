-- 056_drop_source_doc_enum.sql
-- Phase 6 S2-T09: Remove 'source_document' value from content_type enum.
--
-- PREREQUISITE: scripts/phase6/migrate_source_docs.py must have run to completion
-- with 0 remaining source_document nodes.
-- Verify: SELECT count(*) FROM memory_nodes WHERE content_type = 'source_document';
--         Must return 0 before applying this migration.
--
-- PostgreSQL cannot DROP a value from an existing ENUM directly.
-- The workaround is to rename the old type and create a new one.

-- SQL-based auto-migration of source_document nodes to documents table
-- (runs before dropping the enum to make the migration self-contained and robust)

-- 1. Insert documents
INSERT INTO documents (
  id, workspace_id, filename, content_hash, mime_type,
  size_bytes, storage_path, title, uploaded_by, ingestion_job_id
)
SELECT
  'doc_' || id, workspace_id, coalesce(source_file, source_document, 'doc_' || id || '.txt'),
  coalesce(signature, md5(coalesce(body, ''))), 'text/plain',
  octet_length(coalesce(body, '')),
  '/app/data/documents/' || workspace_id || '/' || 'doc_' || id || '.txt',
  coalesce(title, 'Document'),
  author,
  null
FROM memory_nodes
WHERE content_type::text = 'source_document'
ON CONFLICT DO NOTHING;

-- 2. Insert node_document_links
INSERT INTO node_document_links (node_id, document_id, paragraph_ref, excerpt)
SELECT
  child.id, 'doc_' || parent.id, coalesce(child.source_paragraph_ref, ''), substring(coalesce(child.body, '') from 1 for 500)
FROM memory_nodes child
JOIN memory_nodes parent ON parent.id = child.source_doc_node_id
WHERE parent.content_type::text = 'source_document' AND child.status != 'archived'
ON CONFLICT DO NOTHING;

-- 3. Delete source_document nodes from memory_nodes
DELETE FROM memory_nodes WHERE content_type::text = 'source_document';

-- Step 1: Rename old enum
ALTER TYPE content_type RENAME TO content_type_old;


-- Step 2: Create new enum without 'source_document'
CREATE TYPE content_type AS ENUM (
  'factual', 'procedural', 'preference', 'context', 'inquiry'
);

-- Step 3: Migrate the column in memory_nodes
ALTER TABLE memory_nodes
  ALTER COLUMN content_type TYPE content_type
  USING content_type::text::content_type;

-- Step 3.5: Break dependency in backup table by converting to text
ALTER TABLE _migration_backup_nodes_v6
  ALTER COLUMN content_type TYPE text;

-- Step 4: Drop old enum
DROP TYPE content_type_old;

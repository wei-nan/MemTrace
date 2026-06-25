-- 051_documents.sql
-- Phase 6: First-class document support.
-- Creates `documents` table and `node_document_links` many-to-many join table.

CREATE TABLE IF NOT EXISTS documents (
  id               TEXT PRIMARY KEY,          -- doc_<hex8>
  workspace_id     TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  filename         TEXT NOT NULL,
  content_hash     TEXT NOT NULL,             -- SHA-256 of file bytes
  mime_type        TEXT NOT NULL,
  size_bytes       BIGINT NOT NULL,
  storage_path     TEXT NOT NULL,
  title            TEXT,                      -- user-editable display title
  summary          TEXT,                      -- AI-generated summary ≤200 chars
  source_url       TEXT,
  uploaded_by      TEXT NOT NULL REFERENCES users(id),
  uploaded_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  ingestion_job_id TEXT REFERENCES ingestion_logs(id) ON DELETE SET NULL,
  UNIQUE (workspace_id, content_hash)
);

CREATE INDEX IF NOT EXISTS idx_docs_ws     ON documents (workspace_id);
CREATE INDEX IF NOT EXISTS idx_docs_hash   ON documents (content_hash);
CREATE INDEX IF NOT EXISTS idx_docs_upload ON documents (workspace_id, uploaded_at DESC);

CREATE TABLE IF NOT EXISTS node_document_links (
  node_id       TEXT NOT NULL REFERENCES memory_nodes(id) ON DELETE CASCADE,
  document_id   TEXT NOT NULL REFERENCES documents(id)   ON DELETE CASCADE,
  paragraph_ref TEXT NOT NULL DEFAULT '',     -- segment/chunk identifier, e.g. "Chunk 3 (Overview > Auth)"
  excerpt       TEXT,                         -- up to 500 chars of the relevant passage
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (node_id, document_id, paragraph_ref)
);

CREATE INDEX IF NOT EXISTS idx_ndl_node ON node_document_links (node_id);
CREATE INDEX IF NOT EXISTS idx_ndl_doc  ON node_document_links (document_id);

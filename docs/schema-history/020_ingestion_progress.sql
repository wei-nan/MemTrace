SET client_encoding = 'UTF8';
-- ─────────────────────────────────────────────────────────────────
--  MemTrace — Migration 020: Ingestion chunk-level progress
-- ─────────────────────────────────────────────────────────────────
--  Adds two columns so the UI can render a real progress bar while
--  a large document is being chunked & extracted in the background.

ALTER TABLE ingestion_logs
    ADD COLUMN IF NOT EXISTS chunks_total INT,
    ADD COLUMN IF NOT EXISTS chunks_done  INT NOT NULL DEFAULT 0;

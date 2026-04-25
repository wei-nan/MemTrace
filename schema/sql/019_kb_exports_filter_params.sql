SET client_encoding = 'UTF8';
ALTER TABLE kb_exports
  ADD COLUMN IF NOT EXISTS filter_params JSONB,
  ADD COLUMN IF NOT EXISTS file_path TEXT;

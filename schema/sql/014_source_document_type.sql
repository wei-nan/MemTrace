SET client_encoding = 'UTF8';
-- C4: Source Document node type
ALTER TYPE content_type ADD VALUE IF NOT EXISTS 'source_document';
ALTER TABLE memory_nodes ADD COLUMN IF NOT EXISTS source_file TEXT;

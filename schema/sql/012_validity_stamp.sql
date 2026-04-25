SET client_encoding = 'UTF8';
ALTER TABLE memory_nodes
  ADD COLUMN IF NOT EXISTS validity_confirmed_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS validity_confirmed_by TEXT;

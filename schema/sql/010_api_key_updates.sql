SET client_encoding = 'UTF8';
-- Migration to add revoked_at and last_used_ip to api_keys table
ALTER TABLE api_keys
  ADD COLUMN IF NOT EXISTS revoked_at   TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS last_used_ip INET;

-- Migration: 012_nullable_key_enc.sql
-- Description: Allow NULL for key_enc and key_hint in user_ai_keys.
--   This is required for Ollama provider which uses base_url/auth_token 
--   instead of a standard API key.

ALTER TABLE user_ai_keys 
  ALTER COLUMN key_enc DROP NOT NULL,
  ALTER COLUMN key_hint DROP NOT NULL;

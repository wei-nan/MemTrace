-- Migration: 028_ollama_provider.sql
-- Description: Add base_url, auth_mode, and auth_token columns to user_ai_keys for Ollama support.

ALTER TABLE user_ai_keys
  ADD COLUMN base_url   TEXT,
  ADD COLUMN auth_mode  TEXT CHECK (auth_mode IN ('none', 'bearer')) DEFAULT 'none',
  ADD COLUMN auth_token TEXT; -- This will be encrypted via existing key encryption mechanism if used

-- Comment: G-1 in Phase 4

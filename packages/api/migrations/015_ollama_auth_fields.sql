-- Migration: 015_ollama_auth_fields.sql
-- Description: Add base_url, auth_mode, and auth_token columns to user_ai_keys for Ollama support.
--   Note: Using IF NOT EXISTS to ensure compatibility if manually applied.

ALTER TABLE user_ai_keys
  ADD COLUMN IF NOT EXISTS base_url   TEXT,
  ADD COLUMN IF NOT EXISTS auth_mode  TEXT CHECK (auth_mode IN ('none', 'bearer')) DEFAULT 'none',
  ADD COLUMN IF NOT EXISTS auth_token TEXT;

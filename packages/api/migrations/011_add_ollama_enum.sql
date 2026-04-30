-- Migration: 011_add_ollama_enum.sql
-- Description: Add 'ollama' to the ai_provider enum type.
--   008_ollama_provider.sql added the supporting columns (base_url / auth_mode /
--   auth_token) but forgot to extend the enum, causing inserts to fail with
--   "invalid input value for enum ai_provider: 'ollama'".

ALTER TYPE ai_provider ADD VALUE IF NOT EXISTS 'ollama';

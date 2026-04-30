-- Migration: 010_ollama_models.sql
-- Description: Add default_chat_model and default_embedding_model to user_ai_keys.

ALTER TABLE user_ai_keys
  ADD COLUMN IF NOT EXISTS default_chat_model      TEXT,
  ADD COLUMN IF NOT EXISTS default_embedding_model TEXT;

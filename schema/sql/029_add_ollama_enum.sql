-- Migration: 029_add_ollama_enum.sql
-- Description: Add 'ollama' to the ai_provider enum type.

ALTER TYPE ai_provider ADD VALUE IF NOT EXISTS 'ollama';

-- Migration 118: per-user notification preferences
-- Stores which notification groups the user has disabled.
-- Default empty object = all groups enabled.
ALTER TABLE users
  ADD COLUMN IF NOT EXISTS notification_preferences JSONB NOT NULL DEFAULT '{}'::jsonb;

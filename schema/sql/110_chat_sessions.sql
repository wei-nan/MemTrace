-- Migration: Phase 6 AI Chat — Persistent Sessions
-- Goal: Store chat sessions and messages server-side for history continuity and Route C graph anchoring.

CREATE TABLE IF NOT EXISTS chat_sessions (
  id                TEXT PRIMARY KEY,           -- generate_id("chs")
  workspace_id      TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  user_id           TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title             TEXT NOT NULL DEFAULT '',   -- auto-set from first user message (60 chars)
  anchored_node_ids TEXT[] NOT NULL DEFAULT '{}', -- Route C: accumulated hit node IDs
  message_count     INT NOT NULL DEFAULT 0,
  tokens_total      INT NOT NULL DEFAULT 0,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_active_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_chat_sessions_ws_user
  ON chat_sessions(workspace_id, user_id, last_active_at DESC);

CREATE TABLE IF NOT EXISTS chat_messages (
  id              BIGSERIAL PRIMARY KEY,
  session_id      TEXT NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
  role            TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
  content         TEXT NOT NULL,
  source_node_ids TEXT[] NOT NULL DEFAULT '{}', -- nodes hit by this assistant turn
  tokens_used     INT NOT NULL DEFAULT 0,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_session
  ON chat_messages(session_id, created_at ASC);

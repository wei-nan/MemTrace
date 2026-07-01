-- 120_user_voice_keys.sql
-- Personal voice (STT/TTS) credentials, independent from user_ai_keys.
-- Voice providers (gcp/azure/deepgram/elevenlabs) don't overlap cleanly with
-- the chat/embedding ai_provider enum, and STT/TTS must be selectable
-- independently per user (one active key per purpose, not per provider).
-- See spec discussion mem_bede56ef (V6) for the design rationale.

CREATE TABLE IF NOT EXISTS user_voice_keys (
    id              text PRIMARY KEY,
    user_id         text NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    purpose         text NOT NULL CHECK (purpose IN ('stt', 'tts')),
    provider        text NOT NULL CHECK (provider IN ('gcp', 'openai', 'azure', 'deepgram', 'elevenlabs')),
    credential_type text NOT NULL DEFAULT 'api_key' CHECK (credential_type IN ('api_key', 'service_account_json')),
    key_enc         text NOT NULL,
    key_hint        text NOT NULL,
    created_at      timestamp with time zone NOT NULL DEFAULT now(),
    last_used_at    timestamp with time zone,
    UNIQUE (user_id, purpose)
);

CREATE INDEX IF NOT EXISTS idx_user_voice_keys_user ON user_voice_keys(user_id);

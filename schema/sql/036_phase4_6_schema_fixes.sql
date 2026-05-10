-- Phase 4.6 Schema Fixes
-- Addressing risks identified in 035_phase4_6_schema.sql

-- 1. user_registrations: Align field names with tasks.md
DO $$ 
BEGIN 
  IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='user_registrations' AND column_name='reason') THEN
    ALTER TABLE user_registrations RENAME COLUMN reason TO purpose_note;
  END IF;
  
  IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='user_registrations' AND column_name='reviewer_id') THEN
    ALTER TABLE user_registrations RENAME COLUMN reviewer_id TO reviewed_by;
  END IF;
END $$;

ALTER TABLE user_registrations ADD COLUMN IF NOT EXISTS admin_note TEXT;
ALTER TABLE user_registrations ADD COLUMN IF NOT EXISTS notify_rejection BOOLEAN NOT NULL DEFAULT TRUE;

-- 2. anonymous_access_log: Privacy hardening (don't store plaintext IP/UA)
ALTER TABLE anonymous_access_log DROP COLUMN IF EXISTS ip_address;
ALTER TABLE anonymous_access_log ADD COLUMN IF NOT EXISTS ip_hash CHAR(64) NOT NULL DEFAULT 'placeholder';
-- Note: placeholder is just for the ALTER step if table was not empty. 
ALTER TABLE anonymous_access_log ALTER COLUMN ip_hash DROP DEFAULT;

ALTER TABLE anonymous_access_log DROP COLUMN IF EXISTS user_agent;
ALTER TABLE anonymous_access_log ADD COLUMN IF NOT EXISTS user_agent_hash CHAR(64);

-- 3. invitations: Security hardening (don't store plaintext tokens)
ALTER TABLE invitations DROP COLUMN IF EXISTS token;
ALTER TABLE invitations ADD COLUMN IF NOT EXISTS token_hash CHAR(64) UNIQUE;
ALTER TABLE invitations ALTER COLUMN token_hash SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_invitations_token_hash ON invitations (token_hash);

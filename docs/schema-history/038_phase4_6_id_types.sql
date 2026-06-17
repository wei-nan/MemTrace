-- Phase 4.6 Fix: Align ID types with Python generate_id()
-- MemTrace uses custom string prefixes (e.g. reg_xxx, inv_xxx) rather than UUIDs.

-- 1. magic_link_tokens
ALTER TABLE magic_link_tokens ALTER COLUMN id DROP DEFAULT;
ALTER TABLE magic_link_tokens ALTER COLUMN id TYPE TEXT;
ALTER TABLE magic_link_tokens ALTER COLUMN invitation_id TYPE TEXT;

-- 2. user_registrations
ALTER TABLE user_registrations ALTER COLUMN id DROP DEFAULT;
ALTER TABLE user_registrations ALTER COLUMN id TYPE TEXT;

-- 3. invitations
ALTER TABLE invitations ALTER COLUMN id DROP DEFAULT;
ALTER TABLE invitations ALTER COLUMN id TYPE TEXT;

-- 4. anonymous_access_log
-- We used BIGSERIAL in 037, which is fine since it's auto-generated.
-- No change needed there unless we want to use generate_id in Python.
-- For now, let's keep it as BIGSERIAL as implemented in public.py (no ID provided in INSERT).

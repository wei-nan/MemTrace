SET client_encoding = 'UTF8';
-- 016_login_lockout.sql
-- G1 — Login Failure Lockout

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS failed_login_count INT DEFAULT 0,
    ADD COLUMN IF NOT EXISTS locked_until TIMESTAMPTZ;

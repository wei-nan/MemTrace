SET client_encoding = 'UTF8';
-- Allow link-only invites (no email required)
ALTER TABLE workspace_invites ALTER COLUMN email DROP NOT NULL;

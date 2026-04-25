SET client_encoding = 'UTF8';
-- Migration: Add status column to workspace_invites
-- Part of B3/G4 requirements

ALTER TABLE workspace_invites ADD COLUMN status TEXT NOT NULL DEFAULT 'pending' 
  CHECK (status IN ('pending', 'used', 'revoked', 'expired'));

-- Initialize existing records
UPDATE workspace_invites SET status = 'used' WHERE accepted_at IS NOT NULL;
UPDATE workspace_invites SET status = 'expired' WHERE accepted_at IS NULL AND expires_at < now();

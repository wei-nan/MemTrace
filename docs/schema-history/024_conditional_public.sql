-- Add conditional_public visibility option to workspaces
-- This value was used by the join_requests feature (005_join_requests.sql)
-- but was never formally added to the enum.
ALTER TYPE kb_visibility ADD VALUE IF NOT EXISTS 'conditional_public';

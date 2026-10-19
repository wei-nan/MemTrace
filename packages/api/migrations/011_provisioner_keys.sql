-- 011_provisioner_keys.sql
-- A provisioner key lets an external harness create knowledge bases for its owner
-- and receive a workspace-bound kb:write service token for each, without the
-- owner ever handling that token. It can do nothing else (see routers/provision.py).
--   * key_type 'provisioner' joins 'account' and 'service'.
--   * max_workspaces caps how many workspaces one provisioner key may create.
--   * workspaces.provisioned_by_key_id records which provisioner key created a
--     workspace, so the cap can be counted and the origin audited.
--   * api_keys.parent_key_id records which provisioner key minted a service token.
-- Reversible while no provisioner key exists: drop the added columns and index,
-- restore the original key_type CHECK.
ALTER TABLE api_keys DROP CONSTRAINT api_keys_key_type_check;
ALTER TABLE api_keys ADD CONSTRAINT api_keys_key_type_check
    CHECK (key_type::text = ANY (ARRAY['account', 'service', 'provisioner']));

ALTER TABLE api_keys ADD COLUMN max_workspaces integer;
ALTER TABLE api_keys ADD COLUMN parent_key_id text REFERENCES api_keys(id) ON DELETE SET NULL;
ALTER TABLE api_keys ADD CONSTRAINT api_keys_provisioner_shape CHECK (
    key_type::text <> 'provisioner'
    OR (max_workspaces IS NOT NULL AND max_workspaces >= 1
        AND expires_at IS NOT NULL AND workspace_id IS NULL)
);

ALTER TABLE workspaces ADD COLUMN provisioned_by_key_id text REFERENCES api_keys(id) ON DELETE SET NULL;
CREATE INDEX idx_workspaces_provisioned_by ON workspaces (provisioned_by_key_id)
    WHERE provisioned_by_key_id IS NOT NULL;

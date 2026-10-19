-- 012_provision_idempotency.sql
-- Follow-up to 011 (provisioner keys), for a harness manager that retries:
--   * workspaces.provision_request_id / provision_request_hash: the client's Idempotency-Key and a
--     fingerprint of what it asked for. (provisioned_by_key_id, provision_request_id) is unique, so a
--     retry finds the workspace it already created instead of creating another.
--   * api_keys.can_delete_workspaces: a provisioner key may delete the workspaces it created only if its
--     owner switched this on when creating the key. Off by default.
-- Reversible: drop the index and the three columns. No existing row changes.
ALTER TABLE workspaces ADD COLUMN provision_request_id text;
ALTER TABLE workspaces ADD COLUMN provision_request_hash text;
CREATE UNIQUE INDEX uq_workspaces_provision_request
    ON workspaces (provisioned_by_key_id, provision_request_id)
    WHERE provision_request_id IS NOT NULL;

ALTER TABLE api_keys ADD COLUMN can_delete_workspaces boolean NOT NULL DEFAULT false;

# Connector Framework

Connector credentials belong to a user account. Access to a MemTrace knowledge
base is granted separately through an explicit workspace binding. This prevents
one person's Google Drive, Asana, GitHub, or GitLab account from implicitly
mixing data across every knowledge base they can access.

## Core model

- `connector_accounts`: personal provider identity and encrypted credential.
- `connector_bindings`: explicit workspace-to-external-container scope,
  direction, permissions, and event filters.
- `connector_external_objects`: stable mapping between provider objects and
  MemTrace nodes.
- `connector_events`: idempotent inbound event inbox.
- `connector_sync_cursors`: incremental sync checkpoints.
- `connector_runs`: observable execution history.

The provider registry in `services/connector_framework.py` is the shared
capability contract for API validation and future sync workers. Provider-specific
network adapters should consume events, update cursors, write object mappings,
and record each execution in `connector_runs`.

OAuth callback flows and provider-specific synchronization are separate adapter
implementations; the framework deliberately keeps their credentials and scopes
out of workspace records.

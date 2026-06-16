# Migration Baseline Plan

## Current State

`packages/api/core/database.py::run_migrations()` is the runtime migrator. It applies only `packages/api/migrations/*.sql` and records applied files by filename in `schema_migrations`.

`schema/sql/` is the canonical schema history for repository review and new installs. Because `packages/api/migrations/` is ignored by `.gitignore`, every runtime migration that changes schema must be mirrored into `schema/sql/`.

## Double-Write Rule

For the current runtime model, schema changes are written in two places:

1. `packages/api/migrations/NNN_name.sql`
   - Runtime incremental migration for existing deployments.
   - Must be force-added if it needs to be committed because the directory is ignored.
2. `schema/sql/MMM_name.sql`
   - Canonical tracked schema history.
   - Uses the next available canonical sequence number.

Both files must be idempotent. Use `CREATE TABLE IF NOT EXISTS`, `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`, and duplicate-safe enum blocks.

## Current Pairing

| Runtime migration | Canonical migration | Purpose |
| --- | --- | --- |
| `packages/api/migrations/110_job_observability.sql` | `schema/sql/114_job_observability.sql` | Scheduler heartbeats and job run history |
| `packages/api/migrations/111_conductor_safety_queue.sql` | `schema/sql/115_conductor_safety_queue.sql` | Conductor hooks, deliveries, node scale metadata, async safety queue |

## Baseline Design

Do not point `run_migrations()` at all of `schema/sql/` without a baseline. Existing databases record filenames from `packages/api/migrations/`, so the canonical filenames in `schema/sql/` would appear unapplied even when their changes already exist.

Before switching runtime migration source to `schema/sql/`, introduce one of these baseline strategies:

1. **Pinned baseline:** configure the migrator to apply only canonical files at or after a chosen sequence, for example `schema/sql/114_*.sql`.
2. **Explicit allowlist:** configure the migrator with a list of canonical files that are safe for the current deployment.
3. **Baseline stamp:** insert known historical canonical filenames into `schema_migrations` after verifying the live database schema matches them.

For the current one-machine deployment, prefer the pinned baseline approach. It avoids replaying old seed/init migrations while allowing new canonical migrations to become the future runtime source.

## Cutover Checklist

- Inspect the live `schema_migrations` table.
- Verify `packages/api/migrations/110_*` and `111_*` have been applied or apply them once.
- Add a migrator setting such as `MIGRATION_SOURCE=schema_sql` plus `MIGRATION_BASELINE=114`.
- Dry-run list the files that would apply before executing.
- Apply to staging or backup-restorable database first.
- Confirm `scheduler_heartbeats`, `job_runs`, `conductor_hook_subscriptions`, `conductor_deliveries`, and `safety_review_queue` exist.

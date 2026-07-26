-- 124_remove_trust_followup.sql
-- Follow-up to 123_remove_trust.sql. See ws_spec_plan/mem_c10f6685.
--
-- Two columns were missed in the original trust-removal migration:
--
-- 1. kb_health_daily.avg_trust_active — computed from the now-dropped
--    trust_score column; services/analytics.py no longer writes it.
-- 2. memory_nodes.votes_up / votes_down / verifications — confirmed via
--    grep to have zero application-code references anywhere in the repo;
--    dead columns from an earlier, already-removed voting feature, bundled
--    into the same "deferred trust" narrative in docs/SPEC.md.

BEGIN;

ALTER TABLE kb_health_daily DROP COLUMN IF EXISTS avg_trust_active;

ALTER TABLE memory_nodes
  DROP COLUMN IF EXISTS votes_up,
  DROP COLUMN IF EXISTS votes_down,
  DROP COLUMN IF EXISTS verifications;

COMMIT;

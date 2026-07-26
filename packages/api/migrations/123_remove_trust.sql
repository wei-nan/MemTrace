-- 123_remove_trust.sql
-- Trust mechanism full removal (Option C). See ws_spec_plan/mem_c10f6685.
--
-- Drops trust_score + the four dim_* columns and the node_trust_votes vote
-- table from memory_nodes. Also retires the 'answered-low-trust' node_status
-- enum value by folding it into 'answered' (behaviorally equivalent per
-- routers/review.py and jobs/bg_jobs.py — both treat the two states the
-- same way). Live DB confirmed 0 rows in 'answered-low-trust' before this
-- migration was written (ws_spec_plan/mem_d74aa763).

BEGIN;

-- 1. Drop the vote table (FK to memory_nodes.id, no data preserved by design
--    — see mem_c10f6685: this is a breaking migration, not a soft-deprecate).
DROP TABLE IF EXISTS node_trust_votes;

-- 2. Drop the trust score index, then the columns themselves.
DROP INDEX IF EXISTS idx_nodes_trust_score;

ALTER TABLE memory_nodes
  DROP COLUMN IF EXISTS trust_score,
  DROP COLUMN IF EXISTS dim_accuracy,
  DROP COLUMN IF EXISTS dim_freshness,
  DROP COLUMN IF EXISTS dim_utility,
  DROP COLUMN IF EXISTS dim_author_rep;

-- 3. node_status enum: fold 'answered-low-trust' into 'answered'.
-- PostgreSQL has no DROP VALUE, so this is a type swap within one
-- transaction (Postgres rewrites the column in place). The column default
-- must be dropped and re-added around the swap, or it's left pointing at
-- the old (about-to-be-dropped) type.
--
-- _migration_backup_nodes_v6 is a pre-existing, unrelated manual backup
-- snapshot (from the bilingual-to-single migration) whose `status` column
-- also uses this enum. Decouple it to text first so it doesn't block the
-- type rename — this preserves its data, it only stops being enum-typed.
ALTER TABLE _migration_backup_nodes_v6 ALTER COLUMN status TYPE text;

ALTER TABLE memory_nodes ALTER COLUMN status DROP DEFAULT;

ALTER TYPE node_status RENAME TO node_status_old;

CREATE TYPE node_status AS ENUM ('active', 'archived', 'gap', 'answered', 'conflicted');

ALTER TABLE memory_nodes
  ALTER COLUMN status TYPE node_status
  USING (
    CASE WHEN status::text = 'answered-low-trust' THEN 'answered'
         ELSE status::text
    END
  )::node_status;

ALTER TABLE memory_nodes ALTER COLUMN status SET DEFAULT 'active'::node_status;

DROP TYPE node_status_old;

COMMIT;

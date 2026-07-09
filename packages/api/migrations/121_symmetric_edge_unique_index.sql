-- 121_symmetric_edge_unique_index.sql
-- Structural guarantee against both-direction duplicates for symmetric
-- relations (related_to / similar_to). The app-level check in
-- services/edges.create_edge_in_db (P0) blocks the common case, but concurrent
-- inserts of a->b and b->a could still race past it; the existing unique_edge
-- (from_id, to_id, relation) can't catch the reverse. This functional unique
-- index collapses both directions to one canonical pair.
--
-- Prerequisite: existing reverse duplicates were removed by P0b
-- (scripts/p0b_dedup_symmetric_edges.py) so this index can build.

CREATE UNIQUE INDEX IF NOT EXISTS uniq_symmetric_edge
ON edges (LEAST(from_id, to_id), GREATEST(from_id, to_id), relation)
WHERE relation IN ('related_to', 'similar_to');

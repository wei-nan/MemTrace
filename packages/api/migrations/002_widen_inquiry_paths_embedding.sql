-- 002_widen_inquiry_paths_embedding.sql
-- Drops the fixed 1536-dimension constraint (and its dependent ivfflat index)
-- from inquiry_paths.query_emb. See ws_6aa957c3/mem_5cad006f (root cause) and
-- ws_spec_plan/mem_c9c4affd-adjacent investigation, 2026-08-01.
--
-- Each workspace pins its own embedding_provider/embedding_model/embedding_dim
-- (immutable per workspace, see mem_i005-adjacent seed docs). memory_nodes.embedding
-- already supports this: it's an unconstrained `vector` column with no ANN index,
-- queried via `embedding <=> %s::vector` (sequential scan) in services/search.py.
--
-- inquiry_paths.query_emb never followed that pattern — it was left as
-- `vector(1536)` with an ivfflat index (which *requires* a fixed dimension to
-- build), a holdover from when 1536-dim OpenAI embeddings were the only
-- supported case. Verified 2026-08-01: 58 of 113 workspaces (51%) now pin a
-- non-1536 embedding_dim (50 at 1024, 7 at 3072, 1 at 768). Every record_path
-- or search_with_history call for any of those workspaces fails outright with
-- a pgvector dimension-mismatch error — not a rare edge case, a majority case.
--
-- Trade-off: search_with_history's cosine-similarity query on inquiry_paths
-- loses ivfflat-accelerated ANN search and falls back to sequential scan,
-- exactly like memory_nodes.embedding already does. Accepting that trade-off
-- is what makes the column usable for more than half the workspaces that
-- currently get a hard failure instead of a slower query.
--
-- No explicit BEGIN/COMMIT — run_migrations() applies each file inside its
-- own transaction (core/database.py::db_cursor(commit=True)).

DROP INDEX IF EXISTS idx_inquiry_paths_emb;

ALTER TABLE inquiry_paths ALTER COLUMN query_emb TYPE vector;

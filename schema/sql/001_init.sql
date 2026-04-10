-- ─────────────────────────────────────────────────────────────────
--  MemTrace — PostgreSQL Schema v1
--  Auto-executed on first docker-compose up (initdb.d)
-- ─────────────────────────────────────────────────────────────────

-- pgvector extension for semantic search
CREATE EXTENSION IF NOT EXISTS vector;

-- ─── ENUM TYPES ───────────────────────────────────────────────────

CREATE TYPE content_type   AS ENUM ('factual', 'procedural', 'preference', 'context');
CREATE TYPE visibility_type AS ENUM ('public', 'team', 'private');
CREATE TYPE source_type    AS ENUM ('human', 'ai_generated', 'ai_verified');
CREATE TYPE relation_type  AS ENUM ('depends_on', 'extends', 'related_to', 'contradicts');

-- ─── MEMORY NODES ─────────────────────────────────────────────────

CREATE TABLE memory_nodes (
  -- Identity
  id              TEXT PRIMARY KEY,
  schema_version  TEXT NOT NULL DEFAULT '1.0',

  -- Bilingual title
  title_zh        TEXT NOT NULL,
  title_en        TEXT NOT NULL,

  -- Content
  content_type    content_type NOT NULL,
  body_zh         TEXT NOT NULL,
  body_en         TEXT NOT NULL,

  -- Classification
  tags            TEXT[]           NOT NULL DEFAULT '{}',
  visibility      visibility_type  NOT NULL DEFAULT 'private',

  -- Provenance
  author          TEXT         NOT NULL,
  created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
  signature       TEXT         NOT NULL,
  source_type     source_type  NOT NULL,

  -- Trust score (composite)
  trust_score     NUMERIC(4,3) NOT NULL DEFAULT 0 CHECK (trust_score BETWEEN 0 AND 1),

  -- Trust dimensions
  dim_accuracy    NUMERIC(4,3) NOT NULL DEFAULT 0 CHECK (dim_accuracy    BETWEEN 0 AND 1),
  dim_freshness   NUMERIC(4,3) NOT NULL DEFAULT 0 CHECK (dim_freshness   BETWEEN 0 AND 1),
  dim_utility     NUMERIC(4,3) NOT NULL DEFAULT 0 CHECK (dim_utility     BETWEEN 0 AND 1),
  dim_author_rep  NUMERIC(4,3) NOT NULL DEFAULT 0 CHECK (dim_author_rep  BETWEEN 0 AND 1),

  -- Community votes
  votes_up        INTEGER NOT NULL DEFAULT 0 CHECK (votes_up        >= 0),
  votes_down      INTEGER NOT NULL DEFAULT 0 CHECK (votes_down      >= 0),
  verifications   INTEGER NOT NULL DEFAULT 0 CHECK (verifications   >= 0),

  -- Semantic embedding (text-embedding-3-small = 1536 dims)
  embedding       vector(1536)
);

-- Indexes
CREATE INDEX idx_nodes_tags        ON memory_nodes USING GIN (tags);
CREATE INDEX idx_nodes_visibility  ON memory_nodes (visibility);
CREATE INDEX idx_nodes_author      ON memory_nodes (author);
CREATE INDEX idx_nodes_trust_score ON memory_nodes (trust_score);
CREATE INDEX idx_nodes_embedding   ON memory_nodes USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

-- ─── EDGES ────────────────────────────────────────────────────────

CREATE TABLE edges (
  id               TEXT PRIMARY KEY,
  from_id          TEXT          NOT NULL REFERENCES memory_nodes(id) ON DELETE CASCADE,
  to_id            TEXT          NOT NULL REFERENCES memory_nodes(id) ON DELETE CASCADE,
  relation         relation_type NOT NULL,

  -- Decay state
  weight           NUMERIC(6,5)  NOT NULL DEFAULT 1.0 CHECK (weight BETWEEN 0 AND 1),
  co_access_count  INTEGER       NOT NULL DEFAULT 0   CHECK (co_access_count >= 0),
  last_co_accessed TIMESTAMPTZ   NOT NULL DEFAULT now(),

  -- Decay parameters
  half_life_days   INTEGER       NOT NULL DEFAULT 30  CHECK (half_life_days >= 1),
  min_weight       NUMERIC(4,3)  NOT NULL DEFAULT 0.1 CHECK (min_weight BETWEEN 0 AND 1),

  CONSTRAINT no_self_loop CHECK (from_id <> to_id)
);

CREATE INDEX idx_edges_from     ON edges (from_id);
CREATE INDEX idx_edges_to       ON edges (to_id);
CREATE INDEX idx_edges_weight   ON edges (weight);
CREATE INDEX idx_edges_relation ON edges (relation);

-- ─── DECAY FUNCTION ───────────────────────────────────────────────
-- Mirrors packages/core/src/decay.ts :: calculateDecayedWeight()

CREATE OR REPLACE FUNCTION apply_edge_decay()
RETURNS INTEGER AS $$
DECLARE
  updated_count INTEGER;
BEGIN
  -- Update decayed weights
  UPDATE edges
  SET weight = GREATEST(
    min_weight,
    weight * POWER(0.5, EXTRACT(EPOCH FROM (now() - last_co_accessed)) / 86400.0 / half_life_days)
  )
  WHERE last_co_accessed < now() - INTERVAL '1 day';

  GET DIAGNOSTICS updated_count = ROW_COUNT;

  -- Remove edges that have fully decayed (weight == min_weight and stale > 2x half_life)
  DELETE FROM edges
  WHERE weight <= min_weight
    AND last_co_accessed < now() - (half_life_days * 2 || ' days')::INTERVAL;

  RETURN updated_count;
END;
$$ LANGUAGE plpgsql;

-- ─── CO-ACCESS BOOST FUNCTION ─────────────────────────────────────

CREATE OR REPLACE FUNCTION record_co_access(edge_id TEXT)
RETURNS VOID AS $$
DECLARE
  rel relation_type;
  boost NUMERIC;
BEGIN
  SELECT relation INTO rel FROM edges WHERE id = edge_id;

  -- Boost amount depends on relation type (matches SPEC intent)
  boost := CASE rel
    WHEN 'depends_on'  THEN 0.3
    WHEN 'extends'     THEN 0.2
    WHEN 'related_to'  THEN 0.15
    WHEN 'contradicts' THEN 0.1
    ELSE 0.1
  END;

  UPDATE edges
  SET
    weight           = LEAST(1.0, weight + boost),
    co_access_count  = co_access_count + 1,
    last_co_accessed = now()
  WHERE id = edge_id;
END;
$$ LANGUAGE plpgsql;

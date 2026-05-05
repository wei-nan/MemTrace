-- ─────────────────────────────────────────────────────────────────
--  MemTrace — PostgreSQL Schema v1
--  Auto-executed on first docker-compose up (initdb.d)
-- ─────────────────────────────────────────────────────────────────

SET client_encoding = 'UTF8';

-- pgvector extension for semantic search
CREATE EXTENSION IF NOT EXISTS vector;

-- ─── ENUM TYPES ───────────────────────────────────────────────────

CREATE TYPE content_type    AS ENUM ('factual', 'procedural', 'preference', 'context', 'inquiry');
CREATE TYPE content_format  AS ENUM ('plain', 'markdown');
CREATE TYPE visibility_type AS ENUM ('public', 'team', 'private');
CREATE TYPE source_type     AS ENUM ('human', 'ai_generated', 'ai_verified', 'document', 'qa_conversation', 'mcp');
CREATE TYPE relation_type   AS ENUM ('depends_on', 'extends', 'related_to', 'contradicts', 'answered_by', 'similar_to', 'queried_via_mcp');
CREATE TYPE kb_visibility   AS ENUM ('public', 'restricted', 'private');
CREATE TYPE member_role     AS ENUM ('viewer', 'editor');
CREATE TYPE kb_type         AS ENUM ('evergreen', 'ephemeral');
CREATE TYPE node_status     AS ENUM ('active', 'archived', 'gap', 'answered', 'answered-low-trust', 'conflicted');
CREATE TYPE edge_status     AS ENUM ('active', 'faded', 'pinned');

-- ─── USERS ────────────────────────────────────────────────────────

CREATE TABLE users (
  id              TEXT PRIMARY KEY,              -- usr_<hex8>
  display_name    TEXT        NOT NULL,
  email           TEXT        NOT NULL UNIQUE,
  email_verified  BOOLEAN     NOT NULL DEFAULT FALSE,
  password_hash   TEXT,                          -- NULL for OAuth-only accounts
  avatar_url      TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_login_at   TIMESTAMPTZ,

  -- Onboarding state (JSON blob)
  onboarding      JSONB       NOT NULL DEFAULT '{
    "completed": false,
    "steps_done": [],
    "steps_skipped": [],
    "first_kb_id": null
  }'::JSONB
);

CREATE INDEX idx_users_email ON users (email);

-- ─── OAUTH IDENTITIES ─────────────────────────────────────────────

CREATE TABLE oauth_identities (
  id          TEXT PRIMARY KEY,
  user_id     TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  provider    TEXT NOT NULL,                     -- 'google'
  subject     TEXT NOT NULL,                     -- provider's `sub` claim
  linked_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (provider, subject)
);

-- ─── SESSION BLOCKLIST (for logout invalidation) ──────────────────

CREATE TABLE session_blocklist (
  jti         TEXT PRIMARY KEY,                  -- JWT ID claim
  expires_at  TIMESTAMPTZ NOT NULL
);

-- ─── PASSWORD RESET TOKENS ───────────────────────────────────────

CREATE TABLE password_reset_tokens (
  token       TEXT PRIMARY KEY,
  user_id     TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE UNIQUE,
  expires_at  TIMESTAMPTZ NOT NULL
);

CREATE TABLE email_verification_tokens (
  token       TEXT PRIMARY KEY,
  user_id     TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  expires_at  TIMESTAMPTZ NOT NULL
);

-- ─── API KEYS ─────────────────────────────────────────────────────

CREATE TABLE api_keys (
  id            TEXT PRIMARY KEY,                -- apikey_<hex8>
  user_id       TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name          TEXT NOT NULL,
  key_hash      TEXT NOT NULL UNIQUE,            -- bcrypt/sha256 of full key
  prefix        TEXT NOT NULL,                   -- first 12 chars shown in UI
  scopes        TEXT[] NOT NULL DEFAULT '{}',
  workspace_id  TEXT,                            -- NULL = all workspaces
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_used_at  TIMESTAMPTZ,
  expires_at    TIMESTAMPTZ
);

-- ─── KNOWLEDGE BASES (WORKSPACES) ─────────────────────────────────



CREATE TABLE workspaces (
  id            TEXT PRIMARY KEY,                -- ws_<hex8>
  schema_version TEXT NOT NULL DEFAULT '1.0',
  name_zh       TEXT NOT NULL,
  name_en       TEXT NOT NULL,
  visibility    kb_visibility NOT NULL DEFAULT 'private',
  kb_type       kb_type NOT NULL DEFAULT 'evergreen',  -- immutable after creation
  owner_id      TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  
  -- Decay & Archive config (SPEC §7.3)
  archive_window_days  INTEGER NOT NULL DEFAULT 90,
  min_traversals       INTEGER NOT NULL DEFAULT 1,
  
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),

  -- AI Model Locking (Phase 4.1)
  embedding_model TEXT,
  embedding_dim   INTEGER,

  -- Q&A Archiving (Phase 4.5)
  qa_archive_mode VARCHAR(20) NOT NULL DEFAULT 'manual_review'
                  CHECK (qa_archive_mode IN ('manual_review', 'auto_active')),
  
  -- Workspace Agent (P4.5-1B-0)
  agent_node_id TEXT
);

CREATE TABLE workspace_members (
  workspace_id  TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  user_id       TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role          member_role NOT NULL DEFAULT 'viewer',
  joined_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (workspace_id, user_id)
);

CREATE TABLE workspace_invites (
  id            TEXT PRIMARY KEY,                -- inv_<hex8>
  workspace_id  TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  email         TEXT NOT NULL,
  role          member_role NOT NULL DEFAULT 'viewer',
  token         TEXT NOT NULL UNIQUE,
  inviter_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at    TIMESTAMPTZ NOT NULL,
  accepted_at   TIMESTAMPTZ
);

CREATE INDEX idx_members_user ON workspace_members (user_id);
CREATE INDEX idx_invites_token ON workspace_invites (token);

CREATE INDEX idx_workspaces_owner      ON workspaces (owner_id);
CREATE INDEX idx_workspaces_visibility ON workspaces (visibility);



-- ─── MEMORY NODES ─────────────────────────────────────────────────

CREATE TABLE memory_nodes (
  -- Identity
  id              TEXT PRIMARY KEY,              -- mem_<hex8>
  schema_version  TEXT NOT NULL DEFAULT '1.0',
  workspace_id    TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,

  -- Bilingual title
  title_zh        TEXT NOT NULL,
  title_en        TEXT NOT NULL,

  -- Content
  content_type    content_type   NOT NULL,
  content_format  content_format NOT NULL DEFAULT 'plain',
  body_zh         TEXT NOT NULL DEFAULT '',
  body_en         TEXT NOT NULL DEFAULT '',

  -- Classification
  tags            TEXT[]           NOT NULL DEFAULT '{}',
  visibility      visibility_type  NOT NULL DEFAULT 'private',

  -- Provenance
  author          TEXT         NOT NULL,
  created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ,                   -- set on edit
  signature       TEXT         NOT NULL,         -- SHA-256 of content fields
  source_type     source_type  NOT NULL DEFAULT 'human',

  -- AI extraction metadata (nullable)
  source_document   TEXT,                        -- filename or SHA-256 of source
  extraction_model  TEXT,                        -- AI model identifier
  copied_from_node  TEXT,                        -- original node_id if copied
  copied_from_ws    TEXT,                        -- original workspace_id if copied

  -- Trust score (composite)
  trust_score     NUMERIC(4,3) NOT NULL DEFAULT 0.5 CHECK (trust_score BETWEEN 0 AND 1),

  -- Trust dimensions
  dim_accuracy    NUMERIC(4,3) NOT NULL DEFAULT 0.5 CHECK (dim_accuracy   BETWEEN 0 AND 1),
  dim_freshness   NUMERIC(4,3) NOT NULL DEFAULT 1.0 CHECK (dim_freshness  BETWEEN 0 AND 1),
  dim_utility     NUMERIC(4,3) NOT NULL DEFAULT 0.5 CHECK (dim_utility    BETWEEN 0 AND 1),
  dim_author_rep  NUMERIC(4,3) NOT NULL DEFAULT 0.5 CHECK (dim_author_rep BETWEEN 0 AND 1),

  -- Community votes
  votes_up        INTEGER NOT NULL DEFAULT 0 CHECK (votes_up        >= 0),
  votes_down      INTEGER NOT NULL DEFAULT 0 CHECK (votes_down      >= 0),
  verifications   INTEGER NOT NULL DEFAULT 0 CHECK (verifications   >= 0),

  -- Traversal tracking
  traversal_count          INTEGER NOT NULL DEFAULT 0 CHECK (traversal_count          >= 0),
  unique_traverser_count   INTEGER NOT NULL DEFAULT 0 CHECK (unique_traverser_count   >= 0),

  -- Lifecycle (SPEC §7.3)
  status          node_status NOT NULL DEFAULT 'active',
  archived_at     TIMESTAMPTZ,

  -- Phase 4.5
  miss_count      INTEGER NOT NULL DEFAULT 0,
  ask_count       INTEGER NOT NULL DEFAULT 0,

  -- Semantic embedding (Phase 4.1: dynamic vector size based on locked model)
  embedding       vector
);

CREATE INDEX idx_nodes_workspace   ON memory_nodes (workspace_id);
CREATE INDEX idx_nodes_tags        ON memory_nodes USING GIN (tags);
CREATE INDEX idx_nodes_visibility  ON memory_nodes (visibility);
CREATE INDEX idx_nodes_author      ON memory_nodes (author);
CREATE INDEX idx_nodes_trust_score ON memory_nodes (trust_score);
-- Note: Generic vector type (Phase 4.1) does not support HNSW/IVFFlat indexing.
-- Sequential scan with workspace_id filtering is used for semantic search.


-- ─── EDGES ────────────────────────────────────────────────────────

CREATE TABLE edges (
  id               TEXT PRIMARY KEY,             -- edge_<hex8>
  workspace_id     TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  from_id          TEXT NOT NULL REFERENCES memory_nodes(id) ON DELETE CASCADE,
  to_id            TEXT NOT NULL REFERENCES memory_nodes(id) ON DELETE CASCADE,
  relation         relation_type NOT NULL,

  -- Decay state
  weight           NUMERIC(6,5)  NOT NULL DEFAULT 1.0 CHECK (weight BETWEEN 0 AND 1),
  co_access_count  INTEGER       NOT NULL DEFAULT 0   CHECK (co_access_count >= 0),
  last_co_accessed TIMESTAMPTZ   NOT NULL DEFAULT now(),

  -- Decay parameters
  half_life_days   INTEGER       NOT NULL DEFAULT 30  CHECK (half_life_days >= 1),
  min_weight       NUMERIC(4,3)  NOT NULL DEFAULT 0.1 CHECK (min_weight BETWEEN 0 AND 1),

  -- Lifecycle (SPEC §7.3)
  status           edge_status   NOT NULL DEFAULT 'active',
  pinned           BOOLEAN       NOT NULL DEFAULT FALSE,

  -- Traversal tracking
  traversal_count  INTEGER       NOT NULL DEFAULT 0   CHECK (traversal_count >= 0),
  rating_sum       NUMERIC(10,2) NOT NULL DEFAULT 0,
  rating_count     INTEGER       NOT NULL DEFAULT 0   CHECK (rating_count >= 0),

  CONSTRAINT no_self_loop        CHECK (from_id <> to_id),
  CONSTRAINT unique_edge         UNIQUE (from_id, to_id, relation)
);

CREATE INDEX idx_edges_workspace ON edges (workspace_id);
CREATE INDEX idx_edges_from      ON edges (from_id);
CREATE INDEX idx_edges_to        ON edges (to_id);
CREATE INDEX idx_edges_weight    ON edges (weight);
CREATE INDEX idx_edges_relation  ON edges (relation);

-- ─── TRAVERSAL LOG ────────────────────────────────────────────────
-- Tracks unique actor × node/edge pairs for unique_traverser_count

CREATE TABLE traversal_log (
  id            BIGSERIAL    PRIMARY KEY,
  edge_id       TEXT         REFERENCES edges(id) ON DELETE CASCADE,
  node_id       TEXT         REFERENCES memory_nodes(id) ON DELETE CASCADE,
  actor_id      TEXT         NOT NULL,           -- user_id or api_key_id
  traversed_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
  rating        SMALLINT     CHECK (rating BETWEEN 1 AND 5),
  note          TEXT,
  CONSTRAINT must_have_target CHECK (
    (edge_id IS NOT NULL) OR (node_id IS NOT NULL)
  )
);

CREATE INDEX idx_traversal_edge  ON traversal_log (edge_id);
CREATE INDEX idx_traversal_node  ON traversal_log (node_id);
CREATE INDEX idx_traversal_actor ON traversal_log (actor_id);

-- ─── DECAY FUNCTION ───────────────────────────────────────────────
-- Mirrors packages/core/src/decay.ts :: calculateDecayedWeight()

CREATE OR REPLACE FUNCTION apply_edge_decay()
RETURNS INTEGER AS $$
DECLARE
  updated_count INTEGER;
BEGIN
  -- 1. Time-based decay for 'ephemeral' workspaces (SPEC §7.3)
  -- 'evergreen' workspaces use traversal-based archiving instead.
  UPDATE edges
  SET 
    weight = GREATEST(
      min_weight,
      weight * POWER(0.5, EXTRACT(EPOCH FROM (now() - last_co_accessed)) / 86400.0 / half_life_days)
    ),
    status = CASE 
      WHEN (weight * POWER(0.5, EXTRACT(EPOCH FROM (now() - last_co_accessed)) / 86400.0 / half_life_days)) < min_weight 
      THEN 'faded'::edge_status 
      ELSE status 
    END
  FROM workspaces ws
  WHERE edges.workspace_id = ws.id
    AND ws.kb_type = 'ephemeral'
    AND edges.status = 'active'
    AND edges.pinned = FALSE
    AND edges.last_co_accessed < now() - INTERVAL '1 hour'; -- more aggressive for ephemeral

  GET DIAGNOSTICS updated_count = ROW_COUNT;

  -- 2. Traversal-based archiving for 'evergreen' workspaces (SPEC §7.3)
  UPDATE edges
  SET status = 'faded'::edge_status
  FROM workspaces ws
  WHERE edges.workspace_id = ws.id
    AND ws.kb_type = 'evergreen'
    AND edges.status = 'active'
    AND edges.pinned = FALSE
    AND edges.last_co_accessed < now() - (ws.archive_window_days || ' days')::INTERVAL
    AND edges.traversal_count < ws.min_traversals;

  RETURN updated_count;
END;
$$ LANGUAGE plpgsql;

-- ─── NODE ARCHIVING FUNCTION ──────────────────────────────────────
-- Implements archiving logic based on kb_type (SPEC §7.3)

CREATE OR REPLACE FUNCTION apply_node_archiving()
RETURNS INTEGER AS $$
DECLARE
  archived_count INTEGER;
BEGIN
  -- 1. Evergreen: traversal-count based
  UPDATE memory_nodes
  SET 
    status = 'archived'::node_status,
    archived_at = now()
  FROM workspaces ws
  WHERE memory_nodes.workspace_id = ws.id
    AND ws.kb_type = 'evergreen'
    AND memory_nodes.status = 'active'
    AND memory_nodes.created_at < now() - (ws.archive_window_days || ' days')::INTERVAL
    AND memory_nodes.traversal_count < ws.min_traversals;

  GET DIAGNOSTICS archived_count = ROW_COUNT;

  -- 2. Ephemeral: all-edges-faded based
  UPDATE memory_nodes
  SET 
    status = 'archived'::node_status,
    archived_at = now()
  FROM workspaces ws
  WHERE memory_nodes.workspace_id = ws.id
    AND ws.kb_type = 'ephemeral'
    AND memory_nodes.status = 'active'
    -- All edges are either faded or non-existent
    AND NOT EXISTS (
      SELECT 1 FROM edges 
      WHERE (from_id = memory_nodes.id OR to_id = memory_nodes.id)
        AND status = 'active'
    )
    -- Node without edges: archive after 60 days of inactivity
    AND (
      memory_nodes.traversal_count = 0 
      OR memory_nodes.created_at < now() - INTERVAL '60 days'
    );

  RETURN archived_count + archived_count; -- rough estimation
END;
$$ LANGUAGE plpgsql;

-- ─── CO-ACCESS BOOST FUNCTION ─────────────────────────────────────

CREATE OR REPLACE FUNCTION record_co_access(edge_id TEXT)
RETURNS VOID AS $$
DECLARE
  rel   relation_type;
  boost NUMERIC;
BEGIN
  SELECT relation INTO rel FROM edges WHERE id = edge_id;

  boost := CASE rel
    WHEN 'depends_on'  THEN 0.30
    WHEN 'extends'     THEN 0.20
    WHEN 'related_to'  THEN 0.15
    WHEN 'contradicts' THEN 0.10
    ELSE 0.10
  END;

  UPDATE edges
  SET
    weight           = LEAST(1.0, weight + boost),
    co_access_count  = co_access_count + 1,
    last_co_accessed = now()
  WHERE id = edge_id;
END;
$$ LANGUAGE plpgsql;

-- ─── TRAVERSAL RECORD FUNCTION ────────────────────────────────────

CREATE OR REPLACE FUNCTION record_traversal(
  p_edge_id  TEXT,
  p_actor_id TEXT,
  p_rating   SMALLINT DEFAULT NULL,
  p_note     TEXT     DEFAULT NULL
)
RETURNS VOID AS $$
DECLARE
  v_from_id TEXT;
  v_to_id   TEXT;
  v_is_new_actor_edge  BOOLEAN;
  v_is_new_actor_from  BOOLEAN;
  v_is_new_actor_to    BOOLEAN;
BEGIN
  -- Resolve endpoint node IDs
  SELECT from_id, to_id INTO v_from_id, v_to_id FROM edges WHERE id = p_edge_id;

  -- Check novelty before inserting log row
  v_is_new_actor_edge := NOT EXISTS (
    SELECT 1 FROM traversal_log WHERE edge_id = p_edge_id AND actor_id = p_actor_id
  );
  v_is_new_actor_from := NOT EXISTS (
    SELECT 1 FROM traversal_log WHERE node_id = v_from_id AND actor_id = p_actor_id
  );
  v_is_new_actor_to := NOT EXISTS (
    SELECT 1 FROM traversal_log WHERE node_id = v_to_id AND actor_id = p_actor_id
  );

  -- Insert log row (handles both traversal and rating in one row)
  INSERT INTO traversal_log (edge_id, actor_id, rating, note)
  VALUES (p_edge_id, p_actor_id, p_rating, p_note);

  -- Update edge counters
  UPDATE edges
  SET
    traversal_count = traversal_count + 1,
    rating_sum      = rating_sum  + COALESCE(p_rating, 0),
    rating_count    = rating_count + CASE WHEN p_rating IS NOT NULL THEN 1 ELSE 0 END
  WHERE id = p_edge_id;

  -- Update node traversal counters
  UPDATE memory_nodes
  SET
    traversal_count        = traversal_count + 1,
    unique_traverser_count = unique_traverser_count + CASE WHEN v_is_new_actor_from THEN 1 ELSE 0 END
  WHERE id = v_from_id;

  UPDATE memory_nodes
  SET
    traversal_count        = traversal_count + 1,
    unique_traverser_count = unique_traverser_count + CASE WHEN v_is_new_actor_to THEN 1 ELSE 0 END
  WHERE id = v_to_id;

  -- Also trigger co-access boost
  PERFORM record_co_access(p_edge_id);
END;
$$ LANGUAGE plpgsql;

-- ─── WORKSPACE updated_at TRIGGER ─────────────────────────────────

CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_workspaces_updated_at
  BEFORE UPDATE ON workspaces
  FOR EACH ROW EXECUTE FUNCTION update_timestamp();

-- ─── REVIEW QUEUE (AI Candidates) ─────────────────────────────────

CREATE TYPE review_status AS ENUM ('pending', 'accepted', 'rejected');

CREATE TABLE review_queue (
  id            TEXT PRIMARY KEY,                -- rev_<hex8>
  workspace_id  TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  
  -- The proposed node data (matches NodeCreate payload)
  node_data     JSONB NOT NULL,
  
  -- Proposed edges relative to this node or other nodes in the same batch
  suggested_edges JSONB NOT NULL DEFAULT '[]',
  
  status        review_status NOT NULL DEFAULT 'pending',
  source_info   TEXT,                            -- e.g. "ingest: spec.md"
  
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  reviewed_at   TIMESTAMPTZ,
  reviewer_id   TEXT REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX idx_review_workspace ON review_queue (workspace_id);
CREATE INDEX idx_review_status    ON review_queue (status);

-- ─── WORKSPACE CLONE JOBS (Phase 4.1) ─────────────────────────────

CREATE TABLE workspace_clone_jobs (
    id              TEXT PRIMARY KEY,
    source_ws_id    TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    target_ws_id    TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    status          TEXT NOT NULL DEFAULT 'pending', -- pending, running, completed, failed
    total_nodes     INTEGER NOT NULL DEFAULT 0,
    processed_nodes INTEGER NOT NULL DEFAULT 0,
    error_msg       TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TRIGGER trg_update_clone_job_timestamp
    BEFORE UPDATE ON workspace_clone_jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

-- ─── MCP QUERY LOGS (Phase 4.5) ──────────────────────────────────

CREATE TABLE mcp_query_logs (
  id               TEXT PRIMARY KEY,             -- mcp_<hex8>
  workspace_id     TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  tool_name        TEXT NOT NULL,
  query_text       TEXT,
  result_node_count INTEGER NOT NULL DEFAULT 0,
  estimated_tokens  INTEGER NOT NULL DEFAULT 0,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_mcp_logs_ws ON mcp_query_logs (workspace_id);


# MemTrace Specification

## 1. Introduction
MemTrace is an open platform for capturing, connecting, and sharing knowledge memories across teams and AI tools. This specification outlines all core components, including Memory Schema, Edge Schema, Trust mechanics, and the Decay engine.

## 2. Terminology
- **Memory Node**: A discrete piece of knowledge, written bilingually (zh-TW and en) or unilaterally.
- **Edge**: A typed relationship connecting two Memory Nodes.
- **Co-Access**: An event where two connected memories are accessed sequentially or simultaneously in the same context.
- **Decay**: The natural reduction of edge weight over time if not co-accessed.

## 3. Product User Flow
1. **Knowledge Base Creation**: A user can initialize multiple isolated or public "Knowledge Bases" (Workspaces).
2. **Ingestion & Upload**: Users can input raw text, Markdown, or upload rich files (PDF, Word, video, meeting recordings). The Ingestion Pipeline processes these into structured Memory Nodes.
3. **Relationship Mapping**: Memory Nodes are placed into the Knowledge Graph. Users can manually draw connections (Edges) between memories, choose the relation type, adjust relationship structures, and explicitly save the graph state.
4. **Organic Decay**: Once established, the system takes over with the organic decay mechanism unless manually pinned.

## 4. Schemas

### 4.1 Memory Node v1
- Validated via `schema/node.v1.json`
- Supports multi-lingual title/body (en/zh-TW).
- Tags array, visibility (public/team/private).
- Built in trust dimensions: accuracy, freshness, utility, author reputation.

### 4.2 Edge v1
- Validated via `schema/edge.v1.json`
- From -> To directed graph.
- Relationship types: `depends_on`, `extends`, `related_to`, `contradicts`.
- Weight tracked between 0 and 1.
- Decay half-life tracked individually.

## 5. Trust & Anti-Forgery
- Memories are digitally fingerprinted with SHA-256 hashes generated from the content.
- Community and AI votes update the trust scores continuously.

## 6. Operations
- `new`: Create a new memory interacting with standard terminal.
- `link`: Create an edge between two existing nodes.
- `push`: Sync local changes to a remote repository (e.g. GitHub).
- `pull`: Pull remote changes from GitHub or central index.
- `export`: Export memories matching standard JSON schema to local filesystem.
- `import`: Import previously exported memory JSON files into the hub.

## 7. Decay Mechanics
Weight formula over time: `weight(t) = w0_current * (0.5 ^ (days_since_last_access / half_life))`
When weight < `min_weight`, the edge is automatically marked stale or removed.

Co-access boost by relation type:

| Relation      | Boost  |
|---------------|--------|
| `depends_on`  | +0.30  |
| `extends`     | +0.20  |
| `related_to`  | +0.15  |
| `contradicts` | +0.10  |

## 8. Data Storage

### 8.1 Local (Phase 1 — CLI)
The CLI stores memories and edges as JSON files under `~/.memtrace/`, validated against `schema/node.v1.json` and `schema/edge.v1.json`.

### 8.2 Server (Phase 2 — API)
The API layer uses **PostgreSQL 17 + pgvector** as the primary data store.

#### Infrastructure
- Container image: `pgvector/pgvector:pg17`
- Managed via `docker-compose.yml` at the repository root
- Schema auto-applied from `schema/sql/001_init.sql` on first `docker compose up`
- Data persisted in Docker volume `memtrace_pgdata`

#### Tables

**`memory_nodes`**

| Column         | Type              | Notes                              |
|----------------|-------------------|------------------------------------|
| `id`           | TEXT PK           | e.g. `mem_abc123`                  |
| `schema_version` | TEXT            | `'1.0'`                            |
| `title_zh`     | TEXT              | Bilingual title (zh-TW)            |
| `title_en`     | TEXT              | Bilingual title (en)               |
| `content_type` | ENUM              | factual / procedural / preference / context |
| `body_zh`      | TEXT              | Bilingual body (zh-TW)             |
| `body_en`      | TEXT              | Bilingual body (en)                |
| `tags`         | TEXT[]            | GIN-indexed                        |
| `visibility`   | ENUM              | public / team / private            |
| `author`       | TEXT              |                                    |
| `created_at`   | TIMESTAMPTZ       |                                    |
| `signature`    | TEXT              | SHA-256 content hash               |
| `source_type`  | ENUM              | human / ai_generated / ai_verified |
| `trust_score`  | NUMERIC(4,3)      | Composite 0–1                      |
| `dim_accuracy` | NUMERIC(4,3)      | Trust dimension                    |
| `dim_freshness`| NUMERIC(4,3)      | Trust dimension                    |
| `dim_utility`  | NUMERIC(4,3)      | Trust dimension                    |
| `dim_author_rep` | NUMERIC(4,3)   | Trust dimension                    |
| `votes_up`     | INTEGER           |                                    |
| `votes_down`   | INTEGER           |                                    |
| `verifications`| INTEGER           |                                    |
| `embedding`    | vector(1536)      | ivfflat index, cosine similarity   |

**`edges`**

| Column            | Type          | Notes                          |
|-------------------|---------------|--------------------------------|
| `id`              | TEXT PK       | e.g. `edge_xyz789`             |
| `from_id`         | TEXT FK       | → `memory_nodes.id` CASCADE    |
| `to_id`           | TEXT FK       | → `memory_nodes.id` CASCADE    |
| `relation`        | ENUM          | depends_on / extends / related_to / contradicts |
| `weight`          | NUMERIC(6,5)  | 0–1, updated by decay          |
| `co_access_count` | INTEGER       |                                |
| `last_co_accessed`| TIMESTAMPTZ   |                                |
| `half_life_days`  | INTEGER       | Default 30                     |
| `min_weight`      | NUMERIC(4,3)  | Default 0.1; edge removed when reached |

#### SQL Functions
- `apply_edge_decay()` — recalculates all edge weights and removes fully-decayed edges; mirrors `packages/core/src/decay.ts`
- `record_co_access(edge_id)` — increments co-access count and applies boost

#### Environment Configuration
Connection settings are defined in `.env` (not committed). See `.env.example` for the template.

```
DATABASE_URL=postgresql://<user>:<password>@<host>:<port>/<db>
```

#### Developer Setup
```bash
cp .env.example .env       # fill in credentials
docker compose up -d       # start DB (schema auto-applied)
docker compose down -v     # stop and wipe data
```

## 9. Frontend (UI) Specifications

### 9.1 Multi-Language Support (i18n)
The MemTrace Web UI is fully internationalized to support a global user base and knowledge network.
- **Library**: `react-i18next` with `i18next`.
- **Supported Languages**:
  - Traditional Chinese (`zh-TW` / `zh-Hant`)
  - English (`en`)
- **Scope**: All UI elements including sidebars, headers, tooltips, form labels, and placeholders must utilize the translation engine.
- **Language Selection**: Users can toggle between languages globally, which operates independently from the bilingual content tabs used during memory creation.

### 9.2 Memory Export & Import
Users must be able to export their current working memory to a local JSON file (conforming to `node.v1.json`) and import an existing JSON file directly into the editor for further modification or restoration.

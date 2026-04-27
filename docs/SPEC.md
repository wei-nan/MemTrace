# MemTrace Specification

## 1. Introduction
MemTrace is an open platform for building shared knowledge through minimal, well-connected Memory Nodes. Its core design goal is to allow any human or AI agent to reach any answer by following the shortest possible path through a graph of small, typed relationships — rather than reading through large documents. This specification outlines all core components, including Memory Schema, Edge Schema, Trust mechanics, and the Decay engine.

Central to MemTrace is the belief that **knowledge itself has intrinsic value** and that the people who curate it should have full sovereignty over how it is shared — whether openly with the world, conditionally with an audience, or kept entirely private. The platform is designed so that sharing a knowledge base is a deliberate choice, not an accident.

## 1.1 Core Product Philosophy

### Knowledge through connection, not accumulation

The fundamental premise of MemTrace is that knowledge does not need to live in large, monolithic documents. Instead, it is best expressed as a network of small, focused Memory Nodes — each one capturing a single idea clearly — whose value emerges from the relationships between them.

A node on its own is lightweight. Connected to others, it becomes part of a living knowledge base that grows organically over time and survives beyond any single author or conversation.

### Designed for inheritance

MemTrace is built for the moment when someone new needs to understand what came before — whether that is a new team member, a collaborator joining mid-project, or an AI agent operating in an unfamiliar context.

Every Memory Node is designed to be self-contained enough to be read in isolation, yet connected enough that following its edges leads naturally to everything related. A reader does not need prior context from the author: they enter at any node and navigate the graph by following the associations that matter to them.

### Co-authorship between humans and AI

MemTrace is designed for knowledge work that happens collaboratively — between people, between people and AI tools, or between AI agents operating in the same workspace. All contributors, regardless of whether they are human or AI, write into the same graph. The graph's structure — the edges, their weights, the traversal counts — reflects which knowledge has actually proven useful, not just what was recorded.

Decay ensures that the graph stays honest: connections that nobody follows fade over time. Connections that are visited frequently, rated positively, or built upon by other nodes strengthen and persist. The result is a knowledge base that self-organises around what actually matters.

Importantly, **nothing is deleted by decay alone**. A node that has not been accessed in a long time does not disappear — it fades into the background, becoming less visible in default views and traversal results. An author or workspace admin can always retrieve, restore, or archive any node explicitly. The decay mechanism shapes attention, not existence.

### Knowledge has intrinsic value

Knowledge is not a commodity that becomes more valuable only when shared freely. The effort, insight, and curation behind a well-structured Knowledge Base represent real intellectual work — work that belongs to its author.

MemTrace is built on the premise that **anyone can choose how to present the knowledge they manage**:

- **Openly** — a public Knowledge Base becomes a shared resource, discoverable by anyone, growing in value through community traversal and contribution.
- **Conditionally** — a conditionally-public Knowledge Base lets the wider world see its shape and structure, signalling that the knowledge exists, without surrendering the content itself. Interested parties can request access; the author decides who enters.
- **Restrictedly** — a restricted Knowledge Base is invisible to those not invited. Its existence is not disclosed, and access is entirely on the author's terms.
- **Privately** — a private Knowledge Base is for the author alone, a personal thinking space with no external surface.

This is not merely a permissions model. It is a statement about the **relationship between knowledge and its curator**. MemTrace does not assume that value is created only when knowledge is free. It assumes that value is created when knowledge is structured, connected, and curated — and that the curator has the right to decide what happens next.

### Design principles that follow from this

| Principle | Implication |
|-----------|-------------|
| **Nodes are minimal** | A node contains the smallest unit of knowledge that can stand alone. If a thought can be split without losing meaning, it should be. |
| **Relationships carry the knowledge** | The value of a Knowledge Base lies in its edges, not in the volume of its nodes. Two small nodes with a typed edge express more than one large node that conflates two ideas. |
| **Shortest path is the design goal** | Every structural decision — node granularity, edge type, content type — should be evaluated by whether it shortens the path a human or AI agent needs to follow to reach an answer. |
| **Entry point independence** | Any node can serve as an entry point. Navigation follows edges, not a fixed hierarchy. |
| **Value is earned** | Trust scores, traversal counts, and edge weights reflect real usage, not just authorship intent. |
| **Knowledge sovereignty and protection** | The core value is knowledge sharing, but the author retains full control over the depth of that sharing. Roles clearly distinguish between those who can only see the graph structure (Viewers) and those who can access and edit detailed content (Editors/Admins). |
| **Decay shapes attention, not existence** | No node or edge is permanently deleted by the decay engine alone. Faded content is archived, not destroyed. |
| **Knowledge sovereignty belongs to the curator** | Every Knowledge Base owner decides how their knowledge is shared — fully public, conditionally visible, invitation-only, or entirely private. Sharing is always a deliberate act, never a default. |

## 2. Terminology
- **Memory Node**: A discrete piece of knowledge, written bilingually (zh-TW and en) or unilaterally.
- **Edge**: A typed relationship connecting two Memory Nodes.
- **Co-Access**: An event where two connected memories are accessed sequentially or simultaneously in the same context.
- **Decay**: The natural reduction of edge weight over time if not co-accessed.
- **Archive**: The state a node or edge enters when it is no longer relevant to default views. Archived content is hidden but not destroyed and can be restored at any time.
- **Faded**: The state an edge enters when its weight drops below `min_weight` due to decay. A faded edge is archived automatically but can be restored.
- **Knowledge Base Type**: A workspace-level setting (`evergreen` or `ephemeral`) that governs how the decay engine treats nodes and edges in that workspace (see §7.3).
- **Knowledge Base Visibility**: The four-tier sharing level of a Knowledge Base (`public`, `conditional_public`, `restricted`, `private`), controlling who can discover and access it. Set at creation time and immutable thereafter. Distinct from Memory Node visibility, which controls individual node access within a Knowledge Base.
- **Write Serialization**: The per-workspace write queue mechanism that ensures concurrent writes (by humans or AI) are applied in arrival order, preventing race conditions.
- **Conflict Flag**: A marker applied to a Memory Node when the system detects a logical inconsistency introduced by an AI or concurrent human edit (see §17.4).
- **KB Association**: An explicit link between two Knowledge Bases that grants AI agents permission to reason across their contents (see §18).
- **Source Document Node**: A special `source_document` node created when a file is ingested, retaining the original text with paragraph-level markers. Excluded from default graph and search views (see §20).
- **Session Token**: A short-lived signed token issued by MemTrace after successful authentication, used to authorize subsequent API requests.

## 3. Product User Flow
1. **Knowledge Base Creation**: A user can initialize multiple Knowledge Bases (Workspaces) with a chosen **type** (`evergreen` or `ephemeral`, see §7.3) and **sharing level** — one of four tiers: `public`, `conditional_public`, `restricted`, or `private` (see §12). The sharing level is immutable after creation. The creating user is automatically added as an admin. A Knowledge Base may be started blank or bootstrapped from a document (see §11.1). A workspace may be associated with other workspaces to enable AI cross-KB reasoning (see §18).
2. **Ingestion & Upload**: Users can input raw text, Markdown, or upload rich files (PDF, Word, video, meeting recordings). The AI Extraction pipeline applies the Node Minimization Principle (§11.3) to split source material into the smallest meaningful units and proposes typed edges between them. All candidates enter a Review Queue for human approval before committing (see §11.2).
3. **Relationship Mapping**: Edges are as important as nodes. After creating or accepting a node, users are expected to define its relationships — by drawing connections in the Graph View, using the Edge panel in the Node Editor, or accepting AI-proposed edges. A node with no edges is incomplete.
4. **Node Portability**: Any individual Memory Node can be copied to another Knowledge Base without carrying its Edges (see §11.3).
5. **Organic Decay**: Once established, the system takes over with the organic decay mechanism unless manually pinned.

## 4. Schemas

### 4.1 Memory Node v1
- Validated via `schema/node.v1.json`
- Supports multi-lingual title/body (en/zh-TW).
- Tags array.
- **Node-level `visibility`** (per-node, distinct from KB-level visibility in §1.1 / §12): one of `public` / `team` / `private`. Controls whether other members of the same workspace can see this individual node. The four-tier sharing level (`public` / `conditional_public` / `restricted` / `private`) in §1.1 is set at the **Knowledge Base** level and is a separate axis.
- Built in trust dimensions: accuracy, freshness, utility, author reputation.

### 4.2 Edge v1
- Validated via `schema/edge.v1.json`
- From -> To directed graph.
- Relationship types: `depends_on`, `extends`, `related_to`, `contradicts`.
- Weight tracked between 0 and 1.
- Decay half-life tracked individually per edge; default varies by workspace `kb_type` and node `content_type` (see §7.3).
- Edge status: `active` / `faded` / `pinned`. Faded edges are archived, not deleted.

## 5. Trust & Anti-Forgery
- Memories are digitally fingerprinted with SHA-256 hashes generated from the content.
- Community and AI votes update the trust scores continuously.

## 6. Operations

> **Implementation status (2026-04-27):** ⚠ marks operations defined in this section but not yet shipped in the CLI. They are part of `docs/dev/audit-2026-04-phase1.md` §4.1 and are scheduled for Phase 4 (`docs/dev/phase4-plan.md` §P4-D).

- `new`: Create a new Memory Node. Each node should capture exactly one idea — if the content spans multiple ideas, create multiple nodes and link them. Running `link` immediately after `new` is the expected workflow.
- `link`: Create a typed edge between two existing nodes. Edges are the primary carrier of knowledge in MemTrace; a node without edges is not yet a useful part of the graph.
- ⚠ `ingest <file>`: Upload a document and trigger AI extraction to propose candidate Memory Nodes (see §11.2). **CLI not yet implemented** — use the API or the UI's onboarding ingest step instead.
- ⚠ `copy-node <node-id> --to <workspace-id>`: Copy a single Memory Node into another Knowledge Base; Edges are not copied (see §11.3). **CLI not yet implemented** — API endpoint exists.
- ⚠ `push`: Sync local changes to a remote repository (e.g. GitHub). **Not implemented** — local-first sync is deferred; current architecture treats the API as authoritative.
- ⚠ `pull`: Pull remote changes from GitHub or central index. **Not implemented** — see `push` above.
- `export`: Export a Knowledge Base or filtered subset to local filesystem. Accepts `--type` and `--format` flags (see §22).
- `import`: Import a previously exported Knowledge Base archive into MemTrace (see §22).

## 7. Decay Mechanics

### 7.1 Current Model (v1)

Weight formula over time:

```
weight(t) = w0_current × 0.5 ^ (days_since_last_access / half_life)
```

When `weight < min_weight`, the edge transitions to **faded** state — it is not deleted. Faded edges:
- Are hidden from default Graph View and traversal results
- Are still stored in the database with `status = 'faded'`
- Can be restored manually by the workspace owner or original author
- Remain queryable via API with the `include_faded=true` parameter

Co-access boost by relation type:

| Relation      | Boost  |
|---------------|--------|
| `depends_on`  | +0.30  |
| `extends`     | +0.20  |
| `related_to`  | +0.15  |
| `contradicts` | +0.10  |

### 7.2 Open Design Questions (Under Discussion)

The current decay model applies uniformly to all edges based on time since last access. The following questions remain open and will inform a future v2 decay model:

**Q1 — Should content type affect the default half-life?**

Some knowledge is structurally timeless (mathematical facts, definitions), while other knowledge is highly perishable (meeting context, temporary preferences). A content-type-aware default half-life may be more appropriate than a single global value:

| Content Type  | Proposed Default Half-life |
|---------------|---------------------------|
| `factual`     | 365 days (or pinned)      |
| `procedural`  | 90 days                   |
| `preference`  | 30 days                   |
| `context`     | 14 days                   |

**Q2 — Should decay apply to nodes as well as edges?**

Currently only edges decay. A node that has no incoming traversals over time does not fade — it simply becomes an island. Options:
- **Option A**: Apply a node-level `visibility_weight` (separate from trust) that fades if the node has zero traversal activity over a threshold period, causing it to drop out of default search/graph results.
- **Option B**: Keep nodes permanently visible unless explicitly archived; let edge decay naturally isolate unreachable nodes.
- **Option C**: Compute a derived "reachability score" based on the weights of its connected edges; nodes with no active edges become visually dimmed.

> Current lean: **Option C** — derive reachability from edge state rather than adding a separate node decay axis.

**Q3 — Should decay be time-based or activity-based?**

The current formula counts calendar days since last access. An alternative is to count only relative to workspace activity: if nobody has used the workspace at all, no decay should occur. This avoids penalising knowledge in low-activity workspaces.

**Q4 — What triggers the decay recalculation?**

Options: (a) a scheduled nightly job, (b) on every read request (lazy decay), (c) on write events only. Lazy decay is simpler to implement but can lead to stale weights being served briefly.

**Q5 — Pin / exemption mechanism**

High-value nodes and edges should be exemptable from decay. A `pinned: true` flag (set by the author or workspace admin) would bypass the decay formula entirely. Pinned edges still record co-access boosts but their weight does not decrease below the current value.

### 7.3 Knowledge Base Types

A workspace is assigned one of two **types** at creation time, as part of the workspace creation flow (Web UI step ④, CLI step 3). The type governs how the decay engine treats all nodes and edges within that workspace. **The type cannot be changed after the workspace is created.**

---

#### `evergreen` — 長效型知識庫

**Use cases**: Specification documents, architectural decisions, team playbooks, product philosophy, onboarding guides.

**Characteristics**:
- Knowledge in this type of workspace is assumed to be **structurally stable**. Facts do not expire simply because time passes.
- **Time-based decay is disabled.** Edge weights do not decrease based on calendar days.
- **Reference-count-based archiving** is used instead: nodes and edges that fall below a minimum traversal threshold over a configurable observation window are automatically **archived**, not faded.
- Archived nodes remain fully accessible via the Archive view and API but do not appear in default search or graph traversal results, reducing cognitive load without destroying knowledge.
- The observation window and minimum traversal threshold are configurable per workspace (defaults: 90-day window, minimum 1 traversal).
- All nodes and edges start in `active` state. Archiving is triggered by a scheduled job, not in real-time.

**Archive trigger logic (evergreen)**:
```
IF traversal_count(node, last 90 days) == 0
AND node is not pinned
THEN node.status → 'archived'

IF co_access_count(edge, last 90 days) == 0
AND edge is not pinned
THEN edge.status → 'faded'
```

---

#### `ephemeral` — 短效型知識庫

**Use cases**: Troubleshooting runbooks, incident postmortems, daily task procedures, tool-specific how-to guides that change as tools evolve.

**Characteristics**:
- Knowledge in this type of workspace is assumed to have a **natural expiry**: procedures become outdated, tools change, contexts shift.
- **Time-based decay is enabled**, using the weight formula from §7.1. The decay half-life defaults are shorter than the global defaults, reflecting the expected rate of change:

| Content Type  | Default Half-life (ephemeral) |
|---------------|-------------------------------|
| `factual`     | 90 days                       |
| `procedural`  | 30 days                       |
| `preference`  | 14 days                       |
| `context`     | 7 days                        |

- When an edge's weight drops below `min_weight`, it transitions to `faded` (same as the base model in §7.1).
- When **all edges connected to a node** are faded, the node itself is automatically archived.
- A node with no edges is archived after the observation window (default: 60 days without traversal).
- Pinned nodes and edges are exempt from both time-decay and traversal-count archiving.

---

#### Comparison

| Behaviour | `evergreen` | `ephemeral` |
|-----------|-------------|-------------|
| Time-based edge decay | Disabled | Enabled |
| Archive trigger | Low traversal count | Edge weight < min_weight |
| Default half-life | N/A | Short (7–90 days by content type) |
| Node archiving | Traversal threshold | All connected edges faded |
| Pin support | Yes | Yes |
| Can restore archived content | Yes | Yes |
| Permanent deletion | Owner only, explicit | Owner only, explicit |

## 8. Data Storage

MemTrace supports two storage modes that can run side-by-side: a local file-based store for CLI use, and a PostgreSQL-backed server for the API / UI / MCP / multi-user scenarios.

### 8.1 Local Filesystem (CLI)
The CLI stores memories and edges as JSON files under `~/.memtrace/`, validated against `schema/node.v1.json` and `schema/edge.v1.json`. This mode is intended for single-user, offline-first use.

### 8.2 Server (API / UI / MCP)
The server uses **PostgreSQL 17 + pgvector** as the primary data store. All multi-user, AI extraction, MCP integration, and Q&A features run against this store.

#### Infrastructure
- Container image: `pgvector/pgvector:pg17`
- Managed via `docker-compose.yml` at the repository root
- Schema auto-applied from `schema/sql/001_init.sql` on first `docker compose up`
- Data persisted in Docker volume `memtrace_pgdata`

#### Tables

**`workspaces`**

| Column          | Type          | Notes                                                         |
|-----------------|---------------|---------------------------------------------------------------|
| `id`            | TEXT PK       | e.g. `ws_abc123`                                              |
| `name_zh`       | TEXT          | Bilingual name (zh-TW)                                        |
| `name_en`       | TEXT          | Bilingual name (en)                                           |
| `visibility`    | ENUM          | public / restricted / private                                 |
| `kb_type`       | ENUM          | `evergreen` / `ephemeral` — governs decay behaviour (§7.3)    |
| `owner_id`      | TEXT FK       | → `users.id`                                                  |
| `archive_window_days` | INTEGER | Observation window for traversal-count archiving (default 90) |
| `min_traversals`| INTEGER       | Traversal threshold before archiving (evergreen only, default 1) |
| `created_at`    | TIMESTAMPTZ   |                                                               |
| `updated_at`    | TIMESTAMPTZ   |                                                               |

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
| `traversal_count` | INTEGER        | Total times this node was traversed by any actor |
| `unique_traverser_count` | INTEGER | Distinct users or service principals that have traversed this node |
| `status`       | ENUM              | active / archived; archived nodes are hidden from default views |
| `archived_at`  | TIMESTAMPTZ       | Null unless status = 'archived'    |
| `embedding`    | vector(1536)      | ivfflat index, cosine similarity   |

**`edges`**

| Column            | Type          | Notes                          |
|-------------------|---------------|--------------------------------|
| `id`              | TEXT PK       | e.g. `edge_xyz789`             |
| `from_id`         | TEXT FK       | → `memory_nodes.id`            |
| `to_id`           | TEXT FK       | → `memory_nodes.id`            |
| `relation`        | ENUM          | depends_on / extends / related_to / contradicts |
| `weight`          | NUMERIC(6,5)  | 0–1, updated by decay          |
| `status`          | ENUM          | active / faded / pinned; faded edges are hidden from default traversal |
| `co_access_count` | INTEGER       |                                |
| `last_co_accessed`| TIMESTAMPTZ   |                                |
| `half_life_days`  | INTEGER       | Default varies by content_type (see §7.2 Q1) |
| `min_weight`      | NUMERIC(4,3)  | Default 0.1; edge transitions to `faded` when reached (not deleted) |
| `pinned`          | BOOLEAN       | Default false; pinned edges are exempt from decay |
| `traversal_count` | INTEGER       | Total traversals recorded on this edge |
| `rating_sum`      | NUMERIC(10,2) | Sum of all explicit path ratings (for average calculation) |
| `rating_count`    | INTEGER       | Number of explicit ratings submitted |

#### SQL Functions
- `apply_edge_decay()` — recalculates all edge weights; transitions edges to `faded` when weight drops below `min_weight`; never deletes rows; mirrors `packages/core/src/decay.ts`
- `record_co_access(edge_id)` — increments co-access count and applies boost
- `record_traversal(edge_id, actor_id, rating?)` — increments `traversal_count` on both the edge and its endpoint nodes; updates `rating_sum` / `rating_count` if a rating is provided; records the actor for unique traverser tracking

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
Users can export their current working memory to a local file (JSON, Markdown, or plain text) and import an existing archive back into any workspace. Node-level and full-KB export/import are supported. For full specification including export types, filterable scopes, and format details, see **§22 — Knowledge Base Export & Import**.

### 9.3 Manual Memory Node Creation & Editing

#### 9.3.1 Overview
Users can manually create and edit Memory Nodes through a dedicated editor panel within the UI. The editor is accessible from the Graph View (via a toolbar button or double-clicking an empty canvas area) and from the node's context menu.

#### 9.3.2 Input Formats
Each Memory Node body (`content.body`) supports two input modes, selectable via a tab toggle within the editor:

| Mode       | Description                                                             |
|------------|-------------------------------------------------------------------------|
| `plain`    | Plain text input. Stored as-is in `content.body`. No rendering markup. |
| `markdown` | Markdown input. Rendered as HTML in read view; raw Markdown stored.     |

- The selected mode is persisted in the node as `content.format` field (see §4.1 schema extension below).
- The editor must provide a **live preview** panel when in `markdown` mode.
- Switching modes does **not** automatically convert existing content.

#### 9.3.3 Editor Fields
The creation/edit form exposes the following fields:

| Field           | Required | Notes                                                        |
|-----------------|----------|--------------------------------------------------------------|
| Title (zh-TW)   | Yes      | Maps to `title["zh-TW"]`                                    |
| Title (en)      | Yes      | Maps to `title["en"]`                                       |
| Content Type    | Yes      | Dropdown: `factual / procedural / preference / context`      |
| Body (zh-TW)    | No       | Text or Markdown; maps to `content.body["zh-TW"]`           |
| Body (en)       | No       | Text or Markdown; maps to `content.body["en"]`              |
| Tags            | No       | Comma-separated or tag-chip input; maps to `tags[]`          |
| Visibility      | Yes      | Dropdown: `public / team / private`; default `private`       |

- At least one Body language field must be non-empty to save.
- **Body length guidance**: If the body exceeds 280 characters, the editor displays a soft warning: *"This node may contain more than one idea — consider splitting it."* This is a prompt, not a hard limit. The user may dismiss it.
- The body must not restate information already expressed in the title. The title is the index; the body is the substance.
- `provenance.author` is auto-filled from the current session user.
- `provenance.created_at` is auto-set on first save; `updated_at` is added on edit (see §10.1).
- `provenance.signature` (SHA-256) is recomputed on every save.
- `trust` fields are initialized to defaults on creation and not user-editable.

#### 9.3.4 Creating an Edge (Association) from the Editor
After saving a node, the editor **immediately opens the Edge creation sub-panel** by default. A node without any edges is visually flagged in the Graph View with an indicator (e.g. a hollow ring instead of a filled node) to signal that it is not yet connected. Users can also initiate edge creation by dragging from one node's handle to another in the Graph View.

Edges are not optional — they are what give a node its meaning in context. The editor should make edge creation the natural next step after every save, not an afterthought.

Edge creation fields:

| Field         | Required | Notes                                                           |
|---------------|----------|-----------------------------------------------------------------|
| Target Node   | Yes      | Searchable dropdown of existing node titles                     |
| Relation Type | Yes      | `depends_on / extends / related_to / contradicts`               |
| Initial Weight| No       | Slider 0.1–1.0; default `1.0`                                   |
| Half-life     | No       | Integer days; default `30`                                      |

- Direction is always **from the current node → target node**.
- Duplicate edges (same `from`, `to`, `relation`) are rejected with a validation error.
- On creation, `co_access_count` is set to `0` and `last_co_accessed` to the current timestamp.

#### 9.3.5 Editing an Existing Node
- Double-clicking a node in the Graph View opens the editor pre-filled with its current data.
- All fields except `id`, `schema_version`, and `provenance.created_at` are editable.
- Editing a node's content triggers a SHA-256 signature recompute on save.
- Existing edges attached to the node are listed in a collapsible **"Associations"** section within the editor, where each edge's relation type and weight are visible and editable inline.

#### 9.3.6 Archiving and Deletion

**Archive** (default action):
- A node can be **archived** from its context menu (right-click on Graph View) or from the editor toolbar.
- Archived nodes are hidden from the default Graph View and search results but are never destroyed.
- All edges connected to an archived node are automatically faded (not deleted).
- Archived nodes appear in a dedicated **"Archive"** view, accessible from the workspace sidebar.
- An archived node can be restored at any time by the workspace owner or the node's original author.

**Permanent deletion** (destructive, requires confirmation):
- Permanent deletion is only available to workspace **owners**.
- A two-step confirmation dialog is required, listing the count of edges and any dependant nodes that reference this node.
- Permanently deleted nodes and their edges are removed from the database. This action is irreversible.
- Permanent deletion should be reserved for nodes created in error (e.g. duplicate, test data), not for nodes that have simply become irrelevant over time — archiving is preferred for the latter case.

## 11. Document-Based Knowledge Base Bootstrapping

### 11.1 Starting a Knowledge Base from a Document

A Knowledge Base may be initialized from one or more source materials instead of being built node-by-node. The AI Extraction pipeline accepts a wide range of input formats — not limited to formal documents.

| Format | Extension(s) | Preprocessing | Notes |
|--------|-------------|---------------|-------|
| Markdown | `.md` | — | Headings used as structural hints for node boundaries |
| Plain text | `.txt` | — | Paragraph breaks used as structural hints |
| PDF | `.pdf` | Text layer extraction | Scanned PDFs require OCR (Phase 2+) |
| Word | `.docx` | Heading style extraction | Heading levels used as structural hints |
| Presentation | `.pptx`, `.key` | Slide-per-slide text extraction | Each slide treated as a candidate segment |
| Meeting notes / transcripts | `.txt`, `.md`, `.vtt`, `.srt` | Speaker turn segmentation | Action items and decisions prioritised as `procedural` / `context` nodes |
| Video | `.mp4`, `.mov`, URL | Transcription via provider speech-to-text (e.g. Whisper) | Transcript is extracted first, then processed as text |
| Audio | `.mp3`, `.m4a`, `.wav` | Transcription via provider speech-to-text | Same pipeline as video |
| Web page / URL | `https://...` | HTML → Markdown conversion (readability extraction) | Requires the server to fetch and parse the URL |

**Phase 1 scope**: Markdown and plain text only.  
**Phase 2 scope**: PDF, Word, PPTX, meeting notes/VTT/SRT.  
**Phase 3 scope**: Video, audio, and URL ingestion (depends on provider support for transcription).

All ingested materials are stored as **Source Document** references on the Knowledge Base and retained for traceability. Multiple materials can be ingested into the same Knowledge Base sequentially.

### 11.2 AI Provider & API Key

MemTrace does **not** operate its own AI inference service. All AI features (node extraction, classification, title generation) are powered by third-party LLM providers configured by the user.

#### 11.2.1 API Key Management

- Users must supply their own API key for each AI provider they intend to use.
- API keys are stored **locally only** — in `~/.memtrace/config.json` (CLI) or in the browser's `localStorage` (UI). Keys are never transmitted to or stored on any MemTrace server.
- A key must be present and valid before any AI feature can be invoked. If no key is configured, AI features are disabled and the user is prompted to add one via settings.
- Keys are associated with a provider identifier (e.g. `openai`, `anthropic`) and can be updated or deleted at any time from the settings panel.

#### 11.2.2 Supported Providers

The following providers are supported in the official release:

| Provider | Identifier | Chat model (default) | Embedding model | Embedding Dim |
|----------|------------|----------------------|-----------------|---------------|
| OpenAI | `openai` | `gpt-4o-mini` | `text-embedding-3-small` | 1536 |
| Anthropic | `anthropic` | `claude-haiku-4-5-20251001` | `voyage-3-lite` | 1024 |
| **Google Gemini** | `gemini` | `gemini-2.0-flash` | `text-embedding-004` | **768** |

> **Embedding dimension note**: Different providers produce vectors of different dimensions. A workspace's embedding dimension is fixed at creation time based on the provider chosen (stored in `workspaces.embedding_provider` and `workspaces.embedding_dim`). Nodes embedded with different models cannot be compared by cosine similarity.

The Gemini provider is implemented as a built-in `AIProvider` calling the Google Generative Language API. Users supply a personal Gemini API key (`AIza...`) via Settings → AI Provider, stored encrypted under `provider = 'gemini'` in `user_ai_keys`.

#### 11.2.3 Community-Contributed Providers

MemTrace is open source. The AI call path is built around a provider `Protocol` (`packages/api/core/ai.py`) that any contributor can implement to add support for additional models or services — including:

- Other commercial APIs (Gemini, Mistral, Cohere, etc.)
- OpenAI-compatible self-hosted endpoints (Ollama, vLLM, LM Studio, Groq)
- Private or fine-tuned models exposed over HTTP

**To add a provider**, implement the `AIProvider` protocol:

```python
# packages/api/core/ai.py

class AIProvider(Protocol):
    name: str                          # identifier used in DB and UI
    default_chat_model: str
    default_embedding_model: str

    async def chat(
        self,
        api_key: str,
        model: str,
        messages: list[dict],
        max_tokens: int,
        temperature: float,
    ) -> tuple[str, int]: ...          # (response_text, tokens_used)

    async def embed(
        self,
        api_key: str,
        model: str,
        text: str,
    ) -> tuple[list[float], int]: ... # (vector, tokens_used)
```

Register the implementation in `PROVIDER_REGISTRY` at the bottom of `core/ai.py`. No changes to routers, models, or the database schema are needed.

> **Embedding dimension note**: Different models produce vectors of different dimensions. A workspace's embedding dimension is fixed at creation time based on the provider chosen. Nodes embedded with different models cannot be compared by cosine similarity. Contributors adding embedding-capable providers must document the output dimension of their model.


#### 11.2.5 Config Schema (CLI)

API keys are stored in `~/.memtrace/config.json`:

```json
{
  "ai": {
    "provider": "openai",
    "api_keys": {
      "openai": "<user-supplied key>",
      "anthropic": "<user-supplied key>"
    }
  }
}
```

Keys in this file must be protected with user-only read permissions (`chmod 600`).

#### 11.2.6 Failure Handling

If an AI call fails due to an invalid key, quota exhaustion, or provider error, the ingestion step is aborted. No candidate nodes are generated. The user is shown the provider error message and prompted to check their API key in settings.

---

### 11.3 AI-Driven Node Extraction

When a material is ingested via `ingest` (CLI) or the Upload panel (UI), the system invokes an AI Extraction step using the configured provider and API key (see §11.2).

#### Node Minimization Principle

> **The AI must produce the smallest possible nodes and the richest possible set of edges.**

This is the single most important constraint governing extraction. It has two parts:

**Minimize nodes** — A candidate node should contain exactly one discrete idea, fact, procedure step, or context signal. If a segment of the source material contains two separable ideas, the AI must split them into two nodes. Nodes must not serve as containers for related content — that is what edges are for.

| Too large ❌ | Minimal ✓ |
|---|---|
| "The decay formula is `w(t) = w₀ × 0.5^(d/h)`. Co-access boosts weight by +0.10 to +0.30 depending on relation type." | Node A: "Edge Decay Formula" — the formula only. Node B: "Co-Access Weight Boost" — boost values only. Edge A→B: `related_to` |
| "To set up the project: install Node.js, then Python, then run `npm install`." | Node A: "Install Node.js". Node B: "Install Python". Node C: "Run npm install". Edges: A→B `depends_on`, B→C `depends_on` |

**Maximize edges** — After splitting, the AI must identify and propose all meaningful relationships between the resulting nodes. An extracted node with no proposed edges is a signal that the split was too aggressive or the surrounding context was not analysed thoroughly enough.

---

The extraction step:

1. **Segments** the material into candidate chunks based on structural cues (headings, paragraphs, slide boundaries, speaker turns, topic shifts).
2. **Splits** each chunk into minimal atomic units, applying the Node Minimization Principle above.
3. **Classifies** each unit into a Content Type (`factual`, `procedural`, `preference`, `context`).
4. **Generates** a bilingual title (zh-TW + en) and a concise body for each candidate node. The body must not restate what the title already expresses.
5. **Proposes** candidate Edges between all extracted nodes, selecting the most specific relation type available (`depends_on` > `extends` > `related_to` > `contradicts`). Cross-segment edges are explicitly encouraged.

#### 11.3.1 Review Step (required before commit)

All AI-extracted candidates enter a **Review Queue** and are never committed automatically. The user must:

- **Accept** — commit the node as-is.
- **Edit then Accept** — modify title, body, type, or tags before committing.
- **Reject** — discard the candidate; it is not saved.

Bulk accept/reject is allowed. At least one node must be accepted before the review step can be closed.

#### 11.3.2 Extraction Metadata

Each node committed from AI extraction carries:

```json
{
  "provenance": {
    "source_type": "ai_generated",
    "source_document": "<filename or SHA-256 of the source file>",
    "extraction_model": "<model identifier>"
  }
}
```

`source_document` and `extraction_model` are appended to the `provenance` object (see §10.2).

#### 11.3.3 Trust Defaults for AI-Extracted Nodes

| Dimension | Default |
|-----------|---------|
| `accuracy` | 0.5 (unverified; boosted when a human accepts without edits) |
| `freshness` | 1.0 |
| `utility` | 0.5 |
| `author_rep` | 0.5 |
| `source_type` | `ai_generated` → `ai_verified` after human acceptance |

When a human edits a candidate before accepting, `source_type` is set to `human`.

### 11.3.4 Extraction Prompt Design

The AI provider receives a structured prompt that includes:

1. **System role**:
   > "You are a knowledge graph extraction assistant. Your goal is to convert source material into the smallest possible set of atomic Memory Nodes connected by the richest possible set of typed edges. A node must contain exactly one idea — if you find two ideas in a segment, split them. An edge is not optional: every node you produce must have at least one proposed edge to another node in the output, unless it is the only node extracted. The design goal is that a human or AI agent can reach any answer by following the shortest possible path through the graph."

2. **Segment text**: The raw text of the chunk being processed (or transcript segment, slide text, etc.).
3. **Workspace context**: The `kb_type` (`evergreen` or `ephemeral`), existing node titles in the workspace (to avoid duplication), and the edge type vocabulary (`depends_on`, `extends`, `related_to`, `contradicts`).
4. **Quality constraints** (included in the prompt):
   - A node body must not repeat information already expressed in the title.
   - A node body should be as short as possible while remaining self-contained.
   - Prefer `depends_on` and `extends` over `related_to` when a more specific relationship can be inferred.
   - If two candidate nodes could be merged without losing specificity, merge them.
5. **Output schema**: A JSON array of candidate nodes, each with `title_zh`, `title_en`, `content_type`, `body_zh`, `body_en`, `tags`, and a `suggested_edges[]` array referencing other nodes in the same output by their array index.

The prompt is sent once per segment. The provider must return a valid JSON array. If it does not, the segment is flagged as an extraction failure and shown to the user for manual handling.

### 11.4 Copying a Node to Another Knowledge Base

Any individual Memory Node can be copied to a different Knowledge Base. Edges are **not** copied — only the node's content, metadata, and trust snapshot are transferred.

#### 11.4.1 Behavior

- The copied node receives a **new `id`** in the target Knowledge Base.
- `provenance.created_at` is set to the time of the copy operation.
- `provenance.updated_at` is absent (the copy is treated as a fresh creation).
- A `provenance.copied_from` field records the original node's `id` and source workspace for traceability.
- The original node and its Edges are unaffected.
- The `signature` (SHA-256) is recomputed from the copied content in the target workspace context.

#### 11.4.2 Trust on Copy

Trust scores are carried over as a snapshot. They are not linked — subsequent votes or verifications in either workspace do not affect the other copy.

#### 11.4.3 Visibility on Copy

The copied node's `visibility` defaults to `private` in the target Knowledge Base, regardless of its visibility in the source. The user may change it after copying.

## 12. Knowledge Base Sharing Levels

### 12.1 Four-Tier Visibility System

Each Knowledge Base has a **visibility** setting that controls who can discover and access it. This is independent from the `visibility` field on individual Memory Nodes. **Visibility is set at creation time and cannot be changed thereafter.**

| Tier | Identifier | Chinese | Description |
|------|------------|---------|-------------|
| 全公開 | `public` | 公開 | Discoverable and readable by anyone, including unauthenticated users. |
| 有條件公開 | `conditional_public` | 有條件公開 | Anyone can discover the KB and submit a **join request** to admins. Admission requires explicit admin approval. |
| 限制公開 | `restricted` | 限制公開 | The KB is **invisible** to non-members through search or discovery. Access requires explicit invitation from an admin. |
| 私有 | `private` | 私有 | Completely inaccessible to all other users. Invitations cannot be issued. |

> **Design constraint**: The visibility selector must be shown clearly during workspace creation, each tier described inline, and the user must explicitly confirm their choice. The field is immutable — any `PATCH /workspaces/{ws_id}` request that includes `visibility` returns `400 Immutable field: visibility`.

### 12.2 Behavior by Tier

#### `public`
- Appears in global search and discovery feeds, accessible without login.
- Any authenticated user can read all nodes whose node-level `visibility` is `public`.
- Nodes with node-level `visibility: team` or `private` remain hidden from non-members.
- Anyone can copy `public`-visibility nodes to their own Knowledge Base.

#### `conditional_public`
- Appears in global search and discovery. KB name, description, and public-facing summary are readable by anyone.
- **Graph Preview Mode**: Non-members (unauthenticated or not-yet-approved) may view the **knowledge graph topology** (node positions, edge connections, relation type labels) but **cannot access node content**. Clicking any node displays a locked placeholder instead of the node body.
- Node titles are **obfuscated** in graph preview: only the `content_type` badge and an anonymized node ID are shown. Titles and body content are not transmitted to the client.
- The graph preview is read-only and non-interactive beyond panning and zooming.
- Any authenticated user may submit a join request (`POST /workspaces/{ws_id}/join-requests`).
- An admin must explicitly approve or reject each request.
- Approved users are added as `viewer` by default (configurable per request) and gain full node content access.
- Rejected applicants may not reapply for 7 days.

#### `restricted`
- Does **not** appear in global search or discovery. The KB's existence is not disclosed to non-members through any API.
- Access is granted via explicit admin invitation only (`POST /workspaces/{ws_id}/invites`).
- Invited users are added with the role specified in the invite token.

#### `private`
- Completely hidden from all other users.
- **Invitations cannot be issued.** No non-owner user may be added to the workspace.
- Does not appear in any listing or search result.

### 12.3 Workspace Roles & Permissions

To firmly establish the product's core focus on the **Knowledge Owner**, access to knowledge within a workspace (particularly `conditional_public` and `restricted` workspaces) is strictly role-based. Knowledge sharing is the primary goal, but the author has the ultimate choice regarding who can extract raw facts or modify the structure.

| Role | Permissions |
|------|-------------|
| **`viewer`** (檢視者) | Can view the knowledge graph topology and node titles, but **cannot access individual node body content or details**. This allows viewers to understand the shape of the knowledge and its connections without allowing data extraction. |
| **`editor`** (編輯者) | Can view both the topology and full node details. Can propose edits to nodes, create new nodes, and establish edges. |
| **`admin`** (管理者) | Retains full ownership features. Can view and edit everything, configure the Knowledge Base, manage join requests, and invite users while assigning roles. |

A workspace may have **multiple admins**. The original creator is automatically assigned the `admin` role and cannot demote themselves unless another admin exists. Any existing admin may promote another member to admin.

```sql
-- member_role ENUM definition:
ALTER TYPE member_role ADD VALUE IF NOT EXISTS 'admin';
```

API: `PUT /workspaces/{ws_id}/members/{user_id}` accepts `{ "role": "viewer | editor | admin" }`.

### 12.4 Creator Auto-Membership

When a workspace is created, the creating user is automatically inserted into `workspace_members` with `role = 'admin'`. This makes admin status explicit, auditable, and visible in the Members UI.

```sql
-- Runs atomically in the same transaction as the workspace INSERT:
INSERT INTO workspace_members (workspace_id, user_id, role)
VALUES (<new_ws_id>, <creator_id>, 'admin');
```

### 12.5 Join Request Flow (`conditional_public` only)

```
Applicant → POST /workspaces/{ws_id}/join-requests
        ↓
join_requests row created (status = pending)
        ↓
Admin(s) notified (in-app + email)
        ↓
Admin reviews: approve / reject
        ↓
Approved → workspace_members inserted (viewer by default)
Rejected → status = rejected; 7-day reapplication cooldown
```

**Schema:**
```sql
CREATE TABLE join_requests (
  id            TEXT PRIMARY KEY,
  workspace_id  TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  user_id       TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  message       TEXT,
  status        TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending','approved','rejected')),
  requested_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  reviewed_at   TIMESTAMPTZ,
  reviewed_by   TEXT REFERENCES users(id),
  UNIQUE (workspace_id, user_id)
);
```

| KB Visibility | Viewer Type | Graph Topology | Node Title | Node Body | Edges |
|---------------|------------|---------------|-----------|----------|-------|
| `public` | Anyone | ✓ Visible | ✓ Visible | ✓ Visible (if node `public`) | ✓ |
| `conditional_public` | Non-member | ✓ Visible | ✗ Obfuscated | ✗ Hidden | ✓ (relation type only) |
| `conditional_public` | Member (`viewer`) | ✓ Visible | ✓ Visible | ✗ Hidden | ✓ |
| `conditional_public` | Member (`editor`/`admin`) | ✓ Visible | ✓ Visible | ✓ Visible | ✓ |
| `restricted` | Non-member | ✗ Hidden | ✗ Hidden | ✗ Hidden | ✗ |
| `restricted` | Member (`viewer`) | ✓ Visible | ✓ Visible | ✗ Hidden | ✓ |
| `restricted` | Member (`editor`/`admin`) | ✓ Visible | ✓ Visible | ✓ Visible | ✓ |
| `private` | Anyone else | ✗ Hidden | ✗ Hidden | ✗ Hidden | ✗ |

> **Note**: For `conditional_public` non-members, the graph preview transmits only node coordinates, edge connectivity, and relation type labels. For `viewer` members, Titles and Edges are visible, but Body content is **never sent** to the client. This is enforced at the API response layer, not by frontend filtering.

### 12.7 Schema — Knowledge Base Object

```json
{
  "id": "ws_abc123",
  "schema_version": "1.0",
  "name": { "zh-TW": "...", "en": "..." },
  "visibility": "public | conditional_public | restricted | private",
  "visibility_locked": true,
  "kb_type": "evergreen | ephemeral",
  "embedding_provider": "openai | anthropic | gemini",
  "embedding_dim": 1536,
  "owner": "<user-id>",
  "decay_config": { "archive_window_days": 90, "min_traversals": 1 },
  "members": [
    { "user_id": "<user-id>", "role": "viewer | editor | admin" }
  ],
  "associations": ["ws_xyz"],
  "created_at": "<date-time>",
  "updated_at": "<date-time>"
}
```

- `kb_type`, `visibility`, `embedding_provider`, and `embedding_dim` are all **immutable after creation**.
- `members` for `private` workspaces contains only the owner.

### 12.8 Graph Preview Response Shape (`conditional_public`, non-member)

When the graph data endpoint is called by a non-member on a `conditional_public` workspace, the server returns a **stripped graph payload**:

```json
{
  "preview_mode": true,
  "nodes": [
    {
      "id": "node_preview_1",
      "content_type": "factual",
      "position": { "x": 120.4, "y": -88.2 }
    }
  ],
  "edges": [
    {
      "from": "node_preview_1",
      "to": "node_preview_2",
      "relation": "depends_on"
    }
  ]
}
```

- Real `memory_node.id` values are **replaced** with opaque sequential preview IDs (`node_preview_N`) that are not stable across requests.
- `title_zh`, `title_en`, `body_zh`, `body_en`, `tags`, `author`, `signature`, `trust_score`, and all provenance fields are **omitted entirely** from the response.
- The endpoint `GET /api/v1/workspaces/{ws_id}/graph?preview=true` serves this stripped payload. Attempting `GET /api/v1/workspaces/{ws_id}/nodes/{id}` as a non-member returns `HTTP 403`.
- Preview payload is **not cacheable** by the client (response header: `Cache-Control: no-store`).

## 10A. Schema Extensions

> Sections labelled with a letter suffix (e.g. §10A, §12A) are revisions added to SPEC.md after the original numbering was settled. They are deliberately given a unique label rather than a fresh number to keep cross-references in older documents stable. The canonical §10 (Access Control & Permission Roles) appears later in this document.

### 10A.1 Memory Node v1 — Additional Fields for Manual Editing

The following fields are appended to `node.v1.json` to support manual creation and editing:

| Field              | Type     | Required | Notes                                                  |
|--------------------|----------|----------|--------------------------------------------------------|
| `content.format`   | string   | Yes      | `"plain"` or `"markdown"`; defaults to `"plain"`       |
| `provenance.updated_at` | string (date-time) | No | Set on every edit after initial creation   |

`node.v1.json` `content` object updated `required`: adds `"format"`.

**Default values on node creation:**
```json
{
  "content": { "format": "plain" },
  "trust": {
    "score": 0.5,
    "dimensions": { "accuracy": 0.5, "freshness": 1.0, "utility": 0.5, "author_rep": 0.5 },
    "votes": { "up": 0, "down": 0, "verifications": 0 }
  }
}
```

## 13. Authentication & User Accounts

### 13.1 Overview

MemTrace supports two registration and login paths:

| Path | Description |
|------|-------------|
| **Email + Password** | Traditional credential-based registration with email verification |

Both paths produce the same internal `User` object and session token. Features and permissions are identical regardless of how the user signed up.

---

### 13.2 Email + Password Registration

#### 13.2.1 Registration Flow

1. User submits **email**, **display name**, and **password** via the registration form.
2. Server validates:
   - Email format is valid and not already registered.
   - Password meets the minimum policy (see §13.2.2).
3. Password is hashed with **bcrypt** (cost factor ≥ 12). The plaintext password is never stored or logged.
4. A `User` record is created with `email_verified: false`.
5. A **verification email** is sent containing a single-use, time-limited token (expires in 24 hours).
6. The user clicks the link → token is validated → `email_verified` is set to `true`.
7. Until email is verified, the account can sign in but cannot create public or restricted Knowledge Bases.

#### 13.2.2 Password Policy

| Rule | Requirement |
|------|-------------|
| Minimum length | 8 characters |
| Character classes | At least one uppercase, one lowercase, one digit |
| Maximum length | 128 characters |
| Breach check | Rejected if found in known breach datasets (HaveIBeenPwned API, k-anonymity model) |

#### 13.2.3 Login Flow

1. User submits email and password.
2. Server fetches the user record by email, verifies the bcrypt hash.
3. On success, a **session token** (signed JWT, 7-day expiry) is issued and returned.
4. Failed attempts are rate-limited: 5 failures → 15-minute lockout per account.

#### 13.2.4 Password Reset

1. User requests a reset by submitting their email.
2. A single-use reset link (expires in 1 hour) is sent if the email exists. The response is identical whether or not the email is registered (no user enumeration).
3. User sets a new password via the link; all existing sessions for that account are invalidated.

---


---

### 13.4 Session Management

- Sessions are represented as **signed JWTs** (HS256, secret stored in environment).
- Token payload:

```json
{
  "sub": "<user-id>",
  "email": "<email>",
  "display_name": "<name>",
  "iat": <issued-at>,
  "exp": <expiry>
}
```

- Token lifetime: **7 days**. Clients should refresh before expiry using the `/auth/refresh` endpoint.
- Logout invalidates the token server-side via a blocklist (Redis or DB table) until its natural expiry.
- All authenticated API endpoints require the token in the `Authorization: Bearer <token>` header.

---

### 13.5 User Object Schema

```json
{
  "id": "usr_abc123",
  "display_name": "string",
  "email": "string",
  "email_verified": true,
  "avatar_url": "string | null",
  "auth_providers": ["password"],
  "created_at": "<date-time>",
  "last_login_at": "<date-time>"
}
```

`auth_providers` lists all linked authentication methods.

---

### 13.6 API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/auth/register` | Email + password registration |
| `POST` | `/auth/login` | Email + password login |
| `POST` | `/auth/logout` | Invalidate current session |
| `POST` | `/auth/refresh` | Refresh session token |
| `POST` | `/auth/forgot-password` | Request password reset email |
| `POST` | `/auth/reset-password` | Submit new password with reset token |
| `GET` | `/auth/me` | Return current authenticated user |

## 14. External API Access & MCP Integration

### 14.1 Overview

MemTrace exposes its Knowledge Graph through two complementary access mechanisms:

| Mechanism | Use case |
|-----------|----------|
| **REST API** | Human users, web clients, and general-purpose service integrations |
| **MCP Server** | AI agents and LLM tools that consume MemTrace as a context provider |

Both mechanisms share the same authorization model (API keys, §14.2) and enforce the same Knowledge Base visibility rules (§12).

---

### 14.2 API Keys for External Access

External actors (services, agents, scripts) authenticate using **API keys** rather than session tokens. API keys are scoped to a specific user account and optionally to a specific Knowledge Base.

#### 14.2.1 Key Properties

```json
{
  "id": "apikey_abc123",
  "name": "My Agent",
  "prefix": "mt_live_xxxx",
  "scopes": ["kb:read", "kb:write", "node:traverse", "node:rate"],
  "workspace_id": "ws_abc123 | null",
  "created_at": "<date-time>",
  "last_used_at": "<date-time> | null",
  "expires_at": "<date-time> | null"
}
```

- `workspace_id: null` means the key is valid across all workspaces the user owns or has access to.
- The full key value is shown **once** at creation and never again. Only the prefix is stored server-side (hashed).
- Keys are passed in the `Authorization: Bearer mt_live_xxxx...` header (same header as session tokens; the server distinguishes by prefix).

#### 14.2.2 Scopes

| Scope | Grants |
|-------|--------|
| `kb:read` | List and read Knowledge Bases, nodes, and edges |
| `kb:write` | Create and edit nodes and edges within accessible KBs |
| `node:traverse` | Record a traversal event on a node or edge |
| `node:rate` | Submit an explicit path rating on an edge |

#### 14.2.3 Management Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/keys` | List all API keys for the authenticated user |
| `POST` | `/api/keys` | Create a new API key |
| `DELETE` | `/api/keys/{id}` | Revoke an API key |

---

### 14.3 REST API — Knowledge Base & Node Access

All paths are prefixed with `/api/v1`. Requests require `Authorization: Bearer <token_or_key>`.

#### Knowledge Bases

| Method | Path | Scope | Description |
|--------|------|-------|-------------|
| `GET` | `/workspaces` | `kb:read` | List accessible Knowledge Bases |
| `GET` | `/workspaces/{ws_id}` | `kb:read` | Get a single Knowledge Base |
| `GET` | `/workspaces/{ws_id}/nodes` | `kb:read` | List nodes in a KB (paginated) |
| `GET` | `/workspaces/{ws_id}/nodes/{node_id}` | `kb:read` | Get a single node |
| `POST` | `/workspaces/{ws_id}/nodes` | `kb:write` | Create a new node |
| `PATCH` | `/workspaces/{ws_id}/nodes/{node_id}` | `kb:write` | Edit an existing node |
| `GET` | `/workspaces/{ws_id}/edges` | `kb:read` | List edges in a KB |
| `POST` | `/workspaces/{ws_id}/edges` | `kb:write` | Create a new edge |

#### Traversal & Rating

| Method | Path | Scope | Description |
|--------|------|-------|-------------|
| `POST` | `/nodes/{node_id}/traverse` | `node:traverse` | Record that the caller has visited this node |
| `POST` | `/edges/{edge_id}/traverse` | `node:traverse` | Record traversal of an edge; triggers co-access boost and increments traversal counts on both endpoint nodes |
| `POST` | `/edges/{edge_id}/rate` | `node:rate` | Submit an explicit rating (1–5) for this path |

##### `POST /edges/{edge_id}/traverse` — Request body
```json
{
  "actor_id": "usr_abc123 | apikey_abc123",
  "note": "optional free-text annotation"
}
```

##### `POST /edges/{edge_id}/rate` — Request body
```json
{
  "rating": 4,
  "note": "optional free-text annotation"
}
```
- `rating` must be an integer between 1 and 5.
- One rating per actor per edge is enforced; subsequent submissions overwrite the previous rating.

#### Node Traversal Stats (readable via `kb:read`)

The `traversal` object is included in every node and edge response:

```json
{
  "traversal": {
    "count": 42,
    "unique_traversers": 17
  }
}
```

```json
{
  "traversal": {
    "count": 29,
    "rating_avg": 4.2,
    "rating_count": 11
  }
}
```

---

### 14.4 MCP Server Specification

MemTrace implements the **Model Context Protocol (MCP)** so that AI agents and LLMs can consume and contribute to the Knowledge Graph without manual REST integration.

#### 14.4.1 Transport

| Mode | Details |
|------|---------|
| **stdio** | Default for local CLI usage |
| **HTTP + SSE** | Available when `memtrace serve --mcp` is running (Phase 2) |

Authentication is via API key passed as the `MEMTRACE_API_KEY` environment variable (stdio) or `Authorization` header (HTTP).

#### 14.4.2 MCP Resources

Resources allow agents to read structured data as context.

| URI pattern | Description |
|-------------|-------------|
| `memtrace://workspaces` | List of accessible Knowledge Bases |
| `memtrace://workspace/{ws_id}` | Metadata for a single Knowledge Base |
| `memtrace://workspace/{ws_id}/nodes` | Paginated node list |
| `memtrace://node/{node_id}` | Full node content including traversal stats |
| `memtrace://node/{node_id}/edges` | All edges connected to this node |

#### 14.4.3 MCP Tools

Tools allow agents to take actions within MemTrace.

| Tool name | Scopes required | Description |
|-----------|----------------|-------------|
| `search_nodes` | `kb:read` | Semantic or keyword search across nodes in a workspace |
| `get_node` | `kb:read` | Retrieve a single node by ID |
| `create_node` | `kb:write` | Create a new Memory Node. Per the Node Minimization Principle, agents must follow each `create_node` call with one or more `create_edge` calls to connect the new node to the graph. An isolated node is not a valid terminal state. |
| `update_node` | `kb:write` | Edit an existing node's title, body, tags, or type |
| `list_edges` | `kb:read` | List edges for a given node |
| `create_edge` | `kb:write` | Create a typed edge between two existing nodes. Agents should prefer specific relation types (`depends_on`, `extends`) over `related_to` whenever a more precise relationship can be inferred. |
| `traverse_edge` | `node:traverse` | Record traversal of an edge and increment path + node counts |
| `rate_path` | `node:rate` | Submit a 1–5 rating for a traversed edge |

##### `search_nodes` — Input schema
```json
{
  "workspace_id": "ws_abc123",
  "query": "string",
  "mode": "semantic | keyword",
  "content_type": "factual | procedural | preference | context | null",
  "limit": 10
}
```

##### `traverse_edge` — Input schema
```json
{
  "edge_id": "edge_xyz789",
  "note": "optional"
}
```

##### `rate_path` — Input schema
```json
{
  "edge_id": "edge_xyz789",
  "rating": 4,
  "note": "optional"
}
```

#### 14.4.4 Traversal Semantics for Agents

When an AI agent navigates the graph (e.g. fetches node A, follows an edge to node B), it should call `traverse_edge` on each edge it follows. This:

1. Increments `traversal_count` on the edge and both endpoint nodes.
2. Triggers the **co-access boost** on the edge weight (see §7).
3. Updates `unique_traversers` on both nodes if the agent's API key has not previously traversed them.
4. Keeps the graph "alive" — preventing premature decay of knowledge paths that AI agents find valuable.

Agents are not required to rate paths but are encouraged to call `rate_path` when a path proved useful (rating ≥ 4) or misleading (rating ≤ 2), feeding signal back into the trust layer.

## 15. First-Run Onboarding

### 15.1 Overview

Onboarding covers two surfaces:

| Surface | Entry point | Target user |
|---------|-------------|-------------|
| **Web UI** | Sign-up page → guided wizard | New users registering via browser |
| **CLI** | `memtrace init` | Developers and power users installing locally |

Both surfaces share the same conceptual steps but differ in interaction style. Steps are resumable — if a user exits mid-flow, returning to the app resumes from the last incomplete step.

---

### 15.2 Web UI Onboarding Wizard

The wizard is shown automatically on first login and dismissed permanently once all required steps are complete. It is also re-accessible from **Settings → Getting Started** at any time.

#### 15.2.1 Step Map

```
① Create Account
       │
② Verify Email
       │
③ Name Your First Knowledge Base
       │
④ Choose Knowledge Base Type
       ├─── A. Evergreen（長效型）
       └─── B. Ephemeral（短效型）
       │
⑤ Choose a Starting Point
       ├─── A. Start blank
       └─── B. Upload a document
                    │
              ⑥ AI Provider Setup  ──── (skippable)
                    │
              ⑦ Review Extracted Nodes
       │
⑧ Done — Enter Graph View
```

A persistent **progress bar** (e.g. "Step 3 of 7") is shown at the top of each step. Required steps are marked; skippable steps show a "Skip for now" link.

---

#### 15.2.2 Step Detail

**① Create Account**

Two options presented side-by-side:
- "Sign up with Email" — collects display name, email, password. Validates inline against password policy (§13.2.2).

---

**② Verify Email**

- Full-screen notice: "Check your inbox — we sent a verification link to `<email>`."
- Resend button (rate-limited: once per 60 seconds).
- User can continue browsing the app in read-only mode until verified; a persistent banner reminds them.
- Step auto-advances when the verification link is clicked (page polls or uses WebSocket).

---

**③ Name Your First Knowledge Base**

Fields:
| Field | Required | Default |
|-------|----------|---------|
| Name (zh-TW) | Yes | — |
| Name (en) | Yes | — |
| Visibility | Yes | `private` |

A short tooltip explains the three visibility levels (§12).

---

**④ Choose Knowledge Base Type**

Two cards presented side-by-side. The user must select one before proceeding. **This choice cannot be changed after the Knowledge Base is created.**

| | Evergreen 長效型 | Ephemeral 短效型 |
|---|---|---|
| **Icon** | 🌲 | ⏳ |
| **Tagline** | 知識長存，引用塑造能見度 | 知識隨情境更新，舊路自然淡化 |
| **Best for** | Specs, playbooks, architecture decisions, onboarding guides | Troubleshooting runbooks, daily procedures, tool-specific how-tos |
| **How archiving works** | Nodes with no traversals in the observation window are archived | Edges decay over time; nodes with all edges faded are archived |
| **Time-based decay** | Off | On |

A "Learn more" link expands an inline explanation of §7.3 without leaving the step.

Default: **Evergreen** (pre-selected, with a note that most first-time users start with a spec or playbook).

---

**⑤ Choose a Starting Point**

Two cards:

| Option | Description |
|--------|-------------|
| **Start blank** | Go directly to the empty Graph View. Advance to step ⑦. |
| **Upload a document** | Opens file picker. Supported formats: `.md`, `.txt`, `.pdf`, `.docx`. Advance to step ⑤. |

---

**⑤ AI Provider Setup** *(skippable)*

Shown only if the user chose "Upload a document."

- Explains that document extraction requires an AI provider API key (§11.2).
- Provider selector (OpenAI / Anthropic) + API key input field.
- "Test connection" button — makes a minimal API call to validate the key.
- "Skip for now" — stores the document; extraction can be triggered later from the KB settings.

---

**⑦ Review Extracted Nodes** *(document path only)*

Displays the AI-proposed candidate nodes in the Review Queue (§11.3.1):
- Each candidate shows title, content type badge, and body preview.
- Actions: Accept / Edit then Accept / Reject per card, plus "Accept all" and "Reject all" bulk actions.
- A summary counter shows `X accepted / Y rejected / Z pending`.
- Cannot advance until at least one node is accepted.

---

**⑧ Done — Enter Graph View**

Full-screen completion card:
- Congratulates the user and summarises what was created (KB name, type, node count).
- Three shortcut actions:
  1. "Add your first node manually" → opens node editor (§9.3).
  2. "Invite someone" → opens KB sharing settings (§12).
  3. "Connect an AI tool" → opens API key creation flow (§14.2).
- "Go to Graph" button dismisses the wizard permanently.

---

### 15.3 CLI Onboarding (`memtrace init`)

Running `memtrace init` for the first time launches an interactive setup wizard in the terminal.

#### 15.3.1 Flow

```
$ memtrace init

Welcome to MemTrace! Let's get you set up.

Step 1/5 — Authentication
  > Log in or create an account
    [ ] Log in with existing account
    [ ] Create a new account

Step 2/5 — Create your first Knowledge Base
  > Knowledge Base name (en): _
  > Visibility [private / restricted / public]: private

Step 3/5 — Knowledge Base Type
  > Type [evergreen / ephemeral]: evergreen
    evergreen — Knowledge persists; archiving is driven by low reference count.
    ephemeral — Knowledge decays over time as tools and procedures change.
  (This setting cannot be changed after creation.)

Step 4/5 — AI Provider (optional, press Enter to skip)
  > Provider [openai / anthropic / skip]: _
  > API Key: _
  (Testing connection... ✓)

Step 5/5 — Import a document? (optional, press Enter to skip)
  > File path or URL [skip]: _

✓ Setup complete!
  Config saved to ~/.memtrace/config.json
  Knowledge Base "My First KB" created (ws_abc123)

Next steps:
  memtrace new          — create a memory node
  memtrace ingest <f>   — extract nodes from a file
  memtrace --help       — show all commands
```

#### 15.3.2 Config Written by `init`

`~/.memtrace/config.json` is created with:

```json
{
  "auth": {
    "token": "<session-jwt>"
  },
  "default_workspace": "ws_abc123",
  "ai": {
    "provider": "openai",
    "api_keys": {
      "openai": "<user-supplied>"
    }
  }
}
```

File is written with `chmod 600` immediately after creation.

#### 15.3.3 Re-running `memtrace init`

If a config already exists, the CLI asks:

```
Config already exists. What would you like to do?
  [ ] Update AI provider settings
  [ ] Switch default workspace
  [ ] Re-authenticate
  [ ] Exit
```

Existing values are not overwritten unless the user explicitly selects the relevant option.

---

### 15.4 Onboarding State (UI)

Onboarding completion is tracked server-side per user as a `onboarding` object:

```json
{
  "completed": false,
  "steps_done": ["account", "email_verified", "first_kb"],
  "steps_skipped": ["ai_provider"],
  "first_kb_id": "ws_abc123"
}
```

- `steps_done` and `steps_skipped` together determine the current step and progress bar value.
- Once `completed: true`, the wizard is never shown automatically again.

---

## 16. AI Features

MemTrace uses AI in three distinct contexts. All three share the same provider abstraction and API key model defined in §11.2 — the user supplies their own key, and the call is made from the client or server using that key. No AI call is made without explicit user initiation.

### 16.1 Document → Knowledge Base

**Described in detail in §11.1–11.3.4.**

Summary of the pipeline:

```
Source Document
      │
      ▼
 Segmentation          — structural cues (headings, paragraphs)
      │
      ▼
 AI Extraction         — per-segment: classify, generate bilingual title + body, suggest edges
      │
      ▼
 Review Queue          — user accepts / edits / rejects each candidate (never auto-commit)
      │
      ▼
 Committed Nodes       — source_type: ai_generated → ai_verified after acceptance
```

**Trigger**: User uploads a file, pastes a URL, or runs `memtrace ingest <file|url>` in the CLI. Accepted formats include documents, presentations, meeting recordings, video, audio, and web pages (see §11.1 for the full format table and phase availability).

**AI call type**: One LLM completion per segment; additionally one speech-to-text call per media file (if applicable).

**User control**: Every candidate node passes through human review before it is committed. The AI cannot create or modify nodes autonomously.

---

### 16.2 AI-Assisted Node Search

Users can search within a Knowledge Base using natural language instead of exact keywords. The AI layer converts the user's query into a semantic vector and retrieves the most relevant nodes by cosine similarity against stored embeddings.

#### 16.2.1 Search Modes

| Mode | Description | Trigger |
|------|-------------|---------|
| **Keyword** | Traditional full-text search on title, body, and tags | Default; no AI needed |
| **Semantic** | Embedding-based similarity search via `pgvector` ivfflat index | User selects "Smart Search" or prefixes query with `~` in CLI |
| **Hybrid** | Keyword + semantic results merged and ranked | Selectable in UI search settings |

#### 16.2.2 How It Works

1. User enters a natural language query (e.g. "how does edge decay affect traversal visibility?").
2. MemTrace sends the query to the configured AI provider's embedding endpoint.
3. The resulting vector is compared against `memory_nodes.embedding` using cosine similarity.
4. The top-N results (default: 10) are returned, ranked by similarity score.
5. Results are displayed in a **Search Panel** alongside their similarity score, content type badge, and a short body excerpt.

**Embedding generation for nodes**: When a node is created or updated, its embedding is generated from a concatenation of `title_en + body_en` (or `title_zh + body_zh` if only Chinese content is present) and stored in the `embedding` column. Embedding generation is **asynchronous** — it does not block the save operation.

#### 16.2.3 UI — Search Panel

- Accessible via the search icon in the sidebar or keyboard shortcut (`Ctrl+K` / `⌘K`).
- A toggle switches between Keyword / Semantic / Hybrid mode.
- Results show: node title, content type badge, similarity score (semantic mode only), first 100 characters of body, and a "Go to node" action that centers the Graph View on that node.
- Nodes with `status: archived` are excluded from results unless the "Include archived" filter is enabled.

#### 16.2.4 API

```
GET /api/v1/workspaces/{ws_id}/nodes/search
  ?q=<query text>
  &mode=keyword|semantic|hybrid    (default: keyword)
  &limit=10
  &include_archived=false
```

Semantic mode requires the requesting client to have a valid AI provider configured. If the provider embedding call fails, the API returns a `503` with the provider error detail.

#### 16.2.5 CLI

```bash
memtrace search "edge decay traversal"          # keyword
memtrace search --semantic "edge decay traversal"  # semantic
```

---

### 16.3 AI-Assisted Node Restructuring

Over time, a Knowledge Base may accumulate nodes that are redundant, too coarse, or too fine-grained. Manual authorship often produces nodes that are larger than necessary and under-connected. The restructuring feature lets a user ask an AI to re-evaluate a selected set of nodes and propose improvements guided by the Node Minimization Principle (§11.3).

**The primary goal of restructuring is always the same as extraction: smaller nodes, more edges, shorter traversal paths.**

**This is always a proposal, never an automatic operation.** All changes require user confirmation before any node or edge is modified.

#### 16.3.1 Restructuring Operations

The AI evaluates the selected nodes against the Node Minimization Principle and proposes the minimum set of changes needed to bring the subgraph into alignment with it:

| Operation | Trigger condition | Description |
|-----------|------------------|-------------|
| **Split** | Node body contains more than one discrete idea | Split into 2–N smaller focused nodes; propose edges between the resulting nodes |
| **Merge** | Two or more nodes are not meaningfully distinct when separated | Merge into one canonical node; archive the originals |
| **Retitle** | Title is too vague, too long, or redundant with body content | Suggest a minimal, specific title |
| **Reclassify** | `content_type` does not match the node's actual function | Suggest the correct classification |
| **Suggest edges** | Nodes in the selection are related but have no edge between them | Propose typed edges to shorten future traversal paths |
| **Trim body** | Node body restates its title or contains content that belongs in a separate node | Trim the body to the minimum necessary; extract excess into a new node |

#### 16.3.2 User Flow

```
User selects 1–20 nodes in Graph View (checkbox or lasso select)
      │
      ▼
"AI Restructure" action appears in toolbar
      │
      ▼
User clicks → AI analyses the selected nodes and returns a Restructure Proposal
      │
      ▼
Restructure Review Panel opens:
  - Each proposed change is shown as a card with before/after diff
  - User accepts / rejects / modifies each change individually
  - Bulk "Accept all" / "Reject all" available
      │
      ▼
Accepted changes are committed; rejected changes are discarded
```

#### 16.3.3 Restructure Prompt Design

The AI provider receives:

1. **System role**:
   > "You are a knowledge graph editor. Your goal is to help a human reduce a set of Memory Nodes to the smallest meaningful units connected by the richest set of typed edges. Evaluate each node against this question: does it contain more than one discrete idea? If yes, split it. Are two nodes not meaningfully distinct when separated? Merge them. Are related nodes missing an edge? Add it. The measure of a good restructure proposal is whether a human or AI agent can reach any answer faster after your changes than before."
2. **Node payload**: Full content of each selected node (title, body, content_type, tags, existing edges).
3. **Workspace context**: `kb_type`, total node count, and a sample of adjacent nodes (for consistency checking).
4. **Output schema**: A list of `ProposedChange` objects, each with:
   ```json
   {
     "operation": "split | merge | retitle | reclassify | suggest_edges",
     "target_node_ids": ["mem_xxx"],
     "reason": "...",
     "proposed": { ... }
   }
   ```

#### 16.3.4 Provenance After Restructuring

- Nodes modified by accepted restructure proposals have their `provenance.updated_at` set and `source_type` updated to `ai_verified`.
- New nodes created by a Split operation carry `source_type: ai_generated` until manually edited.
- The `signature` is recomputed for any node whose content changes.
- Original nodes that are replaced by a Merge are archived (not deleted), with `provenance.copied_from` pointing to the merged node.

#### 16.3.5 Constraints

- Maximum 20 nodes per restructure request (to control token usage and response coherence).
- Restructuring is only available to users with `editor` role or above in the workspace.
- A restructure proposal expires after 24 hours if not acted upon; the user must re-run the analysis.

---

### 16.4 AI Feature Summary

| Feature | Trigger | AI Call Type | Human Review Required | Modifies Data Autonomously |
|---------|---------|-------------|----------------------|---------------------------|
| Document → KB | Upload / `ingest` | LLM completion (per segment) | Yes — Review Queue | No |
| Node Search | Search query | Embedding | No | No |
| Node Restructuring | Manual selection + action | LLM completion (all selected nodes) | Yes — Restructure Review Panel | No |

### 16.5 Shared AI Provider Behaviour

All three features use the same provider resolution order:

1. **Workspace-level key** — if the user has configured an API key for this workspace.
2. **Account-level key** — if no workspace key is set, fall back to the user's account-level key.
3. **Disabled** — if no key is available, the AI feature button is greyed out with a tooltip prompting the user to configure a provider in Settings.

---

## 10. Access Control & Permission Roles

### 10.1 Design Philosophy

MemTrace adopts a **git-inspired permission model**: read access and write access are separate, and write access is further split between _proposing changes_ (like a pull request) and _merging them directly_. This applies equally to human users and AI tools.

Every workspace member and every API key (including MCP-connected AI agents) operates under exactly one of three roles.

### 10.2 Roles

| Role | Analogy | Capabilities |
|------|---------|-------------|
| **viewer** | `git clone` (read-only) | Search, read, traverse, Q&A chat, rate nodes |
| **contributor** | `git fork` + pull request | All viewer capabilities + propose node/edge changes (→ review queue, requires admin approval) |
| **admin** | Repository owner/maintainer | All contributor capabilities + direct write (create/edit/delete nodes and edges) + approve or reject proposals + manage members + invite users + soft-delete and restore workspace |

The workspace **owner** is always an admin and cannot be demoted.

### 10.3 Role Capabilities Detail

#### viewer
- `GET /workspaces/{ws_id}/nodes` (search, list, get)
- `POST /nodes/{id}/traverse` (traversal tracking)
- `POST /edges/{id}/rate` (node rating: votes_up / votes_down)
- `POST /workspaces/{ws_id}/chat` (conversational Q&A — §13)
- **Cannot** create, modify, or delete any nodes, edges, or workspace settings
- **Cannot** propose changes

#### contributor
- All viewer capabilities
- `POST /workspaces/{ws_id}/proposals` — propose a new node, an edit to an existing node, or a new/deleted edge
- Proposals enter the review queue with `status = pending_admin_review`; they are **not** applied until an admin approves
- A contributor may not approve their own proposals

#### admin
- All contributor capabilities
- Direct write to nodes and edges (bypasses review queue)
- `PATCH /review-queue/{id}/approve` and `/reject` — review contributor proposals
- `PUT /workspaces/{ws_id}/members/{user_id}` — change member role
- `DELETE /workspaces/{ws_id}/members/{user_id}` — remove member
- `POST /workspaces/{ws_id}/invites` — create invite links
- `DELETE /workspaces/{ws_id}` — initiate soft-delete (§12)
- `POST /workspaces/{ws_id}/restore` — cancel pending deletion

### 10.4 API Key Scopes

API keys (used by AI tools and CLI integrations) carry a role encoded as a scope:

| Scope | Role | Description |
|-------|------|-------------|
| `kb:read` | viewer | Search, read, traverse, rate |
| `kb:propose` | contributor | All read + submit proposals |
| `kb:write` | admin | Full write access |

An API key may hold exactly one of these three scopes. MCP tools respect the key's scope identically to a human user of the same role — a `kb:read` key cannot call `create_node`, a `kb:propose` key can call `propose_node`, and a `kb:write` key can call `create_node` directly.

### 10.5 Default Role on Join

| Entry point | Default role |
|-------------|--------------|
| Workspace created by user | admin (owner) |
| Accepted invite link | role embedded in the invite token (set by admin at creation) |
| Copied node (cross-workspace) | no membership granted — copy is independent |

### 10.6 Proposal Flow (contributor)

```
contributor submits proposal
        ↓
review_queue entry (status = pending_admin_review)
        ↓
admin reviews: approve / reject / edit-then-approve
        ↓
approved → change applied to KB
rejected → entry closed, contributor notified
```

Proposals use the same `review_queue` table as AI-extraction candidates (§11.3.1), distinguished by `source_type = 'contributor_proposal'`.

---

## 12A. Workspace Lifecycle & Soft-Delete

### 12A.1 States

A workspace moves through three states:

| State | Description |
|-------|-------------|
| `active` | Normal operation — all members can access |
| `pending_deletion` | Soft-deleted; 30-day grace period in progress |
| `deleted` | Purged from database (cascade) — cannot be restored |

### 12.2 Soft-Delete Behaviour

When an admin calls `DELETE /workspaces/{ws_id}`:
- `status` is set to `pending_deletion`
- `deleted_at` is set to `NOW()`
- All non-admin members immediately **lose access**
- The admin/owner retains read-only access to allow data export during the grace period
- An email notification is sent to the owner at: day 0 (deletion initiated), day 25 (5-day warning), day 30 (final purge)

### 12.3 Restoration

During the 30-day grace period, any admin calls `POST /workspaces/{ws_id}/restore`:
- `status` returns to `active`
- `deleted_at` is cleared
- All member access is restored

### 12.4 Automatic Purge

A background job runs daily and purges all workspaces where:

```sql
status = 'pending_deletion'
AND deleted_at < NOW() - INTERVAL '30 days'
```

Purge is a **hard CASCADE DELETE** — all nodes, edges, members, invites, and chat sessions in the workspace are deleted. This cannot be undone.

### 12.5 Schema Changes

```sql
ALTER TABLE workspaces
  ADD COLUMN status        TEXT NOT NULL DEFAULT 'active'
                           CHECK (status IN ('active','pending_deletion','deleted')),
  ADD COLUMN deleted_at    TIMESTAMPTZ;
```

### 12.6 KB Type Interaction

| KB Type | Grace Period | Notes |
|---------|-------------|-------|
| `evergreen` | 30 days | Standard grace period |
| `ephemeral` | 7 days | Shorter grace period; ephemeral KBs are expected to expire |

---

## 13A. Conversational Q&A

### 13A.1 Overview

Any member with **viewer role or above** can ask natural-language questions against a workspace's knowledge base. The system retrieves relevant nodes, builds a context prompt, calls the configured AI provider, and returns an answer citing the source nodes.

This is distinct from AI extraction (§11.3): Q&A is **read-only** — it never writes to the KB.

### 13.2 Request / Response Flow

```
user message
     ↓
search_nodes(query) → top-5 relevant nodes     [keyword + optional vector]
     ↓
traverse(top node, depth=1) → neighbour context [optional, improves multi-hop answers]
     ↓
build prompt:
  system: "You are a knowledge assistant. Answer using only the provided nodes.
           Cite node IDs in your response."
  context: rendered node blocks (id, title, body)
  user: original question
     ↓
AI completion (respects workspace AI provider config — §16.5)
     ↓
response: { answer, cited_nodes: [node_id, ...], tokens_used, session_id }
```

### 13.3 API

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/workspaces/{ws_id}/chat` | Send a message; optionally pass `session_id` to continue a conversation |
| `GET` | `/workspaces/{ws_id}/chat/sessions` | List the caller's chat sessions |
| `GET` | `/workspaces/{ws_id}/chat/sessions/{session_id}` | Get full message history for a session |

Request body for `POST /chat`:
```json
{
  "message": "What are the decay half-life values for each content type?",
  "session_id": "optional — omit to start a new session",
  "lang": "en"
}
```

Response:
```json
{
  "answer": "...",
  "cited_nodes": ["mem_d002", "mem_g001"],
  "tokens_used": 312,
  "session_id": "sess_a1b2c3d4"
}
```

### 13.4 Session & History

- Each `POST /chat` without a `session_id` creates a new `chat_sessions` row
- Messages are stored in `chat_messages` (role: `user` | `assistant`)
- Sessions are scoped to the workspace and the authenticated user
- Sessions are **not** affected by node decay — conversation history is preserved even if cited nodes are later archived
- Maximum context window: last 10 messages in the session are included for multi-turn continuity

### 13.5 Database Schema

```sql
CREATE TABLE chat_sessions (
  id           TEXT PRIMARY KEY DEFAULT gen_id('sess'),
  workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  user_id      TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE chat_messages (
  id           TEXT PRIMARY KEY DEFAULT gen_id('msg'),
  session_id   TEXT NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
  role         TEXT NOT NULL CHECK (role IN ('user','assistant')),
  content      TEXT NOT NULL,
  cited_nodes  TEXT[] NOT NULL DEFAULT '{}',
  tokens_used  INTEGER NOT NULL DEFAULT 0,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 13.6 Access Control

| Role | Q&A access |
|------|-----------|
| viewer | Full access — can ask questions and view session history |
| contributor | Full access |
| admin | Full access |
| Unauthenticated | Not allowed (even for public workspaces) — requires login |

### 13.7 AI Feature Table Update

| Feature | Trigger | AI Call | Human Review | Modifies Data |
|---------|---------|---------|-------------|--------------|
| Document → KB | Upload / `ingest` | LLM completion | Yes — Review Queue | No (until approved) |
| Node Search | Search query | Embedding | No | No |
| Node Restructuring | Manual selection | LLM completion | Yes — Review Panel | No (until approved) |
| **Conversational Q&A** | **Chat message** | **LLM completion** | **No** | **No (read-only)** |
| **AI Conversation Panel (edit mode)** | **Chat message + allow_edits** | **LLM completion** | **Yes — inline proposal card** | **No (until accepted)** |

---

## 17. Write Serialization & Concurrent Edit Safety

### 17.1 Motivation

When multiple users (or AI agents) submit writes to the same Knowledge Base simultaneously, the following failure modes must be prevented:

- A node is modified by two parties simultaneously, producing a split-brain state.
- A document ingestion creates duplicate nodes or conflicting edges because two ingestions ran in parallel.
- An AI restructure proposes changes on a stale snapshot while a concurrent human edit was being saved.

### 17.2 Optimistic Locking on Nodes

Every `memory_nodes` row carries an `updated_at` timestamp and a `version` integer. All update endpoints require the caller to supply the last-known version:

```http
PATCH /api/v1/workspaces/{ws_id}/nodes/{node_id}
X-Node-Version: <integer>
```

If the node has been modified since the supplied version, the server returns:

```
HTTP 412 Precondition Failed
{ "detail": "Node was modified by another actor since your last fetch. Reload and retry." }
```

The client must re-fetch the node, merge changes, and re-submit. No silent clobber.

**Schema addition:**

```sql
ALTER TABLE memory_nodes ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1;
-- Increment on every successful UPDATE:
-- version = version + 1
```

### 17.3 Write Queue per Workspace

To prevent race conditions during document ingestion, bulk AI extraction, and concurrent node creation, **writes to the same workspace are serialized through a per-workspace advisory lock.**

```sql
-- Acquired at the start of every write transaction:
SELECT pg_advisory_xact_lock(hashtext(<ws_id>));
-- Released automatically on transaction commit or rollback
```

- If the lock cannot be acquired within the timeout, the server returns `HTTP 429 Write queue busy — try again shortly`.
- The lock is scoped per-workspace; writes to different workspaces are fully parallel.
- Read operations are **never** gated by the write lock.
- Timeout is configurable via `WS_WRITE_LOCK_TIMEOUT_SECONDS` (default: 5).

### 17.4 Logical Conflict Detection

After any AI-generated or AI-restructured node is committed, an **asynchronous conflict check** runs to detect logical inconsistencies introduced by the AI.

#### 17.4.1 Conflict Types

| Type | Description |
|------|-------------|
| `contradicts_existing` | Node body contradicts a body-level assertion in an existing `contradicts`-linked node |
| `duplicate_content` | Node embedding cosine-similarity ≥ 0.92 to an existing active node |
| `circular_dependency` | A `depends_on` edge would create a cycle in the dependency graph |
| `orphaned_reference` | Node body references another node by ID but no edge exists |

#### 17.4.2 Conflict Flagging Schema

```sql
ALTER TABLE memory_nodes
  ADD COLUMN IF NOT EXISTS conflict_status  TEXT
    CHECK (conflict_status IN (NULL, 'flagged', 'resolved')),
  ADD COLUMN IF NOT EXISTS conflict_detail  JSONB;
  -- { "type": "...", "conflicting_node_id": "...", "message": "..." }
```

Flagged nodes display an **amber warning indicator** in the Graph View and a dismissible conflict card in the node editor.

**Resolving:** Edit the node to remove the contradiction → `conflict_status = 'resolved'`, or call `PATCH .../acknowledge-conflict` to dismiss without content change.

#### 17.4.3 AI Write Rules

AI agents (MCP) are subject to the same write serialization and conflict detection as human users. A `conflict_warning` field is returned in the next tool response if a conflict is detected post-commit:

```json
{
  "result": "...",
  "conflict_warning": {
    "node_id": "mem_xyz",
    "type": "duplicate_content",
    "similar_node_id": "mem_abc"
  }
}
```

---

## 18. Knowledge Base Associations

### 18.1 Purpose

A Knowledge Base may be **associated** with one or more other Knowledge Bases to form a trusted knowledge network. Associations are the explicit signal that AI agents may use to reason across workspace boundaries. An AI agent operating in a workspace may **not** reference or query nodes from an unassociated workspace, regardless of visibility.

### 18.2 Association Model

Associations are directional. Mutual association (both directions) is required for full bidirectional AI cross-querying.

```sql
CREATE TABLE workspace_associations (
  id              TEXT PRIMARY KEY,
  source_ws_id    TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  target_ws_id    TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  created_by      TEXT NOT NULL REFERENCES users(id),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (source_ws_id, target_ws_id),
  CHECK (source_ws_id <> target_ws_id)
);
```

**API:**

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/workspaces/{ws_id}/associations` | List all associated workspaces |
| `POST` | `/workspaces/{ws_id}/associations` | Add an association (admin only) |
| `DELETE` | `/workspaces/{ws_id}/associations/{target_ws_id}` | Remove an association (admin only) |

### 18.3 AI Cross-Workspace Rules

1. **Boundary enforcement**: AI agents may only query workspaces directly associated with the target workspace. No transitive lookup — one hop maximum.
2. **Permission check**: Before including any node from an associated workspace in a prompt, the system verifies the requesting user has at least `viewer` role in that workspace. Non-accessible nodes are silently excluded.
3. **Write restriction**: AI mutation tools may only write to the workspace specified in the API call. They cannot write to an associated workspace, even if the user has rights in both.
4. **Scope disclosure**: Nodes cited from an associated workspace include a `cross_kb: true` flag in the response.

---

## 19. AI Conversation Panel

### 19.1 Overview

The **AI Conversation Panel** is a first-class, standalone UI surface — separate from the graph search bar. It allows persistent, multi-turn dialogue grounded in the workspace knowledge graph. Unlike the read-only Conversational Q&A (§13), it supports **in-conversation edit proposals**.

### 19.2 Access

- Accessible via a dedicated panel button in the sidebar (distinct from the search icon).
- Available to users with **viewer role or above**.
- Authentication required — not accessible to unauthenticated users.

### 19.3 Conversation Capabilities

| Capability | Description |
|------------|-------------|
| **KB enquiry** | Ask questions about knowledge base content; AI retrieves and cites relevant nodes (same pipeline as §13). |
| **Content clarification** | Ask AI to explain, expand, or simplify a specific node, grounded in its body and depth-1 graph neighborhood. |
| **In-conversation edit proposal** | User says "update this node to reflect X" — AI generates a diff proposal shown as an inline card. User Accepts, Edits, or Rejects. |
| **Cross-KB query** | If associated workspaces are configured (§18) and the user has access, AI may draw on those nodes (labeled accordingly). |

### 19.4 Edit Proposal Flow

```
User: "Update mem_a002 to mention OCR requirement."
        ↓
AI generates proposed body diff
        ↓
Inline proposal card rendered:
  ┌─────────────────────────────────────────────────┐
  │  📝 Proposed edit to mem_a002                   │
  │  + Scanned PDFs require OCR (Phase 2+)          │
  │  [Accept]  [Edit]  [Reject]                     │
  └─────────────────────────────────────────────────┘
        ↓
contributor → enters review_queue (pending_admin_review)
admin       → applied immediately
```

### 19.5 API Extension

```http
POST /api/v1/workspaces/{ws_id}/chat
{
  "message": "...",
  "session_id": "optional",
  "lang": "zh-TW | en",
  "allow_edits": true
}
```

Response when a proposal is generated:

```json
{
  "answer": "Here is the proposed change:",
  "cited_nodes": ["mem_a002"],
  "proposal": {
    "operation": "update_node",
    "target_node_id": "mem_a002",
    "diff": { "body_zh": "...", "body_en": "..." },
    "proposal_id": "prop_xyz"
  },
  "session_id": "sess_xyz"
}
```

A follow-up request with `{ "action": "accept" | "reject", "proposal_id": "prop_xyz" }` applies or discards the change.

### 19.6 Cross-KB Boundary

When `allow_edits: true`, AI may propose edits **only to nodes in the current workspace**. It may read from associated workspaces but may not propose writes to them.

---

## 20. Source File Retention on Ingested Nodes

### 20.1 Purpose

When a document is ingested, the **original source file is retained** as a special node. This ensures extraction traceability and gives users a direct link from any extracted node back to its source passage without polluting the main knowledge graph.

### 20.2 Source Document Node

A `source_document` content type is added:

```sql
ALTER TYPE content_type ADD VALUE IF NOT EXISTS 'source_document';
```

| Field | Value |
|-------|-------|
| `content_type` | `source_document` |
| `title_zh` / `title_en` | Original filename + ingestion timestamp |
| `body_zh` / `body_en` | Full extracted text or transcript |
| `visibility` | `private` (default) |
| `source_type` | `human` |

### 20.3 Paragraph-Level Markers

Each extracted node carries a reference to its source passage:

```sql
ALTER TABLE memory_nodes
  ADD COLUMN IF NOT EXISTS source_doc_node_id   TEXT REFERENCES memory_nodes(id),
  ADD COLUMN IF NOT EXISTS source_paragraph_ref TEXT;
```

| Source Format | Reference Format |
|---------------|-----------------|
| Markdown / plain text | `§<heading>` or `¶<paragraph_index>` |
| PDF / DOCX | `page:<n>, para:<m>` |
| PPTX | `slide:<n>` |
| Video / audio | `<HH:MM:SS>-<HH:MM:SS>` |
| Web page | `<section heading or XPath fragment>` |

### 20.4 Traversal Exclusion

Source document nodes are **excluded by default** from:
- Graph View (hidden unless "Show source files" is enabled)
- Keyword and semantic search results
- Q&A and AI Conversation context retrieval
- MCP `search_nodes` results

They are accessible via:
- Direct `GET /workspaces/{ws_id}/nodes/{node_id}`
- `GET /workspaces/{ws_id}/source-documents` (dedicated endpoint)
- The "View source passage" link in the node editor sidebar

---

## 21. AI Usage Logging

### 21.1 Requirement

**All AI calls — regardless of whether they use a workspace-level or account-level key — must be logged.** The log is the authoritative record for billing, debugging, and policy enforcement.

### 21.2 Log Schema

```sql
CREATE TABLE ai_usage_log (
  id              TEXT PRIMARY KEY,
  user_id         TEXT NOT NULL REFERENCES users(id),
  key_source      TEXT NOT NULL
                  CHECK (key_source IN ('workspace_key', 'account_key')),
  provider        TEXT NOT NULL,        -- 'openai' | 'anthropic' | 'gemini' | ...
  model           TEXT NOT NULL,        -- e.g. 'gpt-4o-mini', 'gemini-2.0-flash'
  feature         TEXT NOT NULL
                  CHECK (feature IN ('extraction','embedding','restructure',
                                     'chat','conflict_check','conversation_panel')),
  workspace_id    TEXT REFERENCES workspaces(id) ON DELETE SET NULL,
  node_id         TEXT,
  tokens_input    INTEGER NOT NULL DEFAULT 0,
  tokens_output   INTEGER NOT NULL DEFAULT 0,
  tokens_total    INTEGER GENERATED ALWAYS AS (tokens_input + tokens_output) STORED,
  latency_ms      INTEGER,
  success         BOOLEAN NOT NULL DEFAULT true,
  error_code      TEXT,
  called_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_ai_usage_user     ON ai_usage_log (user_id, called_at DESC);
CREATE INDEX idx_ai_usage_feature  ON ai_usage_log (feature, called_at DESC);
CREATE INDEX idx_ai_usage_provider ON ai_usage_log (provider, called_at DESC);
```

### 21.3 Field Notes

| Field | Notes |
|-------|-------|
| `key_source` | `workspace_key` = key configured for this workspace; `account_key` = user's global account key |
| `feature` | Which AI capability triggered the call |
| `tokens_input` / `tokens_output` | Reported by provider; used for quota accounting |
| `latency_ms` | Provider call wall time; useful for SLO monitoring |
| `success` | `false` if provider returned an error |
| `error_code` | Raw provider error code (e.g. `insufficient_quota`, `rate_limit_exceeded`) |

### 21.4 API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/user/ai-usage` | Paginated usage log for the current user |
| `GET` | `/api/v1/user/ai-usage/summary` | Aggregated by day, feature, and provider |

Query parameters: `?from=<ISO date>&to=<ISO date>&provider=openai|anthropic|gemini|all`

Summary response:
```json
{
  "period": { "from": "2026-04-01", "to": "2026-04-30" },
  "by_feature": {
    "chat": { "calls": 42, "tokens_total": 18400 },
    "extraction": { "calls": 7, "tokens_total": 31200 }
  },
  "by_provider": {
    "openai": { "tokens_total": 49600 },
    "gemini": { "tokens_total": 0 }
  }
}
```

### 21.5 Retention

Logs are retained for **12 months**, then archived. Logs are never deleted before the retention period expires.

---

## Summary of Schema Changes (Spec Rev 2)

| Table / Object | Change | Section |
|----------------|--------|---------|
| `workspaces` | Add `visibility_locked`, `embedding_provider`, `embedding_dim` columns | §12.7, §11.2.2 |
| `kb_visibility` ENUM | Add `conditional_public` value | §12.1 |
| `member_role` ENUM | Add `admin` value | §12.3 |
| `workspace_members` | Creator auto-inserted as `admin` on CREATE | §12.4 |
| `workspace_associations` | New table | §18.2 |
| `join_requests` | New table | §12.5 |
| `memory_nodes` | Add `version`, `conflict_status`, `conflict_detail`, `source_doc_node_id`, `source_paragraph_ref` | §17.2, §17.4, §20.3 |
| `content_type` ENUM | Add `source_document` value | §20.2 |
| `ai_provider` ENUM | Add `gemini` value | §11.2.2 |
| `ai_usage_log` | New table | §21.2 |
| `kb_exports` | New table (export job tracking) | §22.5 |

---

## 22. Knowledge Base Export & Import

### 22.1 Purpose

Knowledge Base export and import provide a portable, format-agnostic mechanism to:

1. **Back up** a workspace to a local archive that can be restored into any MemTrace instance.
2. **Share** curated subsets of knowledge across teams or organizations without granting direct workspace access.
3. **Migrate** knowledge into a new workspace or a different MemTrace deployment.

Export is always a **pull-only operation** — it never modifies the source workspace. Import is an **additive operation** — it never deletes existing nodes or edges in the target workspace.

---

### 22.2 Export Scope

An export may target the **entire workspace** or a **filtered subset** defined by one or more scope dimensions. Scopes can be combined (intersection of all active filters).

#### 22.2.1 Scope Types

| Scope Key | CLI Flag | Description | Matching Logic |
|-----------|----------|-------------|----------------|
| **User Manual** | `--type user-manual` | Nodes that describe how to use the product from an end-user perspective | Tags contain any of: `how-to`, `tutorial`, `guide`, `usage`, `onboarding`, `walkthrough`; or `content_type = 'procedural'` AND node is traversal-reachable from a root tagged `user-manual` |
| **Business Logic** | `--type business-logic` | Nodes that encode domain rules, decision criteria, or policy constraints | Tags contain any of: `rule`, `policy`, `constraint`, `decision`, `business-logic`, `domain`; or `content_type IN ('factual', 'context')` AND tagged with at least one business-logic signal |
| **Functional Spec** | `--type functional-spec` | Nodes that define product features, acceptance criteria, or system behaviour | Tags contain any of: `spec`, `feature`, `requirement`, `acceptance`, `behaviour`, `api`; or `content_type = 'factual'` AND tagged `spec` or `feature` |
| **User-Defined** | `--filter` (multi-value) | Any combination of tags, content types, node IDs, or a freeform keyword query | See §22.2.2 |
| **Full workspace** | *(no scope flag)* | All active nodes and edges in the workspace | Excludes `archived` nodes by default; include with `--include-archived` |

> **Note**: Scope matching is evaluated on the server at export time. Nodes that have been archived, conflict-flagged, or are of type `source_document` are **excluded by default** from all scope types. Use explicit flags to override.

#### 22.2.2 User-Defined Filter (`--filter`)

Users can compose a custom export by combining any of the following filter primitives:

| Filter Key | Example | Description |
|------------|---------|-------------|
| `tag` | `--filter tag:auth` | Include nodes whose `tags[]` contain the value |
| `content_type` | `--filter type:procedural` | Include nodes of the specified content type |
| `node` | `--filter node:mem_d001` | Include a specific node and its depth-1 neighbours |
| `query` | `--filter query:"edge decay"` | Full-text keyword match across title and body |
| `semantic` | `--filter semantic:"how does trust work"` | Semantic similarity search (requires AI provider) |

Multiple `--filter` flags are combined with **AND** logic. To use OR logic, run separate exports and merge the archives.

The UI provides an equivalent **"Custom Export" panel** with tag pickers, a node selector, and a keyword/semantic search field.

#### 22.2.3 Edge Inclusion

When a node is included in an export, its **edges are included if and only if both endpoint nodes are also included** in the same export. Edges to excluded nodes are dropped. This preserves graph coherence within the export archive.

---

### 22.3 Output Formats

Two formats are supported in Phase 1. Additional formats are planned for later phases.

#### Phase 1 — Supported

| Format | Extension | Description | Phase |
|--------|-----------|-------------|-------|
| **Markdown** | `.md` | Each node is rendered as a Markdown document. Edges are expressed as `## Associations` sections with named links. Equivalent to the node's Graph View representation. | 1 |
| **Plain text** | `.txt` | Each node is rendered as plain text. Edges are listed as indented `→ [relation] Title` lines after the node body. Suitable for viewing in any text editor. | 1 |
| JSON (internal) | `.json` | Full `node.v1.json`-compliant archive with edges. Used internally for backup/restore and import. Always generated alongside the human-readable format. | 1 (internal) |
| PDF | `.pdf` | Formatted multi-page document with table of contents, section headers per cluster, and graph diagram snapshot. | 2 |
| HTML | `.html` | Self-contained single-page HTML with embedded CSS and an interactive node browser. | 2 |
| CSV | `.csv` | Flat table of nodes; edges as a separate edge list file. Useful for spreadsheet analysis. | 3 |

#### 22.3.1 Markdown Format — Structure

The Markdown export produces a **single `.md` file per export**, structured as:

```markdown
# {Knowledge Base Name} — {Scope Label} Export
> Exported: {ISO datetime} | Workspace: {ws_id} | Nodes: {count} | Edges: {count}

---

## {Cluster / Tag Group}

### {node_title_en} | {node_title_zh}
> ID: {node_id} | Type: {content_type} | Tags: {tag1}, {tag2}

{body_en}

---
**Associations:**
- → [depends_on] {linked_node_title} (`{linked_node_id}`)
- → [extends] {linked_node_title} (`{linked_node_id}`)

---
```

Nodes are grouped by their primary tag (or by cluster if the workspace uses cluster metadata). Within each group, nodes are ordered by traversal count descending (most-referenced first).

#### 22.3.2 Plain Text Format — Structure

```
=== {Knowledge Base Name} — {Scope Label} Export ===
Exported: {ISO datetime} | Workspace: {ws_id}

[{node_id}] {node_title_en}
Type: {content_type} | Tags: {tag1}, {tag2}

{body_en}

Associations:
  → depends_on: {linked_node_title} [{linked_node_id}]
  → extends:    {linked_node_title} [{linked_node_id}]

────────────────────────────────────────
```

#### 22.3.3 Archive Structure

The export is packaged as a **`.memtrace` archive** (a ZIP file with a `.memtrace` extension) containing:

```
export_{ws_id}_{timestamp}.memtrace
├── manifest.json          ← metadata: scope, format, timestamps, versions
├── nodes.json             ← all exported nodes in node.v1.json format
├── edges.json             ← all exported edges in edge.v1.json format
├── export.md              ← Markdown render (if requested)
├── export.txt             ← Plain text render (if requested)
└── source_documents/      ← (optional) source file attachments, if --include-sources
    └── {node_id}.{ext}
```

`manifest.json` schema:
```json
{
  "memtrace_version": "1.0",
  "exported_at": "<ISO datetime>",
  "workspace_id": "ws_abc123",
  "workspace_name": { "zh-TW": "...", "en": "..." },
  "scope": "full | user-manual | business-logic | functional-spec | custom",
  "filters": [],
  "node_count": 42,
  "edge_count": 87,
  "formats": ["json", "markdown"],
  "exported_by": "usr_abc123"
}
```

---

### 22.4 Export Access Control

| Role | Export permission |
|------|------------------|
| `viewer` | May export nodes they have read access to (node-level `visibility` filter applies) |
| `editor` | Same as viewer |
| `admin` | May export entire workspace including `team`-visibility nodes |

Practical implications:
- A `viewer` exporting a `public` KB with `--type functional-spec` receives only nodes whose effective access allows reads for their role.
- `private`-visibility nodes are **never** included in exports for non-owner users, regardless of export scope.
- Source document nodes (`content_type = 'source_document'`) require explicit `--include-sources` flag and admin role.

---

### 22.5 Export Job Tracking

For large workspaces, export is an **asynchronous background job**. The API returns a job ID immediately; the client polls for completion.

```sql
CREATE TABLE kb_exports (
  id              TEXT PRIMARY KEY,           -- export_<hex8>
  workspace_id    TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  requested_by    TEXT NOT NULL REFERENCES users(id),
  scope           TEXT NOT NULL,              -- 'full' | 'user-manual' | 'business-logic' | 'functional-spec' | 'custom'
  filters         JSONB NOT NULL DEFAULT '[]',
  formats         TEXT[] NOT NULL,            -- ['json', 'markdown', 'txt']
  include_archived BOOLEAN NOT NULL DEFAULT false,
  include_sources  BOOLEAN NOT NULL DEFAULT false,
  status          TEXT NOT NULL DEFAULT 'pending'
                  CHECK (status IN ('pending','running','done','failed')),
  node_count      INTEGER,
  edge_count      INTEGER,
  download_url    TEXT,                       -- pre-signed URL, valid 1 hour
  error_detail    TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at    TIMESTAMPTZ
);
```

**API:**

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/workspaces/{ws_id}/exports` | Start an export job |
| `GET` | `/api/v1/workspaces/{ws_id}/exports/{export_id}` | Poll job status and get download URL |
| `GET` | `/api/v1/workspaces/{ws_id}/exports` | List previous export jobs (last 30 days) |

Request body for `POST /exports`:
```json
{
  "scope": "user-manual | business-logic | functional-spec | custom | full",
  "filters": [
    { "key": "tag", "value": "auth" },
    { "key": "type", "value": "procedural" }
  ],
  "formats": ["markdown", "json"],
  "include_archived": false,
  "include_sources": false
}
```

Polling response (status `done`):
```json
{
  "id": "export_abc123",
  "status": "done",
  "node_count": 42,
  "edge_count": 87,
  "download_url": "https://...",   <-- pre-signed, valid 1 hour
  "completed_at": "2026-04-13T04:00:00Z"
}
```

---

### 22.6 Import

#### 22.6.1 Behavior

- Import accepts a `.memtrace` archive (from §22.3.3) or a raw `nodes.json` / `edges.json` pair.
- Import is **additive**: existing nodes in the target workspace are never overwritten or deleted.
- Each imported node receives a **new `id`** in the target workspace (same as the copy-node behavior, §11.4).
- `provenance.copied_from` is set to the original node ID and source workspace from `manifest.json`.
- Edges are re-linked to the new node IDs within the import batch. Edges referencing nodes not present in the import archive are dropped.
- The importing user must have **admin role** in the target workspace.

#### 22.6.2 Conflict Resolution

Before committing, the import job runs the same logical conflict detection as §17.4 against the target workspace. Conflicts are surfaced in a **pre-import review screen** rather than applied blindly:

```
Import Preview (42 nodes, 87 edges)
  ✓ 38 nodes — clean
  ⚠  4 nodes — potential duplicates detected
    [View details]  [Skip duplicates]  [Import anyway]
```

The user can choose to skip duplicate-flagged nodes, import all nodes regardless of conflicts (conflicts will be flagged post-import per §17.4), or cancel the import.

#### 22.6.3 API

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/workspaces/{ws_id}/imports` | Start an import job (multipart: archive file) |
| `GET` | `/api/v1/workspaces/{ws_id}/imports/{import_id}` | Poll status |
| `POST` | `/api/v1/workspaces/{ws_id}/imports/{import_id}/confirm` | Confirm after preview |

Request for `POST /imports`:
```http
Content-Type: multipart/form-data

file=<.memtrace archive>
conflict_strategy=skip_duplicates | import_all   (default: skip_duplicates)
```

#### 22.6.4 Trust on Import

Imported nodes carry their original trust scores as a snapshot (same as §11.4.2). Votes and verifications in the target workspace do not affect scores in the source and vice versa.

#### 22.6.5 Visibility on Import

All imported nodes default to `private` visibility in the target workspace, regardless of their visibility in the source (same as §11.4.3). The admin may bulk-update visibility after import.

---

### 22.7 CLI Interface

```bash
# Full workspace export (JSON + Markdown)
memtrace export --workspace ws_abc123 --format markdown,json

# Export by scope
memtrace export --workspace ws_abc123 --type user-manual --format markdown
memtrace export --workspace ws_abc123 --type business-logic --format txt
memtrace export --workspace ws_abc123 --type functional-spec --format markdown,json

# User-defined filter
memtrace export --workspace ws_abc123 \
  --filter tag:auth --filter type:procedural \
  --format markdown

# Semantic filter (requires AI provider)
memtrace export --workspace ws_abc123 \
  --filter semantic:"how does trust scoring work" \
  --format txt

# Include archived nodes
memtrace export --workspace ws_abc123 --include-archived --format json

# Import
memtrace import --workspace ws_xyz789 --file export_ws_abc123_20260413.memtrace
memtrace import --workspace ws_xyz789 --file export_ws_abc123_20260413.memtrace \
  --conflict-strategy import_all
```

The CLI polls the job status automatically and downloads the archive to the current directory on completion:
```
✓ Export complete — 42 nodes, 87 edges
  Saved: ./export_ws_abc123_20260413T040000Z.memtrace
```

---

### 22.8 UI — Export Panel

Accessible from **Workspace Settings → Export**.

#### Layout

```
┌──────────────────────────────────────────────────────┐
│  Export Knowledge Base                               │
│                                                      │
│  Scope:                                              │
│  ○ Full workspace                                    │
│  ○ User Manual                                       │
│  ○ Business Logic                                    │
│  ○ Functional Spec                                   │
│  ○ Custom filter                                     │
│    [+ Tag]  [+ Type]  [+ Node]  [+ Keyword]          │
│                                                      │
│  Format:  ☑ Markdown  ☑ Plain text  ☐ JSON only      │
│                                                      │
│  Options:                                            │
│  ☐ Include archived nodes                            │
│  ☐ Include source files  (admin only)                │
│                                                      │
│  Preview: ~42 nodes, ~87 edges                       │
│                                                      │
│  [Cancel]                        [Export Now →]      │
└──────────────────────────────────────────────────────┘
```

- The **Preview** count updates live as the user adjusts scope and filters.
- On "Export Now", a progress indicator is shown. When complete, the browser downloads the `.memtrace` archive automatically.
- Previous exports are listed with their scope, format, and download link (valid 1 hour after generation).

---

### 22.9 Scope Matching — Implementation Reference

Scope matching is implemented as a server-side SQL query. The following shows the filter composition for each built-in scope:

```sql
-- user-manual scope
WHERE workspace_id = :ws_id
  AND status = 'active'
  AND content_type != 'source_document'
  AND (
    tags && ARRAY['how-to','tutorial','guide','usage','onboarding','walkthrough']
    OR content_type = 'procedural'
  )

-- business-logic scope
WHERE workspace_id = :ws_id
  AND status = 'active'
  AND content_type != 'source_document'
  AND tags && ARRAY['rule','policy','constraint','decision','business-logic','domain']

-- functional-spec scope
WHERE workspace_id = :ws_id
  AND status = 'active'
  AND content_type != 'source_document'
  AND (
    tags && ARRAY['spec','feature','requirement','acceptance','behaviour','api']
    OR (content_type = 'factual' AND tags && ARRAY['spec','feature'])
  )
```

Custom filter primitives are composed as additional `AND` clauses over the base `workspace_id + status` predicate.

---

### 22.10 Phase Roadmap

| Phase | Scope | Formats | Notes |
|-------|-------|---------|-------|
| **1** | Full, user-manual, business-logic, functional-spec, custom | Markdown, plain text, JSON | Core export/import |
| **2** | All Phase 1 scopes + graph-aware clustering | + PDF, HTML | PDF includes graph snapshot |
| **3** | All Phase 2 + cross-workspace federated export | + CSV | Multi-workspace bundle export |

---

## 23. Knowledge Base Protection Mechanisms

### 23.1 Design Goals

The protection mechanisms defined in this section are designed to prevent **knowledge theft** — the systematic unauthorized extraction of node content from a Knowledge Base — while preserving legitimate usability for authorized members and approved previews.

Three attack surfaces are addressed:

| Attack Surface | Threat | Mitigation |
|----------------|--------|-----------|
| **Graph Preview API** | Non-member harvests node content by repeated calls to graph and node endpoints | Server-side data stripping; opaque non-stable preview IDs; `Cache-Control: no-store` |
| **Bulk enumeration** | Authenticated non-member or approved member calls node list API repeatedly to extract all content | Per-user, per-workspace rate limits; pagination caps; traversal logging |
| **Credential sharing / API key leak** | API key is shared or leaked, allowing a third party to access the workspace | Key prefix masking; key rotation; per-key scope enforcement; last-used auditing |

---

### 23.2 Graph Preview Protection (`conditional_public`)

This section expands on §12.8 with detailed enforcement rules.

#### 23.2.1 What Is and Is Not Transmitted

| Data Field | Non-member (preview) | Approved member |
|------------|---------------------|-----------------|
| Node position (`x`, `y`) | ✓ Transmitted | ✓ Transmitted |
| Edge connectivity (`from`, `to`) | ✓ Transmitted | ✓ Transmitted |
| Relation type (`depends_on`, etc.) | ✓ Transmitted | ✓ Transmitted |
| `content_type` badge | ✓ Transmitted | ✓ Transmitted |
| Node title (zh / en) | ✗ Omitted | ✓ Transmitted |
| Node body (zh / en) | ✗ Omitted | ✓ Transmitted |
| Tags | ✗ Omitted | ✓ Transmitted |
| Real node `id` | ✗ Replaced with opaque preview ID | ✓ Transmitted |
| `trust_score`, `author`, `signature` | ✗ Omitted | ✓ Transmitted |
| `source_paragraph_ref` | ✗ Omitted | ✓ Transmitted |
| Embedding vector | ✗ Never transmitted to any client | ✗ Never transmitted |

#### 23.2.2 Opaque Preview ID Non-Stability

Preview IDs (`node_preview_N`) are generated **per-request** using a deterministic but session-keyed hash:

```python
preview_id = hmac_sha256(
    key  = SESSION_PREVIEW_SECRET + request.session_id,
    data = real_node_id
)[:12]  # truncated to 12 hex chars
```

- The same real node ID maps to a **different** preview ID in every new session.
- A non-member cannot build a stable mapping between preview IDs and real node IDs across sessions.
- `SESSION_PREVIEW_SECRET` is a server-side environment variable, never exposed.

#### 23.2.3 Node Detail Endpoint Protection

When a non-member (or unauthenticated user) calls any node-level endpoint on a `conditional_public` workspace:

| Endpoint | Non-member response |
|----------|---------------------|
| `GET /workspaces/{ws_id}/nodes/{id}` | `HTTP 403 Forbidden` — node content not disclosed |
| `GET /workspaces/{ws_id}/nodes` (list) | `HTTP 403 Forbidden` — list not accessible to non-members |
| `GET /workspaces/{ws_id}/nodes/search` | `HTTP 403 Forbidden` — search not accessible to non-members |
| `GET /workspaces/{ws_id}/graph` | `HTTP 200` — stripped preview payload (§12.8) |
| `POST /workspaces/{ws_id}/chat` | `HTTP 403 Forbidden` — Q&A not accessible to non-members |

The `HTTP 403` responses include **no information disclosure** about whether the requested node ID exists. The response body is always:
```json
{ "detail": "Access denied. Join this Knowledge Base to view node content." }
```

---

### 23.3 Rate Limiting & Bulk Enumeration Prevention

Rate limits are applied at three levels: **global** (per IP), **user** (per authenticated account), and **workspace** (per workspace per user).

#### 23.3.1 Rate Limit Table

| Endpoint Group | Limit | Window | Scope | Consequence |
|----------------|-------|--------|-------|-------------|
| Graph preview (`/graph?preview=true`) | 30 requests | 1 minute | Per IP + per workspace | `429 Too Many Requests` |
| Node read (`GET /nodes/{id}`) | 120 requests | 1 minute | Per user per workspace | `429` |
| Node list (`GET /nodes`) | 20 requests | 1 minute | Per user per workspace | `429` |
| Search | 30 requests | 1 minute | Per user per workspace | `429` |
| Join request submission | 3 requests | 1 hour | Per user per workspace | `429` |
| Export job creation | 5 requests | 1 hour | Per user per workspace | `429` |
| API key creation | 10 requests | 1 day | Per user | `429` |

Rate limit state is tracked in Redis (or a DB-backed counter for Phase 1). `Retry-After` header is set on all `429` responses.

#### 23.3.2 Traversal Anomaly Detection

High-volume traversal activity (e.g. automated scraping via memtrace SDK or MCP) is detected by comparing a user's traversal rate against their workspace baseline:

- If a user or API key records more than **500 node traversals in any 10-minute window** within the same workspace, the server transitions the key/session into a **soft-throttle** state: responses are still served but with a 1-second artificial delay per call.
- If traversal rate exceeds **2000 in 10 minutes**, the key/session is **suspended for 1 hour** and the workspace admin is notified.
- Thresholds are configurable via workspace settings (admin only).

---

### 23.4 Workspace-Level Access Audit Log

All read and write accesses to a `conditional_public` or `restricted` workspace are logged in a dedicated audit table to support admin review and threat detection.

```sql
CREATE TABLE ws_access_log (
  id              TEXT PRIMARY KEY,
  workspace_id    TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  actor_id        TEXT,                  -- NULL for unauthenticated requests
  actor_type      TEXT NOT NULL          -- 'user' | 'api_key' | 'anonymous'
                  CHECK (actor_type IN ('user','api_key','anonymous')),
  endpoint        TEXT NOT NULL,         -- e.g. '/api/v1/workspaces/ws_abc/nodes'
  method          TEXT NOT NULL,         -- GET | POST | PATCH | DELETE
  preview_mode    BOOLEAN NOT NULL DEFAULT false,
  status_code     INTEGER NOT NULL,
  ip_address      INET,
  user_agent      TEXT,
  accessed_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_ws_access_ws   ON ws_access_log (workspace_id, accessed_at DESC);
CREATE INDEX idx_ws_access_actor ON ws_access_log (actor_id, accessed_at DESC);
```

**Retention:** Audit logs are retained for **90 days** then purged.

**Admin access:** Workspace admins may query their own workspace's audit log via:

```
GET /api/v1/workspaces/{ws_id}/audit-log
  ?from=<ISO date>
  &to=<ISO date>
  &actor_type=anonymous|user|api_key
  &preview_mode=true|false
```

This allows admins to identify suspicious patterns (e.g. high anonymous preview traffic, failed node access attempts) and take action such as disabling public discovery or issuing an alert.

---

### 23.5 API Key Protection

API keys (§14.2) are subject to additional protection measures to prevent credential leakage from becoming a knowledge theft vector.

#### 23.5.1 Key Masking

- The full key value is shown **exactly once** at creation, then never again.
- Only a **prefix** (`mt_live_xxxx`) is stored server-side as a hashed value (`bcrypt` or `SHA-256`).
- The admin UI shows only the prefix for identification.

#### 23.5.2 Key Scope Enforcement

| Key Scope | Max nodes readable per request | List pagination cap |
|-----------|-------------------------------|---------------------|
| `kb:read` (viewer) | 1 per call | 50 per page, no cursor-less bulk fetch |
| `kb:propose` (contributor) | 1 per call | 50 per page |
| `kb:write` (admin) | 1 per call | 100 per page |

A single API call cannot retrieve all nodes in a workspace in bulk. Clients must paginate. This limits the blast radius of a compromised key.

#### 23.5.3 Key Rotation

- Any admin may rotate an API key at any time: the old key is immediately invalidated and a new one is issued.
- If a key has not been used in **90 days**, it is automatically **expired** and the owner is notified.
- Key expiry can be configured per key at creation time (options: 30d, 90d, 1y, never).

#### 23.5.4 Suspicious Activity on Keys

If a key triggers the traversal anomaly thresholds (§23.3.2), it is suspended and the workspace owner is notified via email with:
- Key prefix
- Timestamp of suspension
- Traversal count that triggered the threshold
- Last-known IP and user agent

---

### 23.6 Content Fingerprinting (Future — Phase 2+)

> **Not in scope for Phase 1.** Documented here as a planned protection layer.

To detect if exported or preview-accessed content has been re-published without authorization, MemTrace may introduce **content fingerprinting**:

- Each node body is embedded with an invisible watermark (zero-width Unicode characters or whitespace steganography) that encodes the workspace ID, the requesting user ID, and a timestamp.
- If watermarked content is detected in another system, the workspace admin can submit it to MemTrace for attribution analysis.
- This does not prevent theft but provides forensic evidence for attribution.

---

### 23.7 Summary of Protection Layers by Tier

| Protection Layer | `public` | `conditional_public` | `restricted` | `private` |
|-----------------|---------|---------------------|-------------|----------|
| Graph topology visible to non-members | ✓ | ✓ (preview only) | ✗ | ✗ |
| Node content to non-members | ✓ | ✗ | ✗ | ✗ |
| Real node IDs to non-members | ✓ | ✗ (opaque) | ✗ | ✗ |
| Rate limiting on preview | ✓ | ✓ | N/A | N/A |
| Access audit log | — | ✓ | ✓ | — |
| Traversal anomaly detection | ✓ | ✓ | ✓ | ✓ |
| API key scope enforcement | ✓ | ✓ | ✓ | ✓ |
| Content fingerprinting | Phase 2+ | Phase 2+ | Phase 2+ | — |

## 24. Active Q&A Archiving

### 24.1 Overview
Every interaction with the AI Chat assistant is a potential knowledge asset. Active Q&A Archiving ensures that these interactions are not lost but instead captured as structured Memory Nodes.

### 24.2 Mechanism
1. **Inquiry Capture**: The user's query is converted into a **Context (����)** node, capturing the intent and scenario of the inquiry.
2. **Answer Distillation**: The AI's response is distilled into a **Factual, Procedural, or Preference** node based on its content.
3. **Semantic Linking**: An edge is established between the Question (Context) and the Answer (Content), and the Answer is further linked to the source nodes used for its generation.

### 24.3 Categorization Rule
- **Question** -> Content Type: \context\ (Captures the 'Why' and 'What' of the search).
- **Answer** -> Content Type: \actual\ | \procedural\ | \preference\ (Determined by AI logic).

### 24.4 Value Proposition
- **Knowledge Gap Identification**: Unanswered or frequently asked questions signal missing or high-value areas in the KB.
- **Accelerated Retrieval**: Subsequent similar queries can be resolved by retrieving the existing Q-A node pair directly via vector similarity.


### 24.5 Reinforcement & Decay of Q&A Assets

To minimize manual curation, MemTrace applies a dynamic weighting system to Q&A nodes:

- **Auto-Promotion**: If a proposed Q&A pair receives positive feedback (explicitly via UI or implicitly via reuse), it is promoted to \ctive\ status automatically, bypassing the Review Queue.
- **Weight Reinforcement**: Every time a Question node is successfully used to resolve a query, its edge to the Answer node receives a boost (\weight += 0.2\).
- **Rapid Decay**: If an Answer node is flagged as unhelpful or a follow-up query indicates the answer was insufficient, the edge weight decreases (\weight -= 0.3\).
- **Knowledge Gap Discovery**: When a Q-A edge weight drops below \min_weight\, the edge fades, and the Question node is flagged as a 'Gap', triggering the AI to seek new connections or generate a fresh answer from updated context.



---

## 25. Workspace Management Operations

### 25.1 Workspace Purge (Clear)

In scenarios where a workspace is contaminated by incorrect data ingestion or human error, a destructive "Purge" operation is available to reset the knowledge state without deleting the workspace identity or membership settings.

#### 25.1.1 Operation Scope
- **Deletes**: All `memory_nodes` associated with the workspace.
- **Deletes**: All `edges` associated with the workspace.
- **Deletes**: All `node_revisions` and `review_queue` items.
- **Deletes**: All `ingest_jobs` records associated with the workspace (ingestion history is also reset).
- **Retains**: Workspace metadata (name, visibility, type), owner, members, and associations.

#### 25.1.2 Security
- Only the **Workspace Owner** (Admin role) can initiate a purge.
- This operation is **irreversible**. The UI **must** implement a "Double Confirmation" pattern: first prompt asks "Are you sure?", second prompt requires the user to type the workspace name to confirm.

#### 25.1.3 API
```
DELETE /api/v1/workspaces/{ws_id}/purge
Response: { deleted_nodes_count: int, deleted_edges_count: int }
```

---

## 16 Extensions — Visualization Updates

> This block extends §16 (AI Features) with later visualization additions. Subsection numbers continue from §16's existing range.

### 16.4 Table View

In addition to 2D and 3D Graph visualizations, MemTrace provides a **Table View** for structured data auditing and bulk review. The Table View is accessible as a third mode in the Graph toolbar (alongside 2D and 3D toggles).

#### 16.4.1 Columns

| Column | Source Field | Sortable |
|--------|-------------|----------|
| Title | `title_zh` / `title_en` (language-aware) | ✓ |
| Content Type | `content_type` | ✓ |
| Tags | `tags[]` | — |
| Trust Score | `trust_score` (0.00–1.00, progress bar) | ✓ |
| Created | `created_at` | ✓ |
| Actions | Edit / Archive buttons | — |

#### 16.4.2 Pagination & Search
- Default page size: 50 rows. Selectable: 25 / 50 / 100.
- Search bar filters across `title_zh`, `title_en`, `body_zh`, `body_en`.
- `source_document` nodes are excluded from the table (they appear in Ingestion History instead).

#### 16.4.3 Bulk Actions
- **Select All** checkbox selects all rows on the current page.
- Bulk Archive: archives all selected nodes.
- Bulk Delete (Admin only): permanently deletes selected nodes and their edges.

#### 16.4.4 API
```
GET /api/v1/workspaces/{ws_id}/table-view?q=&limit=50&offset=0
Response: { nodes: NodeResponse[], total_count: int }
```

---

## 26. Health Mode Visualization

Health Mode is an overlay on the Knowledge Graph that colors each node according to its computed health score, helping admins identify stale or disconnected knowledge.

### 26.1 Health Score Algorithm

#### Evergreen Workspaces (`kb_type = "evergreen"`)
- Score is proportional to active edge count: `min(1.0, edge_count / 5)`
- A node with 5 or more edges is considered fully healthy.

#### Ephemeral Workspaces (`kb_type = "ephemeral"`)
- Score decays with time since last traversal: `max(0.0, 1.0 - days_since / 180)`
- A node that has never been traversed starts at 0.

### 26.2 Health Labels

| Score Range | Label | Color |
|-------------|-------|-------|
| 0.6 – 1.0 | `healthy` | Green `#22c55e` |
| 0.3 – 0.59 | `warning` | Yellow `#eab308` |
| 0.0 – 0.29 | `critical` | Red `#ef4444` |

### 26.3 Visual Behavior
- **2D Graph**: Node border and background tint change to health color. Tooltip shows score percentage and reason on hover.
- **3D Graph**: Node sphere color changes to health color.
- Health Mode does not affect edge visibility or layout.

### 26.4 API
```
GET /api/v1/workspaces/{ws_id}/health-scores
Response: [{ node_id, score, label, reason }]
```

---

## 27. API-Based Document Ingestion

In addition to the UI-based ingestion form, MemTrace supports programmatic document ingestion via REST API. This enables CI/CD pipelines, scripts, and third-party tools to push knowledge into a workspace without human interaction.

### 27.1 Endpoint
```
POST /api/v1/workspaces/{ws_id}/ingest
Authorization: Bearer <workspace-api-key>  (scope: kb:write)
Content-Type: multipart/form-data

Fields:
  file       (optional) — binary file upload (PDF, Markdown, TXT, etc.)
  text       (optional) — raw text string (mutually exclusive with file)
  filename   (optional) — display name for the source document
```
Either `file` or `text` must be provided.

### 27.2 Response
```json
{
  "job_id": "job_xxx",
  "status": "queued",
  "message": "Ingestion started in background"
}
```

### 27.3 Status Polling
```
GET /api/v1/workspaces/{ws_id}/ingest/{job_id}
Response: { job_id, status, progress, chunks_total, chunks_done, error? }
```

---

## 28. Authentication Scope

### 28.1 Supported Authentication Methods

MemTrace supports **email + password** authentication only. This simplifies the auth surface, reduces external dependencies, and avoids consent-screen complexity for self-hosted deployments.

| Method | Status |
|--------|--------|
| Email + Password | ✅ Supported |

### 28.2 Password Reset Flow

1. User clicks "Forgot password?" on the login screen.
2. User enters their registered email address.
3. System sends a password reset link (valid for **1 hour**) via configured email provider (SMTP or Resend).
4. User clicks the link and enters a new password.
5. All existing sessions for that account are invalidated.
6. If no account exists for the given email, the response is identical (prevents email enumeration).

**UI Requirements:**
- "Forgot password?" link on login screen opens an inline form (email input + submit).
- Success state: "If an account exists for that email, a reset link has been sent."
- The reset link (`/auth/reset-password?token=xxx`) renders a dedicated page with new password + confirm password fields.

### 28.3 Email Provider Configuration
```env
EMAIL_PROVIDER=smtp         # or "resend"
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=no-reply@example.com
SMTP_PASS=xxxx
EMAIL_FROM=no-reply@example.com
RESEND_API_KEY=re_xxxx      # if using Resend
```

---

## 29. Workspace API Keys (Service Tokens)

Distinct from personal AI provider keys (for LLM calls), Workspace API Keys are **service-account tokens** scoped to a specific workspace and used for programmatic access — MCP tools, CI/CD pipelines, and API ingestion.

### 29.1 Ownership Model
- A Workspace API Key is owned by the workspace, created by an admin.
- It is **not tied to a specific user account**.
- Multiple keys may exist per workspace (e.g., one for MCP, one for CI).

### 29.2 Scopes

| Scope | Capabilities |
|-------|-------------|
| `kb:read` | Search, list nodes, traverse, Q&A chat |
| `kb:propose` | All read + submit proposals to review queue |
| `kb:write` | Full write access (create/edit/delete nodes and edges) |

### 29.3 Lifecycle
- Keys are created by admins via the Workspace Settings → API Keys panel.
- A key can be **rotated** (invalidates old key, issues new one with same name/scope).
- A key can be **revoked** (permanently invalidated).
- The raw key value is shown **once** on creation. It is stored as a bcrypt hash.

### 29.4 API
```
POST   /api/v1/workspaces/{ws_id}/api-keys        → create key
GET    /api/v1/workspaces/{ws_id}/api-keys        → list keys (no raw values)
POST   /api/v1/workspaces/{ws_id}/api-keys/{id}/rotate → rotate key
DELETE /api/v1/workspaces/{ws_id}/api-keys/{id}   → revoke key
```

---

## 30. Scheduled Local Backups

MemTrace includes a self-healing local backup system to prevent data loss in self-hosted environments. It performs regular database dumps and manages disk space by rotating old backups.

### 30.1 Backup Execution
- **Frequency:** System runs a background task every hour to check the backup schedule.
- **Interval:** The actual backup occurs based on the configured interval (default: 24 hours).
- **Format:** PostgreSQL dumps are compressed using `gzip` (output format: `.sql.gz`).
- **Naming:** `memtrace_backup_YYYYMMDD_HHMMSS.sql.gz`.

### 30.2 Rotation Policy
To prevent disk exhaustion, the system maintains a rolling window of backups:
- **Keep Count:** The number of recent backup files to retain (default: 7).
- **Cleanup:** On every successful backup, the system scans the backup directory and deletes the oldest files exceeding the keep count.

### 30.3 Configuration (Admin Only)
Backup settings are managed globally via the System Admin dashboard:
- **Backup Path:** Absolute path on the server where backups are stored.
- **Enable/Disable:** Toggle automated backups.
- **Interval (Hours):** How often to perform a backup.
- **Retention Count:** How many backups to keep.

### 30.4 Status and Monitoring
The system logs the result of each backup attempt in the `system_settings` table (key: `backup_config`):
- `last_backup_at`: ISO timestamp of the last attempt.
- `last_backup_status`: `success` or `failed`.
- `last_backup_file`: Path to the last successful backup file.
- `error_msg`: Detailed error if the last attempt failed.

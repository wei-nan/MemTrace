# MemTrace Specification

## 1. Introduction
MemTrace is an open platform for building shared knowledge through minimal, well-connected Memory Nodes. Its core design goal is to allow any human or AI agent to reach any answer by following the shortest possible path through a graph of small, typed relationships — rather than reading through large documents. This specification outlines all core components, including Memory Schema, Edge Schema, Trust mechanics, and the Decay engine.

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

### Design principles that follow from this

| Principle | Implication |
|-----------|-------------|
| **Nodes are minimal** | A node contains the smallest unit of knowledge that can stand alone. If a thought can be split without losing meaning, it should be. |
| **Relationships carry the knowledge** | The value of a Knowledge Base lies in its edges, not in the volume of its nodes. Two small nodes with a typed edge express more than one large node that conflates two ideas. |
| **Shortest path is the design goal** | Every structural decision — node granularity, edge type, content type — should be evaluated by whether it shortens the path a human or AI agent needs to follow to reach an answer. |
| **Entry point independence** | Any node can serve as an entry point. Navigation follows edges, not a fixed hierarchy. |
| **Value is earned** | Trust scores, traversal counts, and edge weights reflect real usage, not just authorship intent. |
| **Authorship is traceable but not gatekeeping** | Provenance is always recorded, but anyone with access can read, extend, or copy a node. |
| **Decay shapes attention, not existence** | No node or edge is permanently deleted by the decay engine alone. Faded content is archived, not destroyed. |

## 2. Terminology
- **Memory Node**: A discrete piece of knowledge, written bilingually (zh-TW and en) or unilaterally.
- **Edge**: A typed relationship connecting two Memory Nodes.
- **Co-Access**: An event where two connected memories are accessed sequentially or simultaneously in the same context.
- **Decay**: The natural reduction of edge weight over time if not co-accessed.
- **Archive**: The state a node or edge enters when it is no longer relevant to default views. Archived content is hidden but not destroyed and can be restored at any time.
- **Faded**: The state an edge enters when its weight drops below `min_weight` due to decay. A faded edge is archived automatically but can be restored.
- **Knowledge Base Type**: A workspace-level setting (`evergreen` or `ephemeral`) that governs how the decay engine treats nodes and edges in that workspace (see §7.3).
- **Knowledge Base Visibility**: The sharing level of a Knowledge Base, controlling who can discover and access it. Distinct from Memory Node visibility, which controls individual node access within a Knowledge Base.
- **Identity Provider (IdP)**: An external service that authenticates a user and returns a verified identity claim. Google is the supported IdP for OAuth login.
- **Session Token**: A short-lived signed token issued by MemTrace after successful authentication, used to authorize subsequent API requests.

## 3. Product User Flow
1. **Knowledge Base Creation**: A user can initialize multiple Knowledge Bases (Workspaces) with a chosen **type** (`evergreen` or `ephemeral`, see §7.3) and **sharing level** (`public`, `restricted`, or `private`). A Knowledge Base may be started blank or bootstrapped from a document (see §11.1). Sharing level can be changed by the owner at any time (see §12).
2. **Ingestion & Upload**: Users can input raw text, Markdown, or upload rich files (PDF, Word, video, meeting recordings). The AI Extraction pipeline applies the Node Minimization Principle (§11.3) to split source material into the smallest meaningful units and proposes typed edges between them. All candidates enter a Review Queue for human approval before committing (see §11.2).
3. **Relationship Mapping**: Edges are as important as nodes. After creating or accepting a node, users are expected to define its relationships — by drawing connections in the Graph View, using the Edge panel in the Node Editor, or accepting AI-proposed edges. A node with no edges is incomplete.
4. **Node Portability**: Any individual Memory Node can be copied to another Knowledge Base without carrying its Edges (see §11.3).
5. **Organic Decay**: Once established, the system takes over with the organic decay mechanism unless manually pinned.

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
- Decay half-life tracked individually per edge; default varies by workspace `kb_type` and node `content_type` (see §7.3).
- Edge status: `active` / `faded` / `pinned`. Faded edges are archived, not deleted.

## 5. Trust & Anti-Forgery
- Memories are digitally fingerprinted with SHA-256 hashes generated from the content.
- Community and AI votes update the trust scores continuously.

## 6. Operations
- `new`: Create a new Memory Node. Each node should capture exactly one idea — if the content spans multiple ideas, create multiple nodes and link them. Running `link` immediately after `new` is the expected workflow.
- `link`: Create a typed edge between two existing nodes. Edges are the primary carrier of knowledge in MemTrace; a node without edges is not yet a useful part of the graph.
- `ingest <file>`: Upload a document and trigger AI extraction to propose candidate Memory Nodes (see §11.2).
- `copy-node <node-id> --to <workspace-id>`: Copy a single Memory Node into another Knowledge Base; Edges are not copied (see §11.3).
- `push`: Sync local changes to a remote repository (e.g. GitHub).
- `pull`: Pull remote changes from GitHub or central index.
- `export`: Export memories matching standard JSON schema to local filesystem.
- `import`: Import previously exported memory JSON files into the hub.

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
Users must be able to export their current working memory to a local JSON file (conforming to `node.v1.json`) and import an existing JSON file directly into the editor for further modification or restoration.

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

| Provider | Identifier | Chat model (default) | Embedding model |
|----------|------------|----------------------|-----------------|
| OpenAI | `openai` | `gpt-4o-mini` | `text-embedding-3-small` |
| Anthropic | `anthropic` | `claude-haiku-4-5-20251001` | `voyage-3-lite` |

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

#### 11.2.4 Managed Credits

MemTrace may introduce a **managed credit model** as a future monetization path. Under this model:

- MemTrace proxies AI calls through its own backend so users no longer need to supply a personal API key.
- A free tier provides a monthly token allowance per account (currently 50 000 tokens/month).
- Paid tiers offer higher limits, priority throughput, or access to more capable models.

**Architectural requirement:** The AI call path is already abstracted behind the provider interface so switching between user-supplied keys and managed credits requires no changes to extraction or editor logic — only the credential resolution layer changes.

#### 11.2.3 Managed Credits (Future)

> **Future consideration — not in scope for Phase 1 or Phase 2.**

MemTrace may introduce a **managed credit model** as a future monetization path. Under this model:

- MemTrace proxies AI calls through its own backend, so users no longer need to supply a personal API key.
- A free tier provides a monthly credit allowance per account.
- Paid tiers offer higher credit limits, priority throughput, or access to more capable models.

**Architectural requirement (current phases):** The AI call path must be abstracted behind a provider interface so that switching between user-supplied keys and MemTrace-managed credits requires no changes to the extraction or editor logic — only the credential resolution layer changes.

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

### 12.1 Overview

Each Knowledge Base has a **visibility** setting that controls who can discover and access it. This is independent from the `visibility` field on individual Memory Nodes, which controls access at the node level within a Knowledge Base.

| Level | Identifier | Description |
|-------|------------|-------------|
| 全公開 | `public` | Discoverable and readable by anyone, including unauthenticated users. |
| 限定公開 | `restricted` | Not publicly discoverable. Accessible only to users who hold an explicit invite link or have been granted access by the owner. |
| 私人 | `private` | Visible only to the owner. Not discoverable or accessible by any other user. |

### 12.2 Behavior by Level

#### `public`
- Appears in global search and discovery feeds.
- Any user (authenticated or not) can read all nodes whose node-level `visibility` is `public`.
- Nodes with node-level `visibility: team` or `private` remain hidden from external viewers regardless of Knowledge Base visibility.
- Anyone can copy `public`-visibility nodes to their own Knowledge Base.

#### `restricted`
- Does not appear in global search or discovery feeds.
- Access is granted via **invite link** (time-limited, revocable) or by the owner adding specific users.
- Invited users can read all nodes whose node-level `visibility` is `public` or `team`.
- Node-level `private` nodes remain visible only to the owner.
- Copying nodes is allowed for users who have been granted access.

#### `private`
- Completely hidden from all other users.
- Only the owner can read, edit, or copy nodes.
- Does not appear in any search or listing.

### 12.3 Changing Visibility

- The owner can change the Knowledge Base visibility at any time from the workspace settings panel.
- **Downgrade (e.g. `public` → `private`)**: Previously accessible content becomes inaccessible immediately. Existing invite links are revoked.
- **Upgrade (e.g. `private` → `public`)**: Content becomes accessible according to the new level. No retroactive change to individual node-level visibility.
- Changing Knowledge Base visibility does **not** automatically change node-level `visibility` on any Memory Node.

### 12.4 Interaction with Node-Level Visibility

The effective access of a node is the **more restrictive** of the two levels:

| KB Visibility | Node Visibility | Effective Access |
|---------------|-----------------|-----------------|
| `public` | `public` | Anyone |
| `public` | `team` | Invited / granted users only |
| `public` | `private` | Owner only |
| `restricted` | `public` | Invited / granted users only |
| `restricted` | `team` | Invited / granted users only |
| `restricted` | `private` | Owner only |
| `private` | any | Owner only |

### 12.5 Schema — Knowledge Base Object

A Knowledge Base is represented as a workspace-level object (separate from `node.v1.json`):

```json
{
  "id": "ws_abc123",
  "schema_version": "1.0",
  "name": { "zh-TW": "...", "en": "..." },
  "visibility": "public | restricted | private",
  "kb_type": "evergreen | ephemeral",
  "owner": "<user-id>",
  "decay_config": {
    "archive_window_days": 90,
    "min_traversals": 1
  },
  "members": [
    { "user_id": "<user-id>", "role": "viewer | editor" }
  ],
  "invite_links": [
    {
      "token": "<uuid>",
      "role": "viewer | editor",
      "expires_at": "<date-time | null>"
    }
  ],
  "created_at": "<date-time>",
  "updated_at": "<date-time>"
}
```

- `kb_type` is set at creation and **cannot be changed** after the workspace is created.
- `decay_config` is only relevant for `evergreen` workspaces. For `ephemeral` workspaces, decay parameters are set per content type (see §7.3).
- `members` and `invite_links` are only relevant for `restricted` workspaces. For `public` workspaces, all authenticated users implicitly have `viewer` access.

## 10. Schema Extensions

### 10.1 Memory Node v1 — Additional Fields for Manual Editing

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
| **Google OAuth 2.0** | One-click sign-in via Google; no password stored in MemTrace |

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

### 13.3 Google OAuth 2.0 Login

#### 13.3.1 Flow

```
User clicks "Continue with Google"
        │
        ▼
MemTrace redirects to Google Authorization Endpoint
  (scope: openid, email, profile)
        │
        ▼
User grants consent on Google
        │
        ▼
Google redirects back to MemTrace callback URL
  with authorization code + state parameter
        │
        ▼
MemTrace backend exchanges code for ID token
  (via Google Token Endpoint, server-to-server)
        │
        ▼
MemTrace validates ID token signature (Google JWKS)
  and verifies: aud, iss, exp, email_verified
        │
        ▼
Account lookup / creation (see §13.3.2)
        │
        ▼
Session token issued → user logged in
```

#### 13.3.2 Account Matching

| Condition | Action |
|-----------|--------|
| Google `sub` matches an existing account | Log in; refresh `avatar_url` and `display_name` if changed. |
| Google email matches a password-registered account | Link the Google identity to the existing account; user is notified by email. |
| No match found | Create a new `User` record with `email_verified: true` (Google guarantees this); no password is set. |

#### 13.3.3 Configuration

The following must be configured in the server environment (not committed):

```
GOOGLE_CLIENT_ID=<from Google Cloud Console>
GOOGLE_CLIENT_SECRET=<from Google Cloud Console>
GOOGLE_REDIRECT_URI=https://<domain>/auth/google/callback
```

#### 13.3.4 Security Requirements

- **State parameter**: A cryptographically random value is generated per request, stored server-side, and verified on callback to prevent CSRF.
- **PKCE**: Not required for server-side flows but must be used for any future native/mobile client.
- **ID token validation**: Performed server-side only; the raw ID token is never forwarded to the frontend.
- **Redirect URI**: Exact-match only; no wildcard or open redirects.

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
  "auth_providers": ["password", "google"],
  "created_at": "<date-time>",
  "last_login_at": "<date-time>"
}
```

`auth_providers` lists all linked authentication methods. A user may have both `password` and `google` linked simultaneously.

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
| `GET` | `/auth/google` | Initiate Google OAuth flow |
| `GET` | `/auth/google/callback` | Google OAuth callback handler |
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
② Verify Email  ──── (skipped for Google OAuth users)
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
- "Continue with Google" — triggers OAuth flow (§13.3); on return, skip to step ③.
- "Sign up with Email" — collects display name, email, password. Validates inline against password policy (§13.2.2).

---

**② Verify Email** *(email+password path only)*

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
    [ ] Use Google OAuth (opens browser)

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
3. **Managed credits** (future, §11.2.3) — if neither is present and managed credits are enabled.
4. **Disabled** — if no key is available, the AI feature button is greyed out with a tooltip prompting the user to configure a provider in Settings.

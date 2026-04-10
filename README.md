# MemTrace

> Collaborative memory hub with knowledge graph, trust scoring, and decay — for teams and AI agents.

**MemTrace** is an open platform for capturing, connecting, and sharing knowledge across teams and AI tools.

The core idea is simple: knowledge does not need to live in large documents. It lives in small, focused **Memory Nodes** — each capturing one idea — connected by typed relationships that together form a living knowledge graph. The value is not in any single node, but in the network they form.

MemTrace is designed for **knowledge inheritance**: when someone new joins a project, or an AI agent enters an unfamiliar context, they can enter at any node and follow the edges to everything related — without needing the original author to guide them. Connections that prove useful strengthen over time; connections nobody follows fade away.

It works equally well for human-to-human, human-to-AI, and AI-to-AI knowledge sharing. Every contributor writes into the same graph.

→ Full specification: [docs/SPEC.md](docs/SPEC.md) · Developer setup: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)

---

## Core Concepts

**Memory Node** — A structured, bilingual (zh-TW / en) piece of knowledge with a content type, visibility, tags, trust score, and traversal counter.

**Knowledge Graph** — Nodes connect through typed Edges (`depends_on`, `extends`, `related_to`, `contradicts`). Co-accessed edges grow stronger; unused edges decay and eventually dissolve.

**Trust** — Each node carries a multi-dimensional score built from community votes, author reputation, and verification history. Content is SHA-256 hashed on creation to detect tampering.

**Decay** — Edge weight follows `w(t) = w₀ × 0.5 ^ (days_since_use / half_life)`. Co-access boosts weight by +0.10–0.30 depending on relation type.

**Traversal Tracking** — Every node and edge records how many times it has been visited and by how many distinct actors (users or agents).

---

## Feature Overview

| Area | Features |
|------|----------|
| **Nodes** | Manual create/edit, plain text or Markdown body, bilingual titles, content type, tags, visibility |
| **Graph** | Typed edges, weight decay, co-access boost, path ratings (1–5), traversal counts |
| **Knowledge Bases** | Multiple workspaces, three sharing levels (public / restricted / private), invite links |
| **AI Extraction** | Upload document → AI proposes candidate nodes → user review before commit |
| **AI Providers** | User-supplied API key (OpenAI / Anthropic); no key stored server-side |
| **Node Portability** | Copy individual nodes across Knowledge Bases; edges not copied |
| **Trust** | accuracy, freshness, utility, author\_rep dimensions; SHA-256 anti-forgery |
| **Auth** | Email + password registration with verification, Google OAuth 2.0 |
| **External API** | REST API with scoped API keys (`kb:read`, `kb:write`, `node:traverse`, `node:rate`) |
| **MCP Server** | AI agent integration via Model Context Protocol (stdio & HTTP+SSE) |
| **i18n** | Full UI in Traditional Chinese (zh-TW) and English |
| **Onboarding** | Guided web wizard and interactive `memtrace init` CLI flow |

---

## Architecture

```
┌──────────────────────────────────────────────┐
│            MemTrace Web App (React)          │
│  Graph View · Memory Editor · Onboarding     │
└────────────────────┬─────────────────────────┘
                     │ REST / MCP
┌────────────────────▼─────────────────────────┐
│           MemTrace API (FastAPI)             │
│  Auth · CRUD · Search · Decay · Ingest       │
└──────┬──────────────┬──────────────┬─────────┘
       │              │              │
  PostgreSQL 17   pgvector       MCP Server
  (metadata +    (embeddings)   (stdio / SSE)
   traversal)
```

### Package Layout

```
packages/
├── core/      TypeScript — schema validation, decay engine
├── api/       Python / FastAPI — REST backend
├── ui/        React / Vite — web app
├── cli/       TypeScript — memtrace CLI
└── ingest/    Document & AI extraction pipeline
```

---

## Repository Structure

```
memtrace/
├── docs/
│   ├── SPEC.md              Full specification
│   └── DEVELOPMENT.md       Developer setup guide
├── schema/
│   ├── node.v1.json         Memory Node JSON Schema
│   ├── edge.v1.json         Edge JSON Schema
│   └── sql/
│       └── 001_init.sql     PostgreSQL schema (auto-applied on first docker compose up)
├── packages/
│   ├── core/
│   ├── api/
│   ├── ui/
│   ├── cli/
│   └── ingest/
├── examples/
├── docker-compose.yml       PostgreSQL 17 + pgvector
├── .env.example             Environment variable template
└── package.json             npm workspaces root
```

---

## Quick Start

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for the full setup guide.

```bash
# 1. Clone and install
git clone https://github.com/your-org/memtrace.git
cd memtrace
cp .env.example .env          # fill in credentials
npm install

# 2. Start the database
docker compose up -d

# 3. Start the API
cd packages/api
python -m uvicorn main:app --reload

# 4. Start the UI (new terminal)
cd packages/ui
npm run dev
```

---

## Roadmap

### Phase 1 — Foundation (CLI + Core)
- [x] Memory Node + Edge JSON Schema with validation
- [x] Decay engine (`packages/core/src/decay.ts`)
- [ ] CLI: `memtrace init`, `new`, `link`, `ingest`, `push`, `pull`, `copy-node`
- [ ] Local store (`~/.memtrace/`)
- [ ] `memtrace init` onboarding wizard

### Phase 2 — API & UI
- [x] PostgreSQL 17 + pgvector — schema, Docker, SQL decay functions
- [x] React UI scaffold with i18n (zh-TW / en)
- [x] Graph visualisation (ReactFlow + 3D force graph)
- [ ] Auth — email + password, Google OAuth
- [ ] REST API (CRUD, search, decay, traversal, rating)
- [ ] Memory editor (plain text + Markdown, live preview)
- [ ] Knowledge Base sharing (public / restricted / private)
- [ ] API key management
- [ ] Onboarding wizard (web)

### Phase 3 — AI & Ingestion
- [ ] Document ingestion (Markdown, PDF, Word)
- [ ] AI-driven node extraction with Review Queue
- [ ] User-supplied AI provider API key (OpenAI / Anthropic)
- [ ] Managed credit model (future)

### Phase 4 — MCP & Federation
- [ ] MCP server (stdio + HTTP+SSE)
- [ ] `traverse_edge` and `rate_path` tools for AI agents
- [ ] Cross-workspace node copy
- [ ] Subscribe to remote Knowledge Bases

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

*MemTrace — Because knowledge should outlive the conversation.*

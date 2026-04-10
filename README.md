# MemTrace

> Collaborative memory hub with knowledge graph, trust scoring, and decay — for teams and AI agents.

**MemTrace** is an open platform for capturing, connecting, and sharing knowledge memories across teams and AI tools. Memories are structured nodes in a living knowledge graph — links between them strengthen with use and fade when neglected, mirroring how human memory actually works.

---

## ✨ Core Concepts

### Memory Nodes
Every piece of knowledge is a **Memory** — a structured, bilingual (zh-TW / en) record with a type, visibility, tags, and a trust score.

### Knowledge Graph
Memories connect to each other through typed **Edges**. The more two memories are accessed together, the stronger their link. Links that go unused decay over time and eventually dissolve.

### Trust & Anti-Forgery
Each memory carries a multi-dimensional **trust score** built from community votes, author reputation, and verification history. Content is hashed on creation to detect tampering.

### Public + Private
Memories can be `public`, `team`, or `private`. Public memories can be forked, subscribed to, and contributed back — similar to GitHub repositories.

### Local-first + Remote Sync
MemTrace works offline. You own your data. Remote hubs (including GitHub-backed ones) are opt-in for sharing and discovery.

---

## 🧠 Memory Schema

```yaml
id: mem_abc123
schema_version: "1.0"

title:
  zh-TW: "GKE 排程縮放模式"
  en: "GKE Scheduled Scaling Pattern"

content:
  type: procedural        # factual | procedural | preference | context
  body:
    zh-TW: "使用 bitnami/kubectl CronJob，上班時間擴容，下班後縮容。"
    en: "Use bitnami/kubectl CronJob to scale up during business hours and down after."

tags: [gcp, kubernetes, gke]
visibility: public         # public | team | private

provenance:
  author: "wilian0104"
  created_at: "2026-04-10T10:00:00Z"
  signature: "sha256:abc..."
  source_type: human       # human | ai_generated | ai_verified

trust:
  score: 0.87
  dimensions:
    accuracy: 0.90
    freshness: 0.85
    utility: 0.88
    author_rep: 0.85
  votes:
    up: 24
    down: 2
    verifications: 8
```

---

## 🔗 Edge & Decay Schema

```yaml
id: edge_xyz789
from: mem_abc123
to: mem_def456
relation: depends_on       # depends_on | extends | related_to | contradicts

weight: 0.82               # 0.0 ~ 1.0
co_access_count: 14
last_co_accessed: "2026-04-09T00:00:00Z"

decay:
  half_life_days: 30       # weight halves every 30 days without co-access
  min_weight: 0.1          # auto-removed below this threshold
```

**Decay formula:**
```
weight(t) = w₀ × 0.5 ^ (days_since_use / half_life)
```
Each co-access boosts weight by `+0.1 ~ +0.3` depending on relation type.

---

## 📥 Memory Ingestion

MemTrace accepts memories from multiple sources:

| Source | Processing |
|--------|-----------|
| 📄 Document (PDF, Word, txt) | Text extraction → AI summarisation |
| 🖼 Image / Screenshot | Vision OCR + understanding |
| 🎥 Video / Meeting recording | Speech-to-text → structured summary |
| 🎙 Audio | Whisper transcription → summary |
| 💬 Chat / conversation | Paste or pipe directly |

All ingested content goes through an **AI-assisted review flow** before entering the memory store — the user confirms, edits, or splits the AI-generated draft before it is committed.

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────┐
│              MemTrace Web App               │
│  Knowledge Graph UI · Memory Editor · Chat  │
└────────────────────┬────────────────────────┘
                     │
┌────────────────────▼────────────────────────┐
│              MemTrace API (FastAPI)          │
│  CRUD · Search · Vote · Decay · Ingest      │
└──────┬─────────────┬───────────────┬────────┘
       │             │               │
  PostgreSQL      pgvector        GitHub
  (metadata)    (embeddings)    (public hub)
```

### Packages (planned)

```
packages/
├── core/        # Schema, validation, decay engine (TypeScript)
├── api/         # FastAPI backend
├── ui/          # React web app (knowledge graph + editor)
├── cli/         # mem push / pull / fetch / verify
└── ingest/      # Document, image, video processing pipeline
```

---

## 🔐 Trust & Anti-Forgery

| Mechanism | Description |
|-----------|-------------|
| Content Hash | SHA-256 of body on creation — detects tampering |
| Author DID | Bound to GitHub identity |
| Immutable History | Git-backed — every change is auditable |
| Community Votes | accuracy / freshness / utility dimensions |
| Author Reputation | Score degrades if published memories are flagged |
| Fork Lineage | Forked memories trace back to original source |

Low-trust memories (`score < 0.3`) are flagged ⚠️. Memories below `0.1` are removed from the public index.

---

## 🗺 Roadmap

### Phase 1 — Foundation
- [x] Memory Node + Edge JSON Schema with validation
- [x] Decay engine (`packages/core/src/decay.ts`)
- [ ] CLI: `mem new`, `mem list`, `mem link`, `mem push`, `mem pull`
- [ ] Local store (`~/.memtrace/`)
- [ ] GitHub-backed public hub

### Phase 2 — API & UI
- [x] PostgreSQL 17 + pgvector — DB schema, Docker setup, SQL decay functions
- [ ] FastAPI backend (CRUD, search, vote, decay engine)
- [ ] Multi-Language UI (i18n for `zh-TW` & `en`)
- [ ] Knowledge graph visualisation (D3 / force-directed)
- [ ] Memory detail panel with trust dimensions
- [ ] Team workspaces

### Phase 3 — Ingestion
- [ ] Document ingestion (PDF, Word)
- [ ] Image / screenshot OCR
- [ ] Audio / video transcription pipeline
- [ ] AI-assisted review & confirmation flow

### Phase 4 — Federation
- [ ] Subscribe to remote memory collections
- [ ] Cross-hub search
- [ ] MCP server for AI agent integration

---

## 🚀 Getting Started

> Work in progress. See [SPEC.md](docs/SPEC.md) for full specification.

```bash
# Coming soon
npm install -g @memtrace/cli
mem init
mem new
```

---

## 📁 Repository Structure

```
memtrace/
├── docs/
│   └── SPEC.md              # Full specification
├── schema/
│   ├── node.v1.json         # Memory Node JSON Schema
│   ├── edge.v1.json         # Edge JSON Schema
│   └── sql/
│       └── 001_init.sql     # PostgreSQL schema (auto-applied on docker compose up)
├── packages/
│   ├── core/                # Schema validation + decay engine (TypeScript)
│   ├── api/                 # FastAPI backend
│   ├── ui/                  # React web app
│   ├── cli/                 # CLI tool
│   └── ingest/              # Ingestion pipeline
├── examples/
│   └── sample-collection/
├── docker-compose.yml       # PostgreSQL 17 + pgvector
├── .env.example             # Environment variable template
└── .github/
    └── workflows/
        ├── validate.yml     # Schema validation on PR
        └── decay.yml        # Weekly decay calculation
```

---

## 🤝 Contributing

MemTrace is designed to be open and federated. Contributions to the schema, core engine, and documentation are welcome.

1. Fork the repo
2. Create a feature branch
3. Open a PR with a clear description of the change

Public memory contributions follow the same trust model — community verification builds confidence over time.

---

## 📄 License

MIT — see [LICENSE](LICENSE) for details.

---

*MemTrace — Because knowledge should outlive the conversation.*

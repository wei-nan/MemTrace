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
| **MCP Server** | Native integration via Python API (SSE & Streamable HTTP) |
| **OpenAI API** | OpenAI-compatible endpoint mapping `/v1/chat/completions` to hybrid RAG, with SSE streaming, sources, and system overrides |
| **Python SDK** | Official client SDK (`memtrace`) for sync & async workspace, node, and chat operations |
| **LangChain** | LCEL-compatible `MemTraceRetriever` for simple integration with AI workflows |
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
│  Auth · CRUD · Search · Decay · Ingest · MCP │
└──────┬──────────────┬──────────────┬─────────┘
       │              │              │
  PostgreSQL 17   pgvector     Modern Clients
  (metadata +    (embeddings)   (SSE / Streamable HTTP)
   traversal)
```

### Package Layout

```
packages/
├── core/               TypeScript — schema validation, decay engine
├── api/                Python / FastAPI — REST backend + Native MCP + OpenAI API
├── ui/                 React / Vite — web app
├── cli/                TypeScript — memtrace CLI
├── ingest/             Document & AI extraction pipeline
├── sdk-python/         Python — official client SDK
└── langchain-memtrace/ Python — LangChain retriever integration
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
│   ├── ingest/
│   ├── sdk-python/
│   └── langchain-memtrace/
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

# 3. Seed the spec knowledge base
cd packages/api
python ../../scripts/seed_spec_kb.py

# 4. Start the API
python -m uvicorn main:app --reload

# 5. Start the UI (new terminal)
cd packages/ui
npm run dev
```

---

## MCP Integration

MemTrace exposes its knowledge base to AI coding tools via the **Model Context Protocol (MCP)**. Once connected, your AI assistant can search, read, create, and update knowledge graph nodes directly — without reading raw spec documents.

### Available Tools

#### Read
| Tool | Description |
|------|-------------|
| `list_workspaces` | List all accessible workspaces |
| `search_nodes` | Keyword search across all nodes (title + body) |
| `get_node` | Retrieve a specific node by ID |
| `traverse` | Walk the graph from a node up to N hops |
| `traverse_edge` | Follow a specific edge to its target node |
| `list_by_tag` | List all nodes matching a tag |
| `list_empty_nodes` | Find nodes missing body content |
| `list_review_queue` | List nodes pending review |
| `get_schema` | Retrieve workspace schema and field specs |

#### Write
| Tool | Description |
|------|-------------|
| `create_node` | Add a new memory node |
| `update_node` | Edit an existing node's fields |
| `delete_node` | Remove a node (and its edges) |
| `create_edge` | Connect two nodes with a typed relationship |
| `vote_trust` | Cast a trust vote on a node |
| `confirm_node_validity` | Mark a node as verified |

> All node tools accept an optional `workspace_id` parameter. If omitted, they use the `MEMTRACE_WS` default.

> Write tools require a token with `kb:write` scope. `vote_trust` and `confirm_node_validity` require `node:rate`.

---

---

### Connection Methods

The MCP server is now natively integrated into the Python API. All access uses per-user `mt_` API keys via port **8000**.

#### 1. Streamable HTTP (Recommended)
Single POST endpoint used by **Cursor**, **Antigravity**, and other modern clients.
- **URL**: `https://<your-host>:8000/mcp`
- **Auth**: `Authorization: Bearer mt_<your_api_key>`

#### 2. SSE (Standard)
Server-Sent Events transport used by **Claude Desktop**.
- **URL**: `https://<your-host>:8000/sse`
- **Auth**: `Authorization: Bearer mt_<your_api_key>`

---

### Setup Instructions

#### Claude Desktop
Add this to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "memtrace": {
      "type": "sse",
      "url": "http://localhost:8000/sse",
      "headers": {
        "Authorization": "Bearer mt_<your_api_token>"
      }
    }
  }
}
```

#### Cursor / Antigravity
Add a new MCP server with type **HTTP**:
- **URL**: `http://localhost:8000/mcp`
- **Headers**: `{"Authorization": "Bearer mt_<your_api_token>"}`

---

### Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `Connection refused` | API not running | Check `docker compose ps`; ensure port 8000 is open |
| `401 Unauthorized` | Invalid token | Confirm token starts with `mt_` and has `kb:read` scope |
| `404 Not Found` | Wrong endpoint | Use `/mcp` for Cursor or `/sse` for Claude Desktop |

---

## Ecosystem Integration

MemTrace provides native integrations with the broader AI ecosystem, making it easy to use your knowledge graph in standard LLM applications.

### 1. OpenAI-Compatible API
The backend exposes standard OpenAI-compatible endpoints under `/v1` using your `mt_` API Key. This allows you to connect tools like **Open WebUI**, **Continue.dev**, or any library using the standard `openai` Python SDK directly to MemTrace.

- **Base URL**: `http://localhost:8000/v1`
- **Auth**: `Bearer mt_<your_api_key>`
- **Models**: Maps workspaces to `memtrace-{workspace_id}`.
- **RAG Integration**: `/v1/chat/completions` automatically performs hybrid semantic search over the selected workspace, injecting relevant nodes into the model context before generating the response.
- **Source Citations**: Returns a top-level list of used nodes in `x_source_nodes` and appends inline source footnotes to the choice message. Supports full SSE streaming (`stream: true`).
- **Workspace Override**: You can dynamically select a workspace in the system instructions by including the text `workspace_id: ws_xxx`.

### 2. Python Client SDK
The official Python client SDK allows you to manage workspaces, create/search memory nodes, and perform chat/retrievals programmatically.

```bash
pip install -e packages/sdk-python
```

```python
from memtrace import MemTraceClient

client = MemTraceClient(base_url="http://localhost:8000", api_key="mt_xxx")

# List workspaces & search nodes
workspaces = client.list_workspaces()
nodes = client.search_nodes(workspace_id="ws_abc", query="how to configure auth")
```

### 3. LangChain Integration
Integrate MemTrace as a retriever into your LangChain Expression Language (LCEL) chains.

```bash
pip install -e packages/langchain-memtrace
```

```python
from langchain_memtrace import MemTraceRetriever

retriever = MemTraceRetriever(
    base_url="http://localhost:8000",
    api_key="mt_xxx",
    workspace_id="ws_abc",
    search_type="hybrid",
    k=5
)

# Use in chains
chain = retriever | llm
result = chain.invoke("query")
```

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

*MemTrace — Because knowledge should outlive the conversation.*

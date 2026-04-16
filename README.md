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

MemTrace exposes its knowledge base to AI coding tools via the **Model Context Protocol (MCP)**. Once connected, your AI assistant can search, read, and traverse the knowledge graph directly — without reading raw spec documents.

### Available Tools

| Tool | Description |
|------|-------------|
| `search_nodes` | Keyword search across all nodes (title + body) |
| `get_node` | Retrieve a specific node by ID |
| `traverse` | Walk the graph from a node up to N hops |
| `list_by_tag` | List all nodes matching a tag |

### Step 1 — Build the MCP Server

```bash
cd packages/mcp
npm install
npm run build        # output → packages/mcp/dist/index.js
```

### Step 2 — Start the API

The MCP server proxies requests to the MemTrace API. The API must be running before your AI tool connects.

```bash
cd packages/api
python -m uvicorn main:app --port 8000
```

### Step 3 — Configure Your Tool

All three tools use the same `mcpServers` JSON format. Adjust the env vars to point at your workspace.

| Env Var | Default | Description |
|---------|---------|-------------|
| `MEMTRACE_API` | `http://localhost:8000/api/v1` | API base URL |
| `MEMTRACE_WS` | `ws_spec0001` | Workspace ID to query |
| `MEMTRACE_LANG` | `zh-TW` | Response language (`zh-TW` or `en`) |

---

#### Claude Code

A project-level `.mcp.json` is already included in the repo root. Claude Code picks it up automatically when you open this project.

```json
// .mcp.json  (already committed)
{
  "mcpServers": {
    "memtrace-kb": {
      "command": "node",
      "args": ["packages/mcp/dist/index.js"],
      "env": {
        "MEMTRACE_API": "http://localhost:8000/api/v1",
        "MEMTRACE_WS": "ws_spec0001",
        "MEMTRACE_LANG": "zh-TW"
      }
    }
  }
}
```

To use a different workspace, edit `MEMTRACE_WS` in `.mcp.json`.  
To register globally (all projects), add the same block to `~/.claude/settings.json` under `"mcpServers"`.

---

#### Cursor

Create `.cursor/mcp.json` in the project root (project-scoped) or `~/.cursor/mcp.json` (global):

```json
{
  "mcpServers": {
    "memtrace-kb": {
      "command": "node",
      "args": ["/absolute/path/to/memtrace/packages/mcp/dist/index.js"],
      "env": {
        "MEMTRACE_API": "http://localhost:8000/api/v1",
        "MEMTRACE_WS": "ws_spec0001",
        "MEMTRACE_LANG": "zh-TW"
      }
    }
  }
}
```

> **Note:** Cursor requires **absolute paths** in `args`. Replace `/absolute/path/to/memtrace` with the actual path on your machine.

Then restart Cursor. Verify the server is active under **Cursor Settings → MCP**.

---

#### Antigravity (Google)

Add to the global config file:

- **macOS / Linux:** `~/.gemini/antigravity/mcp_config.json`
- **Windows:** `%USERPROFILE%\.gemini\antigravity\mcp_config.json`

```json
{
  "mcpServers": {
    "memtrace-kb": {
      "command": "node",
      "args": ["C:\\absolute\\path\\to\\memtrace\\packages\\mcp\\dist\\index.js"],
      "env": {
        "MEMTRACE_API": "http://localhost:8000/api/v1",
        "MEMTRACE_WS": "ws_spec0001",
        "MEMTRACE_LANG": "zh-TW"
      }
    }
  }
}
```

> **Note:** Antigravity requires absolute paths and does **not** support `${workspaceFolder}` variable substitution. Keep total enabled MCP tools under 50.

Restart Antigravity after saving. Confirm the server appears in **Settings → AI → MCP Servers**.

---

### Verifying the Connection

Once connected, ask your AI assistant:

```
What MCP tools are available from memtrace-kb?
```

You should see `search_nodes`, `get_node`, `traverse`, and `list_by_tag` listed.

Try a real query:

```
Use memtrace-kb to find the decay half-life for each node type.
```

The assistant should call `search_nodes` and return the answer from `mem_d002` without reading the full spec document.

---

### Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `ENOENT` or `command not found` | Wrong path in `args` | Use absolute path; verify `dist/index.js` exists |
| `Workspace not found` | Wrong `MEMTRACE_WS` | Run `seed_spec_kb.py` and confirm workspace ID |
| `Connection refused` | API not running | Start with `uvicorn main:app --port 8000` |
| Tools not listed | Server crashed on start | Check logs; run `node packages/mcp/dist/index.js` directly to see errors |

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

*MemTrace — Because knowledge should outlive the conversation.*

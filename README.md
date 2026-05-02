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

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MEMTRACE_API` | `http://localhost:8000/api/v1` | API base URL |
| `MEMTRACE_WS` | `ws_spec0001` | Default workspace ID |
| `MEMTRACE_LANG` | `zh-TW` | Response language (`zh-TW` or `en`) |
| `MEMTRACE_TOKEN` | (empty) | API key — required for private workspaces and all write tools |

---

### Setup A — Same Machine as MemTrace (Local)

Use this when your AI tool runs on the same machine as the MemTrace server.

**Step 1 — Build the MCP server**

```bash
cd packages/mcp
npm install
npm run build        # output → packages/mcp/dist/index.js
```

**Step 2 — Configure your tool**

#### Claude Code

A project-level `.mcp.json` is already included in the repo root. Claude Code picks it up automatically when you open this project.

```json
{
  "mcpServers": {
    "memtrace": {
      "command": "node",
      "args": ["packages/mcp/dist/index.js"],
      "env": {
        "MEMTRACE_API": "http://localhost:8000/api/v1",
        "MEMTRACE_WS": "ws_spec0001",
        "MEMTRACE_LANG": "zh-TW",
        "MEMTRACE_TOKEN": "<your_api_token>"
      }
    }
  }
}
```

To register globally across all projects, add the same block to `~/.claude/settings.json` under `"mcpServers"`.

#### Cursor (local)

Create `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "memtrace": {
      "command": "node",
      "args": ["/absolute/path/to/memtrace/packages/mcp/dist/index.js"],
      "env": {
        "MEMTRACE_API": "http://localhost:8000/api/v1",
        "MEMTRACE_WS": "ws_spec0001",
        "MEMTRACE_LANG": "zh-TW",
        "MEMTRACE_TOKEN": "<your_api_token>"
      }
    }
  }
}
```

> Cursor requires absolute paths in `args`.

#### Antigravity (Google)

Config file location:
- macOS / Linux: `~/.gemini/antigravity/mcp_config.json`
- Windows: `%USERPROFILE%\.gemini\antigravity\mcp_config.json`

```json
{
  "mcpServers": {
    "memtrace": {
      "command": "node",
      "args": ["/absolute/path/to/memtrace/packages/mcp/dist/index.js"],
      "env": {
        "MEMTRACE_API": "http://localhost:8000/api/v1",
        "MEMTRACE_WS": "ws_spec0001",
        "MEMTRACE_LANG": "zh-TW",
        "MEMTRACE_TOKEN": "<your_api_token>"
      }
    }
  }
}
```

> Antigravity does **not** support `${workspaceFolder}` variable substitution. Keep total enabled MCP tools under 50.

#### OpenClaw

Run once in a terminal (requires the MCP package to be built first):

```bash
openclaw mcp set memtrace '{
  "command": "node",
  "args": ["/absolute/path/to/memtrace/packages/mcp/dist/index.js"],
  "env": {
    "MEMTRACE_API": "http://localhost:8000/api/v1",
    "MEMTRACE_WS": "ws_spec0001",
    "MEMTRACE_LANG": "zh-TW",
    "MEMTRACE_TOKEN": "<your_api_token>"
  }
}'
```

Verify the server was registered:

```bash
openclaw mcp list
```

To remove it later: `openclaw mcp unset memtrace`

---

### Setup B — Remote Machine

Use this when your AI tool runs on a **different machine** from the MemTrace server. The MCP server runs locally on your machine and communicates with the remote MemTrace API over HTTPS. Each user authenticates with their own personal token — the server enforces their workspace permissions on every operation.

This setup works with any network configuration that makes the MemTrace API reachable from your machine: a VPN, a reverse proxy, a direct public URL, or a private overlay network.

**Step 1 — Ensure the API is reachable**

Confirm you can reach the MemTrace API from your machine:

```bash
curl https://<memtrace-host>/api/v1/health
# expected: {"status":"healthy"}
```

If the API is served on a non-standard port, include it: `https://<host>:<port>/api/v1`.

**Step 2 — Create your API token**

1. Open the MemTrace web UI and log in
2. Go to **Settings → API Keys** → **New Key**
3. Set the following scopes:

| Scope | Required for |
|-------|-------------|
| `kb:write` | create / update / delete nodes and edges |
| `node:traverse` | graph traversal tools |
| `node:rate` | trust votes and validity confirmation |

> Select `*` for full access to all tools.

4. Copy the generated `mt_...` token — it is shown only once.

**Step 3 — Install the MCP package** (requires Node.js 18+)

```bash
# Option A: install from the MemTrace server's package endpoint
npm install -g https://<memtrace-host>/mcp/download/memtrace-mcp-latest.tgz

# Option B: clone the repo and build locally
git clone <repo-url>
cd memtrace/packages/mcp && npm install && npm run build
```

**Step 4 — Configure your AI tool**

#### Cursor

Create or edit `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "memtrace": {
      "command": "memtrace-mcp",
      "env": {
        "MEMTRACE_API": "https://<memtrace-host>/api/v1",
        "MEMTRACE_WS": "<your_workspace_id>",
        "MEMTRACE_LANG": "zh-TW",
        "MEMTRACE_TOKEN": "mt_<your_personal_token>"
      }
    }
  }
}
```

Restart Cursor and verify the server is active under **Cursor Settings → MCP**.

#### Antigravity (Google) — remote

```json
{
  "mcpServers": {
    "memtrace": {
      "command": "memtrace-mcp",
      "env": {
        "MEMTRACE_API": "https://<memtrace-host>/api/v1",
        "MEMTRACE_WS": "<your_workspace_id>",
        "MEMTRACE_LANG": "zh-TW",
        "MEMTRACE_TOKEN": "mt_<your_personal_token>"
      }
    }
  }
}
```

#### OpenClaw — remote

```bash
openclaw mcp set memtrace '{
  "command": "memtrace-mcp",
  "env": {
    "MEMTRACE_API": "https://<memtrace-host>/api/v1",
    "MEMTRACE_WS": "<your_workspace_id>",
    "MEMTRACE_LANG": "zh-TW",
    "MEMTRACE_TOKEN": "mt_<your_personal_token>"
  }
}'
```

> **Security note:** The MCP protocol itself runs locally over stdio — no MCP port is exposed over the network. Only the MemTrace API calls travel over HTTPS. Your personal token determines exactly which workspaces and operations are accessible.

---

### Verifying the Connection

Once connected, ask your AI assistant:

```
What MCP tools are available from memtrace?
```

Try a real query:

```
Use memtrace to find the decay half-life for each node type.
```

The assistant should call `search_nodes` and return the answer without reading the full spec document.

---

### Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `ENOENT` / `command not found` | Wrong path or package not installed | Use absolute path; verify `dist/index.js` exists or reinstall the package |
| `Workspace not found` | Wrong `MEMTRACE_WS` | Confirm workspace ID via `list_workspaces` tool |
| `Connection refused` | API not running | Check `docker compose ps`; all containers should be healthy |
| `401 Unauthorized` | Missing or invalid token | Set `MEMTRACE_TOKEN` to a valid `mt_...` key from Settings → API Keys |
| `403 insufficient_scope` | Token missing required scope | Recreate the token with `kb:write`, `node:traverse`, `node:rate` scopes |
| `404 Invalid oauth error` | Client using wrong endpoint | Cursor (remote): use `command: memtrace-mcp`, not a URL |
| Tools not listed | MCP server crashed | Run `memtrace-mcp` in a terminal to see the error directly |

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

*MemTrace — Because knowledge should outlive the conversation.*

# MemTrace — Development Guide

This document covers everything needed to run, develop, and test the MemTrace monorepo locally.

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Node.js | 20 LTS or later | UI, CLI, core packages |
| npm | 10+ (bundled with Node 20) | Package management (workspaces) |
| Python | 3.11 or later | API package |
| Docker Desktop | Latest | PostgreSQL 17 + pgvector |
| Git | Any recent | Version control |

Optional but recommended:

| Tool | Purpose |
|------|---------|
| VS Code | Editor with TypeScript and Python support |
| `direnv` | Auto-load `.env` in shell |
| `httpie` or Postman | Manual API testing |

---

## 1. Initial Setup

### 1.1 Clone the Repository

```bash
git clone https://github.com/your-org/memtrace.git
cd memtrace
```

### 1.2 Environment Variables

```bash
cp .env.example .env
```

Open `.env` and fill in the required values:

```dotenv
# PostgreSQL
POSTGRES_DB=memtrace
POSTGRES_USER=memtrace
POSTGRES_PASSWORD=changeme
POSTGRES_PORT=5432

# API
DATABASE_URL=postgresql://memtrace:changeme@localhost:5432/memtrace
SECRET_KEY=replace-with-a-random-secret          # JWT signing key
```

### 1.3 Install Node Dependencies

From the repo root (installs all workspace packages in one step):

```bash
npm install
```

### 1.4 Set Up the Python Virtual Environment

```bash
cd packages/api
python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows (PowerShell)
venv\Scripts\Activate.ps1

pip install -r requirements.txt
cd ../..
```

---

## 2. Database

MemTrace uses PostgreSQL 17 with the pgvector extension, managed via Docker Compose.

### 2.1 Start the Database (Recommended)

```bash
docker compose up -d
```

On first run, Docker will:
1. Pull `pgvector/pgvector:pg17`.
2. Create the database with the credentials from `.env`.
3. Auto-execute every file under `schema/sql/` in numeric order — `001_init.sql` creates the core tables, `002_*.sql` through `023_*.sql` are sequential migrations, and `099_seed_spec_kb.sql` seeds the public spec-as-KB workspace.

**Migration convention:** new schema changes are added as a new numbered file (e.g. `024_<short_name>.sql`), never by editing existing files. The DB container applies them in order; `099_*` files are reserved for seed data and run last.

### 2.2 Manual Schema Initialization

If the database was already created or you need to re-run the initialization:

```bash
# Using Docker
docker exec -i memtrace-db psql -U memtrace -d memtrace < schema/sql/001_init.sql

# Using local psql (if installed)
psql -h localhost -U memtrace -d memtrace -f schema/sql/001_init.sql
```

### 2.3 SQLite Fallback (Alternative)

If you cannot run Docker or PostgreSQL, you can use SQLite for local development with limited functionality:

1. **Update `.env`**:
   ```dotenv
   DATABASE_URL=sqlite:///./memtrace.db
   ```
2. **Limitations**:
   - No vector embedding search (pgvector is not available in standard SQLite).
   - Some SQL functions (decay, traversing) may need to be implemented in the application layer or using a different SQL dialect.
   - **Note**: The current API is optimized for PostgreSQL. Switching to SQLite may require updates to `packages/api/core/database.py`.

### 2.4 Verify the Database is Ready

```bash
docker compose ps          # status should be "healthy"
docker compose logs db     # inspect startup logs
```


---

## 3. Running Each Package

### 3.1 API (`packages/api`) — FastAPI

```bash
cd packages/api
source venv/bin/activate   # or venv\Scripts\Activate.ps1 on Windows
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- API root: `http://localhost:8000`
- Interactive docs: `http://localhost:8000/docs` (Swagger UI)
- Health check: `http://localhost:8000/health`

### 3.2 UI (`packages/ui`) — React + Vite

```bash
cd packages/ui
npm run dev
```

- App: `http://localhost:5173`
- Hot module replacement is enabled by default.

To build for production:

```bash
npm run build       # outputs to packages/ui/dist/
npm run preview     # serves the built output locally
```

### 3.3 Core (`packages/core`) — TypeScript library

The core package provides schema validation and the decay engine. It is consumed by `cli` and (optionally) by the API.

```bash
cd packages/core
npm run build       # compiles TypeScript → dist/
```

To run in watch mode during development:

```bash
npx tsc --watch
```

### 3.4 CLI (`packages/cli`) — `memtrace` command

```bash
cd packages/cli
npm run build

# Run locally without global install
node dist/index.js --help

# Or link globally for development
npm link
memtrace --help
```

---

## 4. Running Everything Together

Open four terminal tabs:

| Tab | Command |
|-----|---------|
| DB | `docker compose up` |
| API | `cd packages/api && uvicorn main:app --reload` |
| UI | `cd packages/ui && npm run dev` |
| Core (watch) | `cd packages/core && npx tsc --watch` |

### 4.1 API Testing

We use `pytest` for backend testing. Tests are located in `packages/api/tests/`.

**Run all tests:**

```bash
cd packages/api
./venv/bin/python3 -m pytest tests/ -v
```

**Testing strategy:**
- **Unit Tests**: Most tests use `unittest.mock` to bypass the real database, allowing them to run instantly without a live Postgres instance.
- **CSRF Bypass**: During tests, the `CsrfMiddleware` is configured to skip checks if `settings.app_env == "test"` or when running under `pytest`.

---

## 5. Project Structure (detailed)

```
memtrace/
├── docs/
│   ├── SPEC.md              Full product specification (canonical)
│   ├── DEVELOPMENT.md       This file
│   ├── DESIGN_SYSTEM.md     Color tokens, component rules, theme spec
│   ├── TEMPLATE_KB.md       Reference for the spec-as-KB template
│   ├── VALIDATION.md        Token-efficiency benchmark methodology
│   └── dev/                 Internal development notes (phase plans, audits) — not for public distribution
│
├── examples/
│   └── spec-as-kb/          30 node JSON files + edges/edges.json (see TEMPLATE_KB.md)
│
├── schema/
│   ├── node.v1.json         Memory Node JSON Schema (AJV-validated)
│   ├── edge.v1.json         Edge JSON Schema
│   └── sql/                 Sequential migrations applied on docker compose up
│       ├── 001_init.sql         Core tables, enums, indexes, SQL functions
│       ├── 002_*.sql … 023_*.sql Numbered migrations (add new ones; never edit old ones)
│       └── 099_seed_spec_kb.sql  Public spec-as-KB seed (runs last)
│
├── packages/
│   │
│   ├── core/                TypeScript library (no runtime deps except ajv)
│   │   └── src/             schema.ts, decay.ts, id.ts, types.ts
│   │
│   ├── api/                 Python / FastAPI backend (PostgreSQL + pgvector)
│   │   ├── main.py          App entrypoint, CORS, lifespan, route registration
│   │   ├── routers/         auth, kb, nodes, edges, ingest, review, ai, api_keys, admin, …
│   │   ├── core/            database, deps, ai providers, backup, scheduler
│   │   ├── requirements.txt fastapi, uvicorn, pydantic, psycopg2, jose, bcrypt, resend, …
│   │   └── venv/            Local virtual environment (git-ignored)
│   │
│   ├── ui/                  React 19 + Vite web application
│   │   └── src/
│   │       ├── main.tsx          App entry
│   │       ├── App.tsx           Root component, routing, theme switch
│   │       ├── i18n.ts           react-i18next setup (zh-TW + en)
│   │       ├── api.ts            Typed REST client for the API package
│   │       ├── AuthPage.tsx      Login / register / forgot-password
│   │       ├── ResetPasswordPage.tsx Password-reset landing page
│   │       ├── OnboardingWizard.tsx 7-step first-run wizard
│   │       ├── GraphContainer.tsx  Toolbar + 2D / 3D / Table mode switching
│   │       ├── GraphView.tsx       2D knowledge graph (ReactFlow)
│   │       ├── GraphView3D.tsx     3D knowledge graph (react-force-graph-3d)
│   │       ├── TableView.tsx       Tabular node listing with search & bulk actions
│   │       ├── NodeEditor.tsx      Bilingual Markdown node editor
│   │       ├── MemoryNode.tsx      Custom ReactFlow node component
│   │       ├── ReviewQueue.tsx     AI candidate review UI
│   │       ├── IngestPage.tsx + IngestButton.tsx + IngestionHistory.tsx
│   │       ├── WorkspaceSettings.tsx Members, invites, AI keys, API keys, decay status
│   │       ├── AnalyticsDashboard.tsx Workspace health & token-efficiency cards
│   │       └── NodeHealthManager.tsx Empty-body / single-language warnings
│   │
│   ├── cli/                 memtrace CLI (TypeScript, built with tsc)
│   │   └── src/index.ts     Commander.js entrypoint
│   │
│   └── ingest/              Document + AI extraction pipeline
│
├── scripts/                 Operational scripts (backup, restore, benchmark, seed)
├── docker-compose.yml
├── .env.example
└── package.json             npm workspaces root
```

---

## 6. Development Workflows

### Adding a New API Route

1. Create a router file in `packages/api/routers/<name>.py`.
2. Define your Pydantic request/response models in `packages/api/models/<name>.py`.
3. Register the router in `packages/api/main.py`:
   ```python
   from routers import name
   app.include_router(name.router, prefix="/api/v1")
   ```
4. Restart the API server (or rely on `--reload`).

### Background Jobs

MemTrace uses a background worker for heavy tasks like embedding, complexity analysis, and edge suggestions. 
- Implementation: `packages/api/services/bg_jobs.py`
- Trigger: `trigger_node_background_jobs(background_tasks, ...)`

### MCP Tools

The system exposes tools via the Model Context Protocol (MCP).
- Tools are defined in: `packages/api/services/mcp_tools.py`
- Key tools: `extract_from_text`, `search_cross_workspace`, `ingest_document`.
- Ingestion via MCP is subject to workspace-level quotas and enablement toggles.

### Adding a New UI Page or Panel

1. Create a component in `packages/ui/src/`.
2. Add i18n keys to both `src/locales/zh-TW.json` and `src/locales/en.json`.
3. Wire navigation in `App.tsx`.

### Updating the JSON Schema

1. Edit `schema/node.v1.json` or `schema/edge.v1.json`.
2. Update `packages/core/src/schema.ts` if you added required fields.
3. Update `schema/sql/001_init.sql` for any new DB columns.
4. Run `docker compose down -v && docker compose up -d` to apply the DDL change to a fresh DB.
5. Update `docs/SPEC.md` (§4 and §10) to document the change.

### Modifying the Decay Engine

- Logic lives in `packages/core/src/decay.ts`.
- The SQL mirror is `apply_edge_decay()` in `schema/sql/001_init.sql`.
- Both must stay in sync — update them together and note the change in `docs/SPEC.md` §7.

---

## 7. Environment Variable Reference

The full template lives in `.env.example`. Required vs optional summary:

### Database

| Variable | Required | Description |
|----------|----------|-------------|
| `POSTGRES_HOST` | Yes | DB host (`localhost` for docker compose) |
| `POSTGRES_PORT` | No | Host port (default: `5432`) |
| `POSTGRES_DB` | Yes | Database name |
| `POSTGRES_USER` | Yes | Database user |
| `POSTGRES_PASSWORD` | Yes | Database password |
| `DATABASE_URL` | Yes (API) | Full PostgreSQL connection string |

### API security

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | Yes (API) | JWT signing key (generate via `python -c "import secrets; print(secrets.token_hex(32))"`) |
| `ACCESS_TOKEN_EXPIRE_DAYS` | No | JWT lifetime (default `7`) |

### Managed AI credits (optional, future business model)

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `GEMINI_API_KEY` | Server-level keys used when a user has no personal key. Leave blank to disable managed free tier — users must then bring their own keys via the UI. |
| `AI_FREE_TOKEN_LIMIT` | Free token budget per user per month (default `50000`). |

### Local AI (Ollama)

MemTrace supports **Ollama** for local-first AI workflows. 
- The API provides proxy endpoints (`/providers/ollama/test-connection` and `/providers/ollama/models`) to resolve CORS issues when the UI needs to talk to a local Ollama instance.
- Configuration is stored in the `user_ai_keys` table (per-user).
- See `docs/ollama-deployment.md` for full setup instructions.

### Email

| Variable | Description |
|----------|-------------|
| `EMAIL_PROVIDER` | `resend` / `smtp` / `disabled`. `disabled` prints tokens to console for dev. |
| `EMAIL_API_KEY` | Resend API key (when `EMAIL_PROVIDER=resend`). |
| `EMAIL_FROM` / `EMAIL_FROM_NAME` | Sender address and display name. |
| `APP_URL` | Public base URL injected into verification / password-reset links. |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` | Only when `EMAIL_PROVIDER=smtp`. |

### MCP client side (`config.json`, **not** the API `.env`)

| Variable | Description |
|----------|-------------|
| `url` | API base URL + transport (e.g. `http://localhost:8000/sse` or `/mcp`). |
| `Authorization` | Workspace API key (`mt_...`) passed in headers. |

> **Backup** settings are configured at runtime via the UI (Settings → Backup), not env vars.

Never commit `.env`. It is in `.gitignore`.

---

## 8. Useful Commands

```bash
# Build all TypeScript packages from repo root
npm run build

# Lint all packages
npm run lint

# Check DB is healthy
docker compose ps

# Tail DB logs
docker compose logs -f db

# Open psql shell
docker exec -it memtrace-db psql -U memtrace -d memtrace

# Wipe and recreate database
docker compose down -v && docker compose up -d

# Run core package tests
cd packages/core && npm test

# Check FastAPI route list
curl http://localhost:8000/openapi.json | python -m json.tool | grep '"path"'
```

---

## 9. Troubleshooting

**`docker compose up` fails with "port already in use"**
Another process is using port 5432. Change `POSTGRES_PORT` in `.env` to e.g. `5433` and restart.

**`uvicorn: command not found`**
Activate the virtual environment first: `source packages/api/venv/bin/activate`.

**UI cannot reach the API**
Ensure the API is running on port 8000 and check `packages/ui/vite.config.ts` for the proxy setting. If not yet configured, add:
```ts
server: {
  proxy: {
    '/api': 'http://localhost:8000',
    '/auth': 'http://localhost:8000',
  }
}
```

**Schema validation errors in `packages/core`**
Run `npm run build` in `packages/core` first — the CLI and tests depend on the compiled output in `dist/`.

**`npm install` fails in a specific package**
Run `npm install` from the repo root (not inside the package directory) to respect workspace hoisting.

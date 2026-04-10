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

# Google OAuth (optional during early development)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
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

### 2.1 Start the Database

```bash
docker compose up -d
```

On first run, Docker will:
1. Pull `pgvector/pgvector:pg17`.
2. Create the database with the credentials from `.env`.
3. Auto-execute `schema/sql/001_init.sql` to create all tables, enums, indexes, and SQL functions.

### 2.2 Verify the Database is Ready

```bash
docker compose ps          # status should be "healthy"
docker compose logs db     # inspect startup logs
```

### 2.3 Connect Manually (optional)

```bash
docker exec -it memtrace-db psql -U memtrace -d memtrace
```

### 2.4 Reset the Database

```bash
docker compose down -v     # stops containers and wipes the data volume
docker compose up -d       # re-creates fresh with the SQL schema
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

---

## 5. Project Structure (detailed)

```
memtrace/
├── docs/
│   ├── SPEC.md              Full product specification
│   └── DEVELOPMENT.md       This file
│
├── schema/
│   ├── node.v1.json         Memory Node JSON Schema (AJV-validated)
│   ├── edge.v1.json         Edge JSON Schema
│   └── sql/
│       └── 001_init.sql     PostgreSQL DDL — auto-applied on first docker compose up
│
├── packages/
│   │
│   ├── core/                TypeScript library (no runtime dependencies except ajv)
│   │   └── src/
│   │       ├── index.ts     Public exports
│   │       ├── schema.ts    AJV schema loader and validator
│   │       └── decay.ts     Edge weight decay calculations
│   │
│   ├── api/                 Python / FastAPI backend
│   │   ├── main.py          App entrypoint, CORS, route registration
│   │   ├── requirements.txt fastapi, uvicorn, pydantic, python-dotenv
│   │   └── venv/            Local virtual environment (git-ignored)
│   │
│   ├── ui/                  React 19 + Vite web application
│   │   └── src/
│   │       ├── main.tsx     App entry
│   │       ├── App.tsx      Root component and routing
│   │       ├── i18n.ts      react-i18next setup (zh-TW + en)
│   │       ├── GraphView.tsx     2D knowledge graph (ReactFlow)
│   │       ├── GraphView3D.tsx   3D knowledge graph (react-force-graph-3d)
│   │       └── MemoryNode.tsx    Custom ReactFlow node component
│   │
│   ├── cli/                 memtrace CLI (TypeScript, built with tsc)
│   │   └── src/
│   │       └── index.ts     Commander.js entrypoint
│   │
│   └── ingest/              Document + AI extraction pipeline (to be implemented)
│
├── examples/
│   └── sample-collection/   Example Memory Node JSON files
│
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

| Variable | Required | Description |
|----------|----------|-------------|
| `POSTGRES_DB` | Yes | Database name |
| `POSTGRES_USER` | Yes | Database user |
| `POSTGRES_PASSWORD` | Yes | Database password |
| `POSTGRES_PORT` | No | Host port (default: `5432`) |
| `DATABASE_URL` | Yes (API) | Full PostgreSQL connection string |
| `SECRET_KEY` | Yes (API) | Random secret for JWT signing (min 32 chars) |
| `GOOGLE_CLIENT_ID` | OAuth only | From Google Cloud Console |
| `GOOGLE_CLIENT_SECRET` | OAuth only | From Google Cloud Console |
| `GOOGLE_REDIRECT_URI` | OAuth only | Must match the registered redirect URI |

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

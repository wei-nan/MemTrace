# MemTrace Deployment Guide

This guide describes how to deploy the MemTrace application stack using Docker.

## Prerequisites
- Docker Engine 24.0+
- Docker Compose 2.20+
- At least 4GB RAM (8GB recommended for pgvector operations)

## Quick Start (Docker Compose)

1. **Environment Configuration**:
   Create a `.env` file in the root directory based on `.env.example`:
   ```bash
   cp .env.example .env
   ```
   Ensure you set `GEMINI_API_KEY` (or other provider keys) for AI features.

2. **Build and Launch**:
   ```bash
   docker compose build
   docker compose up -d
   ```

3. **Verify Services**:
   - **UI**: http://localhost:5173
   - **API**: http://localhost:8000/docs (Swagger UI)
   - **MCP**: http://localhost:3001/sse (SSE endpoint)

## Service Architecture
- **API (Python/FastAPI)**: Handles knowledge graph logic, vector search, and AI provider integration.
- **UI (React/Vite)**: Modern, dynamic interface for graph visualization and node editing.
- **MCP (Node.js)**: Model Context Protocol server allowing AI agents to query the knowledge base.
- **DB (PostgreSQL 17 + pgvector)**: Specialized database for graph and semantic search.

## Production Considerations

### Reverse Proxy (Nginx)
In production, it is recommended to use Nginx as a reverse proxy for SSL termination and serving the UI.
Example `nginx.conf` snippet:
```nginx
server {
    listen 443 ssl;
    server_name memtrace.example.com;

    location / {
        proxy_pass http://ui:80;
    }

    location /api/ {
        proxy_pass http://api:8000/api/;
    }
}
```

### Backup & Restore
MemTrace includes a built-in backup mechanism for the database.
- Backups are stored in the volume mapped to `/backups` in the `db` container.
- Manual backup: `docker exec memtrace-db pg_dump -U postgres memtrace > backup.sql`

### Monitoring
Check container health:
```bash
docker compose ps
```
View logs:
```bash
docker compose logs -f api
```

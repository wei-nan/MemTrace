"""
main.py — MemTrace FastAPI application entry point.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from core.backup import get_backup_config
from core.config import settings
from core.database import run_migrations
from core.csrf import CsrfMiddleware
from core.ratelimit import RateLimitMiddleware
from core.audit import AuditLogMiddleware, audit_writer_loop
from core.security_headers import SecurityHeadersMiddleware
from core import scheduler

# ── Routers ───────────────────────────────────────────────────────────────────
from routers.admin        import router as admin_router
from routers.auth         import router as auth_router
from routers.kb           import router as kb_router
from routers.ai           import router as ai_router
from routers.collaboration import router as collaboration_router
from routers.review       import router as review_router
from routers.ingest       import router as ingest_router
from routers.exports      import router as exports_router
from routers.api_keys     import router as api_keys_router
from routers.internal     import router as internal_router
from routers.mcp          import router as mcp_router
from routers.public       import router as public_router
from routers.registration import router as registration_router
from routers.documents       import router as documents_router   # Phase 6: document first-class
from routers.audit_proposals import router as audit_proposals_router  # Phase 6.2: audit badges
from routers.openai_compat   import router as openai_compat_router
from routers.job_observability import router as job_observability_router
from routers.conductor import router as conductor_router
from routers.notifications import router as notifications_router
from routers.connectors import router as connectors_router

# ── Background jobs ───────────────────────────────────────────────────────────
from jobs.ingest import recover_stale_on_startup

logger = logging.getLogger(__name__)

scheduler.register_system_jobs()

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        run_migrations()
        from services.safety_provisioning import bootstrap_safety_from_env
        bootstrap_safety_from_env()
    except Exception as exc:
        logger.warning("Migration failed: %s", exc)

    # Security warnings
    try:
        if not get_backup_config().get("enabled"):
            logger.critical("⚠️ Automated backup is DISABLED")
    except Exception: pass
    if not (settings.admin_emails or "").strip():
        logger.critical("⚠️ ADMIN_EMAILS is not set")

    recover_stale_on_startup()
    scheduler.start_all()
    logger.info("All background schedulers started")
    try:
        yield
    finally:
        await scheduler.stop_all()

app = FastAPI(title="MemTrace API", version="1.0.0", lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.add_middleware(CsrfMiddleware)
app.add_middleware(AuditLogMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=settings.proxy_trusted_hosts)

app.include_router(admin_router)
app.include_router(auth_router)
app.include_router(kb_router)
app.include_router(ai_router)
app.include_router(collaboration_router)
app.include_router(review_router)
app.include_router(ingest_router)
app.include_router(exports_router, prefix="/api/v1")
app.include_router(api_keys_router, prefix="/api/v1")
app.include_router(internal_router, prefix="/api/v1")
app.include_router(mcp_router)
app.include_router(public_router)
app.include_router(registration_router)
app.include_router(documents_router)          # Phase 6: document CRUD
app.include_router(audit_proposals_router)    # Phase 6.2: audit proposals
app.include_router(openai_compat_router)
app.include_router(job_observability_router)
app.include_router(conductor_router)
app.include_router(notifications_router)
app.include_router(connectors_router)

# Top-level /mcp alias for Streamable HTTP (cleaner URL for MCP clients)
from routers.mcp import mcp_streamable
app.add_api_route("/mcp", mcp_streamable, methods=["POST"])

import pathlib as _pathlib
_mcp_pkg_dir = _pathlib.Path(__file__).parent / "data" / "mcp"
_mcp_pkg_dir.mkdir(parents=True, exist_ok=True)
app.mount("/mcp/download", StaticFiles(directory=str(_mcp_pkg_dir)), name="mcp-download")

@app.get("/")
def root(): return {"status": "ok", "version": "1.0.0"}

@app.get("/health")
def health_check(): return {"status": "healthy"}

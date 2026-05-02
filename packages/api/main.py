import asyncio
import logging
import os
from datetime import datetime, timezone, timedelta
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from core.backup import get_backup_config, run_backup_and_update_status
from core.config import settings
from core.database import db_cursor
from core.email import send_workspace_deletion_notice
from core.csrf import CsrfMiddleware
from core.ratelimit import RateLimitMiddleware
from core.audit import AuditLogMiddleware, audit_writer_loop
from core.security_headers import SecurityHeadersMiddleware
from routers.admin import router as admin_router
from routers.auth import router as auth_router
from routers.kb   import router as kb_router
from routers.ai   import router as ai_router
from routers.collaboration import router as collaboration_router
from routers.review import router as review_router
from routers.ingest import router as ingest_router
from routers.exports import router as exports_router
from routers.api_keys import router as api_keys_router
from routers.internal import router as internal_router
from routers.mcp      import router as mcp_router

logger = logging.getLogger(__name__)


DECAY_INTERVAL_SECONDS = 86400  # 24 hours
EPHEMERAL_DECAY_INTERVAL_SECONDS = 3600  # 1 hour (D4)
CLEANUP_INTERVAL_SECONDS = 86400  # 24 hours
BACKUP_CHECK_INTERVAL_SECONDS = 3600  # re-check every hour


async def _decay_loop():
    """Background task: apply edge weight decay and node archiving once per day."""
    while True:
        try:
            with db_cursor(commit=True) as cur:
                cur.execute("SELECT apply_edge_decay()")
                cur.execute("SELECT apply_node_archiving()")  # D4
                cur.execute(
                    """
                    INSERT INTO system_state (key, value, updated_at)
                    VALUES ('last_decay_at', %s, now())
                    ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now()
                    """,
                    (datetime.now(timezone.utc).isoformat(),),
                )
            logger.info("Decay and archiving applied successfully")
        except Exception as exc:
            logger.warning("Edge decay skipped: %s", exc)
        await asyncio.sleep(DECAY_INTERVAL_SECONDS)


async def _ephemeral_decay_loop():
    """D4: Apply edge decay for ephemeral KBs every hour."""
    while True:
        await asyncio.sleep(EPHEMERAL_DECAY_INTERVAL_SECONDS)
        try:
            with db_cursor(commit=True) as cur:
                cur.execute(
                    """
                    UPDATE edges e
                    SET weight = GREATEST(
                        e.min_weight,
                        e.weight * POWER(0.5, EXTRACT(EPOCH FROM (now() - e.last_co_accessed)) / 86400.0 / e.half_life_days)
                    )
                    FROM workspaces w
                    WHERE e.workspace_id = w.id AND w.kb_type = 'ephemeral'
                      AND e.status = 'active' AND e.pinned = FALSE
                    """
                )
            logger.info("Ephemeral KB edge decay applied")
        except Exception as exc:
            logger.warning("Ephemeral decay skipped: %s", exc)


async def _cleanup_loop():
    """G4: Daily cleanup of expired invites, old ai_usage_log and kb_exports."""
    while True:
        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
        try:
            with db_cursor(commit=True) as cur:
                # G4: Mark expired invites
                cur.execute(
                    "UPDATE workspace_invites SET status = 'expired' WHERE expires_at < NOW() AND status = 'pending'"
                )
                # G4: Weekly — delete ai_credit_ledger older than retention limit
                cur.execute(
                    "DELETE FROM ai_credit_ledger WHERE created_at < NOW() - (%s * INTERVAL '1 month')",
                    (settings.ai_usage_retention_months,)
                )
                # G4: Weekly — delete old completed kb_exports (30+ days) and their files
                cur.execute(
                    "SELECT id, file_path FROM kb_exports WHERE status = 'done' AND completed_at < NOW() - INTERVAL '30 days'"
                )
                old_exports = cur.fetchall()
                for exp in old_exports:
                    if exp["file_path"]:
                        try:
                            os.remove(exp["file_path"])
                        except OSError:
                            pass
                if old_exports:
                    cur.execute(
                        "DELETE FROM kb_exports WHERE id = ANY(%s)",
                        ([e["id"] for e in old_exports],)
                    )

                # P4-D8: Monthly summary
                now_dt = datetime.now()
                # Aggregate current and previous month to ensure continuity
                for m_offset in [0, 1]:
                    target_month = (now_dt.replace(day=1) - timedelta(days=m_offset*28)).strftime("%Y-%m")
                    cur.execute("""
                        INSERT INTO ai_usage_summary (workspace_id, year_month, token_count)
                        SELECT workspace_id, TO_CHAR(created_at, 'YYYY-MM') as ym, SUM(tokens_used)
                        FROM ai_credit_ledger
                        WHERE TO_CHAR(created_at, 'YYYY-MM') = %s
                        GROUP BY workspace_id, ym
                        ON CONFLICT (workspace_id, year_month) DO UPDATE 
                        SET token_count = EXCLUDED.token_count, last_updated = now()
                    """, (target_month,))

                # P4-D8 part 2: Cleanup ledger (retention policy)
                retention = settings.ai_usage_retention_months
                cur.execute(
                    "DELETE FROM ai_credit_ledger WHERE created_at < NOW() - (%s * INTERVAL '1 month')",
                    (retention,)
                )

                # P4-D9: Apply Node Archiving
                # Evergreen: Archive if no traversals in 90 days
                cur.execute("""
                    UPDATE memory_nodes
                    SET status = 'archived', archived_at = now()
                    FROM workspaces
                    WHERE memory_nodes.workspace_id = workspaces.id
                      AND workspaces.kb_type = 'evergreen'
                      AND memory_nodes.status = 'active'
                      AND memory_nodes.created_at < now() - interval '90 days'
                      AND NOT EXISTS (
                          SELECT 1 FROM traversal_log 
                          WHERE traversal_log.node_id = memory_nodes.id 
                            AND traversal_log.traversed_at > now() - interval '90 days'
                      )
                """)
                
                # Ephemeral: Archive if all edges faded OR 60 days without traversal
                cur.execute("""
                    UPDATE memory_nodes
                    SET status = 'archived', archived_at = now()
                    FROM workspaces
                    WHERE memory_nodes.workspace_id = workspaces.id
                      AND workspaces.kb_type = 'ephemeral'
                      AND memory_nodes.status = 'active'
                      AND (
                          (
                            memory_nodes.created_at < now() - interval '60 days' 
                            AND NOT EXISTS (
                                SELECT 1 FROM traversal_log 
                                WHERE traversal_log.node_id = memory_nodes.id 
                                  AND traversal_log.traversed_at > now() - interval '60 days'
                            )
                          )
                          OR NOT EXISTS (
                              SELECT 1 FROM edges 
                              WHERE (edges.from_id = memory_nodes.id OR edges.to_id = memory_nodes.id)
                                AND edges.status = 'active'
                          )
                      )
                """)

                # P2-3: Auto-revoke API keys inactive for 90 days.
                # A key is "inactive" if it has never been used and was created
                # ≥ 90 days ago, OR was last used ≥ 90 days ago.
                cur.execute(
                    """
                    UPDATE api_keys
                    SET revoked_at = now()
                    WHERE revoked_at IS NULL
                      AND (
                            (last_used_at IS NULL AND created_at < now() - INTERVAL '90 days')
                         OR (last_used_at IS NOT NULL AND last_used_at < now() - INTERVAL '90 days')
                          )
                    RETURNING id, user_id, name
                    """
                )
                revoked_keys = cur.fetchall()
                if revoked_keys:
                    logger.info(
                        "Auto-revoked %d inactive API key(s): %s",
                        len(revoked_keys),
                        [r["id"] for r in revoked_keys],
                    )
            logger.info("Daily cleanup complete (expired invites, old logs/exports, inactive API keys)")
        except Exception as exc:
            logger.warning("Cleanup loop error: %s", exc)

        # Purge access-log separately so a missing table/function never breaks
        # the main cleanup transaction (table created by migration 003).
        try:
            with db_cursor(commit=True) as cur:
                cur.execute("SELECT purge_old_access_logs()")
        except Exception:
            pass  # function not yet created — migration pending

        # Purge expired/revoked refresh tokens (migration 004).
        try:
            with db_cursor(commit=True) as cur:
                cur.execute("SELECT purge_old_refresh_tokens()")
        except Exception:
            pass  # function not yet created — migration pending




async def _deletion_notification_loop():
    """
    Background task: send email warnings for workspaces pending deletion.
    Runs once per day and notifies owners at:
      - 30 days remaining (first notice, sent immediately on soft-delete)
      - 5 days remaining  (urgent warning)
      - 0 days remaining  (purged — hard delete performed)
    """
    while True:
        await asyncio.sleep(DECAY_INTERVAL_SECONDS)   # first run after 24 h
        try:
            _run_deletion_notifications()
        except Exception as exc:
            logger.warning("Deletion notification loop error: %s", exc)


def _run_deletion_notifications() -> None:
    with db_cursor(commit=True) as cur:
        # ── Purge workspaces past the grace period ────────────────────────────
        cur.execute("""
            SELECT w.id, w.name_en, w.name_zh, u.email, u.display_name,
                   w.kb_type,
                   CASE w.kb_type
                     WHEN 'ephemeral' THEN 7
                     ELSE 30
                   END AS grace_days
            FROM workspaces w
            JOIN users u ON u.id = w.owner_id
            WHERE w.status = 'pending_deletion'
              AND w.deleted_at < now() - (
                    CASE w.kb_type WHEN 'ephemeral' THEN INTERVAL '7 days'
                                   ELSE INTERVAL '30 days' END
                  )
        """)
        to_purge = cur.fetchall()
        for ws in to_purge:
            try:
                send_workspace_deletion_notice(
                    ws["email"], ws["name_zh"] or ws["name_en"], days_left=0
                )
                logger.info("Purging workspace %s (%s)", ws["id"], ws["name_en"])
            except Exception as e:
                logger.warning("Failed to send purge notice for %s: %s", ws["id"], e)
            cur.execute("DELETE FROM workspaces WHERE id = %s", (ws["id"],))

        # ── 5-day urgent warning ──────────────────────────────────────────────
        cur.execute("""
            SELECT w.id, w.name_en, w.name_zh, u.email,
                   w.kb_type,
                   CASE w.kb_type WHEN 'ephemeral' THEN 7 ELSE 30 END AS grace_days
            FROM workspaces w
            JOIN users u ON u.id = w.owner_id
            WHERE w.status = 'pending_deletion'
              AND w.deleted_at BETWEEN
                    now() - (CASE w.kb_type WHEN 'ephemeral' THEN INTERVAL '7 days'
                                            ELSE INTERVAL '30 days' END)
                              + INTERVAL '1 day'
                AND now() - (CASE w.kb_type WHEN 'ephemeral' THEN INTERVAL '7 days'
                                            ELSE INTERVAL '30 days' END)
                              + INTERVAL '2 days'
        """)
        for ws in cur.fetchall():
            days_left = 5 if ws["kb_type"] != "ephemeral" else 2
            restore_url = f"http://localhost:5173/workspaces/{ws['id']}/restore"
            try:
                send_workspace_deletion_notice(
                    ws["email"],
                    ws["name_zh"] or ws["name_en"],
                    days_left=days_left,
                    restore_url=restore_url,
                )
            except Exception as e:
                logger.warning("Failed to send warning notice for %s: %s", ws["id"], e)

    logger.info("Deletion notification cycle complete (purged=%d)", len(to_purge))


async def _backup_loop():
    """Check backup schedule every hour and run pg_dump when interval has elapsed."""
    while True:
        await asyncio.sleep(BACKUP_CHECK_INTERVAL_SECONDS)
        try:
            config = get_backup_config()
            if not config.get("enabled"):
                continue
            interval_seconds = int(config.get("interval_hours", 24)) * 3600
            last_at = config.get("last_backup_at")
            if last_at:
                from datetime import datetime, timezone
                last_dt = datetime.fromisoformat(last_at)
                if last_dt.tzinfo is None:
                    last_dt = last_dt.replace(tzinfo=timezone.utc)
                elapsed = (datetime.now(timezone.utc) - last_dt).total_seconds()
                if elapsed < interval_seconds:
                    continue
            db_url = os.environ.get("DATABASE_URL", "")
            keep_count = int(config.get("keep_count", 7))
            await asyncio.to_thread(run_backup_and_update_status, config["path"], db_url, keep_count)
        except Exception as exc:
            logger.warning("Backup loop error: %s", exc)


def _run_migrations():
    """Apply pending SQL migrations (PostgreSQL only; skipped for SQLite)."""
    from core.config import settings
    if not settings.database_url.startswith("postgresql"):
        return
    import pathlib
    migrations_dir = pathlib.Path(__file__).parent / "migrations"
    if not migrations_dir.exists():
        return
    with db_cursor(commit=True) as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
              filename TEXT PRIMARY KEY,
              applied_at TIMESTAMPTZ DEFAULT now()
            )
            """
        )
        for sql_file in sorted(migrations_dir.glob("*.sql")):
            cur.execute("SELECT 1 FROM schema_migrations WHERE filename = %s", (sql_file.name,))
            if cur.fetchone():
                continue
            cur.execute(sql_file.read_text(encoding="utf-8"))
            cur.execute("INSERT INTO schema_migrations (filename) VALUES (%s)", (sql_file.name,))
            logger.info("Migration applied: %s", sql_file.name)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        _run_migrations()
    except Exception as exc:
        logger.warning("Migration skipped: %s", exc)

    # ── Startup security checks ────────────────────────────────────────────────
    try:
        backup_cfg = get_backup_config()
        if not backup_cfg.get("enabled"):
            logger.critical(
                "⚠️  SECURITY WARNING: Automated backup is DISABLED. "
                "Enable it via PATCH /api/v1/system/backup-config or the admin panel."
            )
    except Exception:
        pass  # DB might not be ready yet; backup loop will log its own errors

    # Warn loudly if no system admin is configured — admin endpoints will all 403.
    from core.config import settings as _s
    if not (_s.admin_emails or "").strip():
        logger.critical(
            "⚠️  SECURITY WARNING: ADMIN_EMAILS is not set. "
            "All /api/v1/system/* endpoints will deny access until you set "
            "ADMIN_EMAILS=user@example.com in your .env file."
        )

    decay_task         = asyncio.create_task(_decay_loop())
    ephemeral_task     = asyncio.create_task(_ephemeral_decay_loop())   # D4
    deletion_task      = asyncio.create_task(_deletion_notification_loop())
    cleanup_task       = asyncio.create_task(_cleanup_loop())            # G4
    backup_task        = asyncio.create_task(_backup_loop())
    audit_task         = asyncio.create_task(audit_writer_loop())        # P1-2 batched audit writer
    logger.info("Background schedulers started (decay + ephemeral decay + deletion notifications + cleanup + backup + audit)")
    try:
        yield
    finally:
        for t in (decay_task, ephemeral_task, deletion_task, cleanup_task, backup_task, audit_task):
            t.cancel()
            try:
                await t
            except asyncio.CancelledError:
                pass
        logger.info("Background schedulers stopped")


app = FastAPI(
    title="MemTrace API",
    description="Knowledge graph API with trust scoring and decay",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",                          # Vite dev server
        "https://mac-mini.tail6066c6.ts.net",            # Tailscale UI
        "https://mac-mini.tail6066c6.ts.net:5173",       # Tailscale UI alt port
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware execution order in Starlette: LAST added = FIRST executed.
# Desired order: RateLimit → SecurityHeaders → AuditLog → CSRF → route
app.add_middleware(CsrfMiddleware)           # 4th: validates CSRF token
app.add_middleware(AuditLogMiddleware)       # 3rd: records every API call
app.add_middleware(SecurityHeadersMiddleware)  # 2nd: adds security headers
app.add_middleware(RateLimitMiddleware)      # 1st: blocks before doing anything else

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

# ── MCP package download (served from data/mcp/) ─────────────────────────────
import pathlib as _pathlib
_mcp_pkg_dir = _pathlib.Path(__file__).parent / "data" / "mcp"
_mcp_pkg_dir.mkdir(parents=True, exist_ok=True)
app.mount("/mcp/download", StaticFiles(directory=str(_mcp_pkg_dir)), name="mcp-download")

@app.get("/")
def root():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}

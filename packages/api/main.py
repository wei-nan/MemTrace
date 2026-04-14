import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from core.database import db_cursor
from core.email import send_workspace_deletion_notice
from routers.auth import router as auth_router
from routers.kb   import router as kb_router
from routers.ai   import router as ai_router
from routers.collaboration import router as collaboration_router
from routers.review import router as review_router
from routers.ingest import router as ingest_router
from routers.exports import router as exports_router

logger = logging.getLogger(__name__)

DECAY_INTERVAL_SECONDS = 86400  # 24 hours


async def _decay_loop():
    """Background task: apply edge weight decay and node archiving once per day."""
    while True:
        try:
            with db_cursor(commit=True) as cur:
                cur.execute("SELECT apply_edge_decay()")
                cur.execute("SELECT apply_node_archiving()")
            logger.info("Decay and archiving applied successfully")
        except Exception as exc:
            logger.warning("Edge decay skipped: %s", exc)
        await asyncio.sleep(DECAY_INTERVAL_SECONDS)


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


@asynccontextmanager
async def lifespan(app: FastAPI):
    decay_task      = asyncio.create_task(_decay_loop())
    deletion_task   = asyncio.create_task(_deletion_notification_loop())
    logger.info("Background schedulers started (decay + deletion notifications)")
    try:
        yield
    finally:
        for t in (decay_task, deletion_task):
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
    allow_origins=["http://localhost:5173"],   # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(kb_router)
app.include_router(ai_router)
app.include_router(collaboration_router)
app.include_router(review_router)
app.include_router(ingest_router)
app.include_router(exports_router)


@app.get("/")
def root():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.database import db_cursor
from routers.auth import router as auth_router
from routers.kb   import router as kb_router

logger = logging.getLogger(__name__)

DECAY_INTERVAL_SECONDS = 86400  # 24 hours


async def _decay_loop():
    """Background task: apply edge weight decay once per day."""
    while True:
        try:
            with db_cursor(commit=True) as cur:
                cur.execute("SELECT apply_edge_decay()")
            logger.info("Edge decay applied successfully")
        except Exception as exc:
            # apply_edge_decay() may not exist in SQLite dev mode — log and continue
            logger.warning("Edge decay skipped: %s", exc)
        await asyncio.sleep(DECAY_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_decay_loop())
    logger.info("Decay scheduler started (interval=%ds)", DECAY_INTERVAL_SECONDS)
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        logger.info("Decay scheduler stopped")


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


@app.get("/")
def root():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}

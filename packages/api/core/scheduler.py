import asyncio
import logging
from typing import Callable, Coroutine, Any

logger = logging.getLogger(__name__)

class Scheduler:
    def __init__(self):
        self._tasks = []
        self._running_tasks = []

    def register_loop(self, name: str, coro_func: Callable[[], Coroutine[Any, Any, None]], interval_seconds: float):
        """Register a background loop task."""
        async def loop():
            logger.info(f"Starting background loop: {name} (interval: {interval_seconds}s)")
            while True:
                try:
                    await coro_func()
                except asyncio.CancelledError:
                    logger.info(f"Background loop {name} cancelled")
                    break
                except Exception as e:
                    logger.exception(f"Error in background loop {name}: {e}")
                await asyncio.sleep(interval_seconds)
        
        self._tasks.append((name, loop))

    def start_all(self):
        for name, coro in self._tasks:
            t = asyncio.create_task(coro(), name=name)
            self._running_tasks.append(t)

    async def stop_all(self):
        logger.info("Stopping all background tasks...")
        for t in self._running_tasks:
            t.cancel()
        if self._running_tasks:
            await asyncio.gather(*self._running_tasks, return_exceptions=True)
        self._running_tasks = []

    def register_system_jobs(self):
        """Register all system background jobs."""
        from jobs.decay   import decay_job, DECAY_INTERVAL_SECONDS, ephemeral_decay_job, EPHEMERAL_DECAY_INTERVAL_SECONDS
        from jobs.cleanup import cleanup_job, CLEANUP_INTERVAL_SECONDS, deletion_notification_job
        from jobs.ingest  import stale_ingest_job, STALE_INGEST_CHECK_INTERVAL_SECONDS
        from jobs.backup  import backup_job, BACKUP_CHECK_INTERVAL_SECONDS
        from core.audit   import audit_writer_loop

        self.register_loop("decay",           decay_job,           DECAY_INTERVAL_SECONDS)
        self.register_loop("ephemeral_decay", ephemeral_decay_job, EPHEMERAL_DECAY_INTERVAL_SECONDS)
        self.register_loop("cleanup",         cleanup_job,         CLEANUP_INTERVAL_SECONDS)
        self.register_loop("deletion_notify", deletion_notification_job, DECAY_INTERVAL_SECONDS)
        self.register_loop("backup",          backup_job,          BACKUP_CHECK_INTERVAL_SECONDS)
        self.register_loop("stale_ingest",    stale_ingest_job,    STALE_INGEST_CHECK_INTERVAL_SECONDS)
        
        # audit_writer_loop is special because it has internal while True and queue.
        # We still register it but with a very long interval or we'll need to refactor it.
        # For now, register it as is.
        self.register_loop("audit_writer",    audit_writer_loop,   5)

# Global instance
scheduler = Scheduler()

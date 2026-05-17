import logging
import asyncio
from core.database import db_cursor
from services.collaboration import assign_stewards_in_db, process_review_sla_in_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def steward_cycle():
    """Run assignment and SLA check for all active workspaces."""
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT id FROM workspaces")
        workspaces = [r["id"] for r in cur.fetchall()]
        
        for ws_id in workspaces:
            logger.info(f"Processing steward cycle for {ws_id}")
            process_review_sla_in_db(cur, ws_id)
            assign_stewards_in_db(cur, ws_id)

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(".env")
    asyncio.run(steward_cycle())

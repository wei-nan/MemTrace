import logging
from core.database import db_cursor

logger = logging.getLogger(__name__)

PATH_REINFORCEMENT_INTERVAL_SECONDS = 86400  # 24 hours

def reinforce_paths_in_db(cur):
    """Reinforce successful paths and archive old failed ones."""
    # 1. Reinforce successful paths from the last 24 hours
    cur.execute(
        """
        SELECT id, workspace_id, node_sequence
        FROM inquiry_paths
        WHERE outcome = 'success'
          AND ended_at >= now() - INTERVAL '1 day'
          AND archived_at IS NULL
        """
    )
    paths = cur.fetchall()
    
    reinforced_count = 0
    for p in paths:
        ws_id = p["workspace_id"]
        seq = p["node_sequence"] or []
        if len(seq) < 2:
            continue
        
        # Boost each adjacent pair in the sequence
        for i in range(len(seq) - 1):
            n1 = seq[i]
            n2 = seq[i+1]
            cur.execute(
                """
                UPDATE edges
                SET weight = LEAST(weight + 0.05, 1.0)
                WHERE workspace_id = %s
                  AND status = 'active'
                  AND ((from_id = %s AND to_id = %s) OR (from_id = %s AND to_id = %s))
                """,
                (ws_id, n1, n2, n2, n1)
            )
            reinforced_count += cur.rowcount
    
    logger.info(f"Reinforced {reinforced_count} edges from successful paths.")

    # 2. Decay/archive failed paths with no activity for 30 days
    cur.execute(
        """
        UPDATE inquiry_paths
        SET archived_at = now()
        WHERE outcome = 'failed'
          AND ended_at < now() - INTERVAL '30 days'
          AND archived_at IS NULL
        """
    )
    archived_count = cur.rowcount
    logger.info(f"Soft-deleted {archived_count} old failed inquiry paths.")

async def path_reinforcement_job():
    """Daily job to reinforce successful inquiry paths and soft-delete old failed ones."""
    logger.info("Running path reinforcement and decay job...")
    try:
        with db_cursor(commit=True) as cur:
            reinforce_paths_in_db(cur)
    except Exception as e:
        logger.exception(f"Error in path_reinforcement_job: {e}")

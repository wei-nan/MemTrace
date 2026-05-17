import logging
import datetime
from typing import List, Optional
from core.database import db_cursor

logger = logging.getLogger(__name__)

def assign_stewards_in_db(cur, ws_id: str):
    """
    S2-T03: Assign pending reviews to workspace members (stewards) using round-robin.
    """
    # 1. Get all members who can review (admin/editor)
    cur.execute("SELECT owner_id FROM workspaces WHERE id = %s", (ws_id,))
    owner = cur.fetchone()
    if not owner:
        return
        
    stewards = [owner["owner_id"]]
    # Use 'editor' which exists in member_role enum
    cur.execute("SELECT user_id FROM workspace_members WHERE workspace_id = %s AND role = 'editor'", (ws_id,))
    stewards.extend([r["user_id"] for r in cur.fetchall()])
    stewards = list(set(stewards)) # Unique
    
    if not stewards:
        return
        
    # 2. Get unassigned pending reviews
    cur.execute(
        "SELECT id FROM review_queue WHERE workspace_id = %s AND status = 'pending' AND assigned_to IS NULL ORDER BY created_at ASC",
        (ws_id,)
    )
    pending_ids = [r["id"] for r in cur.fetchall()]
    
    if not pending_ids:
        return
        
    # 3. Round-robin assignment
    for i, rid in enumerate(pending_ids):
        steward = stewards[i % len(stewards)]
        due_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7)
        cur.execute(
            "UPDATE review_queue SET assigned_to = %s, due_at = %s WHERE id = %s",
            (steward, due_at, rid)
        )
        logger.info(f"Assigned review {rid} to steward {steward}, due at {due_at}")

def process_review_sla_in_db(cur, ws_id: str):
    """
    S2-T03: Penalize stale reviews (SLA breach).
    If due_at < now, decay the node's freshness and push to next steward or extend.
    """
    cur.execute(
        """
        SELECT id, target_node_id, assigned_to 
        FROM review_queue 
        WHERE workspace_id = %s AND status = 'pending' AND due_at < NOW()
        """,
        (ws_id,)
    )
    overdue = cur.fetchall()
    
    for row in overdue:
        rid = row["id"]
        node_id = row["target_node_id"]
        
        # Penalize the node (if it exists)
        if node_id:
            cur.execute(
                "UPDATE memory_nodes SET dim_freshness = dim_freshness * 0.8 WHERE id = %s",
                (node_id,)
            )
            
        # Reset assignment to trigger re-assignment in next run
        cur.execute(
            "UPDATE review_queue SET assigned_to = NULL, due_at = NULL WHERE id = %s",
            (rid,)
        )
        logger.warning(f"SLA Breach for review {rid} (assigned to {row['assigned_to']}). Node {node_id} penalized.")

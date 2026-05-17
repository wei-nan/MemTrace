import json
import hashlib
import logging
from typing import Optional, Any
from core.database import db_cursor

logger = logging.getLogger(__name__)

def log_audit_event(cur, ws_id: str, action: str, target_type: str, target_id: str, actor_id: str, metadata: Optional[dict] = None) -> str:
    """
    S3-T05: Log an audit event with hash chain.
    """
    # 1. Fetch latest hash for this workspace
    cur.execute(
        "SELECT curr_hash FROM audit_trail WHERE workspace_id = %s ORDER BY id DESC LIMIT 1",
        (ws_id,)
    )
    row = cur.fetchone()
    prev_hash = row["curr_hash"] if row else "GENESIS"
    
    # 2. Prepare data for hashing
    meta_str = json.dumps(metadata or {}, sort_keys=True, ensure_ascii=False)
    payload = f"{prev_hash}|{action}|{target_type}|{target_id}|{actor_id}|{meta_str}"
    curr_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    
    # 3. Insert
    cur.execute(
        """
        INSERT INTO audit_trail (workspace_id, action, target_type, target_id, actor_id, metadata, prev_hash, curr_hash)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING curr_hash
        """,
        (ws_id, action, target_type, target_id, actor_id, json.dumps(metadata or {}), prev_hash, curr_hash)
    )
    return curr_hash

def verify_audit_chain(cur, ws_id: str) -> dict:
    """
    S3-T05: Verify the integrity of the audit trail hash chain for a workspace.
    """
    cur.execute(
        "SELECT * FROM audit_trail WHERE workspace_id = %s ORDER BY id ASC",
        (ws_id,)
    )
    rows = cur.fetchall()
    
    expected_prev = "GENESIS"
    valid_count = 0
    errors = []
    
    for row in rows:
        if row["prev_hash"] != expected_prev:
            errors.append(f"Chain broken at ID {row['id']}: expected prev_hash {expected_prev}, got {row['prev_hash']}")
            break
            
        meta_str = json.dumps(row["metadata"] or {}, sort_keys=True, ensure_ascii=False)
        payload = f"{row['prev_hash']}|{row['action']}|{row['target_type']}|{row['target_id']}|{row['actor_id']}|{meta_str}"
        recalculated = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        
        if row["curr_hash"] != recalculated:
            errors.append(f"Hash mismatch at ID {row['id']}: stored {row['curr_hash']}, recalculated {recalculated}")
            break
            
        expected_prev = row["curr_hash"]
        valid_count += 1
        
    return {
        "workspace_id": ws_id,
        "verified_count": valid_count,
        "total_count": len(rows),
        "is_intact": len(errors) == 0,
        "errors": errors
    }

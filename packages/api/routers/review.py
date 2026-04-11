from fastapi import APIRouter, Depends, HTTPException
from typing import List
from datetime import datetime, timezone
import json

from core.database import db_cursor
from core.deps import get_current_user
from core.security import generate_id
from models.review import ReviewQueueResponse, ReviewUpdate
from models.kb import NodeCreate, NodeResponse
from routers.kb import _require_ws_access, create_node, create_edge, EdgeCreate

router = APIRouter(prefix="/workspaces", tags=["review"])

@router.get("/{ws_id}/review-queue", response_model=List[ReviewQueueResponse])
def list_review_queue(ws_id: str, status: str = "pending", user: dict = Depends(get_current_user)):
    with db_cursor() as cur:
        _require_ws_access(cur, ws_id, user)
        cur.execute(
            "SELECT * FROM review_queue WHERE workspace_id = %s AND status = %s ORDER BY created_at ASC",
            (ws_id, status)
        )
        return cur.fetchall()

@router.patch("/review-queue/{id}", response_model=ReviewQueueResponse)
def update_review_item(id: str, body: ReviewUpdate, user: dict = Depends(get_current_user)):
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT workspace_id FROM review_queue WHERE id = %s", (id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Review item not found")
        
        _require_ws_access(cur, row["workspace_id"], user, write=True)
        
        updates = []
        params = []
        if body.node_data is not None:
            updates.append("node_data = %s")
            params.append(json.dumps(body.node_data))
        if body.suggested_edges is not None:
            updates.append("suggested_edges = %s")
            params.append(json.dumps(body.suggested_edges))
            
        if not updates:
            cur.execute("SELECT * FROM review_queue WHERE id = %s", (id,))
            return cur.fetchone()
            
        params.append(id)
        cur.execute(f"UPDATE review_queue SET {', '.join(updates)} WHERE id = %s RETURNING *", params)
        return cur.fetchone()

@router.post("/review-queue/{id}/accept", response_model=NodeResponse)
def accept_review_item(id: str, user: dict = Depends(get_current_user)):
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT * FROM review_queue WHERE id = %s", (id,))
        item = cur.fetchone()
        if not item:
            raise HTTPException(status_code=404, detail="Review item not found")
        if item["status"] != "pending":
            raise HTTPException(status_code=400, detail=f"Item is already {item['status']}")
            
        ws_id = item["workspace_id"]
        _require_ws_access(cur, ws_id, user, write=True)
        
        # Convert JSON node_data to NodeCreate
        node_data = item["node_data"]
        # In actual implementation, we'd call the logic of create_node directly to avoid redundant checks
        # But for now, let's just do the INSERT
        
        # Re-verify the node_data matches expected structure
        node_create = NodeCreate(**node_data)
        
        # We need a hack here because create_node is a decorated function that expects a Request or similar dependencies if we call it as a function
        # Better to refactor create_node logic into a library function. 
        # For Phase B, I'll just write the internal logic here or hope I can call it.
        
        # Actually, let's just do the DB insert ourselves to be safe and clean.
        from routers.kb import compute_signature, generate_id as gen_id
        
        author = user["sub"]
        title   = {"zh-TW": node_create.title_zh, "en": node_create.title_en}
        content = {"type": node_create.content_type, "format": node_create.content_format,
                   "body": {"zh-TW": node_create.body_zh, "en": node_create.body_en}}
        sig = compute_signature(title, content, node_create.tags, author)
        node_id = gen_id("mem")
        
        cur.execute("""
            INSERT INTO memory_nodes (
                id, workspace_id, title_zh, title_en,
                content_type, content_format, body_zh, body_en,
                tags, visibility, author, signature, source_type
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'ai')
            RETURNING *
        """, (
            node_id, ws_id,
            node_create.title_zh, node_create.title_en,
            node_create.content_type, node_create.content_format, node_create.body_zh, node_create.body_en,
            node_create.tags, node_create.visibility,
            author, sig
        ))
        new_node = cur.fetchone()
        
        # Handle edges
        for edge in item["suggested_edges"]:
            to_id = edge.get("to_node_id")
            if not to_id: continue # skip relative index edges for now in this simple implementation
            
            edge_id = gen_id("edge")
            cur.execute("""
                INSERT INTO edges (id, workspace_id, from_id, to_id, relation)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (edge_id, ws_id, node_id, to_id, edge["relation"]))

        # Mark as accepted
        cur.execute(
            "UPDATE review_queue SET status = 'accepted', reviewed_at = now(), reviewer_id = %s WHERE id = %s",
            (user["sub"], id)
        )
        
        return new_node

@router.post("/review-queue/{id}/reject")
def reject_review_item(id: str, user: dict = Depends(get_current_user)):
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT workspace_id FROM review_queue WHERE id = %s", (id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Review item not found")
            
        _require_ws_access(cur, row["workspace_id"], user, write=True)
        
        cur.execute(
            "UPDATE review_queue SET status = 'rejected', reviewed_at = now(), reviewer_id = %s WHERE id = %s",
            (user["sub"], id)
        )
        return {"message": "Rejected"}

@router.post("/{ws_id}/review-queue/accept-all")
def accept_all_review_items(ws_id: str, user: dict = Depends(get_current_user)):
    with db_cursor(commit=True) as cur:
        _require_ws_access(cur, ws_id, user, write=True)
        cur.execute("SELECT id FROM review_queue WHERE workspace_id = %s AND status = 'pending'", (ws_id,))
        ids = [r["id"] for r in cur.fetchall()]
        
        results = []
        for rid in ids:
            try:
                # We reuse the logic by calling the accept function internally or refactoring
                # For simplicity here, let's just loop and call the accept logic
                # (Ideally refactor to a internal function)
                res = accept_review_item(rid, user)
                results.append(res)
            except Exception:
                continue
        return {"accepted_count": len(results)}

@router.post("/{ws_id}/review-queue/reject-all")
def reject_all_review_items(ws_id: str, user: dict = Depends(get_current_user)):
    with db_cursor(commit=True) as cur:
        _require_ws_access(cur, ws_id, user, write=True)
        cur.execute(
            "UPDATE review_queue SET status = 'rejected', reviewed_at = now(), reviewer_id = %s "
            "WHERE workspace_id = %s AND status = 'pending'",
            (user["sub"], ws_id)
        )
        return {"message": "All pending items rejected"}

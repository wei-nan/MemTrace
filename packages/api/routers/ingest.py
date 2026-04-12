from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from typing import List
import json

from core.database import db_cursor
from core.deps import get_current_user
from core.security import generate_id
from core.ai import (
    resolve_provider, 
    chat_completion, 
    record_usage, 
    EXTRACTION_SYSTEM, 
    strip_fences
)
from routers.kb import _require_ws_access

router = APIRouter(prefix="/api/v1/workspaces", tags=["ingest"])

async def process_ingestion(job_id: str, ws_id: str, content: str, user_id: str, filename: str):
    """Background task to extract knowledge nodes from uploaded content."""
    try:
        resolved = resolve_provider(user_id, "extraction")
        messages = [
            {"role": "system", "content": EXTRACTION_SYSTEM},
            {"role": "user", "content": f"Extract Memory Nodes from this file: {filename}\n---\n{content}\n---"}
        ]
        raw, tokens = await chat_completion(resolved, messages)
        
        # Cleanup JSON using shared utility
        nodes_data = json.loads(strip_fences(raw))
        
        with db_cursor(commit=True) as cur:
            for n in nodes_data:
                rev_id = generate_id("rev")
                edges = n.pop("suggested_edges", [])
                cur.execute("""
                    INSERT INTO review_queue (id, workspace_id, node_data, suggested_edges, source_info)
                    VALUES (%s, %s, %s, %s, %s)
                """, (rev_id, ws_id, json.dumps(n, ensure_ascii=False), json.dumps(edges), f"ingest: {filename}"))
        
        record_usage(resolved, "extraction", tokens, ws_id)
        
        with db_cursor(commit=True) as cur:
            cur.execute(
                "UPDATE ingestion_logs SET status = 'completed', completed_at = now() WHERE id = %s",
                (job_id,)
            )
        
    except Exception as e:
        error_str = str(e)
        print(f"Ingestion failed for {filename}: {error_str}")
        with db_cursor(commit=True) as cur:
            cur.execute(
                "UPDATE ingestion_logs SET status = 'failed', error_msg = %s, completed_at = now() WHERE id = %s",
                (error_str, job_id)
            )

@router.post("/{ws_id}/ingest")
async def ingest_file(
    ws_id: str, 
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...), 
    user: dict = Depends(get_current_user)
):
    with db_cursor(commit=True) as cur:
        _require_ws_access(cur, ws_id, user, write=True)
        job_id = generate_id("ing")
        cur.execute("""
            INSERT INTO ingestion_logs (id, workspace_id, user_id, filename, status)
            VALUES (%s, %s, %s, %s, 'processing')
        """, (job_id, ws_id, user["sub"], file.filename))
    
    # Read content
    try:
        content_bytes = await file.read()
        content = content_bytes.decode("utf-8")
    except Exception:
        with db_cursor(commit=True) as cur:
            cur.execute(
                "UPDATE ingestion_logs SET status = 'failed', error_msg = %s, completed_at = now() WHERE id = %s",
                ("Only UTF-8 encoded files (.txt, .md) are supported currently.", job_id)
            )
        raise HTTPException(
            status_code=400, 
            detail="Only UTF-8 encoded files (.txt, .md) are supported currently."
        )
        
    background_tasks.add_task(process_ingestion, job_id, ws_id, content, user["sub"], file.filename)
    
    return {"message": "Ingestion started in background", "filename": file.filename, "job_id": job_id}

@router.get("/{ws_id}/ingest/logs")
def list_ingestion_logs(ws_id: str, user: dict = Depends(get_current_user)):
    with db_cursor() as cur:
        _require_ws_access(cur, ws_id, user)
        cur.execute("""
            SELECT id, filename, status, error_msg, created_at, completed_at
            FROM ingestion_logs
            WHERE workspace_id = %s
            ORDER BY created_at DESC
            LIMIT 20
        """, (ws_id,))
        return cur.fetchall()

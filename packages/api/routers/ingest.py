from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from typing import List
import json

from core.database import db_cursor
from core.deps import get_current_user
from core.security import generate_id
from models.ai import ExtractionRequest
from routers.kb import _require_ws_access
from routers.ai import extract_nodes

router = APIRouter(prefix="/workspaces", tags=["ingest"])

async def process_ingestion(ws_id: str, content: str, user_id: str, filename: str):
    # This calls the AI extraction
    # We fake the ExtractionRequest for extract_nodes
    # Note: in a real background task, we'd need to mock the user dict for Depends
    
    # For now, let's implement the logic directly or call the helper functions from ai.py
    from core.ai import resolve_provider, chat_completion, record_usage, EXTRACTION_SYSTEM
    
    try:
        resolved = resolve_provider(user_id, "extraction")
        messages = [
            {"role": "system", "content": EXTRACTION_SYSTEM},
            {"role": "user", "content": f"Extract Memory Nodes from this file: {filename}\n---\n{content}\n---"}
        ]
        raw, tokens = await chat_completion(resolved, messages)
        
        # Cleanup JSON
        import re
        text = raw.strip()
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        nodes_data = json.loads(text)
        
        with db_cursor(commit=True) as cur:
            for n in nodes_data:
                rev_id = generate_id("rev")
                edges = n.pop("suggested_edges", [])
                cur.execute("""
                    INSERT INTO review_queue (id, workspace_id, node_data, suggested_edges, source_info)
                    VALUES (%s, %s, %s, %s, %s)
                """, (rev_id, ws_id, json.dumps(n), json.dumps(edges), f"ingest: {filename}"))
        
        record_usage(resolved, "extraction", tokens, ws_id)
        
    except Exception as e:
        print(f"Ingestion failed for {filename}: {e}")

@router.post("/{ws_id}/ingest")
async def ingest_file(
    ws_id: str, 
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...), 
    user: dict = Depends(get_current_user)
):
    with db_cursor() as cur:
        _require_ws_access(cur, ws_id, user, write=True)
    
    # Read content (assuming text for now)
    try:
        content_bytes = await file.read()
        content = content_bytes.decode("utf-8")
    except Exception:
        raise HTTPException(status_code=400, detail="Only UTF-8 text files are supported currently")
        
    background_tasks.add_task(process_ingestion, ws_id, content, user["sub"], file.filename)
    
    return {"message": "Ingestion started in background", "filename": file.filename}

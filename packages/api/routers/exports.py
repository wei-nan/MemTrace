import os
import zipfile
import json
import logging
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from core.database import db_cursor
from core.deps import get_current_user
from core.security import generate_id
from models.exports import KBExportRequest, KBExportResponse
from routers.kb import _require_ws_access

router = APIRouter(prefix="/api/v1", tags=["Exports"])
logger = logging.getLogger(__name__)

EXPORT_DIR = "data/exports"
os.makedirs(EXPORT_DIR, exist_ok=True)

def _bg_export_kb(export_id: str, ws_id: str, include_markdown: bool, tags: List[str] = None):
    try:
        with db_cursor(commit=True) as cur:
            cur.execute("UPDATE kb_exports SET status = 'processing' WHERE id = %s", (export_id,))
            
            # 1. Fetch data
            if tags:
                cur.execute("""
                    SELECT * FROM memory_nodes 
                    WHERE workspace_id = %s 
                      AND status = 'active'
                      AND tags && %s::text[]
                """, (ws_id, tags))
            else:
                cur.execute("SELECT * FROM memory_nodes WHERE workspace_id = %s AND status = 'active'", (ws_id,))
            nodes = cur.fetchall()
            
            node_ids = [n["id"] for n in nodes]
            if node_ids:
                cur.execute("""
                    SELECT * FROM edges 
                    WHERE workspace_id = %s 
                      AND status = 'active'
                      AND (from_id = ANY(%s) AND to_id = ANY(%s))
                """, (ws_id, node_ids, node_ids))
                edges = cur.fetchall()
            else:
                edges = []

            cur.execute("SELECT * FROM workspaces WHERE id = %s", (ws_id,))
            workspace = cur.fetchone()

            # 2. Setup Zip
            filename = f"{ws_id}_{export_id}.memtrace"
            filepath = os.path.join(EXPORT_DIR, filename)
            
            with zipfile.ZipFile(filepath, 'w', zipfile.ZIP_DEFLATED) as zf:
                # Metadata
                ws_data = {
                    "id": workspace["id"],
                    "name_en": workspace["name_en"],
                    "name_zh": workspace["name_zh"],
                    "kb_type": workspace["kb_type"],
                    "exported_at": datetime.now(timezone.utc).isoformat()
                }
                zf.writestr("workspace.json", json.dumps(ws_data, indent=2, ensure_ascii=False))
                
                # Edges
                edges_data = [dict(e) for e in edges]
                for e in edges_data:
                    if isinstance(e.get("created_at"), datetime):
                        e["created_at"] = e["created_at"].isoformat()
                zf.writestr("edges.json", json.dumps(edges_data, indent=2, ensure_ascii=False))
                
                # Nodes (as objects)
                nodes_data = [dict(n) for n in nodes]
                for n in nodes_data:
                    for k, v in n.items():
                        if isinstance(v, datetime):
                            n[k] = v.isoformat()
                zf.writestr("nodes.json", json.dumps(nodes_data, indent=2, ensure_ascii=False))

                # Markdown Export
                if include_markdown:
                    for n in nodes:
                        content = f"# {n['title_en'] or n['title_zh']}\n\n"
                        if n['tags']:
                            content += f"Tags: {', '.join(n['tags'])}\n\n"
                        content += "## English\n"
                        content += n['body_en'] or ""
                        content += "\n\n## 中文\n"
                        content += n['body_zh'] or ""
                        
                        safe_title = (n['title_en'] or n['title_zh']).replace("/", "_").replace("\\", "_")
                        zf.writestr(f"markdown/{n['id']}_{safe_title}.md", content)

            # 3. Update Status
            download_url = f"/exports/{filename}"
            cur.execute("""
                UPDATE kb_exports 
                SET status = 'completed', download_url = %s, completed_at = now() 
                WHERE id = %s
            """, (download_url, export_id))
            
    except Exception as e:
        logger.error(f"Export failed for {export_id}: {e}")
        with db_cursor(commit=True) as cur:
            cur.execute("UPDATE kb_exports SET status = 'failed', error_msg = %s WHERE id = %s", (str(e), export_id))

@router.post("/workspaces/{ws_id}/exports", response_model=KBExportResponse)
def trigger_export(ws_id: str, body: KBExportRequest, background_tasks: BackgroundTasks, user: dict = Depends(get_current_user)):
    with db_cursor(commit=True) as cur:
        _require_ws_access(cur, ws_id, user)
        
        export_id = generate_id("exp")
        cur.execute("""
            INSERT INTO kb_exports (id, workspace_id, status)
            VALUES (%s, %s, 'pending')
            RETURNING *
        """, (export_id, ws_id))
        export_row = cur.fetchone()
        
        background_tasks.add_task(_bg_export_kb, export_id, ws_id, body.include_markdown, body.tags)
        return export_row

@router.get("/workspaces/{ws_id}/exports", response_model=List[KBExportResponse])
def list_exports(ws_id: str, user: dict = Depends(get_current_user)):
    with db_cursor() as cur:
        _require_ws_access(cur, ws_id, user)
        cur.execute("SELECT * FROM kb_exports WHERE workspace_id = %s ORDER BY created_at DESC", (ws_id,))
        return cur.fetchall()

@router.get("/workspaces/{ws_id}/exports/{export_id}", response_model=KBExportResponse)
def get_export(ws_id: str, export_id: str, user: dict = Depends(get_current_user)):
    with db_cursor() as cur:
        _require_ws_access(cur, ws_id, user)
        cur.execute("SELECT * FROM kb_exports WHERE id = %s AND workspace_id = %s", (export_id, ws_id))
        export = cur.fetchone()
        if not export:
            raise HTTPException(status_code=404, detail="Export not found")
        return export

@router.get("/workspaces/{ws_id}/exports/{export_id}/download")
def download_export(ws_id: str, export_id: str, user: dict = Depends(get_current_user)):
    with db_cursor() as cur:
        _require_ws_access(cur, ws_id, user)
        cur.execute("SELECT download_url FROM kb_exports WHERE id = %s AND workspace_id = %s", (export_id, ws_id))
        row = cur.fetchone()
        if not row or not row["download_url"]:
            raise HTTPException(status_code=404, detail="Download not found")
        
        # Extract filename from relative URL
        filename = row["download_url"].split("/")[-1]
        filepath = os.path.join(EXPORT_DIR, filename)
        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail="File lost on server")
            
        return FileResponse(filepath, media_type='application/octet-stream', filename=filename)

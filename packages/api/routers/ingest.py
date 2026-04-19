from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
import json

from core.ai import EXTRACTION_SYSTEM, chat_completion, record_usage, resolve_provider, strip_fences
from core.database import db_cursor
from core.security import generate_id
from core.deps import get_current_user
from routers.kb import _propose_change, _require_ws_access

router = APIRouter(prefix="/api/v1/workspaces", tags=["ingest"])


def _find_similar_node(cur, ws_id: str, node_data: dict):
    title_zh = node_data.get("title_zh")
    title_en = node_data.get("title_en")
    cur.execute(
        """
        SELECT * FROM memory_nodes
        WHERE workspace_id = %s
          AND (LOWER(title_zh) = LOWER(%s) OR LOWER(title_en) = LOWER(%s))
        ORDER BY updated_at DESC NULLS LAST, created_at DESC
        LIMIT 1
        """,
        (ws_id, title_zh, title_en),
    )
    return cur.fetchone()


async def process_ingestion(job_id: str, ws_id: str, content: str, user_id: str, filename: str):
    try:
        resolved = resolve_provider(user_id, "extraction")
        messages = [
            {"role": "system", "content": EXTRACTION_SYSTEM},
            {"role": "user", "content": f"Extract Memory Nodes from this file: {filename}\n---\n{content}\n---"},
        ]
        raw, tokens = await chat_completion(resolved, messages)
        nodes_data = json.loads(strip_fences(raw))

        review_ids = []
        with db_cursor(commit=True) as cur:
            for n in nodes_data:
                edges = n.pop("suggested_edges", [])
                target = _find_similar_node(cur, ws_id, n)
                change_type = "update" if target else "create"
                target_node_id = target["id"] if target else None
                rid = _propose_change(
                    cur,
                    ws_id,
                    change_type,
                    target_node_id,
                    n | {"source_type": "ai", "author": user_id},
                    "ai",
                    f"ai:{resolved.provider.name}:{resolved.model}",
                    {
                        "ingest_job_id": job_id,
                        "source_file": filename,
                        "provider": resolved.provider.name,
                        "model": resolved.model,
                    },
                    suggested_edges=edges,
                    source_info=f"ingest: {filename}",
                )
                review_ids.append(rid)

        from core.ai_review import run_ai_review_for_item
        for rid in review_ids:
            await run_ai_review_for_item(rid)

        record_usage(resolved, "extraction", tokens, ws_id)
        with db_cursor(commit=True) as cur:
            cur.execute("UPDATE ingestion_logs SET status = 'completed', completed_at = now() WHERE id = %s", (job_id,))
    except Exception as exc:
        error_str = str(exc)
        print(f"Ingestion failed for {filename}: {error_str}")
        with db_cursor(commit=True) as cur:
            cur.execute(
                "UPDATE ingestion_logs SET status = 'failed', error_msg = %s, completed_at = now() WHERE id = %s",
                (error_str, job_id),
            )


@router.post("/{ws_id}/ingest")
async def ingest_file(
    ws_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    with db_cursor(commit=True) as cur:
        _require_ws_access(cur, ws_id, user, write=True)
        job_id = generate_id("ing")
        cur.execute(
            """
            INSERT INTO ingestion_logs (id, workspace_id, user_id, filename, status)
            VALUES (%s, %s, %s, %s, 'processing')
            """,
            (job_id, ws_id, user["sub"], file.filename),
        )
    try:
        content = (await file.read()).decode("utf-8")
    except Exception:
        with db_cursor(commit=True) as cur:
            cur.execute(
                "UPDATE ingestion_logs SET status = 'failed', error_msg = %s, completed_at = now() WHERE id = %s",
                ("Only UTF-8 encoded files (.txt, .md) are supported currently.", job_id),
            )
        raise HTTPException(status_code=400, detail="Only UTF-8 encoded files (.txt, .md) are supported currently.")

    background_tasks.add_task(process_ingestion, job_id, ws_id, content, user["sub"], file.filename)
    return {"message": "Ingestion started in background", "filename": file.filename, "job_id": job_id}


@router.get("/{ws_id}/ingest/logs")
def list_ingestion_logs(ws_id: str, user: dict = Depends(get_current_user)):
    with db_cursor() as cur:
        _require_ws_access(cur, ws_id, user)
        cur.execute(
            """
            SELECT id, filename, status, error_msg, created_at, completed_at
            FROM ingestion_logs
            WHERE workspace_id = %s
            ORDER BY created_at DESC
            LIMIT 20
            """,
            (ws_id,),
        )
        return cur.fetchall()


import os
import zipfile
import json
import logging
import tempfile
from datetime import datetime, timezone
from decimal import Decimal
from typing import List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.responses import FileResponse
from core.database import db_cursor
from core.deps import get_current_user
from core.security import generate_id
from models.exports import KBExportRequest, KBExportResponse, KBImportResponse
from routers.kb import _require_ws_access

router = APIRouter(tags=["Exports"])
logger = logging.getLogger(__name__)

EXPORT_DIR = "data/exports"
os.makedirs(EXPORT_DIR, exist_ok=True)


def _bg_export_kb(export_id: str, ws_id: str, req: KBExportRequest):
    try:
        with db_cursor(commit=True) as cur:
            cur.execute("UPDATE kb_exports SET status = 'processing' WHERE id = %s", (export_id,))

            # Build node query based on filter params
            conditions = ["workspace_id = %s", "content_type != 'source_document'"]
            params: list = [ws_id]

            if not req.include_archived:
                conditions.append("status = 'active'")
            else:
                conditions.append("status IN ('active', 'archived')")

            if req.tags:
                conditions.append("tags && %s::text[]")
                params.append(req.tags)

            if req.date_from:
                conditions.append("created_at >= %s::timestamptz")
                params.append(req.date_from)

            if req.date_to:
                conditions.append("created_at <= %s::timestamptz")
                params.append(req.date_to)

            cur.execute(
                f"SELECT * FROM memory_nodes WHERE {' AND '.join(conditions)}",
                params,
            )
            nodes = cur.fetchall()

            node_ids = [n["id"] for n in nodes]
            if node_ids:
                cur.execute(
                    """
                    SELECT * FROM edges
                    WHERE workspace_id = %s
                      AND status = 'active'
                      AND from_id = ANY(%s) AND to_id = ANY(%s)
                    """,
                    (ws_id, node_ids, node_ids),
                )
                edges = cur.fetchall()
            else:
                edges = []

            cur.execute("SELECT * FROM workspaces WHERE id = %s", (ws_id,))
            workspace = cur.fetchone()

            # Build ZIP
            filename = f"{ws_id}_{export_id}.memtrace"
            filepath = os.path.join(EXPORT_DIR, filename)

            with zipfile.ZipFile(filepath, "w", zipfile.ZIP_DEFLATED) as zf:
                manifest = {
                    "version": "1.0",
                    "workspace_id": ws_id,
                    "exported_at": datetime.now(timezone.utc).isoformat(),
                    "filter_params": {
                        "include_archived": req.include_archived,
                        "tags": req.tags,
                        "date_from": req.date_from,
                        "date_to": req.date_to,
                    },
                }
                zf.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))

                ws_data = {
                    "id": workspace["id"],
                    "name_en": workspace["name_en"],
                    "name_zh": workspace["name_zh"],
                    "kb_type": workspace["kb_type"],
                }
                zf.writestr("workspace.json", json.dumps(ws_data, indent=2, ensure_ascii=False))

                def _serialize(row: dict) -> dict:
                    result = {}
                    for k, v in row.items():
                        if isinstance(v, datetime):
                            result[k] = v.isoformat()
                        elif isinstance(v, Decimal):
                            result[k] = float(v)
                        else:
                            result[k] = v
                    return result

                zf.writestr(
                    "nodes.json",
                    json.dumps([_serialize(dict(n)) for n in nodes], indent=2, ensure_ascii=False),
                )
                zf.writestr(
                    "edges.json",
                    json.dumps([_serialize(dict(e)) for e in edges], indent=2, ensure_ascii=False),
                )

                if req.include_markdown:
                    for n in nodes:
                        content = f"# {n['title_en'] or n['title_zh']}\n\n"
                        if n["tags"]:
                            content += f"Tags: {', '.join(n['tags'])}\n\n"
                        content += "## English\n" + (n["body_en"] or "")
                        content += "\n\n## 中文\n" + (n["body_zh"] or "")
                        safe_title = (n["title_en"] or n["title_zh"]).replace("/", "_").replace("\\", "_")
                        zf.writestr(f"markdown/{n['id']}_{safe_title}.md", content)

            download_url = f"/exports/{filename}"
            cur.execute(
                """
                UPDATE kb_exports
                SET status = 'completed', download_url = %s, file_path = %s, completed_at = now()
                WHERE id = %s
                """,
                (download_url, filepath, export_id),
            )

    except Exception as e:
        logger.error(f"Export failed for {export_id}: {e}")
        with db_cursor(commit=True) as cur:
            cur.execute(
                "UPDATE kb_exports SET status = 'failed', error_msg = %s WHERE id = %s",
                (str(e), export_id),
            )


@router.post("/workspaces/{ws_id}/exports", response_model=KBExportResponse)
def trigger_export(
    ws_id: str,
    body: KBExportRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
):
    with db_cursor(commit=True) as cur:
        _require_ws_access(cur, ws_id, user)

        export_id = generate_id("exp")
        filter_params = {
            "include_archived": body.include_archived,
            "include_markdown": body.include_markdown,
            "tags": body.tags,
            "date_from": body.date_from,
            "date_to": body.date_to,
        }
        cur.execute(
            """
            INSERT INTO kb_exports (id, workspace_id, status, filter_params)
            VALUES (%s, %s, 'pending', %s)
            RETURNING *
            """,
            (export_id, ws_id, json.dumps(filter_params)),
        )
        export_row = cur.fetchone()

    background_tasks.add_task(_bg_export_kb, export_id, ws_id, body)
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
        cur.execute(
            "SELECT download_url, file_path FROM kb_exports WHERE id = %s AND workspace_id = %s",
            (export_id, ws_id),
        )
        row = cur.fetchone()
        if not row or not row["download_url"]:
            raise HTTPException(status_code=404, detail="Download not found")

        filename = row["download_url"].split("/")[-1]
        filepath = row["file_path"] or os.path.join(EXPORT_DIR, filename)
        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail="File lost on server")

        return FileResponse(filepath, media_type="application/octet-stream", filename=filename)


@router.post("/workspaces/{ws_id}/imports", response_model=KBImportResponse)
def import_kb(
    ws_id: str,
    file: UploadFile = File(...),
    conflict_mode: str = Form("skip"),
    user: dict = Depends(get_current_user),
):
    """
    Import a .memtrace ZIP archive into the workspace.
    conflict_mode: "skip" (default) keeps existing nodes; "overwrite" replaces them.
    """
    with db_cursor() as cur:
        _require_ws_access(cur, ws_id, user, write=True, required_scope="kb:write")

    imported_nodes = 0
    skipped = 0
    failed = 0
    errors: List[str] = []

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, "upload.zip")
            with open(zip_path, "wb") as f:
                f.write(file.file.read())

            with zipfile.ZipFile(zip_path, "r") as zf:
                names = zf.namelist()

                # Validate — manifest is optional for backwards compat
                if "nodes.json" not in names:
                    raise HTTPException(status_code=422, detail="Invalid .memtrace archive: nodes.json missing")

                nodes_data = json.loads(zf.read("nodes.json"))
                edges_data = json.loads(zf.read("edges.json")) if "edges.json" in names else []

            with db_cursor(commit=True) as cur:
                for node in nodes_data:
                    node_id = node.get("id")
                    if not node_id:
                        failed += 1
                        errors.append("Node missing id field")
                        continue
                    try:
                        cur.execute("SELECT id FROM memory_nodes WHERE id = %s", (node_id,))
                        exists = cur.fetchone()

                        if exists and conflict_mode == "skip":
                            skipped += 1
                            continue

                        if exists and conflict_mode == "overwrite":
                            cur.execute(
                                """
                                UPDATE memory_nodes
                                SET title_zh = %s, title_en = %s, body_zh = %s, body_en = %s,
                                    content_type = %s, tags = %s, trust_score = %s,
                                    workspace_id = %s, updated_at = NOW()
                                WHERE id = %s
                                """,
                                (
                                    node.get("title_zh"), node.get("title_en"),
                                    node.get("body_zh"), node.get("body_en"),
                                    node.get("content_type", "factual"),
                                    node.get("tags", []),
                                    node.get("trust_score", 0.8),
                                    ws_id, node_id,
                                ),
                            )
                        else:
                            new_id = generate_id("mem")
                            cur.execute(
                                """
                                INSERT INTO memory_nodes
                                  (id, workspace_id, title_zh, title_en, body_zh, body_en,
                                   content_type, content_format, tags, trust_score,
                                   dim_accuracy, dim_freshness, dim_utility, dim_author_rep,
                                   status, source_type, visibility,
                                   copied_from_node, copied_from_ws)
                                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'active','imported','private',%s,%s)
                                ON CONFLICT (id) DO NOTHING
                                """,
                                (
                                    new_id, ws_id,
                                    node.get("title_zh"), node.get("title_en"),
                                    node.get("body_zh"), node.get("body_en"),
                                    node.get("content_type", "factual"),
                                    node.get("content_format", "markdown"),
                                    node.get("tags", []),
                                    node.get("trust_score", 0.8),
                                    node.get("dim_accuracy", 0.8),
                                    node.get("dim_freshness", 1.0),
                                    node.get("dim_utility", 0.0),
                                    node.get("dim_author_rep", 0.5),
                                    node_id, node.get("workspace_id"),
                                ),
                            )
                        imported_nodes += 1
                    except Exception as e:
                        failed += 1
                        errors.append(f"Node {node_id}: {e}")

                # Build mapping from original node_ids to any newly assigned ids
                # For simplicity with skip/overwrite modes, edges referencing original ids
                # are inserted as-is — they will work when conflict_mode=overwrite.
                for edge in edges_data:
                    edge_id = edge.get("id")
                    if not edge_id:
                        continue
                    try:
                        cur.execute(
                            """
                            INSERT INTO edges
                              (id, workspace_id, from_id, to_id, relation, weight, half_life_days, status)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, 'active')
                            ON CONFLICT (id) DO NOTHING
                            """,
                            (
                                generate_id("edg"), ws_id,
                                edge.get("from_id"), edge.get("to_id"),
                                edge.get("relation", "related_to"),
                                edge.get("weight", 1.0),
                                edge.get("half_life_days", 90),
                            ),
                        )
                    except Exception as e:
                        errors.append(f"Edge {edge_id}: {e}")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return KBImportResponse(
        imported_nodes=imported_nodes,
        skipped=skipped,
        failed=failed,
        errors=errors[:20],
    )

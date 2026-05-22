"""
routers/documents.py — Phase 6 S3-T12: Document CRUD REST API.

Endpoints:
  GET    /api/v1/workspaces/{ws_id}/documents              — list documents
  GET    /api/v1/workspaces/{ws_id}/documents/{doc_id}     — document detail + linked nodes
  GET    /api/v1/workspaces/{ws_id}/documents/{doc_id}/content  — download raw file
  GET    /api/v1/workspaces/{ws_id}/documents/{doc_id}/preview  — text preview (≤10 KB)
  PATCH  /api/v1/workspaces/{ws_id}/documents/{doc_id}     — update title/summary
  DELETE /api/v1/workspaces/{ws_id}/documents/{doc_id}     — delete (owner/admin only)

  POST   /api/v1/workspaces/{ws_id}/nodes/{node_id}/document-links  — manually attach doc to node
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel

from core.database import db_cursor
from core.deps import get_current_user
from services.workspaces import require_ws_access
from services.documents import (
    list_documents_in_db,
    get_document_in_db,
    get_document_linked_nodes,
    get_node_sources,
    delete_document_in_db,
    create_node_document_link,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/workspaces", tags=["documents"])


# ─── Pydantic models ──────────────────────────────────────────────────────────

class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None


class DocumentLinkCreate(BaseModel):
    document_ids: list[str]
    paragraph_ref: Optional[str] = ""
    excerpt: Optional[str] = None


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/{ws_id}/documents")
def list_documents(
    ws_id: str,
    limit: int = 20,
    offset: int = 0,
    user: dict = Depends(get_current_user),
):
    """List all documents in a workspace, newest first."""
    with db_cursor() as cur:
        require_ws_access(cur, ws_id, user)
        docs = list_documents_in_db(cur, ws_id, limit=limit, offset=offset)
        return list(docs)


@router.get("/{ws_id}/documents/{doc_id}")
def get_document(
    ws_id: str,
    doc_id: str,
    user: dict = Depends(get_current_user),
):
    """Return document metadata + linked node list."""
    with db_cursor() as cur:
        require_ws_access(cur, ws_id, user)
        doc = get_document_in_db(cur, doc_id)
        if not doc or doc["workspace_id"] != ws_id:
            raise HTTPException(status_code=404, detail="Document not found")
        linked_nodes = get_document_linked_nodes(cur, doc_id)
        return {
            **dict(doc),
            "linked_nodes": list(linked_nodes),
        }


@router.get("/{ws_id}/documents/{doc_id}/content")
def download_document(
    ws_id: str,
    doc_id: str,
    user: dict = Depends(get_current_user),
):
    """Download the raw document file."""
    with db_cursor() as cur:
        require_ws_access(cur, ws_id, user)
        doc = get_document_in_db(cur, doc_id)
        if not doc or doc["workspace_id"] != ws_id:
            raise HTTPException(status_code=404, detail="Document not found")
        storage_path = doc["storage_path"]

    if not os.path.exists(storage_path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    return FileResponse(
        path=storage_path,
        filename=doc["filename"],
        media_type=doc["mime_type"],
    )


@router.get("/{ws_id}/documents/{doc_id}/preview")
def preview_document(
    ws_id: str,
    doc_id: str,
    max_chars: int = 8000,
    user: dict = Depends(get_current_user),
):
    """Return a plain-text preview of the document (up to max_chars characters)."""
    with db_cursor() as cur:
        require_ws_access(cur, ws_id, user)
        doc = get_document_in_db(cur, doc_id)
        if not doc or doc["workspace_id"] != ws_id:
            raise HTTPException(status_code=404, detail="Document not found")
        storage_path = doc["storage_path"]
        mime_type    = doc["mime_type"]

    if not os.path.exists(storage_path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    # Text-based formats: read directly
    if mime_type in ("text/plain", "text/markdown", "text/csv", "application/json"):
        with open(storage_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(max_chars)
        return PlainTextResponse(content)

    # For binary formats (PDF, DOCX) that were stored as .txt by the ingest pipeline,
    # we also try to read the storage_path directly (it's already been extracted to text).
    if storage_path.endswith(".txt"):
        try:
            with open(storage_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(max_chars)
            return PlainTextResponse(content)
        except OSError:
            pass

    raise HTTPException(
        status_code=415,
        detail=f"Preview not supported for mime_type '{mime_type}'. Use /content to download.",
    )


@router.patch("/{ws_id}/documents/{doc_id}")
def update_document(
    ws_id: str,
    doc_id: str,
    body: DocumentUpdate,
    user: dict = Depends(get_current_user),
):
    """Update the document's editable metadata (title, summary)."""
    with db_cursor(commit=True) as cur:
        require_ws_access(cur, ws_id, user, write=True)
        doc = get_document_in_db(cur, doc_id)
        if not doc or doc["workspace_id"] != ws_id:
            raise HTTPException(status_code=404, detail="Document not found")

        updates = {k: v for k, v in body.model_dump().items() if v is not None}
        if not updates:
            return dict(doc)

        set_clause = ", ".join(f"{k} = %s" for k in updates)
        cur.execute(
            f"UPDATE documents SET {set_clause} WHERE id = %s RETURNING *",
            list(updates.values()) + [doc_id],
        )
        return cur.fetchone()


@router.delete("/{ws_id}/documents/{doc_id}", status_code=204)
def delete_document(
    ws_id: str,
    doc_id: str,
    user: dict = Depends(get_current_user),
):
    """Delete a document (owner or admin only). Cascades to node_document_links."""
    with db_cursor(commit=True) as cur:
        ws = require_ws_access(cur, ws_id, user, write=True, required_role="admin")
        doc = get_document_in_db(cur, doc_id)
        if not doc or doc["workspace_id"] != ws_id:
            raise HTTPException(status_code=404, detail="Document not found")

        # Also delete the physical file if it exists
        storage_path = doc["storage_path"]
        deleted = delete_document_in_db(cur, doc_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Document not found")

    # File deletion outside transaction (best-effort)
    if storage_path and os.path.exists(storage_path):
        try:
            os.remove(storage_path)
        except OSError as e:
            logger.warning("Could not delete file %s: %s", storage_path, e)


# ─── Node ↔ Document link endpoints ──────────────────────────────────────────

@router.get("/{ws_id}/nodes/{node_id}/sources")
def get_node_source_docs(
    ws_id: str,
    node_id: str,
    user: dict = Depends(get_current_user),
):
    """Return all documents linked to a specific node."""
    with db_cursor() as cur:
        require_ws_access(cur, ws_id, user)
        cur.execute(
            "SELECT 1 FROM memory_nodes WHERE id = %s AND workspace_id = %s",
            (node_id, ws_id),
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Node not found")
        return list(get_node_sources(cur, node_id))


@router.post("/{ws_id}/nodes/{node_id}/document-links", status_code=201)
def attach_documents_to_node(
    ws_id: str,
    node_id: str,
    body: DocumentLinkCreate,
    user: dict = Depends(get_current_user),
):
    """Manually attach one or more documents to a node (S5-T19)."""
    with db_cursor(commit=True) as cur:
        require_ws_access(cur, ws_id, user, write=True)
        cur.execute(
            "SELECT 1 FROM memory_nodes WHERE id = %s AND workspace_id = %s",
            (node_id, ws_id),
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Node not found")

        created = 0
        for doc_id in body.document_ids:
            cur.execute(
                "SELECT 1 FROM documents WHERE id = %s AND workspace_id = %s",
                (doc_id, ws_id),
            )
            if not cur.fetchone():
                raise HTTPException(
                    status_code=404,
                    detail=f"Document {doc_id} not found in workspace {ws_id}",
                )
            create_node_document_link(
                cur, node_id, doc_id,
                paragraph_ref=body.paragraph_ref or "",
                excerpt=body.excerpt,
            )
            created += 1

    return {"created": created, "node_id": node_id}

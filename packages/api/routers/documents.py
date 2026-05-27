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

import hashlib
import logging
import uuid as _uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, RedirectResponse
from pydantic import BaseModel

from core.database import db_cursor
from core.deps import get_current_user
from services.workspaces import require_ws_access
from core.security import generate_id
from core.storage import get_storage, Storage
from services.documents import (
    list_documents_in_db,
    get_document_in_db,
    get_document_linked_nodes,
    get_node_sources,
    delete_document_in_db,
    create_node_document_link,
    create_document_in_db,
    create_url_document_in_db,
    get_existing_document,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/workspaces", tags=["documents"])


# ─── Pydantic models ──────────────────────────────────────────────────────────

class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    filename: Optional[str] = None   # S5-T21: allow renaming via dedup dialog


class DocumentLinkCreate(BaseModel):
    document_ids: list[str]
    paragraph_ref: Optional[str] = ""
    excerpt: Optional[str] = None


class UrlDocumentCreate(BaseModel):
    url: str
    title: Optional[str] = None
    node_id: Optional[str] = None  # attach to node immediately if given


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/{ws_id}/documents/upload", status_code=201)
async def upload_document_direct(
    ws_id: str,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
    storage: Storage = Depends(get_storage),
):
    """
    Upload a raw file as a document record WITHOUT AI extraction (S5-T19).
    Stores the file via the configured storage backend (S5-T22) and creates
    a `documents` table entry.
    Duplicate files (same content hash within the workspace) return 409
    so the UI can present the dedup dialog (S5-T21).
    """
    with db_cursor() as cur:
        require_ws_access(cur, ws_id, user, write=True)

    file_bytes = await file.read()
    if len(file_bytes) > 30 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 30 MB)")
    content_hash = hashlib.sha256(file_bytes).hexdigest()
    filename = file.filename or "upload"
    mime_type = file.content_type or "application/octet-stream"

    # If a document with identical content already exists in this workspace,
    # return 409 so the UI can present the dedup dialog (S5-T21).
    with db_cursor() as cur:
        existing = get_existing_document(cur, ws_id, content_hash)
        if existing:
            return JSONResponse(
                status_code=409,
                content={
                    "code": "DUPLICATE_CONTENT",
                    "message": (
                        f"A document with the same content already exists: "
                        f"'{existing['filename']}'"
                    ),
                    "existing_document": {
                        k: (v.isoformat() if hasattr(v, "isoformat") else v)
                        for k, v in dict(existing).items()
                    },
                },
            )

    # Persist bytes via storage backend (S5-T22)
    storage_path = storage.make_path(ws_id, f"{_uuid.uuid4().hex}_{filename}")
    storage.put(storage_path, file_bytes)

    # Create the documents record
    with db_cursor(commit=True) as cur:
        row = create_document_in_db(
            cur,
            workspace_id=ws_id,
            filename=filename,
            file_bytes=file_bytes,
            mime_type=mime_type,
            storage_path=storage_path,
            uploaded_by=user["sub"],
        )
        if row is None:
            # Concurrent duplicate — fetch the winner
            row = get_existing_document(cur, ws_id, content_hash)

    # Re-fetch with computed linked_node_count
    with db_cursor() as cur:
        full = get_document_in_db(cur, row["id"])
    return dict(full)


@router.post("/{ws_id}/documents/link-url", status_code=201)
def attach_url_document(
    ws_id: str,
    body: UrlDocumentCreate,
    user: dict = Depends(get_current_user),
):
    """Register an external URL as a document and optionally attach it to a node."""
    if not body.url.startswith(("http://", "https://")):
        raise HTTPException(status_code=422, detail="URL must start with http:// or https://")
    with db_cursor(commit=True) as cur:
        require_ws_access(cur, ws_id, user, write=True)
        row = create_url_document_in_db(cur, ws_id, body.url, user["sub"], title=body.title)
        if row is None:
            import hashlib as _hl
            ch = _hl.sha256(body.url.encode()).hexdigest()
            row = get_existing_document(cur, ws_id, ch)
        if body.node_id:
            cur.execute(
                "SELECT 1 FROM memory_nodes WHERE id = %s AND workspace_id = %s",
                (body.node_id, ws_id),
            )
            if cur.fetchone():
                create_node_document_link(cur, body.node_id, row["id"])
    with db_cursor() as cur:
        full = get_document_in_db(cur, row["id"])
    return dict(full)


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
    storage: Storage = Depends(get_storage),
):
    """Download the raw document file."""
    with db_cursor() as cur:
        require_ws_access(cur, ws_id, user)
        doc = get_document_in_db(cur, doc_id)
        if not doc or doc["workspace_id"] != ws_id:
            raise HTTPException(status_code=404, detail="Document not found")
        storage_path = doc["storage_path"]
        source_url = doc.get("source_url")

    # URL-only document — redirect to the external link
    if not storage_path and source_url:
        return RedirectResponse(url=source_url, status_code=302)

    if not storage.exists(storage_path):
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
    storage: Storage = Depends(get_storage),
):
    """Return a plain-text preview of the document (up to max_chars characters)."""
    with db_cursor() as cur:
        require_ws_access(cur, ws_id, user)
        doc = get_document_in_db(cur, doc_id)
        if not doc or doc["workspace_id"] != ws_id:
            raise HTTPException(status_code=404, detail="Document not found")
        storage_path = doc["storage_path"]
        mime_type    = doc["mime_type"]

    # URL-only documents have no file to preview
    if not storage_path:
        raise HTTPException(
            status_code=415,
            detail="Preview not available for URL-only documents.",
        )

    if not storage.exists(storage_path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    # Text-based formats and ingest-extracted .txt files: read via storage
    if mime_type in ("text/plain", "text/markdown", "text/csv", "application/json") or storage_path.endswith(".txt"):
        try:
            raw = storage.get(storage_path)
            content = raw.decode("utf-8", errors="replace")[:max_chars]
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
    """Update the document's editable metadata (title, summary, filename)."""
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
    storage: Storage = Depends(get_storage),
):
    """Delete a document (owner or admin only). Cascades to node_document_links."""
    with db_cursor(commit=True) as cur:
        require_ws_access(cur, ws_id, user, write=True, required_role="admin")
        doc = get_document_in_db(cur, doc_id)
        if not doc or doc["workspace_id"] != ws_id:
            raise HTTPException(status_code=404, detail="Document not found")

        storage_path = doc["storage_path"]
        deleted = delete_document_in_db(cur, doc_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Document not found")

    # File deletion outside transaction — best-effort via storage backend
    if storage_path:
        storage.delete(storage_path)


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


@router.delete("/{ws_id}/nodes/{node_id}/document-links/{doc_id}", status_code=204)
def detach_document_from_node(
    ws_id: str,
    node_id: str,
    doc_id: str,
    user: dict = Depends(get_current_user),
):
    """Remove a document ↔ node link without deleting either record."""
    with db_cursor(commit=True) as cur:
        require_ws_access(cur, ws_id, user, write=True)
        cur.execute(
            """
            DELETE FROM node_document_links
            WHERE node_id = %s AND document_id = %s
            """,
            (node_id, doc_id),
        )


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

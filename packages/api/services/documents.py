"""
services/documents.py — Document entity dataclasses and DB helpers.

Phase 6: Documents as first-class citizens.
This module defines the data models for the `documents` table and
`node_document_links` join table, plus lightweight DB helpers used by
routers/documents.py and services/ingest/pipeline.py.
"""
from __future__ import annotations

import hashlib
import os
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass, field

from core.security import generate_id


# ─── Dataclasses ─────────────────────────────────────────────────────────────

@dataclass
class Document:
    id: str
    workspace_id: str
    filename: str
    content_hash: str
    mime_type: str
    size_bytes: int
    storage_path: str
    uploaded_by: str
    uploaded_at: datetime
    title: Optional[str] = None
    summary: Optional[str] = None
    source_url: Optional[str] = None
    ingestion_job_id: Optional[str] = None

    @classmethod
    def from_row(cls, row: dict) -> "Document":
        return cls(**{k: row[k] for k in cls.__dataclass_fields__ if k in row})


@dataclass
class NodeDocumentLink:
    node_id: str
    document_id: str
    paragraph_ref: str
    excerpt: Optional[str] = None
    created_at: Optional[datetime] = None

    @classmethod
    def from_row(cls, row: dict) -> "NodeDocumentLink":
        return cls(**{k: row[k] for k in cls.__dataclass_fields__ if k in row})


# ─── DB Helpers ───────────────────────────────────────────────────────────────

def create_document_in_db(
    cur,
    workspace_id: str,
    filename: str,
    file_bytes: bytes,
    mime_type: str,
    storage_path: str,
    uploaded_by: str,
    ingestion_job_id: Optional[str] = None,
    title: Optional[str] = None,
    summary: Optional[str] = None,
    source_url: Optional[str] = None,
) -> dict:
    """Insert a document record. Returns the inserted row as dict.
    Raises nothing on duplicate hash — caller should check first.
    """
    doc_id = generate_id("doc")
    content_hash = hashlib.sha256(file_bytes).hexdigest()
    size_bytes = len(file_bytes)

    cur.execute(
        """
        INSERT INTO documents (
            id, workspace_id, filename, content_hash, mime_type,
            size_bytes, storage_path, title, summary, source_url,
            uploaded_by, ingestion_job_id
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (workspace_id, content_hash) DO NOTHING
        RETURNING *
        """,
        (
            doc_id, workspace_id, filename, content_hash, mime_type,
            size_bytes, storage_path, title, summary, source_url,
            uploaded_by, ingestion_job_id,
        ),
    )
    return cur.fetchone()


def get_existing_document(cur, workspace_id: str, content_hash: str) -> Optional[dict]:
    """Return existing document by content hash within a workspace."""
    cur.execute(
        "SELECT * FROM documents WHERE workspace_id = %s AND content_hash = %s",
        (workspace_id, content_hash),
    )
    return cur.fetchone()


def create_node_document_link(
    cur,
    node_id: str,
    document_id: str,
    paragraph_ref: str = "",
    excerpt: Optional[str] = None,
) -> None:
    """Create a node ↔ document link. Silently ignores duplicates."""
    cur.execute(
        """
        INSERT INTO node_document_links (node_id, document_id, paragraph_ref, excerpt)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT DO NOTHING
        """,
        (node_id, document_id, paragraph_ref, excerpt[:500] if excerpt else None),
    )


def list_documents_in_db(
    cur,
    workspace_id: str,
    limit: int = 20,
    offset: int = 0,
) -> List[dict]:
    """List documents for a workspace, newest first."""
    cur.execute(
        """
        SELECT d.*,
               count(ndl.node_id) AS linked_node_count
        FROM documents d
        LEFT JOIN node_document_links ndl ON ndl.document_id = d.id
        WHERE d.workspace_id = %s
        GROUP BY d.id
        ORDER BY d.uploaded_at DESC
        LIMIT %s OFFSET %s
        """,
        (workspace_id, limit, offset),
    )
    return cur.fetchall()


def get_document_in_db(cur, document_id: str) -> Optional[dict]:
    """Fetch a single document with its linked node count."""
    cur.execute(
        """
        SELECT d.*,
               count(ndl.node_id) AS linked_node_count
        FROM documents d
        LEFT JOIN node_document_links ndl ON ndl.document_id = d.id
        WHERE d.id = %s
        GROUP BY d.id
        """,
        (document_id,),
    )
    return cur.fetchone()


def get_document_linked_nodes(cur, document_id: str) -> List[dict]:
    """Return memory nodes linked to a document."""
    cur.execute(
        """
        SELECT n.id, n.title, n.content_type, n.status,
               ndl.paragraph_ref, ndl.excerpt
        FROM node_document_links ndl
        JOIN memory_nodes n ON n.id = ndl.node_id
        WHERE ndl.document_id = %s
          AND n.status = 'active'
        ORDER BY ndl.paragraph_ref
        """,
        (document_id,),
    )
    return cur.fetchall()


def get_node_sources(cur, node_id: str) -> List[dict]:
    """Return documents linked to a node."""
    cur.execute(
        """
        SELECT d.id, d.filename, d.title, d.mime_type, d.uploaded_at,
               ndl.paragraph_ref, ndl.excerpt
        FROM node_document_links ndl
        JOIN documents d ON d.id = ndl.document_id
        WHERE ndl.node_id = %s
        ORDER BY d.uploaded_at DESC
        """,
        (node_id,),
    )
    return cur.fetchall()


def delete_document_in_db(cur, document_id: str) -> Optional[dict]:
    """Delete a document record (CASCADE removes node_document_links)."""
    cur.execute(
        "DELETE FROM documents WHERE id = %s RETURNING *",
        (document_id,),
    )
    return cur.fetchone()

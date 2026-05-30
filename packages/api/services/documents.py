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
    node_id: Optional[str] = None  # P61-T01: corresponding memory_node id

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
    evidence_type: str = "human_upload",
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
            uploaded_by, ingestion_job_id, evidence_type
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (workspace_id, content_hash) DO NOTHING
        RETURNING *
        """,
        (
            doc_id, workspace_id, filename, content_hash, mime_type,
            size_bytes, storage_path, title, summary, source_url,
            uploaded_by, ingestion_job_id, evidence_type
        ),
    )
    return cur.fetchone()


def create_url_document_in_db(
    cur,
    workspace_id: str,
    source_url: str,
    uploaded_by: str,
    title: Optional[str] = None,
) -> dict:
    """Insert a URL-only document (no file). content_hash = sha256(url)."""
    import urllib.parse
    doc_id = generate_id("doc")
    content_hash = hashlib.sha256(source_url.encode()).hexdigest()
    filename = urllib.parse.urlparse(source_url).netloc or source_url[:80]

    cur.execute(
        """
        INSERT INTO documents (
            id, workspace_id, filename, content_hash, mime_type,
            size_bytes, storage_path, title, source_url, uploaded_by
        )
        VALUES (%s, %s, %s, %s, 'text/uri-list', 0, '', %s, %s, %s)
        ON CONFLICT (workspace_id, content_hash) DO NOTHING
        RETURNING *
        """,
        (doc_id, workspace_id, filename, content_hash, title, source_url, uploaded_by),
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
    """Return documents linked to a node.

    P61-T01: Reads from extracted_from edges first.  Falls back to the legacy
    node_document_links junction table for rows not yet migrated.
    """
    # Primary path: edges (P61-T01)
    edge_rows = get_node_sources_via_edges(cur, node_id)

    # Fallback / legacy path: junction table (kept until Phase 6.2 drops it)
    cur.execute(
        """
        SELECT d.id, d.filename, d.title, d.mime_type, d.size_bytes,
               d.source_url, d.uploaded_at, d.evidence_type, ndl.paragraph_ref, ndl.excerpt
        FROM node_document_links ndl
        JOIN documents d ON d.id = ndl.document_id
        WHERE ndl.node_id = %s
        ORDER BY d.uploaded_at DESC
        """,
        (node_id,),
    )
    link_rows = cur.fetchall()

    # Merge: prefer edge rows; suppress duplicates by doc id
    seen_doc_ids = {r["id"] for r in edge_rows}
    merged = list(edge_rows)
    for r in link_rows:
        if r["id"] not in seen_doc_ids:
            merged.append(r)

    return merged


def delete_document_in_db(cur, document_id: str) -> Optional[dict]:
    """Delete a document record (CASCADE removes node_document_links)."""
    cur.execute(
        "DELETE FROM documents WHERE id = %s RETURNING *",
        (document_id,),
    )
    return cur.fetchone()


# ─── P61-T01: Document node helpers ──────────────────────────────────────────

def create_document_node_in_db(
    cur,
    workspace_id: str,
    doc_id: str,
    filename: str,
    author: str,
    summary: Optional[str] = None,
) -> dict:
    """Create a memory_node with content_type='document' for the given document.

    Returns the inserted node row.  The caller is responsible for updating
    ``documents.node_id`` with the returned id.
    """
    from core.security import generate_id, compute_signature

    node_id = generate_id("mem")
    title = filename
    body = summary or f"Document: {filename}"
    sig = compute_signature(title, {"type": "document", "format": "plain", "body": body}, [], author)

    cur.execute(
        """
        INSERT INTO memory_nodes (
            id, workspace_id, title, content_type, content_format, body,
            tags, visibility, author, signature, source_type,
            status, trust_score, dim_author_rep, dim_freshness,
            updated_at
        ) VALUES (
            %s, %s, %s, 'document', 'plain', %s,
            '{}', 'private', %s, %s, 'document',
            'active', 0.7, 0.7, 1.0,
            now()
        )
        RETURNING id, workspace_id, title, content_type, body, author, status
        """,
        (node_id, workspace_id, title, body, author, sig),
    )
    row = cur.fetchone()

    # Link documents.node_id back
    cur.execute("UPDATE documents SET node_id = %s WHERE id = %s", (node_id, doc_id))
    return row


def get_document_node(cur, doc_id: str) -> Optional[dict]:
    """Return the memory_node associated with a document (via documents.node_id)."""
    cur.execute(
        """
        SELECT n.*
        FROM documents d
        JOIN memory_nodes n ON n.id = d.node_id
        WHERE d.id = %s
        """,
        (doc_id,),
    )
    return cur.fetchone()


def create_extracted_from_edge(
    cur,
    workspace_id: str,
    from_node_id: str,
    doc_node_id: str,
    paragraph_ref: str = "",
    excerpt: Optional[str] = None,
) -> None:
    """Insert an extracted_from edge from a knowledge node to its document node.

    Silently ignores duplicates (ON CONFLICT DO NOTHING).
    """
    from core.security import generate_id
    import json

    edge_id = generate_id("edge")
    meta = {}
    if paragraph_ref:
        meta["paragraph_ref"] = paragraph_ref
    if excerpt:
        meta["excerpt"] = excerpt[:500]

    cur.execute(
        """
        INSERT INTO edges (
            id, workspace_id, from_id, to_id, relation,
            weight, status, source_type, proposer, metadata
        )
        VALUES (%s, %s, %s, %s, 'extracted_from', 1.0, 'active', 'document', 'ingest_pipeline', %s)
        ON CONFLICT (from_id, to_id, relation) DO NOTHING
        """,
        (edge_id, workspace_id, from_node_id, doc_node_id, json.dumps(meta)),
    )


def get_node_sources_via_edges(cur, node_id: str) -> List[dict]:
    """Return documents linked to a node via extracted_from edges (P61-T01 path)."""
    cur.execute(
        """
        SELECT d.id, d.filename, d.title, d.mime_type, d.size_bytes,
               d.source_url, d.uploaded_at, d.evidence_type,
               e.metadata->>'paragraph_ref'  AS paragraph_ref,
               e.metadata->>'excerpt'         AS excerpt
        FROM edges e
        JOIN documents d ON d.node_id = e.to_id
        WHERE e.from_id = %s
          AND e.relation = 'extracted_from'
          AND e.status   = 'active'
        ORDER BY d.uploaded_at DESC
        """,
        (node_id,),
    )
    return cur.fetchall()

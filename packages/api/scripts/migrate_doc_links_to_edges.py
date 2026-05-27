"""
scripts/migrate_doc_links_to_edges.py
Phase 6.1 T01 — One-time migration: create document nodes + extracted_from edges.

Actions:
  1. For every document that has no node_id, create a memory_node
     (content_type='document', title=filename, body=summary or placeholder).
  2. For every node_document_links row, insert an extracted_from edge
     from the knowledge node to the document's memory_node.

Usage:
    python -m scripts.migrate_doc_links_to_edges [--dry-run] [--ws-id <id>]

Idempotent: safe to re-run.  Already-created nodes and edges are skipped.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import os

# Allow running from /packages/api directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import db_cursor
from core.security import generate_id, compute_signature

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _create_doc_node(cur, ws_id: str, doc_id: str, filename: str, author: str, summary: str | None) -> str:
    """Insert a document memory_node and update documents.node_id. Returns new node id."""
    node_id = generate_id("mem")
    title = filename or f"Document {doc_id}"
    body = summary or f"Document: {title}"
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
        ON CONFLICT DO NOTHING
        RETURNING id
        """,
        (node_id, ws_id, title, body, author, sig),
    )
    row = cur.fetchone()
    if row:
        node_id = row["id"]
        cur.execute("UPDATE documents SET node_id = %s WHERE id = %s", (node_id, doc_id))
        return node_id
    else:
        # Conflict — fetch existing (shouldn't happen but be safe)
        cur.execute("SELECT node_id FROM documents WHERE id = %s", (doc_id,))
        existing = cur.fetchone()
        return existing["node_id"] if existing else node_id


def _create_edge(cur, ws_id: str, from_id: str, to_id: str, para_ref: str, excerpt: str | None) -> bool:
    """Insert extracted_from edge. Returns True if inserted, False if already existed."""
    edge_id = generate_id("edge")
    meta = {}
    if para_ref:
        meta["paragraph_ref"] = para_ref
    if excerpt:
        meta["excerpt"] = excerpt[:500]

    cur.execute(
        """
        INSERT INTO edges (
            id, workspace_id, from_id, to_id, relation,
            weight, status, source_type, proposer, metadata
        )
        VALUES (%s, %s, %s, %s, 'extracted_from', 1.0, 'active', 'document', 'migration_p61', %s)
        ON CONFLICT (from_id, to_id, relation) DO NOTHING
        """,
        (edge_id, ws_id, from_id, to_id, json.dumps(meta)),
    )
    return cur.rowcount > 0


def run(dry_run: bool = False, ws_id_filter: str | None = None):
    # ── Step 1: Create document nodes for docs that lack one ─────────────────
    with db_cursor() as cur:
        ws_filter = "AND d.workspace_id = %s" if ws_id_filter else ""
        params = (ws_id_filter,) if ws_id_filter else ()
        cur.execute(
            f"""
            SELECT d.id, d.workspace_id, d.filename, d.summary, d.uploaded_by
            FROM documents d
            WHERE d.node_id IS NULL
            {ws_filter}
            ORDER BY d.uploaded_at ASC
            """,
            params,
        )
        docs_without_nodes = cur.fetchall()

    logger.info(f"Documents without node_id: {len(docs_without_nodes)}")

    nodes_created = 0
    if not dry_run:
        for doc in docs_without_nodes:
            with db_cursor(commit=True) as cur:
                _create_doc_node(
                    cur,
                    doc["workspace_id"],
                    doc["id"],
                    doc["filename"] or "",
                    doc["uploaded_by"],
                    doc.get("summary"),
                )
            nodes_created += 1
            if nodes_created % 10 == 0:
                logger.info(f"  Created {nodes_created}/{len(docs_without_nodes)} document nodes...")
    else:
        logger.info(f"[dry-run] Would create {len(docs_without_nodes)} document nodes")

    logger.info(f"Document nodes created: {nodes_created}")

    # ── Step 2: Create extracted_from edges for node_document_links ──────────
    with db_cursor() as cur:
        ws_filter = "AND d.workspace_id = %s" if ws_id_filter else ""
        params2 = (ws_id_filter,) if ws_id_filter else ()
        cur.execute(
            f"""
            SELECT ndl.node_id, ndl.document_id, ndl.paragraph_ref, ndl.excerpt,
                   d.node_id AS doc_node_id, d.workspace_id
            FROM node_document_links ndl
            JOIN documents d ON d.id = ndl.document_id
            WHERE d.node_id IS NOT NULL
            {ws_filter}
            ORDER BY ndl.created_at ASC
            """,
            params2,
        )
        links = cur.fetchall()

    logger.info(f"node_document_links to migrate: {len(links)}")

    edges_created = 0
    edges_skipped = 0

    if not dry_run:
        for lnk in links:
            if not lnk["doc_node_id"]:
                logger.warning(f"  Skipping link {lnk['node_id']}→{lnk['document_id']}: doc has no node_id yet")
                edges_skipped += 1
                continue
            with db_cursor(commit=True) as cur:
                inserted = _create_edge(
                    cur,
                    lnk["workspace_id"],
                    lnk["node_id"],
                    lnk["doc_node_id"],
                    lnk["paragraph_ref"] or "",
                    lnk.get("excerpt"),
                )
            if inserted:
                edges_created += 1
            else:
                edges_skipped += 1

            if (edges_created + edges_skipped) % 50 == 0:
                logger.info(f"  Processed {edges_created + edges_skipped}/{len(links)} links...")
    else:
        logger.info(f"[dry-run] Would create up to {len(links)} extracted_from edges")

    logger.info(f"Edges created: {edges_created}  |  Skipped (already existed): {edges_skipped}")

    # ── Step 3: Verify ────────────────────────────────────────────────────────
    if not dry_run:
        with db_cursor() as cur:
            cur.execute("SELECT count(*) AS n FROM documents WHERE node_id IS NULL")
            remaining = cur.fetchone()["n"]
            cur.execute("SELECT count(*) AS n FROM edges WHERE relation = 'extracted_from'")
            total_edges = cur.fetchone()["n"]

        logger.info(f"\n=== Verification ===")
        logger.info(f"Documents still without node_id: {remaining}")
        logger.info(f"Total extracted_from edges: {total_edges}")
        if remaining > 0:
            logger.warning(f"  {remaining} documents still lack a node. Re-run after uploading those files.")


def main():
    parser = argparse.ArgumentParser(description="Migrate node_document_links → extracted_from edges (P61-T01)")
    parser.add_argument("--dry-run", action="store_true", help="Print plan without writing")
    parser.add_argument("--ws-id", metavar="ID", help="Limit to a single workspace")
    args = parser.parse_args()
    run(dry_run=args.dry_run, ws_id_filter=args.ws_id)


if __name__ == "__main__":
    main()

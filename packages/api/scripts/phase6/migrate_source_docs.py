"""
scripts/phase6/migrate_source_docs.py — S2-T09: Migrate source_document nodes to documents table.

For every memory_node with content_type='source_document':
  1. Compute content_hash from body_zh (the stored raw content)
  2. Write the content to disk at ./data/documents/{ws_id}/{doc_id}.txt
  3. Insert into documents table
  4. For every child node (nodes where source_doc_node_id = this node's id),
     insert a node_document_link
  5. Delete the source_document node

Note: The final DROP of 'source_document' from the content_type enum
      is performed manually via 056_drop_source_doc_enum.sql after this
      migration completes (enum removal requires table rebuild in PostgreSQL).

Usage (via CLI):
    python -m scripts.phase6 migrate-source-docs [--dry-run] [--ws-id <id>]
"""
from __future__ import annotations

import hashlib
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


def _get_storage_root() -> str:
    """Return the base directory for document storage."""
    return os.environ.get("DOCUMENT_STORAGE_PATH", "./data/documents")


def _write_file(storage_path: str, content: str) -> None:
    """Write content to disk, creating parent directories as needed."""
    os.makedirs(os.path.dirname(storage_path), exist_ok=True)
    with open(storage_path, "w", encoding="utf-8") as f:
        f.write(content)


def migrate_one(cur, node: dict, dry_run: bool, verbose: bool) -> bool:
    """
    Migrate a single source_document node. Returns True on success.
    """
    from core.security import generate_id

    node_id    = node["id"]
    ws_id      = node["workspace_id"]
    filename   = node.get("source_file") or node.get("source_document") or f"doc_{node_id}.txt"
    content    = node.get("body_zh") or node.get("body_en") or ""
    author     = node.get("author") or "system"
    job_id     = None  # source_document nodes don't carry this reliably

    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    doc_id       = generate_id("doc")
    storage_path = os.path.join(_get_storage_root(), ws_id, f"{doc_id}.txt")

    if verbose:
        logger.info(
            "  Migrating node=%s → doc=%s  file=%s  chars=%d",
            node_id, doc_id, filename, len(content),
        )

    if dry_run:
        logger.info(
            "  [DRY-RUN] Would create doc=%s for node=%s (ws=%s)", doc_id, node_id, ws_id
        )
        return True

    # Write file to disk
    try:
        _write_file(storage_path, content)
    except OSError as e:
        logger.error("Failed to write %s: %s", storage_path, e)
        return False

    # Insert into documents (skip if duplicate content_hash in same workspace)
    cur.execute(
        "SELECT id FROM documents WHERE workspace_id = %s AND content_hash = %s",
        (ws_id, content_hash),
    )
    existing = cur.fetchone()
    if existing:
        doc_id = existing["id"]
        logger.debug("  Reusing existing doc=%s for node=%s", doc_id, node_id)
    else:
        cur.execute(
            """
            INSERT INTO documents (
                id, workspace_id, filename, content_hash, mime_type,
                size_bytes, storage_path, title, uploaded_by, ingestion_job_id
            )
            VALUES (%s, %s, %s, %s, 'text/plain', %s, %s, %s, %s, %s)
            """,
            (
                doc_id, ws_id, filename, content_hash,
                len(content.encode("utf-8")),
                storage_path,
                node.get("title_zh") or node.get("title_en"),
                author,
                job_id,
            ),
        )

    # Find child nodes (those pointing to this source_document node)
    cur.execute(
        """
        SELECT id, source_paragraph_ref, body_zh, body_en
        FROM memory_nodes
        WHERE source_doc_node_id = %s AND status != 'archived'
        """,
        (node_id,),
    )
    children = cur.fetchall()
    for child in children:
        para_ref = child.get("source_paragraph_ref") or ""
        excerpt  = (child.get("body_zh") or child.get("body_en") or "")[:500]
        cur.execute(
            """
            INSERT INTO node_document_links (node_id, document_id, paragraph_ref, excerpt)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT DO NOTHING
            """,
            (child["id"], doc_id, para_ref, excerpt),
        )

    # Delete the source_document node
    cur.execute("DELETE FROM memory_nodes WHERE id = %s", (node_id,))
    return True


def run(
    dry_run: bool = False,
    ws_id: Optional[str] = None,
    verbose: bool = False,
):
    """Main entry point for migrate-source-docs command."""
    from core.database import db_cursor

    with db_cursor(commit=not dry_run) as cur:
        # Check documents table exists
        cur.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_name = 'documents'"
        )
        if not cur.fetchone():
            logger.error("documents table does not exist — apply 051_documents.sql first.")
            return

        # Fetch source_document nodes
        ws_filter = "AND workspace_id = %s" if ws_id else ""
        params = [ws_id] if ws_id else []

        try:
            cur.execute(
                f"""
                SELECT * FROM memory_nodes
                WHERE content_type = 'source_document'
                  {ws_filter}
                ORDER BY workspace_id, created_at
                """,
                params,
            )
        except Exception as e:
            logger.error(
                "Could not query source_document nodes (enum may already be removed): %s", e
            )
            return

        nodes = cur.fetchall()
        logger.info(
            "Found %d source_document node(s) to migrate%s.",
            len(nodes), " (dry-run)" if dry_run else "",
        )

        success = 0
        failed  = 0
        for node in nodes:
            ok = migrate_one(cur, dict(node), dry_run=dry_run, verbose=verbose)
            if ok:
                success += 1
            else:
                failed += 1

    logger.info(
        "migrate-source-docs complete: %d migrated, %d failed%s.",
        success, failed, " (dry-run)" if dry_run else "",
    )
    if not dry_run and failed == 0:
        logger.info(
            "✅ All source_document nodes migrated. You can now apply 056_drop_source_doc_enum.sql."
        )

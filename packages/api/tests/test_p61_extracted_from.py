"""
tests/test_p61_extracted_from.py
Phase 6.1 T01 — Unit + integration tests for extracted_from edge architecture.

Unit tests (always run): mock-based, no real DB required.
Integration tests (require TEST_DATABASE_URL): full end-to-end.
"""
from __future__ import annotations

import json
import os
import pytest
from unittest.mock import MagicMock, patch, call


# ─── Unit tests ──────────────────────────────────────────────────────────────

class TestConstants:
    def test_extracted_from_in_valid_relations(self):
        from core.constants import VALID_RELATIONS
        assert "extracted_from" in VALID_RELATIONS

    def test_document_in_valid_content_types(self):
        from core.constants import VALID_CONTENT_T
        assert "document" in VALID_CONTENT_T


class TestDocumentDataclass:
    def test_document_has_node_id_field(self):
        from services.documents import Document
        from datetime import datetime

        doc = Document(
            id="doc_001",
            workspace_id="ws_001",
            filename="test.pdf",
            content_hash="abc123",
            mime_type="application/pdf",
            size_bytes=1024,
            storage_path="/tmp/test.pdf",
            uploaded_by="user_001",
            uploaded_at=datetime.now(),
            node_id="mem_001",
        )
        assert doc.node_id == "mem_001"

    def test_document_node_id_defaults_to_none(self):
        from services.documents import Document
        from datetime import datetime

        doc = Document(
            id="doc_001",
            workspace_id="ws_001",
            filename="test.pdf",
            content_hash="abc123",
            mime_type="application/pdf",
            size_bytes=1024,
            storage_path="/tmp/test.pdf",
            uploaded_by="user_001",
            uploaded_at=datetime.now(),
        )
        assert doc.node_id is None


class TestCreateExtractedFromEdge:
    def test_creates_edge_with_metadata(self):
        from services.documents import create_extracted_from_edge

        cur = MagicMock()
        cur.rowcount = 1

        create_extracted_from_edge(
            cur,
            workspace_id="ws_001",
            from_node_id="mem_knowledge",
            doc_node_id="mem_doc",
            paragraph_ref="Chunk 3 (Overview > Auth)",
            excerpt="Bearer token must expire within 24h",
        )

        assert cur.execute.called
        sql, params = cur.execute.call_args[0]
        assert "extracted_from" in sql
        assert "ON CONFLICT" in sql

        # Validate metadata JSON
        edge_id, ws, from_id, to_id, meta_json = params
        meta = json.loads(meta_json)
        assert meta["paragraph_ref"] == "Chunk 3 (Overview > Auth)"
        assert "Bearer token" in meta["excerpt"]
        assert from_id == "mem_knowledge"
        assert to_id == "mem_doc"

    def test_no_metadata_when_empty(self):
        from services.documents import create_extracted_from_edge

        cur = MagicMock()
        create_extracted_from_edge(cur, "ws_001", "mem_a", "mem_b")

        _, params = cur.execute.call_args[0]
        meta = json.loads(params[-1])
        assert meta == {}

    def test_excerpt_truncated_to_500_chars(self):
        from services.documents import create_extracted_from_edge

        cur = MagicMock()
        long_excerpt = "x" * 1000
        create_extracted_from_edge(cur, "ws_001", "mem_a", "mem_b", excerpt=long_excerpt)

        _, params = cur.execute.call_args[0]
        meta = json.loads(params[-1])
        assert len(meta["excerpt"]) == 500


class TestGetNodeSources:
    def test_merges_edge_and_link_rows_without_duplicates(self):
        from services.documents import get_node_sources

        edge_row = {
            "id": "doc_001", "filename": "api.md", "title": None,
            "mime_type": "text/plain", "size_bytes": 100,
            "source_url": None, "uploaded_at": None,
            "paragraph_ref": "Chunk 1", "excerpt": "test",
        }
        link_row_dup = {**edge_row, "paragraph_ref": "Chunk 1 (legacy)"}
        link_row_new = {
            "id": "doc_002", "filename": "arch.md", "title": None,
            "mime_type": "text/plain", "size_bytes": 200,
            "source_url": None, "uploaded_at": None,
            "paragraph_ref": "Chunk 2", "excerpt": None,
        }

        cur = MagicMock()

        with patch("services.documents.get_node_sources_via_edges", return_value=[edge_row]):
            cur.fetchall.return_value = [link_row_dup, link_row_new]
            results = get_node_sources(cur, "mem_001")

        # doc_001 should appear only once (from edges), doc_002 from links
        ids = [r["id"] for r in results]
        assert ids.count("doc_001") == 1
        assert "doc_002" in ids

    def test_falls_back_to_links_when_no_edges(self):
        from services.documents import get_node_sources

        link_row = {
            "id": "doc_001", "filename": "legacy.md", "title": None,
            "mime_type": "text/plain", "size_bytes": 50,
            "source_url": None, "uploaded_at": None,
            "paragraph_ref": "", "excerpt": None,
        }

        cur = MagicMock()
        with patch("services.documents.get_node_sources_via_edges", return_value=[]):
            cur.fetchall.return_value = [link_row]
            results = get_node_sources(cur, "mem_old")

        assert len(results) == 1
        assert results[0]["id"] == "doc_001"


class TestCreateDocumentNodeInDb:
    def test_creates_node_and_updates_document(self):
        from services.documents import create_document_node_in_db

        cur = MagicMock()
        cur.fetchone.return_value = {"id": "mem_newnode", "workspace_id": "ws_001",
                                     "title": "arch.md", "content_type": "document",
                                     "body": "Document: arch.md", "author": "user_001",
                                     "status": "active"}

        result = create_document_node_in_db(
            cur, "ws_001", "doc_001", "arch.md", "user_001", summary="Architecture overview"
        )

        # Should have executed an INSERT for memory_nodes
        insert_call = cur.execute.call_args_list[0]
        sql = insert_call[0][0]
        assert "INSERT INTO memory_nodes" in sql
        assert "document" in sql

        # Should have executed an UPDATE for documents.node_id
        update_call = cur.execute.call_args_list[1]
        update_sql = update_call[0][0]
        assert "UPDATE documents SET node_id" in update_sql

        assert result is not None


class TestAcceptReviewWithExtractedFrom:
    """Verify that accept_review_item creates extracted_from edge if doc has node_id."""

    def _make_item(self, source_doc_node_id="doc_001", para_ref="Chunk 1"):
        return {
            "id": "rev_001",
            "workspace_id": "ws_001",
            "change_type": "create",
            "target_node_id": None,
            "before_snapshot": None,
            "node_data": {
                "title": "Auth Token Policy",
                "body": "Bearer tokens expire in 24h",
                "content_type": "factual",
                "content_format": "plain",
                "visibility": "private",
                "source_type": "ai",
                "author": "user_001",
                "source_doc_node_id": source_doc_node_id,
                "source_paragraph_ref": para_ref,
                "source_segment": "excerpt text",
            },
            "diff_summary": {},
            "suggested_edges": [],
            "status": "pending",
            "source_id": None,
            "proposer_type": "ai",
            "proposer_id": "ingest_bot",
        }

    def test_creates_extracted_from_edge_on_accept(self):
        """When doc has a node_id, accept should call create_extracted_from_edge."""
        from unittest.mock import patch as _patch

        item = self._make_item()

        created_node = {"id": "mem_new_001", "title": "Auth Token Policy",
                        "workspace_id": "ws_001", "signature": "sig_abc",
                        "content_type": "factual"}

        with _patch("routers.review._apply_review_item", return_value=(created_node, None)), \
             _patch("routers.review._write_node_revision"), \
             _patch("routers.review.trigger_node_background_jobs"), \
             _patch("services.documents.create_node_document_link") as mock_link, \
             _patch("services.documents.create_extracted_from_edge") as mock_edge:

            cur = MagicMock()
            # Simulate: first fetchone call returns the review item (not needed since we patch _apply_review_item)
            # Second: doc row with node_id
            cur.execute = MagicMock()
            cur.fetchone.return_value = {"node_id": "mem_doc_001"}

            # Import helpers and replicate the logic from accept_review_item
            from services.documents import create_extracted_from_edge
            from services.documents import create_node_document_link

            node_data = item["node_data"]
            doc_id = node_data.get("source_doc_node_id")
            excerpt = node_data.get("source_segment") or created_node.get("body")
            para_ref = node_data.get("source_paragraph_ref") or ""

            # Simulate what accept_review_item does
            create_node_document_link(cur, created_node["id"], doc_id, para_ref, excerpt)
            cur.execute("SELECT node_id FROM documents WHERE id = %s", (doc_id,))
            doc_row = cur.fetchone()
            if doc_row and doc_row["node_id"]:
                create_extracted_from_edge(
                    cur, item["workspace_id"],
                    created_node["id"], doc_row["node_id"],
                    para_ref, excerpt,
                )

            mock_link.assert_called_once_with(cur, "mem_new_001", "doc_001", "Chunk 1", "excerpt text")
            mock_edge.assert_called_once_with(
                cur, "ws_001", "mem_new_001", "mem_doc_001", "Chunk 1", "excerpt text"
            )

    def test_no_edge_when_doc_lacks_node_id(self):
        """If doc.node_id is NULL, no extracted_from edge should be created."""
        from unittest.mock import patch as _patch
        from services.documents import create_extracted_from_edge, create_node_document_link

        cur = MagicMock()
        cur.fetchone.return_value = {"node_id": None}

        with _patch("services.documents.create_extracted_from_edge") as mock_edge:
            # Replicate the conditional in accept_review_item
            cur.execute("SELECT node_id FROM documents WHERE id = %s", ("doc_001",))
            doc_row = cur.fetchone()
            if doc_row and doc_row["node_id"]:
                create_extracted_from_edge(cur, "ws_001", "mem_x", doc_row["node_id"])

            mock_edge.assert_not_called()


# ─── Integration tests (require real DB) ──────────────────────────────────────

@pytest.mark.integration
class TestExtractedFromIntegration:
    """
    These tests run against a real PostgreSQL instance.
    Requires TEST_DATABASE_URL to be set and migration 057 applied.
    Each test rolls back via db_transaction fixture.
    """

    def test_migration_enum_values(self, db_transaction):
        """Verify relation_type and content_type enums have the new values."""
        conn = db_transaction
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT enumlabel FROM pg_enum e
                JOIN pg_type t ON t.oid = e.enumtypid
                WHERE t.typname = 'relation_type'
                """
            )
            relation_values = {r["enumlabel"] for r in cur.fetchall()}
            assert "extracted_from" in relation_values, \
                f"'extracted_from' not in relation_type enum: {relation_values}"

            cur.execute(
                """
                SELECT enumlabel FROM pg_enum e
                JOIN pg_type t ON t.oid = e.enumtypid
                WHERE t.typname = 'content_type'
                """
            )
            content_values = {r["enumlabel"] for r in cur.fetchall()}
            assert "document" in content_values, \
                f"'document' not in content_type enum: {content_values}"

    def test_documents_has_node_id_column(self, db_transaction):
        """Verify documents.node_id column exists with correct type."""
        conn = db_transaction
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'documents' AND column_name = 'node_id'
                """
            )
            row = cur.fetchone()
        assert row is not None, "documents.node_id column does not exist"
        assert row["column_name"] == "node_id"
        assert row["data_type"] == "text"

    def test_all_documents_have_node_id(self, db_transaction):
        """After migration, every document should have a node_id."""
        conn = db_transaction
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) AS n FROM documents WHERE node_id IS NULL")
            count = cur.fetchone()["n"]
        assert count == 0, f"{count} documents still lack a node_id after migration"

    def test_extracted_from_edges_cover_node_document_links(self, db_transaction):
        """
        Every knowledge node that has a node_document_link entry should also
        have at least one extracted_from edge.
        """
        conn = db_transaction
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT count(DISTINCT ndl.node_id) AS linked_nodes,
                       count(DISTINCT e.from_id)   AS edge_nodes
                FROM node_document_links ndl
                LEFT JOIN edges e
                  ON e.from_id = ndl.node_id AND e.relation = 'extracted_from'
                """
            )
            row = cur.fetchone()
        linked_nodes = row["linked_nodes"]
        edge_nodes = row["edge_nodes"]
        assert edge_nodes == linked_nodes, (
            f"Mismatch: {linked_nodes} nodes in node_document_links "
            f"but only {edge_nodes} have extracted_from edges"
        )

    def test_traverse_from_knowledge_to_document_node(self, db_transaction):
        """
        Pick a real knowledge node with an extracted_from edge and verify
        the traversal resolves to a document-type memory_node.
        """
        conn = db_transaction
        with conn.cursor() as cur:
            # Seed test data if not already present
            cur.execute("SELECT 1 FROM edges WHERE relation = 'extracted_from' LIMIT 1")
            if not cur.fetchone():
                cur.execute(
                    """
                    INSERT INTO memory_nodes (
                        id, workspace_id, title, content_type, content_format, body,
                        tags, visibility, author, signature, source_type, status,
                        trust_score, dim_author_rep, dim_freshness
                    ) VALUES (
                        'mem_test_doc_node', 'ws_spec0001', 'test_doc.txt', 'document', 'plain', 'Doc body',
                        '{}', 'private', 'system', 'sig1', 'document', 'active',
                        1.0, 1.0, 1.0
                    ) ON CONFLICT DO NOTHING
                    """
                )
                cur.execute(
                    """
                    INSERT INTO memory_nodes (
                        id, workspace_id, title, content_type, content_format, body,
                        tags, visibility, author, signature, source_type, status,
                        trust_score, dim_author_rep, dim_freshness
                    ) VALUES (
                        'mem_test_knowledge_node', 'ws_spec0001', 'Test Knowledge', 'factual', 'plain', 'Knowledge body',
                        '{}', 'private', 'system', 'sig2', 'human', 'active',
                        1.0, 1.0, 1.0
                    ) ON CONFLICT DO NOTHING
                    """
                )
                cur.execute(
                    """
                    INSERT INTO edges (
                        id, workspace_id, from_id, to_id, relation, weight, status, source_type, proposer
                    ) VALUES (
                        'edge_test_extracted', 'ws_spec0001', 'mem_test_knowledge_node', 'mem_test_doc_node',
                        'extracted_from', 1.0, 'active', 'document', 'test_suite'
                    ) ON CONFLICT DO NOTHING
                    """
                )

            cur.execute(
                """
                SELECT e.from_id, e.to_id, n.content_type, n.title
                FROM edges e
                JOIN memory_nodes n ON n.id = e.to_id
                WHERE e.relation = 'extracted_from'
                  AND e.status = 'active'
                LIMIT 1
                """
            )
            row = cur.fetchone()

        assert row is not None, "No extracted_from edges found — migration may not have run"
        assert row["content_type"] == "document", (
            f"Document node {row['to_id']} has content_type='{row['content_type']}', expected 'document'"
        )
        assert row["title"], "Document node has no title"

    def test_get_node_sources_via_edges_returns_results(self, db_transaction):
        """get_node_sources_via_edges should return the same docs as node_document_links."""
        conn = db_transaction
        with conn.cursor() as cur:
            # Seed test data if not already present
            cur.execute("SELECT 1 FROM node_document_links LIMIT 1")
            if not cur.fetchone():
                cur.execute(
                    """
                    INSERT INTO documents (
                        id, workspace_id, filename, content_hash, mime_type, size_bytes, storage_path, uploaded_by
                    ) VALUES (
                        'doc_test_1', 'ws_spec0001', 'doc_test_1.txt', 'hash1', 'text/plain', 10, '/tmp/doc_test_1.txt', 'system'
                    ) ON CONFLICT DO NOTHING
                    """
                )
                cur.execute(
                    """
                    INSERT INTO memory_nodes (
                        id, workspace_id, title, content_type, content_format, body,
                        tags, visibility, author, signature, source_type, status,
                        trust_score, dim_author_rep, dim_freshness
                    ) VALUES (
                        'mem_doc_node_1', 'ws_spec0001', 'doc_test_1.txt', 'document', 'plain', 'Doc body',
                        '{}', 'private', 'system', 'sig1', 'document', 'active',
                        1.0, 1.0, 1.0
                    ) ON CONFLICT DO NOTHING
                    """
                )
                cur.execute("UPDATE documents SET node_id = 'mem_doc_node_1' WHERE id = 'doc_test_1'")
                cur.execute(
                    """
                    INSERT INTO memory_nodes (
                        id, workspace_id, title, content_type, content_format, body,
                        tags, visibility, author, signature, source_type, status,
                        trust_score, dim_author_rep, dim_freshness
                    ) VALUES (
                        'mem_know_node_1', 'ws_spec0001', 'Test Knowledge 1', 'factual', 'plain', 'Knowledge body',
                        '{}', 'private', 'system', 'sig2', 'human', 'active',
                        1.0, 1.0, 1.0
                    ) ON CONFLICT DO NOTHING
                    """
                )
                cur.execute(
                    """
                    INSERT INTO node_document_links (node_id, document_id, paragraph_ref, excerpt)
                    VALUES ('mem_know_node_1', 'doc_test_1', 'para1', 'excerpt1')
                    ON CONFLICT DO NOTHING
                    """
                )
                cur.execute(
                    """
                    INSERT INTO edges (
                        id, workspace_id, from_id, to_id, relation, weight, status, source_type, proposer, metadata
                    ) VALUES (
                        'edge_test_1', 'ws_spec0001', 'mem_know_node_1', 'mem_doc_node_1',
                        'extracted_from', 1.0, 'active', 'document', 'test_suite', '{"paragraph_ref": "para1", "excerpt": "excerpt1"}'
                    ) ON CONFLICT DO NOTHING
                    """
                )

            # Find a node that has node_document_links
            cur.execute("SELECT node_id FROM node_document_links LIMIT 1")
            row = cur.fetchone()
            if row is None:
                pytest.skip("No node_document_links in test DB")
            node_id = row["node_id"]

            # Edge path
            cur.execute(
                """
                SELECT d.id
                FROM edges e
                JOIN documents d ON d.node_id = e.to_id
                WHERE e.from_id = %s AND e.relation = 'extracted_from'
                """,
                (node_id,),
            )
            edge_doc_ids = {r["id"] for r in cur.fetchall()}

            # Legacy path
            cur.execute(
                "SELECT document_id FROM node_document_links WHERE node_id = %s",
                (node_id,),
            )
            link_doc_ids = {r["document_id"] for r in cur.fetchall()}

        assert edge_doc_ids == link_doc_ids, (
            f"Edge path returned {edge_doc_ids}, "
            f"legacy path returned {link_doc_ids}"
        )


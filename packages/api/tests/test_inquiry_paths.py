"""
tests/test_inquiry_paths.py
Phase 6.2 Track B Part 1 — Unit and integration tests for inquiry paths, search miss gap proposal, and path reinforcement.
"""
from __future__ import annotations

import datetime
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from services.inquiry_paths import record_path_in_db, search_with_history_in_db
from services.analytics import handle_search_miss
from jobs.path_reinforcement import reinforce_paths_in_db

# Helper to build a resolved provider that won't cause psycopg2 adaptation errors in record_usage
def build_mock_resolved_provider(vector):
    mock_resolve = MagicMock()
    mock_resolve.user_id = "system"
    mock_resolve.model = "text-embedding-3-small"
    
    mock_prov = MagicMock()
    mock_prov.name = "openai"
    mock_prov.embed = AsyncMock(return_value=(vector, 10))
    mock_resolve.provider = mock_prov
    return mock_resolve

# ─── Unit Tests (Mocked DB / AI) ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_record_path_in_db_unit():
    vector = [0.1] * 1536
    mock_resolve = build_mock_resolved_provider(vector)
    
    cur = MagicMock()
    cur.fetchone.side_effect = [
        {"embedding_model": "text-embedding-3-small", "embedding_provider": "openai"}, # select workspace
        {"id": "path_123", "query_text": "hello", "node_sequence": ["n1", "n2"], "outcome": "success"} # insert return
    ]
    
    payload = {
        "query_text": "hello",
        "node_sequence": ["n1", "n2"],
        "outcome": "success",
        "started_at": "2026-05-27T12:00:00Z",
        "token_used": 100,
        "rating": 5,
        "metadata": {}
    }
    
    with patch("services.inquiry_paths.resolve_provider", return_value=mock_resolve), \
         patch("services.inquiry_paths.record_usage") as mock_record:
         
        res = await record_path_in_db(cur, "ws_test", "user_test", payload)
        assert res["query_text"] == "hello"
        assert res["outcome"] == "success"
        mock_resolve.provider.embed.assert_called_once()
        mock_record.assert_called_once()


@pytest.mark.asyncio
async def test_search_with_history_in_db_unit():
    vector = [0.1] * 1536
    mock_resolve = build_mock_resolved_provider(vector)
    
    cur = MagicMock()
    cur.fetchone.return_value = {"embedding_model": "text-embedding-3-small", "embedding_provider": "openai"}
    cur.fetchall.return_value = [
        {"id": "path_1", "query_text": "query 1", "node_sequence": ["n1"], "outcome": "success", "similarity": 0.95, "rating": 5}
    ]
    
    with patch("services.inquiry_paths.resolve_provider", return_value=mock_resolve), \
         patch("services.inquiry_paths.record_usage") as mock_record:
         
        res = await search_with_history_in_db(cur, "ws_test", "query 1", 0.85, 3, "user_test")
        assert len(res) == 1
        assert res[0]["path_id"] == "path_1"
        assert res[0]["similarity"] == 0.95


# ─── Integration Tests (Real DB) ──────────────────────────────────────────────

@pytest.mark.integration
class TestInquiryPathsIntegration:
    """
    Integration tests against a real PostgreSQL instance.
    Runs only when TEST_DATABASE_URL is set.
    """

    def test_inquiry_paths_table_exists(self, db_transaction):
        conn = db_transaction
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'inquiry_paths' AND column_name = 'outcome'
                """
            )
            row = cur.fetchone()
        assert row is not None
        assert row["column_name"] == "outcome"

    @pytest.mark.asyncio
    async def test_record_and_search_integration(self, db_transaction):
        conn = db_transaction
        vector = [0.01] * 1536
        mock_resolve = build_mock_resolved_provider(vector)

        ws_id = "ws_spec0001"
        with conn.cursor() as cur:
            # Ensure workspace has embedding_model set so record_path_in_db enters the embed branch
            cur.execute(
                """
                UPDATE workspaces
                SET embedding_model = 'text-embedding-3-small',
                    embedding_provider = 'openai'
                WHERE id = %s
                """,
                (ws_id,)
            )

            # Record a path
            payload = {
                "query_text": "find code formatting",
                "node_sequence": ["mem_00d32c49", "mem_013d11be"],
                "outcome": "success",
                "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "rating": 5
            }
            
            with patch("services.inquiry_paths.resolve_provider", return_value=mock_resolve), \
                 patch("services.inquiry_paths.record_usage"):
                 
                res = await record_path_in_db(cur, ws_id, "system", payload)
                assert res["id"] is not None
                assert res["outcome"] == "success"

                # Search with history
                search_res = await search_with_history_in_db(cur, ws_id, "find code formatting", 0.90, 5, "system")
                assert len(search_res) == 1
                assert search_res[0]["query_text"] == "find code formatting"
                assert search_res[0]["outcome"] == "success"

    @pytest.mark.asyncio
    async def test_handle_search_miss_integration(self, db_transaction):
        conn = db_transaction
        vector = [0.02] * 1536
        mock_resolve = build_mock_resolved_provider(vector)

        ws_id = "ws_spec0001"
        with conn.cursor() as cur:
            with patch("core.ai.resolve_provider", return_value=mock_resolve):
                # 1. Run handle_search_miss -> should propose a gap node
                await handle_search_miss(ws_id, "missing feature request", "system")
                
                # 2. Check that the proposal is in review_queue
                cur.execute(
                    "SELECT id, node_data, source_info FROM review_queue WHERE workspace_id = %s AND status = 'pending' AND source_info = 'search-miss'",
                    (ws_id,)
                )
                rows = cur.fetchall()
                assert len(rows) == 1
                assert rows[0]["source_info"] == "search-miss"
                node_data = rows[0]["node_data"]
                assert node_data["content_type"] == "gap"
                assert node_data["trust_score"] == 0.3
                assert node_data["body"] == "missing feature request"

                # 3. Running it again with same query should NOT create duplicate proposal
                await handle_search_miss(ws_id, "missing feature request", "system")
                cur.execute(
                    "SELECT count(*) as cnt FROM review_queue WHERE workspace_id = %s AND status = 'pending' AND source_info = 'search-miss'",
                    (ws_id,)
                )
                assert cur.fetchone()["cnt"] == 1

    @pytest.mark.asyncio
    async def test_path_reinforcement_and_decay_integration(self, db_transaction):
        conn = db_transaction
        ws_id = "ws_spec0001"
        
        with conn.cursor() as cur:
            # Explicitly insert/ensure the edge exists first
            cur.execute(
                """
                INSERT INTO edges (id, workspace_id, from_id, to_id, relation, weight, status)
                VALUES ('edge_test_reinf', %s, 'mem_00d32c49', 'mem_013d11be', 'related_to', 0.5, 'active')
                ON CONFLICT (id) DO UPDATE SET weight = 0.5
                """,
                (ws_id,)
            )
            
            # Record successful path in the last 24h
            cur.execute(
                """
                INSERT INTO inquiry_paths (
                    id, workspace_id, agent_id, query_text, node_sequence, outcome, started_at, ended_at
                ) VALUES (
                    'path_ok', %s, 'system', 'test', ARRAY['mem_00d32c49', 'mem_013d11be'], 'success', now() - INTERVAL '10 minutes', now()
                )
                """,
                (ws_id,)
            )
            
            # Record failed path from 40 days ago
            cur.execute(
                """
                INSERT INTO inquiry_paths (
                    id, workspace_id, agent_id, query_text, node_sequence, outcome, started_at, ended_at
                ) VALUES (
                    'path_fail_old', %s, 'system', 'test fail', ARRAY['mem_00d32c49'], 'failed', now() - INTERVAL '40 days', now() - INTERVAL '40 days'
                )
                """,
                (ws_id,)
            )

            # Run job directly inside the test transaction
            reinforce_paths_in_db(cur)

            # Check edge weight boosted by 0.05 (either direction)
            cur.execute(
                """
                SELECT weight FROM edges 
                WHERE workspace_id = 'ws_spec0001' 
                  AND ((from_id = 'mem_00d32c49' AND to_id = 'mem_013d11be') 
                       OR (from_id = 'mem_013d11be' AND to_id = 'mem_00d32c49'))
                """
            )
            edge_weight = cur.fetchone()["weight"]
            assert float(edge_weight) == pytest.approx(0.55)
            
            # Check failed path older than 30 days is archived
            cur.execute("SELECT archived_at FROM inquiry_paths WHERE id = 'path_fail_old'")
            archived_at = cur.fetchone()["archived_at"]
            assert archived_at is not None
            
            # Check successful path is NOT archived
            cur.execute("SELECT archived_at FROM inquiry_paths WHERE id = 'path_ok'")
            archived_ok = cur.fetchone()["archived_at"]
            assert archived_ok is None

import sys
import os
from unittest.mock import MagicMock

# Add packages/api to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from services.search import bfs_neighborhood

def test_bfs_neighborhood_basic():
    cur = MagicMock()
    ws_id = "ws_test"
    node_id = "mem_root"
    
    # Mock edges fetch (1st fetchall) and then nodes fetch (2nd fetchall)
    cur.fetchall.side_effect = [
        [
            {
                "id": "edge_1",
                "from_id": "mem_root",
                "to_id": "mem_child",
                "relation": "depends_on",
                "weight": 1.0,
                "direction": "outbound"
            }
        ],
        [
            {
                "id": "mem_root",
                "title_en": "Root Node",
                "title_zh": "",
                "content_type": "factual",
                "tags": [],
                "visibility": "public"
            },
            {
                "id": "mem_child",
                "title_en": "Child Node",
                "title_zh": "",
                "content_type": "factual",
                "tags": [],
                "visibility": "public"
            }
        ]
    ]
    
    result = bfs_neighborhood(
        cur=cur,
        ws_id=ws_id,
        root_id=node_id,
        depth=1,
        relation=None,
        direction="outbound"
    )
    
    assert "nodes" in result
    assert "edges" in result
    assert len(result["nodes"]) == 2
    assert len(result["edges"]) == 1
    assert result["nodes"][0]["id"] == "mem_root"
    assert result["nodes"][1]["id"] == "mem_child"
    assert result["edges"][0]["id"] == "edge_1"
    
    # Verify the SQL query executes correctly
    assert cur.execute.call_count >= 2

def test_bfs_neighborhood_not_found():
    cur = MagicMock()
    # Mock no edges found, and no nodes found
    cur.fetchall.side_effect = [[], []]
    
    result = bfs_neighborhood(cur, "ws_test", "mem_missing", 1)
    
    assert len(result["nodes"]) == 0
    assert len(result["edges"]) == 0

@pytest.mark.asyncio
async def test_bg_reindex_workspace_embeddings():
    from services.bg_jobs import bg_reindex_workspace_embeddings
    from unittest.mock import patch, MagicMock

    mock_resolved = MagicMock()
    mock_resolved.provider.name = "test_provider"
    mock_resolved.model = "test_model"

    with patch("core.database.db_cursor") as mock_db:
        mock_cur = mock_db.return_value.__enter__.return_value
        
        # 1. Fetch workspace embedding config
        # 2. Fetch all active memory nodes
        mock_cur.fetchone.return_value = {"embedding_model": "text-embedding-3-small", "embedding_provider": "openai"}
        mock_cur.fetchall.return_value = [
            {"id": "node_1", "title": "Node 1", "body": "Body 1"}
        ]
        
        with patch("core.ai.resolve_provider", return_value=mock_resolved):
            with patch("core.ai.embed", return_value=([0.1, 0.2], 50)) as mock_embed:
                with patch("core.ai.record_usage") as mock_usage:
                    await bg_reindex_workspace_embeddings("ws_1", "user_1")
                    
                    mock_embed.assert_called_once_with(mock_resolved, "Node 1\nBody 1")
                    mock_usage.assert_called_once()
                    assert mock_cur.execute.called


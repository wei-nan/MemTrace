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

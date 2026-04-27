import sys
import os
from unittest.mock import MagicMock, patch

# Add packages/api to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from routers.kb import _create_edges_directly

@patch("routers.kb.generate_id")
def test_create_edges_directly_admin(mock_gen_id):
    mock_gen_id.return_value = "edge_123"
    cur = MagicMock()
    ws_id = "ws_test"
    from_id = "mem_1"
    suggested_edges = [
        {"to_id": "mem_2", "relation": "extends", "weight": 0.9}
    ]
    
    # Mocking:
    # 1. Node existence check -> returns node
    # 2. Edge existence check -> returns None (edge doesn't exist)
    cur.fetchone.side_effect = [
        {"id": "mem_2"}, # Node exists check
        None            # Edge exists check
    ]
    
    _create_edges_directly(cur, ws_id, from_id, suggested_edges)
    
    # Check if INSERT was called
    cur.execute.assert_any_call(
        "INSERT INTO edges (id, workspace_id, from_id, to_id, relation, weight) VALUES (%s, %s, %s, %s, %s, %s)",
        ("edge_123", ws_id, from_id, "mem_2", "extends", 0.9)
    )

@patch("routers.kb.generate_id")
def test_create_edges_directly_skips_invalid(mock_gen_id):
    cur = MagicMock()
    ws_id = "ws_test"
    from_id = "mem_1"
    
    # 1. Invalid relation
    # 2. Self-link
    # 3. Non-existent target node
    suggested_edges = [
        {"to_id": "mem_2", "relation": "invalid_rel"},
        {"to_id": "mem_1", "relation": "extends"},
        {"to_id": "mem_missing", "relation": "extends"}
    ]
    
    # Mocking for mem_missing check:
    cur.fetchone.return_value = None
    
    _create_edges_directly(cur, ws_id, from_id, suggested_edges)
    
    # Ensure INSERT was never called
    for call in cur.execute.call_args_list:
        assert "INSERT INTO edges" not in str(call)

@patch("routers.kb.generate_id")
def test_create_edges_directly_skips_existing(mock_gen_id):
    mock_gen_id.return_value = "edge_123"
    cur = MagicMock()
    ws_id = "ws_test"
    from_id = "mem_1"
    suggested_edges = [
        {"to_id": "mem_2", "relation": "extends"}
    ]
    
    # Mocking:
    # 1. Node existence check -> returns node
    # 2. Edge existence check -> returns existing edge (True)
    cur.fetchone.side_effect = [
        {"id": "mem_2"}, # Node exists
        {"id": "edge_old"} # Edge exists
    ]
    
    _create_edges_directly(cur, ws_id, from_id, suggested_edges)
    
    # Ensure INSERT was never called
    for call in cur.execute.call_args_list:
        assert "INSERT INTO edges" not in str(call)

@patch("routers.kb._create_edges_directly")
@patch("routers.kb._create_node_in_db")
@patch("routers.kb._write_node_revision")
@patch("routers.kb._propose_change")
@patch("routers.kb._get_effective_role")
@patch("routers.kb._require_ws_access")
@patch("routers.kb.db_cursor")
@patch("routers.kb.BackgroundTasks")
def test_create_node_role_behavior(mock_bg, mock_db_ctx, mock_ws, mock_role, mock_propose, mock_rev, mock_create_db, mock_create_edges):
    from routers.kb import create_node
    from models.kb import NodeCreate
    
    ws_id = "ws_123"
    user = {"sub": "user_1"}
    body = NodeCreate(
        title_en="Test",
        content_type="factual",
        content_format="plain",
        body_en="Test body",
        source_type="ai",
        suggested_edges=[{"to_id": "mem_2", "relation": "extends"}]
    )
    
    # Setup mock DB context
    mock_cur = MagicMock()
    mock_db_ctx.return_value.__enter__.return_value = mock_cur
    mock_propose.return_value = "rev_123"
    
    # 1. Test Admin Role (Direct creation)
    mock_role.return_value = "admin"
    mock_create_db.return_value = {"id": "new_node", "signature": "sig", "title_zh": "", "title_en": "Test", "body_zh": "", "body_en": ""}
    
    create_node(ws_id, body, mock_bg(), user)
    
    mock_create_edges.assert_called_once_with(mock_cur, ws_id, "new_node", [{"to_id": "mem_2", "relation": "extends", "weight": 1.0}])
    mock_propose.assert_not_called()
    
    mock_create_edges.reset_mock()
    mock_propose.reset_mock()
    
    # 2. Test Editor Role (Queueing)
    mock_role.return_value = "editor"
    create_node(ws_id, body, mock_bg(), user)
    
    mock_propose.assert_called_once()
    args, kwargs = mock_propose.call_args
    assert kwargs["suggested_edges"] == [{"to_id": "mem_2", "relation": "extends", "weight": 1.0}]
    mock_create_edges.assert_not_called()

import sys
import os
from unittest.mock import MagicMock, patch
import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.nodes import (
    validate_node_payload, prepare_node_data, create_node_in_db,
    update_node_in_db, delete_node_in_db, node_row_to_snapshot
)
from fastapi import HTTPException

def test_validate_node_payload():
    # Valid
    validate_node_payload({"content_type": "factual", "content_format": "plain", "visibility": "public", "title": "test", "body": "test"})
    
    with pytest.raises(HTTPException):
        validate_node_payload({"content_type": "invalid", "title": "t", "body": "t"})
    
    with pytest.raises(HTTPException):
        validate_node_payload({"content_type": "factual", "content_format": "invalid", "title": "t", "body": "t"})
        
    with pytest.raises(HTTPException):
        validate_node_payload({"content_type": "factual", "content_format": "plain", "visibility": "invalid", "title": "t", "body": "t"})

@patch("services.nodes.compute_signature")
def test_prepare_node_data(mock_sig):
    mock_sig.return_value = "sig_123"
    
    data = {"title": "Hello", "body": "World", "tags": ["test"], "content_type": "factual", "content_format": "plain", "visibility": "public"}
    prepared = prepare_node_data(data, author="admin")
    
    assert prepared["author"] == "admin"
    assert prepared["source_type"] == "human"
    assert prepared["signature"] == "sig_123"
    assert prepared["title"] == "Hello"

@patch("services.nodes.generate_id")
@patch("services.nodes.prepare_node_data")
def test_create_node_in_db(mock_prepare, mock_gen_id):
    mock_gen_id.return_value = "mem_new"
    mock_prepare.return_value = {
        "title": "test", "content_type": "factual",
        "content_format": "plain", "body": "test",
        "tags": [], "visibility": "public", "author": "admin", "signature": "sig",
        "source_type": "human", "copied_from_node": None, "copied_from_ws": None,
        "dim_author_rep": 0.8, "trust_score": 0.5
    }
    
    cur = MagicMock()
    cur.fetchone.return_value = {"id": "mem_new", "title": "test"}
    
    res = create_node_in_db(cur, "ws_test", {"author": "admin"})
    assert res["id"] == "mem_new"
    assert cur.execute.call_count == 1

@patch("services.nodes.log_audit_event")
@patch("services.nodes.prepare_node_data")
def test_update_node_in_db(mock_prepare, mock_audit):
    mock_prepare.return_value = {
        "title": "upd", "content_type": "factual",
        "content_format": "plain", "body": "upd",
        "tags": [], "visibility": "public", "signature": "sig_upd",
        "trust_score": 0.5
    }
    
    cur = MagicMock()
    cur.fetchone.side_effect = [
        {"id": "mem_1", "title": "old", "source_type": "human", "updated_at": None}, # existing
        {"id": "mem_1", "title": "upd"} # return after update
    ]
    
    res = update_node_in_db(cur, "ws_test", "mem_1", {"title": "upd"}, "admin")
    assert res["title"] == "upd"
    assert cur.execute.call_count == 3

def test_delete_node_in_db():
    cur = MagicMock()
    cur.fetchone.return_value = {"id": "mem_1"}
    
    res = delete_node_in_db(cur, "ws_test", "mem_1")
    assert res["id"] == "mem_1"
    
    cur.fetchone.return_value = None
    with pytest.raises(HTTPException):
        delete_node_in_db(cur, "ws_test", "mem_missing")

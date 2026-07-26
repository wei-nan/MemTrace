import sys
import os
from unittest.mock import MagicMock, patch
import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.nodes import (
    validate_node_payload, prepare_node_data, create_node_in_db,
    update_node_in_db, delete_node_in_db, node_row_to_snapshot,
    publish_new_version,
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
    }
    
    cur = MagicMock()
    cur.fetchone.side_effect = [
        {"id": "mem_1", "title": "old", "source_type": "human", "updated_at": None}, # existing
        {"id": "mem_1", "title": "upd"} # return after update
    ]
    
    res = update_node_in_db(cur, "ws_test", "mem_1", {"title": "upd"}, "admin")
    assert res["title"] == "upd"
    assert cur.execute.call_count == 3

def _update_call(cur):
    """Return the (sql, params) of the UPDATE memory_nodes statement."""
    for call in cur.execute.call_args_list:
        if "UPDATE memory_nodes" in call.args[0]:
            return call.args[0], call.args[1]
    raise AssertionError("no UPDATE memory_nodes statement was issued")


@patch("services.nodes.log_audit_event")
@patch("services.nodes.prepare_node_data")
def test_update_node_param_count_matches_placeholders(mock_prepare, mock_audit):
    """Guard against tuple misalignment — a silent data-corruption failure mode."""
    mock_prepare.return_value = {
        "title": "upd", "content_type": "factual",
        "content_format": "plain", "body": "upd",
        "tags": [], "visibility": "public", "signature": "sig_upd",
    }

    cur = MagicMock()
    cur.fetchone.side_effect = [
        {"id": "mem_1", "title": "old", "source_type": "human", "updated_at": None},
        {"id": "mem_1", "title": "upd"},
    ]

    update_node_in_db(cur, "ws_test", "mem_1", {"title": "upd"}, "admin")
    sql, params = _update_call(cur)
    assert sql.count("%s") == len(params)


def test_delete_node_in_db():
    cur = MagicMock()
    cur.fetchone.return_value = {"id": "mem_1"}

    res = delete_node_in_db(cur, "ws_test", "mem_1")
    assert res["id"] == "mem_1"

    cur.fetchone.return_value = None
    with pytest.raises(HTTPException):
        delete_node_in_db(cur, "ws_test", "mem_missing")


# ─── Spec validity: publish_new_version (ws_spec_plan/mem_310a1c2d) ───────────

def test_publish_new_version_requires_canonical_key():
    cur = MagicMock()
    with pytest.raises(HTTPException, match="canonical_key"):
        publish_new_version(cur, "ws_test", "", {"title": "x", "content_type": "factual"})


@patch("services.edges.create_edge_in_db")
@patch("services.nodes.create_node_in_db")
def test_publish_new_version_supersedes_prior_current_and_links_edge(mock_create_node, mock_create_edge):
    mock_create_node.return_value = {"id": "mem_new", "metadata": {"canonical_key": "k", "spec_status": "current"}}
    cur = MagicMock()
    cur.fetchall.return_value = [{"id": "mem_old_1"}, {"id": "mem_old_2"}]

    result = publish_new_version(cur, "ws_test", "k", {"title": "v2", "content_type": "factual"})

    assert result["node"]["id"] == "mem_new"
    assert result["superseded"] == ["mem_old_1", "mem_old_2"]

    # metadata passed into create_node_in_db carries the canonical_key/current status
    passed_node_data = mock_create_node.call_args.args[2]
    assert passed_node_data["metadata"]["canonical_key"] == "k"
    assert passed_node_data["metadata"]["spec_status"] == "current"

    # a superseded_by edge is drawn from each old node to the new one
    assert mock_create_edge.call_count == 2
    edge_targets = {call.args[2]["from_id"] for call in mock_create_edge.call_args_list}
    assert edge_targets == {"mem_old_1", "mem_old_2"}
    for call in mock_create_edge.call_args_list:
        assert call.args[2]["to_id"] == "mem_new"
        assert call.args[2]["relation"] == "superseded_by"


@patch("services.edges.create_edge_in_db")
@patch("services.nodes.create_node_in_db")
def test_publish_new_version_no_prior_current_supersedes_nothing(mock_create_node, mock_create_edge):
    mock_create_node.return_value = {"id": "mem_new", "metadata": {}}
    cur = MagicMock()
    cur.fetchall.return_value = []

    result = publish_new_version(cur, "ws_test", "k", {"title": "v1", "content_type": "factual"})

    assert result["superseded"] == []
    mock_create_edge.assert_not_called()

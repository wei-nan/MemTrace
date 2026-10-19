"""
tests/test_mcp_tool_access.py — every MCP tool x every kind of caller.

Before this guard, several MCP tools (update_node, delete_node, resolve_conflict,
summarize_cluster, release_task, ...) never checked the caller's access to the
workspace, so a read-only service token, a token bound to another workspace, and
even a stranger's account key could rewrite or trash nodes. enforce_mcp_tool_access
now runs for every tool before its handler; MCP_TOOL_ACCESS classifies each tool.

Requires TEST_DATABASE_URL (disposable Postgres, schema migrated); skipped
otherwise. Rows carry a unique suffix and are removed afterwards.
"""
from __future__ import annotations

import asyncio
import hashlib
import secrets
import uuid

import pytest
from fastapi import BackgroundTasks, HTTPException

from services.mcp_tools import MCP_TOOL_ACCESS, TOOLS, enforce_mcp_tool_access, execute_tool

ALL_WS_TOOLS = sorted(n for n, lvl in MCP_TOOL_ACCESS.items() if lvl != "none")
BY_LEVEL = {lvl: sorted(n for n, v in MCP_TOOL_ACCESS.items() if v == lvl) for lvl in ("read", "write", "admin")}


# ─── classification ───────────────────────────────────────────────────────────

# A fixed, hand-written copy of the table. MCP_TOOL_ACCESS is the security-critical
# list, and the matrix tests below derive their expectations from it, so without
# this literal a careless downgrade (say claim_task -> read) would pass every test.
EXPECTED_LEVELS = {
    "list_workspaces": "none", "create_workspace": "none", "get_schema": "none",
    "update_workspace": "read", "list_members": "read", "list_associations": "read",
    "add_association": "read", "remove_association": "read",
    "list_nodes": "read", "get_node": "read", "search_nodes": "read",
    "search_cross_workspace": "read", "list_trash": "read", "wait_for_embedding": "read",
    "get_embedding_status": "read", "traverse": "read", "consult": "read",
    "list_by_tag": "read", "list_review_queue": "read", "get_ingestion_status": "read",
    "suggest_edges": "read", "verify_audit": "read", "list_documents": "read",
    "get_document": "read", "get_node_sources": "read", "search_with_history": "read",
    "get_next_task": "read", "get_playbook": "read", "converge_check": "read",
    "converge_proposals": "read",
    "create_node": "write", "update_node": "write", "delete_node": "write",
    "restore_node": "write", "restore_archived_node": "write", "restore_edge": "write",
    "create_edge": "write", "update_edge": "write", "delete_edge": "write",
    "extract_from_text": "write", "ingest_document": "write", "sync_from_source": "write",
    "attach_url": "write", "attach_evidence": "write", "upload_file": "write",
    "record_path": "write", "propose_decision": "write", "submit_outcome": "write",
    "emit_residue": "write", "claim_task": "write", "release_task": "write",
    "summarize_cluster": "write", "complement_node_languages": "write",
    "reject_proposal": "admin", "resolve_conflict": "admin", "transfer_authorship": "admin",
}


def test_access_table_equals_the_reviewed_literal():
    assert MCP_TOOL_ACCESS == EXPECTED_LEVELS



def test_every_tool_is_classified_and_no_stale_entries():
    assert set(MCP_TOOL_ACCESS) == {t["name"] for t in TOOLS}


def test_only_tools_without_a_workspace_argument_are_exempt():
    for tool in TOOLS:
        props = tool.get("inputSchema", {}).get("properties", {})
        required = tool.get("inputSchema", {}).get("required", [])
        if MCP_TOOL_ACCESS[tool["name"]] == "none":
            assert "workspace_id" not in props, tool["name"]
        else:
            assert "workspace_id" in required, f"{tool['name']} must require workspace_id"


def test_unclassified_tool_is_refused():
    with pytest.raises(HTTPException) as exc:
        enforce_mcp_tool_access("brand_new_tool", {"workspace_id": "ws_x"}, {"sub": "u"})
    assert exc.value.status_code == 403


@pytest.mark.parametrize("bad", [None, "", 5, ["ws"]])
def test_workspace_id_must_be_a_non_empty_string(bad):
    with pytest.raises(HTTPException) as exc:
        enforce_mcp_tool_access("get_node", {"workspace_id": bad}, {"sub": "u"})
    assert exc.value.status_code == 400


def test_levels_cover_expected_tools():
    # a few anchors so a careless re-classification shows up in review
    assert {"update_node", "delete_node", "create_node", "release_task", "summarize_cluster"} <= set(BY_LEVEL["write"])
    assert {"resolve_conflict", "reject_proposal", "transfer_authorship"} == set(BY_LEVEL["admin"])
    assert {"get_node", "search_nodes", "list_nodes", "traverse"} <= set(BY_LEVEL["read"])


# ─── fixtures ─────────────────────────────────────────────────────────────────

def _svc(user_id, ws_id, scopes):
    return {"sub": user_id, "email": "x@example.invalid", "api_key_id": "apikey_t", "role": None,
            "scopes": scopes, "workspace_id": ws_id, "key_type": "service"}


@pytest.fixture
def world(db_conn):
    sfx = uuid.uuid4().hex[:8]
    owner, viewer, editor, stranger = (f"usr_{r}{sfx}" for r in ("o", "v", "e", "s"))
    ws1, ws2 = f"ws_m{sfx}a", f"ws_m{sfx}b"
    db_conn.autocommit = True
    cur = db_conn.cursor()
    for uid in (owner, viewer, editor, stranger):
        cur.execute("INSERT INTO users (id, display_name, email) VALUES (%s, %s, %s)",
                    (uid, "mcp-access", f"{uid}@example.invalid"))
    for ws in (ws1, ws2):
        cur.execute("INSERT INTO workspaces (id, owner_id, name, language, visibility) VALUES (%s, %s, %s, 'zh-TW', 'private')",
                    (ws, owner, f"mcp-access-{ws}"))
    for uid, role in ((viewer, "viewer"), (editor, "editor")):
        cur.execute("INSERT INTO workspace_members (workspace_id, user_id, role) VALUES (%s, %s, %s)", (ws1, uid, role))
    raw = "mt_" + secrets.token_hex(20)
    cur.execute(
        """INSERT INTO api_keys (id, user_id, name, key_hash, prefix, scopes, workspace_id, key_type)
           VALUES (%s, %s, 'owner', %s, %s, '{}', NULL, 'account')""",
        (f"apikey_{sfx}", owner, hashlib.sha256(raw.encode()).hexdigest(), raw[:8]),
    )
    ctx = {"ws1": ws1, "ws2": ws2, "owner_key": raw, "owner": owner,
           "users": {
               "owner": {"sub": owner, "api_key_id": "apikey_o", "role": "admin", "scopes": [], "workspace_id": None},
               "editor": {"sub": editor, "api_key_id": "apikey_e", "role": "editor", "scopes": [], "workspace_id": None},
               "viewer": {"sub": viewer, "api_key_id": "apikey_v", "role": "viewer", "scopes": [], "workspace_id": None},
               "stranger": {"sub": stranger, "api_key_id": "apikey_s", "role": None, "scopes": [], "workspace_id": None},
               "svc_read": _svc(owner, ws1, ["kb:read"]),
               "svc_write": _svc(owner, ws1, ["kb:write"]),
               "svc_admin": _svc(owner, ws1, ["workspace:admin"]),
               "svc_propose": _svc(owner, ws1, ["kb:propose"]),
               "svc_unknown": _svc(owner, ws1, ["repo:read"]),
               "svc_unbound": _svc(owner, None, ["*"]),
           }}
    try:
        yield ctx
    finally:
        cur.execute("DELETE FROM memory_nodes WHERE workspace_id IN (%s, %s)", (ws1, ws2))
        cur.execute("DELETE FROM workspace_members WHERE workspace_id IN (%s, %s)", (ws1, ws2))
        cur.execute("DELETE FROM api_keys WHERE user_id = %s", (owner,))
        cur.execute("DELETE FROM workspaces WHERE owner_id = %s", (owner,))
        cur.execute("DELETE FROM users WHERE id IN (%s, %s, %s, %s)", (owner, viewer, editor, stranger))


def _allowed(world, who, tool, ws="ws1"):
    try:
        enforce_mcp_tool_access(tool, {"workspace_id": world[ws]}, world["users"][who])
        return True
    except HTTPException as e:
        assert e.status_code == 403, f"{who} {tool}: {e.status_code} {e.detail}"
        return False


# ─── the matrix ───────────────────────────────────────────────────────────────

EXPECTED = {
    #               read   write  admin
    "owner":       (True,  True,  True),
    "editor":      (True,  True,  False),
    "viewer":      (True,  False, False),
    "stranger":    (False, False, False),
    "svc_read":    (True,  False, False),
    "svc_write":   (True,  True,  False),
    "svc_admin":   (True,  True,  True),
    "svc_propose": (False, False, False),
    "svc_unknown": (False, False, False),
    "svc_unbound": (False, False, False),
}


@pytest.mark.parametrize("who", list(EXPECTED))
def test_every_tool_against_every_caller(world, who):
    for level, expect in zip(("read", "write", "admin"), EXPECTED[who]):
        for tool in BY_LEVEL[level]:
            assert _allowed(world, who, tool) is expect, f"{who} / {tool} ({level}) expected allowed={expect}"


@pytest.mark.parametrize("who", ["svc_read", "svc_write", "svc_admin", "svc_propose", "svc_unknown"])
def test_service_token_cannot_use_any_tool_on_a_sibling_workspace(world, who):
    for tool in ALL_WS_TOOLS:
        assert _allowed(world, who, tool, ws="ws2") is False, f"{who} reached ws2 via {tool}"


@pytest.mark.parametrize("who", ["viewer", "editor", "stranger"])
def test_members_have_no_access_to_a_workspace_they_do_not_belong_to(world, who):
    for tool in ALL_WS_TOOLS:
        assert _allowed(world, who, tool, ws="ws2") is False, f"{who} reached ws2 via {tool}"


def test_denied_write_names_the_missing_scope(world):
    with pytest.raises(HTTPException) as exc:
        enforce_mcp_tool_access("update_node", {"workspace_id": world["ws1"]}, world["users"]["svc_read"])
    assert exc.value.detail == {"error": "insufficient_scope", "required": "kb:write"}
    with pytest.raises(HTTPException) as exc:
        enforce_mcp_tool_access("resolve_conflict", {"workspace_id": world["ws1"]}, world["users"]["svc_write"])
    assert exc.value.detail == {"error": "insufficient_scope", "required": "workspace:admin"}


# ─── end to end: the original proof of concept, through execute_tool ──────────

@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from main import app
    return TestClient(app, client=("127.0.0.1", 50000))


def _make_node(client, world, ws):
    r = client.post(f"/api/v1/workspaces/{world[ws]}/nodes",
                    json={"title": "original", "content_type": "factual", "body": "x", "force_create": True},
                    headers={"Authorization": f"Bearer {world['owner_key']}"})
    assert r.status_code == 201, r.text[:200]
    return r.json()["id"]


def _node(db_conn, node_id):
    cur = db_conn.cursor()
    cur.execute("SELECT title, status FROM memory_nodes WHERE id = %s", (node_id,))
    return cur.fetchone()


def _call(name, args, user):
    return asyncio.run(execute_tool(name, args, user, BackgroundTasks()))


@pytest.mark.parametrize("who", ["svc_read", "svc_propose", "svc_unknown", "stranger", "viewer"])
def test_update_and_delete_node_are_refused_and_change_nothing(client, world, db_conn, who):
    nid = _make_node(client, world, "ws1")
    user = world["users"][who]
    for tool, extra in (("update_node", {"title": "HACKED"}), ("delete_node", {})):
        with pytest.raises(HTTPException) as exc:
            _call(tool, {"workspace_id": world["ws1"], "node_id": nid, **extra}, user)
        assert exc.value.status_code == 403, f"{who} {tool}"
    row = _node(db_conn, nid)
    assert (row["title"], row["status"]) == ("original", "active")


def test_token_bound_to_ws1_cannot_touch_a_node_in_ws2(client, world, db_conn):
    nid = _make_node(client, world, "ws2")
    for tool, extra in (("update_node", {"title": "HACKED"}), ("delete_node", {})):
        with pytest.raises(HTTPException) as exc:
            _call(tool, {"workspace_id": world["ws2"], "node_id": nid, **extra}, world["users"]["svc_admin"])
        assert exc.value.status_code == 403
    assert _node(db_conn, nid)["title"] == "original"


def test_resolve_conflict_needs_workspace_admin(world):
    for who in ("svc_read", "svc_write", "stranger", "editor"):
        with pytest.raises(HTTPException) as exc:
            _call("resolve_conflict", {"workspace_id": world["ws1"], "review_id": "rv_x", "resolution": "keep_a"},
                  world["users"][who])
        assert exc.value.status_code == 403, who


@pytest.mark.parametrize("who", ["svc_write", "editor", "owner"])
def test_a_permitted_writer_can_still_update_and_trash(client, world, db_conn, who):
    nid = _make_node(client, world, "ws1")
    user = world["users"][who]
    _call("update_node", {"workspace_id": world["ws1"], "node_id": nid, "title": "edited"}, user)
    assert _node(db_conn, nid)["title"] == "edited"
    _call("delete_node", {"workspace_id": world["ws1"], "node_id": nid}, user)
    assert _node(db_conn, nid)["status"] == "trashed"


# ─── resources/read: same rules as the tools ──────────────────────────────────

SECRET_BODY = "SECRET-BODY-MARKER-0451"


def _read_resource(uri, user):
    from services.mcp_tools import dispatch
    payload = {"jsonrpc": "2.0", "id": 1, "method": "resources/read", "params": {"uri": uri}}
    return asyncio.run(dispatch(payload, user, BackgroundTasks()))


def _secret_node(client, world, ws):
    r = client.post(f"/api/v1/workspaces/{world[ws]}/nodes",
                    json={"title": "resource-title", "content_type": "factual", "body": SECRET_BODY, "force_create": True},
                    headers={"Authorization": f"Bearer {world['owner_key']}"})
    assert r.status_code == 201, r.text[:200]
    return r.json()["id"]


@pytest.mark.parametrize("who", ["svc_propose", "svc_unknown", "svc_unbound", "stranger"])
def test_node_resource_is_refused_without_access(client, world, who):
    nid = _secret_node(client, world, "ws1")
    out = _read_resource(f"memtrace://node/{nid}", world["users"][who])
    assert "error" in out and "result" not in out, who
    text = str(out)
    assert "resource-title" not in text and SECRET_BODY not in text, f"{who} read the node through resources/read"


@pytest.mark.parametrize("who", ["svc_read", "svc_write", "svc_admin", "owner", "editor"])
def test_node_resource_is_readable_with_access(client, world, who):
    nid = _secret_node(client, world, "ws1")
    out = _read_resource(f"memtrace://node/{nid}", world["users"][who])
    text = out["result"]["contents"][0]["text"]
    assert "resource-title" in text and SECRET_BODY in text


def test_viewer_gets_the_node_resource_without_its_body(client, world):
    nid = _secret_node(client, world, "ws1")
    text = _read_resource(f"memtrace://node/{nid}", world["users"]["viewer"])["result"]["contents"][0]["text"]
    assert "resource-title" in text and SECRET_BODY not in text


@pytest.mark.parametrize("who", ["svc_read", "svc_write", "svc_admin"])
def test_node_resource_does_not_cross_into_a_sibling_workspace(client, world, who):
    nid = _secret_node(client, world, "ws2")
    out = _read_resource(f"memtrace://node/{nid}", world["users"][who])
    assert "error" in out and SECRET_BODY not in str(out)


@pytest.mark.parametrize("who", ["svc_propose", "svc_unknown", "svc_unbound", "stranger"])
def test_workspace_summary_resource_is_refused_without_access(world, who):
    from fastapi import HTTPException as _HTTP
    try:
        out = _read_resource(f"memtrace://workspace/{world['ws1']}/summary", world["users"][who])
    except _HTTP as e:
        assert e.status_code in (401, 403)
    else:
        assert "error" in out, who

"""
tests/test_service_token_scope.py — service-token scope enforcement (P1).

Workspace service tokens (key_type='service') carry a `scopes` list, and their
user_id is the workspace owner. Before this fix the list was not enforced
anywhere, so a token labelled read-only could write, and any service token
could mint new keys. These tests pin the intended behaviour against a real
Postgres:

  read-class scopes  -> read only      (kb:read, node:traverse, node:rate)
  kb:write           -> read + write nodes
  workspace:admin/*  -> also workspace settings and associations
  kb:propose / unknown -> nothing (fail closed)
  any service token  -> never touches API-key or workspace-creation endpoints

Requires TEST_DATABASE_URL (disposable Postgres, schema migrated). Skipped
otherwise. All rows carry a unique suffix and are removed afterwards.
"""
from __future__ import annotations

import asyncio
import hashlib
import secrets
import uuid

import pytest
from fastapi import BackgroundTasks, HTTPException


def _insert_key(cur, *, user_id, ws_id, scopes, key_type="service"):
    raw = "mt_" + secrets.token_hex(20)
    cur.execute(
        """INSERT INTO api_keys (id, user_id, name, key_hash, prefix, scopes, workspace_id, key_type)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
        (f"apikey_{uuid.uuid4().hex[:10]}", user_id, "test", hashlib.sha256(raw.encode()).hexdigest(),
         raw[:8], scopes, ws_id, key_type),
    )
    return raw


SERVICE_SCOPES = {
    "read": ["kb:read"],
    "traverse": ["node:traverse"],
    "write": ["kb:write"],
    "admin": ["workspace:admin"],
    "star": ["*"],
    "propose": ["kb:propose"],
    "unknown": ["repo:read"],
}


@pytest.fixture
def world(db_conn):
    """An owner with two workspaces, an account key, and service tokens bound to W1."""
    sfx = uuid.uuid4().hex[:8]
    user_id, ws1, ws2 = f"usr_t{sfx}", f"ws_t{sfx}a", f"ws_t{sfx}b"
    db_conn.autocommit = True
    cur = db_conn.cursor()
    cur.execute(
        "INSERT INTO users (id, display_name, email) VALUES (%s, %s, %s)",
        (user_id, "scope-test", f"scope-test-{sfx}@example.invalid"),
    )
    for ws in (ws1, ws2):
        cur.execute(
            "INSERT INTO workspaces (id, owner_id, name, language) VALUES (%s, %s, %s, 'zh-TW')",
            (ws, user_id, f"scope-test-{ws}"),
        )
    tokens = {
        name: _insert_key(cur, user_id=user_id, ws_id=ws1, scopes=scopes)
        for name, scopes in SERVICE_SCOPES.items()
    }
    owner_key = _insert_key(cur, user_id=user_id, ws_id=None, scopes=[], key_type="account")
    try:
        yield {"user_id": user_id, "ws1": ws1, "ws2": ws2, "tokens": tokens, "owner_key": owner_key}
    finally:
        cur.execute("DELETE FROM memory_nodes WHERE workspace_id IN (%s, %s)", (ws1, ws2))
        cur.execute("DELETE FROM api_keys WHERE user_id = %s", (user_id,))
        cur.execute("DELETE FROM workspaces WHERE owner_id = %s", (user_id,))
        cur.execute("DELETE FROM users WHERE id = %s", (user_id,))


@pytest.fixture
def client():
    """TestClient with a real-looking peer address (api_keys.last_used_ip is inet)."""
    from fastapi.testclient import TestClient
    from main import app
    return TestClient(app, client=("127.0.0.1", 50000))


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _node_body():
    # force_create skips semantic dedup, which needs an embedding provider.
    return {"title": "scope test", "content_type": "factual", "body": "x", "force_create": True}


def _svc_user(world, name, ws_id=None):
    return {
        "sub": world["user_id"], "email": "x@example.invalid", "api_key_id": "apikey_t",
        "role": None, "scopes": SERVICE_SCOPES[name], "workspace_id": ws_id or world["ws1"],
        "key_type": "service",
    }


# ─── node reads / writes (central: require_ws_access) ─────────────────────────

def test_read_only_service_token_cannot_write_nodes(client, world):
    r = client.post(f"/api/v1/workspaces/{world['ws1']}/nodes", json=_node_body(),
                    headers=_auth(world["tokens"]["read"]))
    assert r.status_code == 403, f"read-only token wrote a node: {r.status_code} {r.text[:200]}"
    assert r.json()["detail"]["required"] == "kb:write"


@pytest.mark.parametrize("name", ["read", "traverse", "write", "admin", "star"])
def test_service_tokens_with_a_known_scope_can_read(client, world, name):
    r = client.get(f"/api/v1/workspaces/{world['ws1']}/nodes", headers=_auth(world["tokens"][name]))
    assert r.status_code == 200, r.text[:200]


@pytest.mark.parametrize("name", ["write", "admin", "star"])
def test_service_tokens_with_write_scope_can_write_nodes(client, world, name):
    r = client.post(f"/api/v1/workspaces/{world['ws1']}/nodes", json=_node_body(),
                    headers=_auth(world["tokens"][name]))
    assert r.status_code == 201, r.text[:200]


@pytest.mark.parametrize("name", ["propose", "unknown"])
def test_propose_and_unknown_scopes_get_nothing(client, world, name):
    for method, kwargs in (("get", {}), ("post", {"json": _node_body()})):
        r = getattr(client, method)(f"/api/v1/workspaces/{world['ws1']}/nodes",
                                    headers=_auth(world["tokens"][name]), **kwargs)
        assert r.status_code == 403, f"{name} token {method}: {r.status_code}"


def test_token_stays_bound_to_its_workspace(client, world):
    r = client.get(f"/api/v1/workspaces/{world['ws2']}/nodes", headers=_auth(world["tokens"]["star"]))
    assert r.status_code == 403


# ─── key management endpoints ─────────────────────────────────────────────────

@pytest.mark.parametrize("name", ["read", "write", "admin", "star"])
def test_service_token_cannot_mint_keys(client, world, name):
    r = client.post(f"/api/v1/workspaces/{world['ws1']}/api-keys",
                    json={"name": "escalation", "scopes": ["*"]}, headers=_auth(world["tokens"][name]))
    assert r.status_code == 403, f"{name} service token minted a key: {r.status_code} {r.text[:200]}"


@pytest.mark.parametrize("name", ["read", "star"])
def test_service_token_cannot_use_any_key_endpoint(client, world, name):
    h = _auth(world["tokens"][name])
    ws = world["ws1"]
    calls = [
        ("get", f"/api/v1/workspaces/{ws}/api-keys", None),
        ("post", f"/api/v1/workspaces/{ws}/api-keys/apikey_x/rotate", None),
        ("delete", f"/api/v1/workspaces/{ws}/api-keys/apikey_x", None),
        ("post", "/api/v1/users/me/api-keys", {"name": "personal-escalation"}),
        ("get", "/api/v1/users/me/api-keys", None),
        ("delete", "/api/v1/users/me/api-keys/apikey_x", None),
        ("post", "/api/v1/users/me/api-keys/apikey_x/rotate", None),
    ]
    for method, url, body in calls:
        r = getattr(client, method)(url, headers=h, **({"json": body} if body else {}))
        assert r.status_code == 403, f"{method.upper()} {url} -> {r.status_code} {r.text[:120]}"


def test_owner_account_key_can_still_mint_service_tokens(client, world):
    r = client.post(f"/api/v1/workspaces/{world['ws1']}/api-keys",
                    json={"name": "ci", "scopes": ["kb:read"]}, headers=_auth(world["owner_key"]))
    assert r.status_code == 200, r.text[:200]
    assert r.json()["key"].startswith("mt_")


@pytest.mark.parametrize("scopes", [[], ["bogus"], ["kb:read", "kb:admin"], ["repo:read"]])
def test_minting_rejects_unknown_or_empty_scopes(client, world, scopes):
    r = client.post(f"/api/v1/workspaces/{world['ws1']}/api-keys",
                    json={"name": "ci", "scopes": scopes}, headers=_auth(world["owner_key"]))
    assert r.status_code == 422, f"{scopes}: {r.status_code}"


@pytest.mark.parametrize("scopes", [["kb:read"], ["kb:propose"], ["kb:write"], ["node:traverse", "node:rate"],
                                    ["workspace:admin"], ["*"]])
def test_minting_accepts_the_documented_scopes(client, world, scopes):
    r = client.post(f"/api/v1/workspaces/{world['ws1']}/api-keys",
                    json={"name": "ci", "scopes": scopes}, headers=_auth(world["owner_key"]))
    assert r.status_code == 200, f"{scopes}: {r.status_code} {r.text[:120]}"


# ─── membership endpoints (invites are credentials too) ───────────────────────

@pytest.mark.parametrize("name", ["read", "star"])
def test_service_token_cannot_use_membership_endpoints(client, world, name):
    h = _auth(world["tokens"][name])
    ws = world["ws1"]
    calls = [
        ("post", f"/api/v1/workspaces/{ws}/invites", {"role": "viewer"}),
        ("get", f"/api/v1/workspaces/{ws}/invites", None),
        ("get", f"/api/v1/workspaces/{ws}/members", None),
        ("put", f"/api/v1/workspaces/{ws}/members/{world['user_id']}", {"role": "viewer"}),
        ("delete", f"/api/v1/workspaces/{ws}/members/{world['user_id']}", None),
        ("get", f"/api/v1/workspaces/{ws}/join-requests", None),
    ]
    for method, url, body in calls:
        r = getattr(client, method)(url, headers=h, **({"json": body} if body else {}))
        assert r.status_code == 403, f"{method.upper()} {url} -> {r.status_code} {r.text[:120]}"


def test_owner_account_key_can_still_create_invites(client, world):
    r = client.post(f"/api/v1/workspaces/{world['ws1']}/invites", json={"role": "viewer"},
                    headers=_auth(world["owner_key"]))
    assert r.status_code == 201, r.text[:200]


# ─── workspace create / update (REST) ─────────────────────────────────────────

@pytest.mark.parametrize("name", ["write", "admin", "star"])
def test_service_token_cannot_create_workspaces(client, world, name):
    r = client.post("/api/v1/workspaces", json={"name": "spawned", "language": "zh-TW"},
                    headers=_auth(world["tokens"][name]))
    assert r.status_code == 403, r.text[:200]


def test_owner_account_key_can_still_create_workspaces(client, world, db_conn):
    r = client.post("/api/v1/workspaces", json={"name": "spawned-by-owner", "language": "zh-TW"},
                    headers=_auth(world["owner_key"]))
    assert r.status_code == 201, r.text[:200]
    cur = db_conn.cursor()
    cur.execute("DELETE FROM workspaces WHERE id = %s", (r.json()["id"],))


def test_service_token_cannot_patch_another_workspace_of_the_same_owner(client, world):
    r = client.patch(f"/api/v1/workspaces/{world['ws2']}", json={"description": "hijack"},
                     headers=_auth(world["tokens"]["star"]))
    assert r.status_code == 403, r.text[:200]


@pytest.mark.parametrize("name", ["read", "write"])
def test_patching_own_workspace_needs_workspace_admin(client, world, name):
    r = client.patch(f"/api/v1/workspaces/{world['ws1']}", json={"description": "x"},
                     headers=_auth(world["tokens"][name]))
    assert r.status_code == 403, r.text[:200]


@pytest.mark.parametrize("name", ["admin", "star"])
def test_workspace_admin_token_can_patch_its_own_workspace(client, world, name):
    r = client.patch(f"/api/v1/workspaces/{world['ws1']}", json={"description": "ok"},
                     headers=_auth(world["tokens"][name]))
    assert r.status_code == 200, r.text[:200]


@pytest.mark.parametrize("name", ["read", "write"])
def test_destructive_workspace_operations_need_workspace_admin(client, world, db_conn, name):
    h = _auth(world["tokens"][name])
    ws = world["ws1"]
    for method, url in (("delete", f"/api/v1/workspaces/{ws}"),
                        ("post", f"/api/v1/workspaces/{ws}/purge"),
                        ("post", f"/api/v1/workspaces/{ws}/reembed-all")):
        r = getattr(client, method)(url, headers=h)
        assert r.status_code in (403, 404, 405), f"{method.upper()} {url} -> {r.status_code} {r.text[:120]}"
        assert r.status_code != 404 or "purge" in url, f"{url} not found"
    cur = db_conn.cursor()
    cur.execute("SELECT 1 FROM workspaces WHERE id = %s", (ws,))
    assert cur.fetchone(), "workspace was deleted by a token without workspace:admin"


def test_workspace_admin_token_can_delete_its_workspace(client, world, db_conn):
    r = client.delete(f"/api/v1/workspaces/{world['ws1']}", headers=_auth(world["tokens"]["admin"]))
    assert r.status_code == 204, r.text[:200]


# ─── MCP workspace-management tools ───────────────────────────────────────────

def _run_tool(name, args, user):
    from services.mcp_tools import execute_tool
    return asyncio.run(execute_tool(name, args, user, BackgroundTasks()))


@pytest.mark.parametrize("tool,args", [
    ("update_workspace", {"description": "x"}),
    ("add_association", {"target_workspace_id": "{ws2}"}),
    ("remove_association", {"target_workspace_id": "{ws2}"}),
])
@pytest.mark.parametrize("name", ["read", "write"])
def test_mcp_workspace_management_refuses_tokens_without_workspace_admin(world, tool, args, name):
    args = {k: (v.format(**world) if isinstance(v, str) else v) for k, v in args.items()}
    with pytest.raises(HTTPException) as exc:
        _run_tool(tool, {"workspace_id": world["ws1"], **args}, _svc_user(world, name))
    assert exc.value.status_code == 403
    assert exc.value.detail["required"] == "workspace:admin"


def test_mcp_update_workspace_allows_workspace_admin_token(world):
    out = _run_tool("update_workspace", {"workspace_id": world["ws1"], "description": "via mcp"},
                    _svc_user(world, "admin"))
    assert out["description"] == "via mcp"


def test_mcp_update_workspace_cannot_reach_another_workspace(world):
    with pytest.raises(HTTPException) as exc:
        _run_tool("update_workspace", {"workspace_id": world["ws2"], "description": "x"},
                  _svc_user(world, "star"))
    assert exc.value.status_code == 403


# ─── pure tier logic ──────────────────────────────────────────────────────────

def test_tier_mapping():
    from services.workspaces import service_token_tier
    mk = lambda scopes: {"key_type": "service", "scopes": scopes}
    assert service_token_tier({"sub": "u"}) is None            # not a service token
    assert service_token_tier({"key_type": "account", "scopes": []}) is None
    assert service_token_tier(mk(["kb:read"])) == "read"
    assert service_token_tier(mk(["node:rate"])) == "read"
    assert service_token_tier(mk(["kb:read", "kb:write"])) == "write"
    assert service_token_tier(mk(["kb:write", "workspace:admin"])) == "admin"
    assert service_token_tier(mk(["*"])) == "admin"
    assert service_token_tier(mk(["kb:propose"])) == "none"
    assert service_token_tier(mk([])) == "none"
    assert service_token_tier({"key_type": "service"}) == "none"

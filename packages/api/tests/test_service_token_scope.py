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


def test_insufficient_scope_label_names_the_missing_scope(client, world):
    r = client.get(f"/api/v1/workspaces/{world['ws1']}/nodes", headers=_auth(world["tokens"]["unknown"]))
    assert r.status_code == 403
    assert r.json()["detail"] == {"error": "insufficient_scope", "required": "kb:read"}


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


# ─── content writes beyond nodes: kb:write is enough, kb:read is not ──────────

def _two_nodes(client, world):
    ids = []
    for t in ("a", "b"):
        r = client.post(f"/api/v1/workspaces/{world['ws1']}/nodes", json={**_node_body(), "title": f"edge-{t}"},
                        headers=_auth(world["owner_key"]))
        assert r.status_code == 201, r.text[:200]
        ids.append(r.json()["id"])
    return ids


def test_kb_write_token_can_create_edges_and_read_token_cannot(client, world):
    a, b = _two_nodes(client, world)
    body = {"from_id": a, "to_id": b, "relation": "related_to"}
    r = client.post(f"/api/v1/workspaces/{world['ws1']}/edges", json=body, headers=_auth(world["tokens"]["read"]))
    assert r.status_code == 403 and r.json()["detail"]["required"] == "kb:write", r.text[:200]
    r = client.post(f"/api/v1/workspaces/{world['ws1']}/edges", json=body, headers=_auth(world["tokens"]["write"]))
    assert r.status_code in (200, 201), r.text[:200]


@pytest.mark.parametrize("name,forbidden", [("read", True), ("write", True), ("admin", False)])
def test_review_queue_rest_needs_workspace_admin(client, world, name, forbidden):
    r = client.get(f"/api/v1/workspaces/{world['ws1']}/review-queue", headers=_auth(world["tokens"][name]))
    if forbidden:
        assert r.status_code == 403 and r.json()["detail"]["error"] == "service_token_forbidden"
    else:
        assert r.status_code != 403, r.text[:200]


# ─── audit proposals: the handlers themselves must check access ───────────────

SECRET_REASON = "SECRET-AUDIT-REASONING-7731"


@pytest.fixture
def audit_row(world, db_conn):
    cur = db_conn.cursor()
    pid = f"aprop_{uuid.uuid4().hex[:10]}"
    cur.execute(
        """INSERT INTO audit_proposals (id, workspace_id, reviewer, category, target_ids, reasoning)
           VALUES (%s, %s, 'integrity_auditor', 'missing_embedding', %s, %s)""",
        (pid, world["ws1"], ["mem_x"], SECRET_REASON),
    )
    yield pid
    cur.execute("DELETE FROM audit_proposals WHERE id = %s", (pid,))


def _acct_user(world, sub, role=None):
    return {"sub": sub, "api_key_id": "apikey_t", "role": role, "scopes": [], "workspace_id": None}


@pytest.mark.parametrize("name", ["propose", "unknown"])
def test_none_tier_service_tokens_cannot_read_audit_proposals(client, world, audit_row, name):
    h = _auth(world["tokens"][name])
    for url in (f"/api/v1/workspaces/{world['ws1']}/audit-proposals",
                f"/api/v1/workspaces/{world['ws1']}/nodes/mem_x/audit-summary"):
        r = client.get(url, headers=h)
        assert r.status_code == 403, f"{name} {url}: {r.status_code} {r.text[:120]}"
        assert SECRET_REASON not in r.text


@pytest.mark.parametrize("name", ["read", "write", "admin"])
def test_service_tokens_with_a_read_scope_can_still_read_audit_proposals(client, world, audit_row, name):
    r = client.get(f"/api/v1/workspaces/{world['ws1']}/audit-proposals", headers=_auth(world["tokens"][name]))
    assert r.status_code == 200 and SECRET_REASON in r.text, r.text[:200]
    r = client.get(f"/api/v1/workspaces/{world['ws1']}/nodes/mem_x/audit-summary", headers=_auth(world["tokens"][name]))
    assert r.status_code == 200, r.text[:200]


def test_audit_proposals_are_not_readable_by_a_non_member_account_key(client, world, db_conn, audit_row):
    sfx = uuid.uuid4().hex[:8]
    cur = db_conn.cursor()
    cur.execute("INSERT INTO users (id, display_name, email) VALUES (%s, 'outsider', %s)",
                (f"usr_out{sfx}", f"out{sfx}@example.invalid"))
    raw = _insert_key(cur, user_id=f"usr_out{sfx}", ws_id=None, scopes=[], key_type="account")
    try:
        for url in (f"/api/v1/workspaces/{world['ws1']}/audit-proposals",
                    f"/api/v1/workspaces/{world['ws1']}/nodes/mem_x/audit-summary"):
            r = client.get(url, headers=_auth(raw))
            assert r.status_code == 403 and SECRET_REASON not in r.text, f"{url}: {r.status_code}"
    finally:
        cur.execute("DELETE FROM api_keys WHERE user_id = %s", (f"usr_out{sfx}",))
        cur.execute("DELETE FROM users WHERE id = %s", (f"usr_out{sfx}",))


def test_the_owner_account_key_can_read_audit_proposals(client, world, audit_row):
    r = client.get(f"/api/v1/workspaces/{world['ws1']}/audit-proposals", headers=_auth(world["owner_key"]))
    assert r.status_code == 200 and SECRET_REASON in r.text


def test_audit_proposals_in_an_unknown_workspace_stay_404(client, world):
    r = client.get("/api/v1/workspaces/ws_does_not_exist/audit-proposals", headers=_auth(world["owner_key"]))
    assert r.status_code == 404


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
        ("post", f"/api/v1/workspaces/{ws}/join-requests", {"message": "x"}),
        ("post", f"/api/v1/workspaces/{ws}/join-requests/jr_x/approve", None),
        ("post", f"/api/v1/workspaces/{ws}/join-requests/jr_x/reject", None),
        ("post", f"/api/v1/workspaces/{ws}/members", {"user_id": "usr_x", "role": "viewer"}),
        ("delete", f"/api/v1/workspaces/{ws}/members/me", None),
        ("get", f"/api/v1/workspaces/{ws}/user-candidates?q=a", None),
        ("delete", f"/api/v1/workspaces/{ws}/invites/tok_x", None),
        ("post", "/api/v1/workspaces/invites/tok_x/accept", None),
        ("delete", "/api/v1/workspaces/invites/inv_x", None),
    ]
    for method, url, body in calls:
        r = getattr(client, method)(url, headers=h, **({"json": body} if body else {}))
        assert r.status_code == 403, f"{method.upper()} {url} -> {r.status_code} {r.text[:120]}"
        assert r.json()["detail"]["error"] == "service_token_forbidden", f"{method.upper()} {url}: {r.text[:120]}"


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


# ─── routes outside the workspace: fail-closed allowlist ─────────────────────

NON_WORKSPACE_ROUTES = [
    ("post", "/auth/me/password", {"new_password": "Sup3r-secret-pw!"}),
    ("get", "/auth/me", None),
    ("patch", "/auth/me/onboarding", {}),
    ("put", "/auth/me/notification-preferences", {}),
    ("post", "/api/v1/ai/keys", {"provider": "openai", "api_key": "sk-not-a-real-key"}),
    ("get", "/api/v1/ai/keys", None),
    ("get", "/api/v1/ai/voice-keys", None),
    ("post", "/api/v1/ai/chat", {"workspace_id": "{ws2}", "message": "hi"}),
    ("get", "/api/v1/notifications", None),
    ("delete", "/api/v1/notifications", None),
    ("get", "/api/v1/users/me/connector-accounts", None),
    ("delete", "/api/v1/clone-jobs/clonejob_x", None),
    ("post", "/api/v1/clone-jobs/clonejob_x/cancel", None),
    ("get", "/api/v1/system/users", None),
]


@pytest.mark.parametrize("name", ["read", "write", "star"])
def test_service_token_cannot_reach_account_level_routes(client, world, name):
    for method, url, body in NON_WORKSPACE_ROUTES:
        body = {k: (v.format(**world) if isinstance(v, str) else v) for k, v in body.items()} if body is not None else None
        r = getattr(client, method)(url, headers=_auth(world["tokens"][name]), **({"json": body} if body is not None else {}))
        assert r.status_code == 403, f"{name}: {method.upper()} {url} -> {r.status_code} {r.text[:120]}"
        assert r.json()["detail"]["error"] == "service_token_forbidden", f"{name}: {url}: {r.text[:120]}"


@pytest.mark.parametrize("url", ["/api/v1/workspaces", "/api/v1/workspaces/explore"])
def test_workspace_listings_do_not_reveal_the_owners_other_workspaces(client, world, url):
    # These routes serve anonymous callers too, so a service token is treated as anonymous.
    r = client.get(url, headers=_auth(world["tokens"]["star"]))
    assert world["ws1"] not in r.text and world["ws2"] not in r.text


def test_route_allowlist_is_fail_closed():
    from core.deps import _service_token_route_allowed as allowed
    assert allowed("/api/v1/workspaces/ws_a/nodes", "ws_a", ["kb:read"])
    assert allowed("/api/v1/workspaces/ws_a", "ws_a", ["kb:read"])
    assert allowed("/mcp", "ws_a", ["kb:read"])
    assert not allowed("/api/v1/workspaces/ws_a/some-future-route", "ws_a", ["*"])
    assert not allowed("/api/v1/workspaces/ws_b/nodes", "ws_a", ["*"])
    assert not allowed("/api/v1/workspaces/ws_a/ai-reviewers", "ws_a", ["kb:write"])
    assert allowed("/api/v1/workspaces/ws_a/ai-reviewers", "ws_a", ["workspace:admin"])
    assert not allowed("/api/v1/workspaces", "ws_a", ["*"])
    assert not allowed("/auth/me/password", "ws_a", ["*"])
    assert not allowed("/api/v1/ai/chat", "ws_a", ["*"])


def test_password_change_with_a_service_token_leaves_the_password_alone(client, world, db_conn):
    cur = db_conn.cursor()
    cur.execute("UPDATE users SET password_hash = 'ORIGINAL' WHERE id = %s", (world["user_id"],))
    r = client.post("/auth/me/password", json={"new_password": "Sup3r-secret-pw!"},
                    headers=_auth(world["tokens"]["read"]))
    assert r.status_code == 403, r.text[:200]
    cur.execute("SELECT password_hash FROM users WHERE id = %s", (world["user_id"],))
    assert cur.fetchone()["password_hash"] == "ORIGINAL"


@pytest.mark.parametrize("segment,method", [
    ("clone", "post"), ("fork", "post"), ("pin", "post"), ("clone-status", "get"),
])
def test_workspace_sub_routes_off_the_allowlist_are_denied(client, world, segment, method):
    r = getattr(client, method)(f"/api/v1/workspaces/{world['ws1']}/{segment}",
                                headers=_auth(world["tokens"]["star"]))
    assert r.status_code == 403 and r.json()["detail"]["error"] == "service_token_forbidden", \
        f"{segment}: {r.status_code} {r.text[:120]}"


@pytest.mark.parametrize("name,expect_denied", [("read", True), ("write", True), ("admin", False), ("star", False)])
def test_workspace_configuration_routes_need_workspace_admin(client, world, name, expect_denied):
    for method, segment in (("get", "ai-reviewers"), ("get", "review-policy"), ("get", "conductor/hooks"),
                            ("get", "model-bindings"), ("get", "job-runs")):
        r = getattr(client, method)(f"/api/v1/workspaces/{world['ws1']}/{segment}", headers=_auth(world["tokens"][name]))
        if expect_denied:
            assert r.status_code == 403 and r.json()["detail"]["error"] == "service_token_forbidden", \
                f"{name} {segment}: {r.status_code}"
        else:
            assert r.status_code != 403, f"{name} {segment}: {r.status_code} {r.text[:120]}"


def test_ai_reviewer_cannot_be_created_by_a_read_token(client, world):
    r = client.post(f"/api/v1/workspaces/{world['ws1']}/ai-reviewers",
                    json={"name": "x", "system_prompt": "x"}, headers=_auth(world["tokens"]["read"]))
    assert r.status_code == 403


def test_mcp_endpoint_is_reachable_by_service_tokens(client, world):
    r = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
                    headers=_auth(world["tokens"]["read"]))
    assert r.status_code == 200, r.text[:200]


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


def test_mcp_list_workspaces_shows_only_the_bound_workspace(world):
    out = _run_tool("list_workspaces", {}, _svc_user(world, "read"))
    assert [w["id"] for w in out] == [world["ws1"]]


def test_mcp_list_members_refuses_service_tokens(world):
    with pytest.raises(HTTPException) as exc:
        _run_tool("list_members", {"workspace_id": world["ws1"]}, _svc_user(world, "star"))
    assert exc.value.status_code == 403


def test_mcp_update_workspace_allows_workspace_admin_token(world):
    out = _run_tool("update_workspace", {"workspace_id": world["ws1"], "description": "via mcp"},
                    _svc_user(world, "admin"))
    assert out["description"] == "via mcp"


def test_mcp_update_workspace_cannot_reach_another_workspace(world):
    with pytest.raises(HTTPException) as exc:
        _run_tool("update_workspace", {"workspace_id": world["ws2"], "description": "x"},
                  _svc_user(world, "star"))
    assert exc.value.status_code == 403


# ─── defense in depth: pinned without going through the route allowlist ───────

def test_no_service_token_dependency_refuses_service_tokens_and_passes_others():
    from core.deps import get_current_user_no_service_token as dep
    with pytest.raises(HTTPException) as exc:
        dep({"sub": "u", "key_type": "service", "scopes": ["*"]})
    assert exc.value.status_code == 403 and exc.value.detail["error"] == "service_token_forbidden"
    with pytest.raises(HTTPException) as exc:        # provisioner keys are refused here too
        dep({"sub": "u", "key_type": "provisioner", "scopes": ["provision"]})
    assert exc.value.status_code == 403
    account = {"sub": "u", "api_key_id": "k", "scopes": []}
    assert dep(account) is account
    jwt = {"sub": "u"}
    assert dep(jwt) is jwt


@pytest.mark.parametrize("name,allowed", [("read", False), ("write", False), ("admin", True)])
def test_reembed_all_needs_workspace_admin_even_without_the_allowlist(world, db_conn, name, allowed):
    from services.nodes import reembed_all_nodes_in_db
    cur = db_conn.cursor()
    try:
        reembed_all_nodes_in_db(cur, world["ws1"], _svc_user(world, name))
        assert allowed
    except HTTPException as e:
        assert not allowed and e.status_code == 403
        assert e.detail == {"error": "insufficient_scope", "required": "workspace:admin"}


@pytest.mark.parametrize("name", ["read", "write"])
def test_delete_workspace_needs_workspace_admin_even_without_the_allowlist(world, db_conn, name):
    from services.workspaces import delete_workspace_in_db
    with pytest.raises(HTTPException) as exc:
        delete_workspace_in_db(db_conn.cursor(), world["ws1"], _svc_user(world, name))
    assert exc.value.status_code == 403


def _route_depends_on(route, target):
    stack = list(route.dependant.dependencies)
    while stack:
        d = stack.pop()
        if d.call is target:
            return True
        stack.extend(d.dependencies)
    return False


def test_credential_membership_and_creation_routes_keep_the_service_token_guard():
    """The route allowlist already blocks these; this pins the second layer."""
    from main import app
    from core.deps import get_current_user_no_service_token as guard
    wanted = []
    for r in app.routes:
        path = getattr(r, "path", "")
        methods = getattr(r, "methods", None) or set()
        if not hasattr(r, "dependant") or "review-policy" in path:
            continue
        if "api-keys" in path or "/join-requests" in path or "/invites" in path or "/members" in path \
                or "/user-candidates" in path or (path == "/api/v1/workspaces" and "POST" in methods):
            wanted.append(r)
    assert len(wanted) >= 20, "route discovery is broken"
    missing = [f"{sorted(r.methods)} {r.path}" for r in wanted if not _route_depends_on(r, guard)]
    assert not missing, missing


@pytest.mark.parametrize("name,kwargs,allowed", [
    ("read", {"write": True}, False),
    ("read", {"required_role": "admin"}, False),
    ("read", {"required_role": "editor"}, False),
    ("write", {"write": True}, True),
    ("write", {"required_role": "admin"}, True),
    ("read", {}, True),
])
def test_require_ws_access_maps_write_and_role_requirements_to_the_write_tier(world, db_conn, name, kwargs, allowed):
    from services.workspaces import require_ws_access
    cur = db_conn.cursor()
    try:
        require_ws_access(cur, world["ws1"], _svc_user(world, name), **kwargs)
        assert allowed
    except HTTPException as e:
        assert not allowed and e.status_code == 403
        assert e.detail == {"error": "insufficient_scope", "required": "kb:write"}


@pytest.mark.parametrize("name", ["read", "write"])
def test_purge_workspace_needs_workspace_admin_even_without_the_allowlist(world, db_conn, name):
    from services.workspaces import purge_workspace_in_db
    with pytest.raises(HTTPException) as exc:
        purge_workspace_in_db(db_conn.cursor(), world["ws1"], _svc_user(world, name))
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

"""
tests/test_provisioner_keys.py — provisioner keys (migration 011, routers/provision.py).

A provisioner key lets an external harness create knowledge bases for its owner and
receive a workspace-bound kb:write service token for each, in one transaction. It can
do nothing else, and the token it mints is an ordinary (limited) service token.

Requires TEST_DATABASE_URL (disposable Postgres, schema migrated); skipped otherwise.
Rows carry a unique suffix and are removed afterwards.
"""
from __future__ import annotations

import concurrent.futures
import hashlib
import secrets
import uuid

from unittest.mock import patch

import pytest


def _hash(raw):
    return hashlib.sha256(raw.encode()).hexdigest()


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from main import app
    return TestClient(app, client=("127.0.0.1", 50000))


@pytest.fixture
def world(db_conn):
    """An owner (with a JWT, as a signed-in person) and an account-level API key."""
    from core.security import create_access_token
    sfx = uuid.uuid4().hex[:8]
    uid = f"usr_p{sfx}"
    email = f"prov-{sfx}@example.invalid"
    db_conn.autocommit = True
    cur = db_conn.cursor()
    cur.execute("INSERT INTO users (id, display_name, email) VALUES (%s, %s, %s)", (uid, "prov-test", email))
    raw = "mt_" + secrets.token_hex(20)
    cur.execute(
        """INSERT INTO api_keys (id, user_id, name, key_hash, prefix, scopes, key_type)
           VALUES (%s, %s, 'acct', %s, %s, '{}', 'account')""",
        (f"apikey_a{sfx}", uid, _hash(raw), raw[:8]),
    )
    ctx = {"uid": uid, "jwt": create_access_token(uid, email, "prov-test"), "account_key": raw, "sfx": sfx}
    try:
        yield ctx
    finally:
        cur.execute("SELECT id FROM workspaces WHERE owner_id = %s", (uid,))
        ws_ids = [r["id"] for r in cur.fetchall()]
        if ws_ids:
            cur.execute("DELETE FROM edges WHERE workspace_id = ANY(%s)", (ws_ids,))
            cur.execute("DELETE FROM memory_nodes WHERE workspace_id = ANY(%s)", (ws_ids,))
            cur.execute("DELETE FROM workspace_members WHERE workspace_id = ANY(%s)", (ws_ids,))
        cur.execute("DELETE FROM api_keys WHERE user_id = %s", (uid,))
        cur.execute("DELETE FROM workspaces WHERE owner_id = %s", (uid,))
        cur.execute("DELETE FROM users WHERE id = %s", (uid,))


def _bearer(token):
    return {"Authorization": f"Bearer {token}"}


def _mint_provisioner(client, world, **body):
    r = client.post("/api/v1/users/me/provisioner-keys", json={"name": "harness-prov", **body},
                    headers=_bearer(world["jwt"]))
    assert r.status_code == 201, r.text[:300]
    return r.json()


def _provision(client, key, **body):
    payload = {"name": "harness kb", "language": "zh-TW", **body}
    return client.post("/api/v1/provision/workspaces", json=payload, headers=_bearer(key))


# ─── creating, listing and revoking provisioner keys ─────────────────────────

def test_a_signed_in_person_can_create_list_and_revoke_a_provisioner_key(client, world, db_conn):
    made = _mint_provisioner(client, world, expires_in_days=30, max_workspaces=3)
    assert made["key"].startswith("mt_") and made["max_workspaces"] == 3 and made["workspaces_created"] == 0

    cur = db_conn.cursor()
    cur.execute("SELECT key_hash, key_type, user_id, workspace_id, max_workspaces, "
                "expires_at > now() + interval '29 days' AS long_enough, expires_at < now() + interval '31 days' AS short_enough "
                "FROM api_keys WHERE id = %s", (made["id"],))
    row = cur.fetchone()
    assert row["key_hash"] == _hash(made["key"]) and made["key"] not in str(row)   # only a hash is stored
    assert (row["key_type"], row["user_id"], row["workspace_id"], row["max_workspaces"]) == ("provisioner", world["uid"], None, 3)
    assert row["long_enough"] and row["short_enough"]

    listed = client.get("/api/v1/users/me/provisioner-keys", headers=_bearer(world["jwt"])).json()
    assert [k["id"] for k in listed] == [made["id"]]
    assert "key" not in listed[0] and listed[0]["prefix"] == made["prefix"] and listed[0]["workspaces_created"] == 0

    r = client.delete(f"/api/v1/users/me/provisioner-keys/{made['id']}", headers=_bearer(world["jwt"]))
    assert r.status_code == 204
    assert client.get("/api/v1/users/me/provisioner-keys", headers=_bearer(world["jwt"])).json() == []
    assert _provision(client, made["key"]).status_code == 401           # revoked keys stop working
    assert client.delete(f"/api/v1/users/me/provisioner-keys/{made['id']}", headers=_bearer(world["jwt"])).status_code == 404


@pytest.mark.parametrize("body", [
    {"expires_in_days": 91}, {"expires_in_days": 0}, {"max_workspaces": 51}, {"max_workspaces": 0}, {"name": ""},
    {"name": "   "}, {"name": "a\u0000b"}, {"expires_in_days": True}, {"max_workspaces": True}, {"can_delete_workspaces": "yes"},
])
def test_provisioner_key_limits_are_enforced(client, world, body):
    r = client.post("/api/v1/users/me/provisioner-keys", json={"name": "k", **body}, headers=_bearer(world["jwt"]))
    assert r.status_code == 422, f"{body}: {r.status_code}"


def test_defaults_are_the_deployments_ceiling(client, world):
    made = _mint_provisioner(client, world)
    assert made["max_workspaces"] == 50 and made["can_delete_workspaces"] is False


def test_the_ceiling_comes_from_the_deployment_setting(client, world):
    from core.config import settings
    with patch.object(settings, "max_provisioned_workspaces", 3):
        assert _mint_provisioner(client, world)["max_workspaces"] == 3
        assert _mint_provisioner(client, world, max_workspaces=2)["max_workspaces"] == 2
        r = client.post("/api/v1/users/me/provisioner-keys", json={"name": "k", "max_workspaces": 4},
                        headers=_bearer(world["jwt"]))
        assert r.status_code == 422 and r.json()["detail"] == {"error": "max_workspaces_too_large", "max": 3}


def test_a_lowered_ceiling_also_limits_existing_keys(client, world):
    from core.config import settings
    prov = _mint_provisioner(client, world, max_workspaces=5)
    with patch.object(settings, "max_provisioned_workspaces", 1):
        assert _provision(client, prov["key"]).status_code == 201
        r = _provision(client, prov["key"])
        assert r.status_code == 403 and r.json()["detail"] == {"error": "quota_exceeded", "max_workspaces": 1}
        assert client.get("/api/v1/provision/quota", headers=_bearer(prov["key"])).json()["max_workspaces"] == 1


def test_an_api_key_cannot_create_or_manage_provisioner_keys(client, world):
    prov = _mint_provisioner(client, world)
    for who, token in (("account key", world["account_key"]), ("provisioner key", prov["key"])):
        r = client.post("/api/v1/users/me/provisioner-keys", json={"name": "x"}, headers=_bearer(token))
        assert r.status_code == 403, f"{who} minted a provisioner key: {r.status_code}"
        assert client.get("/api/v1/users/me/provisioner-keys", headers=_bearer(token)).status_code == 403
        assert client.delete(f"/api/v1/users/me/provisioner-keys/{prov['id']}", headers=_bearer(token)).status_code == 403
    assert client.post("/api/v1/users/me/provisioner-keys", json={"name": "x"}).status_code in (401, 403)


def test_personal_key_endpoints_do_not_touch_provisioner_keys(client, world):
    prov = _mint_provisioner(client, world)
    listed = client.get("/api/v1/users/me/api-keys", headers=_bearer(world["account_key"])).json()
    assert prov["id"] not in [k["id"] for k in listed]
    # rotating or revoking through the personal endpoints must not convert or delete it
    assert client.post(f"/api/v1/users/me/api-keys/{prov['id']}/rotate", headers=_bearer(world["account_key"])).status_code == 404
    assert client.delete(f"/api/v1/users/me/api-keys/{prov['id']}", headers=_bearer(world["account_key"])).status_code == 404
    assert _provision(client, prov["key"]).status_code == 201


# ─── provisioning ────────────────────────────────────────────────────────────

def test_provisioning_creates_the_workspace_and_a_bound_kb_write_token(client, world, db_conn):
    prov = _mint_provisioner(client, world)
    r = _provision(client, prov["key"], name="Project C memory", language="en", description="for the harness")
    assert r.status_code == 201, r.text[:300]
    out = r.json()
    ws_id, tok = out["workspace_id"], out["service_token"]
    assert tok["key"].startswith("mt_") and tok["scopes"] == ["kb:write"] and tok["expires_at"] is None

    cur = db_conn.cursor()
    cur.execute("SELECT owner_id, name, language, visibility, qa_archive_mode, auto_split, provisioned_by_key_id, "
                "settings->>'mcp_ingest_enabled' AS ingest FROM workspaces WHERE id = %s", (ws_id,))
    ws = cur.fetchone()
    assert ws["owner_id"] == world["uid"] and ws["name"] == "Project C memory" and ws["language"] == "en"
    assert (ws["visibility"], ws["qa_archive_mode"], ws["auto_split"], ws["ingest"]) == ("private", "manual_review", False, "true")
    assert ws["provisioned_by_key_id"] == prov["id"]

    cur.execute("SELECT key_hash, key_type, scopes, workspace_id, user_id, parent_key_id, expires_at "
                "FROM api_keys WHERE id = %s", (tok["id"],))
    k = cur.fetchone()
    assert k["key_hash"] == _hash(tok["key"]) and tok["key"] not in str(k)
    assert (k["key_type"], k["scopes"], k["workspace_id"], k["user_id"], k["parent_key_id"]) == \
        ("service", ["kb:write"], ws_id, world["uid"], prov["id"])

    listed = client.get("/api/v1/users/me/provisioner-keys", headers=_bearer(world["jwt"])).json()
    assert listed[0]["workspaces_created"] == 1


def test_the_minted_token_can_work_in_its_workspace_and_nothing_else(client, world):
    prov = _mint_provisioner(client, world)
    out = _provision(client, prov["key"]).json()
    ws, h = out["workspace_id"], _bearer(out["service_token"]["key"])
    node = {"title": "first", "content_type": "factual", "body": "hello", "force_create": True}
    a = client.post(f"/api/v1/workspaces/{ws}/nodes", json=node, headers=h)
    b = client.post(f"/api/v1/workspaces/{ws}/nodes", json={**node, "title": "second"}, headers=h)
    assert a.status_code == 201 and b.status_code == 201, (a.text[:200], b.text[:200])
    e = client.post(f"/api/v1/workspaces/{ws}/edges",
                    json={"from_id": a.json()["id"], "to_id": b.json()["id"], "relation": "related_to"}, headers=h)
    assert e.status_code in (200, 201), e.text[:200]
    assert client.get(f"/api/v1/workspaces/{ws}/nodes", headers=h).status_code == 200
    # what it must not be able to do
    assert client.post("/api/v1/workspaces", json={"name": "x", "language": "zh-TW"}, headers=h).status_code == 403
    assert client.post(f"/api/v1/workspaces/{ws}/api-keys", json={"name": "x", "scopes": ["*"]}, headers=h).status_code == 403
    assert client.post("/api/v1/provision/workspaces", json={"name": "x", "language": "en"}, headers=h).status_code == 403
    assert client.patch(f"/api/v1/workspaces/{ws}", json={"description": "x"}, headers=h).status_code == 403


def test_the_minted_token_works_over_mcp_with_the_default_profile(client, world):
    prov = _mint_provisioner(client, world)
    out = _provision(client, prov["key"]).json()
    ws, h = out["workspace_id"], _bearer(out["service_token"]["key"])
    call = lambda name, args: client.post("/mcp", headers=h, json={
        "jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": name, "arguments": args}}).json()
    listed = call("list_workspaces", {})
    assert "error" not in listed, listed
    assert ws in str(listed)
    created = call("create_node", {"workspace_id": ws, "title": "via mcp", "content_type": "factual", "body": "x",
                                   "force_create": True})
    assert "error" not in created, created


def test_the_token_expiry_option(client, world, db_conn):
    prov = _mint_provisioner(client, world)
    out = _provision(client, prov["key"], token_expires_in_days=30).json()
    assert out["service_token"]["expires_at"] is not None
    for bad in (0, 366):
        assert _provision(client, prov["key"], token_expires_in_days=bad).status_code == 422


@pytest.mark.parametrize("body", [{"name": ""}, {"language": "fr"}, {"language": ""}, {"token_name": ""}])
def test_provision_validates_input(client, world, body):
    prov = _mint_provisioner(client, world)
    assert _provision(client, prov["key"], **body).status_code == 422, body


def test_only_a_provisioner_key_can_provision(client, world):
    for who, token in (("account key", world["account_key"]), ("jwt", world["jwt"])):
        r = _provision(client, token)
        assert r.status_code == 403, f"{who}: {r.status_code}"
    prov = _mint_provisioner(client, world)
    tok = _provision(client, prov["key"]).json()["service_token"]["key"]
    assert _provision(client, tok).status_code == 403
    assert client.post("/api/v1/provision/workspaces", json={"name": "x", "language": "en"}).status_code in (401, 403)


# ─── a provisioner key can do nothing else ───────────────────────────────────

def test_a_provisioner_key_is_refused_everywhere_else(client, world):
    prov = _mint_provisioner(client, world)
    made = _provision(client, prov["key"]).json()
    h = _bearer(prov["key"])
    ws = made["workspace_id"]
    calls = [
        ("get", "/auth/me"), ("get", f"/api/v1/workspaces/{ws}"),
        ("get", f"/api/v1/workspaces/{ws}/nodes"), ("post", f"/api/v1/workspaces/{ws}/nodes"),
        ("get", "/api/v1/users/me/api-keys"), ("get", "/api/v1/ai/keys"), ("get", "/api/v1/notifications"),
        ("post", "/mcp"), ("post", "/api/v1/mcp/mcp"), ("post", "/api/v1/workspaces"),
        ("get", f"/api/v1/workspaces/{ws}/members"), ("post", f"/api/v1/workspaces/{ws}/invites"),
    ]
    for method, url in calls:
        kwargs = {"json": {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}} if "mcp" in url else {}
        r = getattr(client, method)(url, headers=h, **kwargs)
        assert r.status_code in (400, 403), f"{method.upper()} {url} -> {r.status_code} {r.text[:120]}"
        assert r.status_code != 200
    # Routes that also serve anonymous callers treat the key as anonymous: no private workspaces
    for url in ("/api/v1/workspaces", "/api/v1/workspaces/explore"):
        assert ws not in client.get(url, headers=h).text, url
    # on the provisioning routes themselves only the documented methods are allowed
    for method in ("put", "patch"):
        assert getattr(client, method)("/api/v1/provision/workspaces", headers=h).status_code in (403, 405)
    assert client.post("/api/v1/provision/quota", headers=h).status_code in (403, 405)


def test_a_provisioner_key_does_not_inherit_account_access(client, world):
    """Regression guard: unhandled key types would fall through to account-key behaviour."""
    prov = _mint_provisioner(client, world)
    r = client.get("/api/v1/users/me/api-keys", headers=_bearer(prov["key"]))
    assert r.status_code == 403
    assert r.json()["detail"]["error"] in ("provisioner_key_forbidden", "service_token_forbidden")


# ─── limits, expiry, atomicity ───────────────────────────────────────────────

def test_the_workspace_quota(client, world):
    prov = _mint_provisioner(client, world, max_workspaces=2)
    assert _provision(client, prov["key"]).status_code == 201
    assert _provision(client, prov["key"]).status_code == 201
    r = _provision(client, prov["key"])
    assert r.status_code == 403 and r.json()["detail"] == {"error": "quota_exceeded", "max_workspaces": 2}


def test_the_quota_holds_under_concurrent_requests(client, world, db_conn):
    prov = _mint_provisioner(client, world, max_workspaces=1)
    from fastapi.testclient import TestClient
    from main import app

    def go(_):
        return _provision(TestClient(app, client=("127.0.0.1", 50000)), prov["key"]).status_code

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        codes = sorted(pool.map(go, range(5)))
    assert codes == [201, 403, 403, 403, 403], codes
    cur = db_conn.cursor()
    cur.execute("SELECT count(*) AS n FROM workspaces WHERE provisioned_by_key_id = %s", (prov["id"],))
    assert cur.fetchone()["n"] == 1


def test_an_expired_provisioner_key_is_rejected(client, world, db_conn):
    prov = _mint_provisioner(client, world)
    db_conn.cursor().execute("UPDATE api_keys SET expires_at = now() - interval '1 minute' WHERE id = %s", (prov["id"],))
    assert _provision(client, prov["key"]).status_code == 401


def test_a_failure_part_way_leaves_nothing_behind(world, db_conn, monkeypatch):
    """The workspace is created before the token is inserted; if the insert fails, neither may remain."""
    from fastapi.testclient import TestClient
    from main import app
    import routers.provision as provision
    quiet = TestClient(app, client=("127.0.0.1", 50000), raise_server_exceptions=False)
    prov = _mint_provisioner(quiet, world, max_workspaces=1)

    monkeypatch.setattr(provision, "PROVISIONED_TOKEN_SCOPES", None)   # violates scopes NOT NULL at the key insert
    r = _provision(quiet, prov["key"])
    assert r.status_code == 500
    monkeypatch.undo()

    cur = db_conn.cursor()
    cur.execute("SELECT count(*) AS n FROM workspaces WHERE owner_id = %s", (world["uid"],))
    assert cur.fetchone()["n"] == 0
    cur.execute("SELECT count(*) AS n FROM api_keys WHERE parent_key_id = %s", (prov["id"],))
    assert cur.fetchone()["n"] == 0
    assert _provision(quiet, prov["key"]).status_code == 201     # the failed attempt did not use up the quota


def test_revoking_a_provisioner_key_leaves_the_tokens_it_minted_working(client, world):
    prov = _mint_provisioner(client, world)
    out = _provision(client, prov["key"]).json()
    client.delete(f"/api/v1/users/me/provisioner-keys/{prov['id']}", headers=_bearer(world["jwt"]))
    r = client.get(f"/api/v1/workspaces/{out['workspace_id']}/nodes", headers=_bearer(out["service_token"]["key"]))
    assert r.status_code == 200


def test_plaintext_keys_are_not_logged(client, world, caplog, capsys):
    import logging
    caplog.set_level(logging.DEBUG)
    prov = _mint_provisioner(client, world)
    out = _provision(client, prov["key"]).json()
    seen = caplog.text + capsys.readouterr().out + capsys.readouterr().err
    assert prov["key"] not in seen and out["service_token"]["key"] not in seen


def test_the_database_constraint_rejects_a_malformed_provisioner_key(world, db_conn):
    import psycopg2
    cur = db_conn.cursor()
    for cols, vals in (
        ("max_workspaces", (None,)),                    # missing cap
    ):
        with pytest.raises(psycopg2.errors.CheckViolation):
            cur.execute(
                """INSERT INTO api_keys (id, user_id, name, key_hash, prefix, key_type, max_workspaces, expires_at)
                   VALUES (%s, %s, 'bad', %s, 'mt_bad', 'provisioner', %s, now() + interval '1 day')""",
                (f"apikey_bad{uuid.uuid4().hex[:6]}", world["uid"], _hash(uuid.uuid4().hex), *vals),
            )
    with pytest.raises(psycopg2.errors.CheckViolation):  # no expiry
        cur.execute(
            """INSERT INTO api_keys (id, user_id, name, key_hash, prefix, key_type, max_workspaces)
               VALUES (%s, %s, 'bad', %s, 'mt_bad', 'provisioner', 3)""",
            (f"apikey_bad{uuid.uuid4().hex[:6]}", world["uid"], _hash(uuid.uuid4().hex)),
        )

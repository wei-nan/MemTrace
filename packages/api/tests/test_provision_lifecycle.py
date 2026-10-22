"""
tests/test_provision_lifecycle.py — migration 012 and the rest of the provisioner API:
Idempotency-Key, quota, listing, token revocation, guarded deletion.

A harness manager retries, restarts and cleans up; these pin what it can rely on. Everything here
is about workspaces a provisioner key created itself: other keys, other owners and workspaces the
owner made some other way must stay out of reach.

Requires TEST_DATABASE_URL (disposable Postgres, schema migrated); skipped otherwise.
"""
from __future__ import annotations

import concurrent.futures
import uuid
from unittest.mock import patch

import pytest

from tests.test_provisioner_keys import _bearer, _hash, _mint_provisioner, _provision, client, world  # noqa: F401


def _provision_idem(client, key, idem, **body):
    payload = {"name": "harness kb", "language": "zh-TW", **body}
    return client.post("/api/v1/provision/workspaces", json=payload,
                       headers={**_bearer(key), "Idempotency-Key": idem})


def _nodes(client, ws, token):
    return client.get(f"/api/v1/workspaces/{ws}/nodes", headers=_bearer(token))


def _add_node(client, ws, token, title="n"):
    return client.post(f"/api/v1/workspaces/{ws}/nodes", headers=_bearer(token),
                       json={"title": title, "content_type": "factual", "body": "x", "force_create": True})


def _count(db_conn, sql, *params):
    cur = db_conn.cursor()
    cur.execute(sql, params)
    return cur.fetchone()["n"]


def _workspaces_of(db_conn, key_id):
    return _count(db_conn, "SELECT count(*) AS n FROM workspaces WHERE provisioned_by_key_id = %s", key_id)


def _active_tokens(db_conn, ws_id):
    return _count(db_conn, "SELECT count(*) AS n FROM api_keys WHERE workspace_id = %s AND key_type = 'service' "
                           "AND revoked_at IS NULL", ws_id)


# ─── Idempotency-Key ─────────────────────────────────────────────────────────

def test_a_retry_returns_the_same_workspace_with_a_fresh_token_and_revokes_the_old_one(client, world, db_conn):
    prov = _mint_provisioner(client, world)
    first = _provision_idem(client, prov["key"], "proj-1")
    assert first.status_code == 201 and first.json()["idempotent_replay"] is False
    a = first.json()
    again = _provision_idem(client, prov["key"], "proj-1")
    assert again.status_code == 200, again.text[:300]
    b = again.json()
    assert b["idempotent_replay"] is True and b["workspace_id"] == a["workspace_id"]
    assert b["service_token"]["key"] != a["service_token"]["key"]
    assert b["service_token"]["scopes"] == ["kb:write"]
    # the old token is dead, the new one works, and there is exactly one workspace and one live token
    assert _add_node(client, a["workspace_id"], a["service_token"]["key"]).status_code == 401      # a revoked token is refused
    assert _nodes(client, a["workspace_id"], b["service_token"]["key"]).status_code == 200
    assert _workspaces_of(db_conn, prov["id"]) == 1
    assert _active_tokens(db_conn, a["workspace_id"]) == 1
    cur = db_conn.cursor()
    cur.execute("SELECT provision_request_id, provision_request_hash FROM workspaces WHERE id = %s", (a["workspace_id"],))
    row = cur.fetchone()
    assert row["provision_request_id"] == "proj-1" and len(row["provision_request_hash"]) == 64


def test_a_replay_does_not_use_up_quota_even_at_the_cap(client, world):
    prov = _mint_provisioner(client, world, max_workspaces=1)
    assert _provision_idem(client, prov["key"], "only").status_code == 201
    assert _provision_idem(client, prov["key"], "only").status_code == 200
    assert _provision_idem(client, prov["key"], "second").status_code == 403           # a different key is a new workspace
    assert client.get("/api/v1/provision/quota", headers=_bearer(prov["key"])).json()["remaining"] == 0


def test_the_same_key_with_a_different_request_is_a_conflict_and_changes_nothing(client, world, db_conn):
    prov = _mint_provisioner(client, world)
    a = _provision_idem(client, prov["key"], "proj-1", name="one", description="d").json()
    for change in ({"name": "two"}, {"language": "en"}, {"description": "other"}, {"description": None}):
        r = _provision_idem(client, prov["key"], "proj-1", **{"name": "one", "description": "d", **change})
        assert r.status_code == 409 and r.json()["detail"]["error"] == "idempotency_conflict", change
    assert _workspaces_of(db_conn, prov["id"]) == 1
    assert _nodes(client, a["workspace_id"], a["service_token"]["key"]).status_code == 200   # the conflict revoked nothing


def test_token_options_and_surrounding_whitespace_do_not_make_a_retry_a_different_request(client, world):
    prov = _mint_provisioner(client, world)
    a = _provision_idem(client, prov["key"], "proj-1", name="same").json()
    r = _provision_idem(client, prov["key"], "proj-1", name="  same  ", token_name="renamed", token_expires_in_days=30)
    assert r.status_code == 200, r.text[:200]
    assert r.json()["workspace_id"] == a["workspace_id"] and r.json()["service_token"]["expires_at"] is not None


def test_idempotency_keys_belong_to_one_provisioner_key(client, world):
    one, two = _mint_provisioner(client, world), _mint_provisioner(client, world)
    a = _provision_idem(client, one["key"], "shared").json()
    b = _provision_idem(client, two["key"], "shared")
    assert b.status_code == 201 and b.json()["workspace_id"] != a["workspace_id"]
    assert _nodes(client, a["workspace_id"], a["service_token"]["key"]).status_code == 200   # not revoked by the other key


@pytest.mark.parametrize("bad", ["", "x" * 129, "has space", "tab\there", "slash/not-allowed", "semi;colon"])
def test_a_malformed_idempotency_key_is_rejected(client, world, bad):
    prov = _mint_provisioner(client, world)
    r = _provision_idem(client, prov["key"], bad)
    assert r.status_code == 422, f"{bad!r}: {r.status_code}"


@pytest.mark.parametrize("good", ["a", "x" * 128, "proj_1.2:3-4", "p_0123456789abcdef0123456789abcdef"])
def test_well_formed_idempotency_keys_are_accepted(client, world, good):
    prov = _mint_provisioner(client, world)
    assert _provision_idem(client, prov["key"], good).status_code == 201


def test_without_the_header_every_call_creates_a_workspace(client, world, db_conn):
    prov = _mint_provisioner(client, world)
    ids = {_provision(client, prov["key"]).json()["workspace_id"] for _ in range(2)}
    assert len(ids) == 2
    assert _count(db_conn, "SELECT count(*) AS n FROM workspaces WHERE provisioned_by_key_id = %s "
                           "AND provision_request_id IS NULL", prov["id"]) == 2


def test_concurrent_retries_make_one_workspace_and_leave_one_live_token(client, world, db_conn):
    prov = _mint_provisioner(client, world)
    from fastapi.testclient import TestClient
    from main import app

    def go(_):
        r = _provision_idem(TestClient(app, client=("127.0.0.1", 50000)), prov["key"], "race")
        return r.status_code, r.json().get("workspace_id")

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(go, range(4)))
    assert {code for code, _ in results} <= {200, 201}, results
    assert sorted(code for code, _ in results).count(201) == 1
    ws_ids = {ws for _, ws in results}
    assert len(ws_ids) == 1
    assert _workspaces_of(db_conn, prov["id"]) == 1
    assert _active_tokens(db_conn, ws_ids.pop()) == 1


def test_a_replay_that_fails_leaves_the_old_token_working(client, world, monkeypatch):
    from fastapi.testclient import TestClient
    from main import app
    import routers.provision as provision
    quiet = TestClient(app, client=("127.0.0.1", 50000), raise_server_exceptions=False)
    prov = _mint_provisioner(client, world)
    a = _provision_idem(client, prov["key"], "proj-1").json()
    monkeypatch.setattr(provision, "_mint_token", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    assert _provision_idem(quiet, prov["key"], "proj-1").status_code == 500
    monkeypatch.undo()
    assert _nodes(client, a["workspace_id"], a["service_token"]["key"]).status_code == 200


def test_after_the_owner_deletes_the_workspace_the_same_key_creates_a_new_one(client, world, db_conn):
    prov = _mint_provisioner(client, world)
    a = _provision_idem(client, prov["key"], "proj-1").json()
    db_conn.cursor().execute("DELETE FROM api_keys WHERE workspace_id = %s", (a["workspace_id"],))
    db_conn.cursor().execute("DELETE FROM workspaces WHERE id = %s", (a["workspace_id"],))
    b = _provision_idem(client, prov["key"], "proj-1")
    assert b.status_code == 201 and b.json()["workspace_id"] != a["workspace_id"]


def test_new_tokens_from_a_replay_are_not_logged(client, world, caplog, capsys):
    import logging
    caplog.set_level(logging.DEBUG)
    prov = _mint_provisioner(client, world)
    _provision_idem(client, prov["key"], "p")
    out = _provision_idem(client, prov["key"], "p").json()
    seen = caplog.text + capsys.readouterr().out
    assert out["service_token"]["key"] not in seen and prov["key"] not in seen


# ─── quota ───────────────────────────────────────────────────────────────────

def test_the_quota_endpoint(client, world):
    prov = _mint_provisioner(client, world, max_workspaces=3)
    h = _bearer(prov["key"])
    q = client.get("/api/v1/provision/quota", headers=h).json()
    assert (q["max_workspaces"], q["workspaces_created"], q["remaining"]) == (3, 0, 3) and q["expires_at"]
    _provision(client, prov["key"])
    q = client.get("/api/v1/provision/quota", headers=h).json()
    assert (q["workspaces_created"], q["remaining"]) == (1, 2)
    for _ in range(2):
        _provision(client, prov["key"])
    assert client.get("/api/v1/provision/quota", headers=h).json()["remaining"] == 0


def test_the_quota_endpoint_needs_a_live_provisioner_key(client, world):
    prov = _mint_provisioner(client, world)
    out = _provision(client, prov["key"]).json()
    for who, token in (("account key", world["account_key"]), ("jwt", world["jwt"]),
                       ("minted token", out["service_token"]["key"])):
        assert client.get("/api/v1/provision/quota", headers=_bearer(token)).status_code == 403, who
    client.delete(f"/api/v1/users/me/provisioner-keys/{prov['id']}", headers=_bearer(world["jwt"]))
    assert client.get("/api/v1/provision/quota", headers=_bearer(prov["key"])).status_code == 401


# ─── listing and lookup ──────────────────────────────────────────────────────

def test_listing_shows_only_this_keys_workspaces_and_never_a_token_secret(client, world):
    one, two = _mint_provisioner(client, world), _mint_provisioner(client, world)
    a1 = _provision_idem(client, one["key"], "a", name="alpha").json()
    a2 = _provision_idem(client, one["key"], "b", name="beta").json()
    b1 = _provision_idem(client, two["key"], "a", name="other-key").json()
    # an owner-made workspace the keys know nothing about
    r = client.post("/api/v1/workspaces", json={"name": "owner-made", "language": "en"}, headers=_bearer(world["jwt"]))
    assert r.status_code == 201

    listed = client.get("/api/v1/provision/workspaces", headers=_bearer(one["key"])).json()
    assert [w["workspace_id"] for w in listed] == [a1["workspace_id"], a2["workspace_id"]]
    assert [w["idempotency_key"] for w in listed] == ["a", "b"]
    assert listed[0]["token"]["prefix"] == a1["service_token"]["prefix"] and listed[0]["token"]["id"] == a1["service_token"]["id"]
    text = str(listed)
    assert a1["service_token"]["key"] not in text and a2["service_token"]["key"] not in text
    assert b1["workspace_id"] not in text and r.json()["id"] not in text


def test_lookup_by_idempotency_key_and_paging(client, world):
    prov = _mint_provisioner(client, world)
    made = [_provision_idem(client, prov["key"], f"p{i}", name=f"n{i}").json()["workspace_id"] for i in range(3)]
    h = _bearer(prov["key"])
    one = client.get("/api/v1/provision/workspaces", params={"idempotency_key": "p1"}, headers=h).json()
    assert [w["workspace_id"] for w in one] == [made[1]]
    assert client.get("/api/v1/provision/workspaces", params={"idempotency_key": "nope"}, headers=h).json() == []
    page = client.get("/api/v1/provision/workspaces", params={"limit": 2, "offset": 1}, headers=h).json()
    assert [w["workspace_id"] for w in page] == made[1:3]
    assert client.get("/api/v1/provision/workspaces", params={"limit": 0}, headers=h).status_code == 422
    assert client.get("/api/v1/provision/workspaces", params={"limit": 201}, headers=h).status_code == 422


def test_listing_needs_a_provisioner_key_and_an_empty_key_lists_nothing(client, world):
    prov = _mint_provisioner(client, world)
    assert client.get("/api/v1/provision/workspaces", headers=_bearer(prov["key"])).json() == []
    for token in (world["account_key"], world["jwt"]):
        assert client.get("/api/v1/provision/workspaces", headers=_bearer(token)).status_code == 403


# ─── revoking the tokens a key minted ────────────────────────────────────────

def test_revoking_a_workspaces_tokens_disables_the_harness_and_is_repeatable(client, world, db_conn):
    prov = _mint_provisioner(client, world)
    out = _provision_idem(client, prov["key"], "p").json()
    ws, tok = out["workspace_id"], out["service_token"]["key"]
    assert _nodes(client, ws, tok).status_code == 200
    h = _bearer(prov["key"])
    assert client.delete(f"/api/v1/provision/workspaces/{ws}/token", headers=h).status_code == 204
    assert _add_node(client, ws, tok).status_code == 401
    assert client.delete(f"/api/v1/provision/workspaces/{ws}/token", headers=h).status_code == 204   # harmless again
    listed = client.get("/api/v1/provision/workspaces", headers=h).json()
    assert listed[0]["token"] is None
    # the workspace and its data are untouched, and a retry brings the harness back
    assert _workspaces_of(db_conn, prov["id"]) == 1
    back = _provision_idem(client, prov["key"], "p").json()
    assert _nodes(client, ws, back["service_token"]["key"]).status_code == 200


def test_revoking_leaves_tokens_the_key_did_not_mint_alone(client, world):
    prov = _mint_provisioner(client, world)
    out = _provision(client, prov["key"]).json()
    ws = out["workspace_id"]
    owners = client.post(f"/api/v1/workspaces/{ws}/api-keys", json={"name": "by-owner", "scopes": ["kb:read"]},
                         headers=_bearer(world["account_key"])).json()["key"]
    client.delete(f"/api/v1/provision/workspaces/{ws}/token", headers=_bearer(prov["key"]))
    assert _add_node(client, ws, out["service_token"]["key"]).status_code == 401
    assert _nodes(client, ws, owners).status_code == 200


def test_a_key_cannot_touch_workspaces_it_did_not_create(client, world):
    one, two = _mint_provisioner(client, world), _mint_provisioner(client, world)
    mine = _provision(client, one["key"]).json()
    theirs = _provision(client, two["key"]).json()
    made_by_owner = client.post("/api/v1/workspaces", json={"name": "owner-made", "language": "en"},
                                headers=_bearer(world["jwt"])).json()["id"]
    h = _bearer(one["key"])
    for ws in (theirs["workspace_id"], made_by_owner, "ws_does_not_exist"):
        assert client.delete(f"/api/v1/provision/workspaces/{ws}/token", headers=h).status_code == 404, ws
    assert _nodes(client, theirs["workspace_id"], theirs["service_token"]["key"]).status_code == 200
    assert _nodes(client, mine["workspace_id"], mine["service_token"]["key"]).status_code == 200


# ─── deleting a workspace the key created ────────────────────────────────────

def _delete(client, key, ws, **body):
    return client.request("DELETE", f"/api/v1/provision/workspaces/{ws}", headers=_bearer(key), json=body)


def test_deletion_is_off_unless_the_owner_enabled_it_for_the_key(client, world, db_conn):
    prov = _mint_provisioner(client, world)
    out = _provision(client, prov["key"]).json()
    client.delete(f"/api/v1/provision/workspaces/{out['workspace_id']}/token", headers=_bearer(prov["key"]))
    r = _delete(client, prov["key"], out["workspace_id"], confirm_name="harness kb")
    assert r.status_code == 403 and r.json()["detail"]["error"] == "deletion_not_allowed"
    assert _workspaces_of(db_conn, prov["id"]) == 1


def test_deletion_needs_the_tokens_revoked_first_and_the_current_name(client, world, db_conn):
    prov = _mint_provisioner(client, world, can_delete_workspaces=True)
    assert prov["can_delete_workspaces"] is True
    out = _provision(client, prov["key"], name="Delete Me").json()
    ws, h = out["workspace_id"], _bearer(prov["key"])
    assert client.request("DELETE", f"/api/v1/provision/workspaces/{ws}", headers=h).status_code == 422   # no body
    assert _delete(client, prov["key"], ws, confirm_name="wrong").status_code == 409
    r = _delete(client, prov["key"], ws, confirm_name="Delete Me")
    assert r.status_code == 409 and r.json()["detail"]["error"] == "tokens_still_active"
    assert _workspaces_of(db_conn, prov["id"]) == 1
    client.delete(f"/api/v1/provision/workspaces/{ws}/token", headers=h)
    assert _delete(client, prov["key"], ws, confirm_name="delete me").status_code == 409     # exact match only
    assert _delete(client, prov["key"], ws, confirm_name="Delete Me").status_code == 204
    assert _workspaces_of(db_conn, prov["id"]) == 0


def test_deletion_removes_the_workspace_its_data_and_every_token_and_frees_quota(client, world, db_conn):
    prov = _mint_provisioner(client, world, can_delete_workspaces=True, max_workspaces=2)
    keep = _provision(client, prov["key"], name="keep").json()
    gone = _provision(client, prov["key"], name="gone").json()
    ws, tok = gone["workspace_id"], gone["service_token"]["key"]
    assert _add_node(client, ws, tok).status_code == 201 and _add_node(client, ws, tok, "m").status_code == 201
    owners = client.post(f"/api/v1/workspaces/{ws}/api-keys", json={"name": "by-owner", "scopes": ["kb:read"]},
                         headers=_bearer(world["account_key"])).json()["key"]
    owner_made = client.post("/api/v1/workspaces", json={"name": "owner-made", "language": "en"},
                             headers=_bearer(world["jwt"])).json()["id"]
    h = _bearer(prov["key"])
    client.delete(f"/api/v1/provision/workspaces/{ws}/token", headers=h)
    assert _delete(client, prov["key"], ws, confirm_name="gone").status_code == 204

    assert _count(db_conn, "SELECT count(*) AS n FROM workspaces WHERE id = %s", ws) == 0
    assert _count(db_conn, "SELECT count(*) AS n FROM memory_nodes WHERE workspace_id = %s", ws) == 0
    assert _count(db_conn, "SELECT count(*) AS n FROM api_keys WHERE workspace_id = %s", ws) == 0   # incl. the owner-made token
    assert _nodes(client, ws, owners).status_code in (401, 403, 404)
    # untouched: the other provisioned workspace, its token, and the owner's own workspace
    assert _nodes(client, keep["workspace_id"], keep["service_token"]["key"]).status_code == 200
    assert _count(db_conn, "SELECT count(*) AS n FROM workspaces WHERE id = %s", owner_made) == 1
    q = client.get("/api/v1/provision/quota", headers=h).json()
    assert (q["workspaces_created"], q["remaining"]) == (1, 1)
    assert _provision(client, prov["key"]).status_code == 201


def test_deletion_only_reaches_workspaces_this_key_created(client, world, db_conn):
    one = _mint_provisioner(client, world, can_delete_workspaces=True)
    two = _mint_provisioner(client, world, can_delete_workspaces=True)
    theirs = _provision(client, two["key"], name="theirs").json()
    made_by_owner = client.post("/api/v1/workspaces", json={"name": "owner-made", "language": "en"},
                                headers=_bearer(world["jwt"])).json()["id"]
    client.delete(f"/api/v1/provision/workspaces/{theirs['workspace_id']}/token", headers=_bearer(two["key"]))
    for ws, name in ((theirs["workspace_id"], "theirs"), (made_by_owner, "owner-made"), ("ws_nope", "x")):
        assert _delete(client, one["key"], ws, confirm_name=name).status_code == 404, ws
    assert _count(db_conn, "SELECT count(*) AS n FROM workspaces WHERE id IN (%s, %s)", theirs["workspace_id"], made_by_owner) == 2


def test_the_confirmation_follows_a_rename(client, world):
    prov = _mint_provisioner(client, world, can_delete_workspaces=True)
    out = _provision(client, prov["key"], name="before").json()
    ws = out["workspace_id"]
    r = client.patch(f"/api/v1/workspaces/{ws}", json={"name": "after"}, headers=_bearer(world["jwt"]))
    assert r.status_code == 200, r.text[:200]
    client.delete(f"/api/v1/provision/workspaces/{ws}/token", headers=_bearer(prov["key"]))
    assert _delete(client, prov["key"], ws, confirm_name="before").status_code == 409
    assert _delete(client, prov["key"], ws, confirm_name="after").status_code == 204


def test_a_new_request_after_deletion_creates_a_fresh_workspace(client, world):
    prov = _mint_provisioner(client, world, can_delete_workspaces=True)
    a = _provision_idem(client, prov["key"], "proj", name="x").json()
    h = _bearer(prov["key"])
    client.delete(f"/api/v1/provision/workspaces/{a['workspace_id']}/token", headers=h)
    assert _delete(client, prov["key"], a["workspace_id"], confirm_name="x").status_code == 204
    b = _provision_idem(client, prov["key"], "proj", name="x")
    assert b.status_code == 201 and b.json()["workspace_id"] != a["workspace_id"]


def test_only_a_provisioner_key_can_use_the_provisioner_delete(client, world):
    prov = _mint_provisioner(client, world, can_delete_workspaces=True)
    out = _provision(client, prov["key"]).json()
    ws = out["workspace_id"]
    for who, token in (("account key", world["account_key"]), ("jwt", world["jwt"]),
                       ("minted token", out["service_token"]["key"])):
        r = _delete(client, token, ws, confirm_name="harness kb")
        assert r.status_code == 403, f"{who}: {r.status_code}"
        r = client.delete(f"/api/v1/provision/workspaces/{ws}/token", headers=_bearer(token))
        assert r.status_code == 403, f"{who} token revoke: {r.status_code}"
    assert _nodes(client, ws, out["service_token"]["key"]).status_code == 200


def test_a_provisioner_key_cannot_use_the_ordinary_workspace_delete(client, world):
    prov = _mint_provisioner(client, world, can_delete_workspaces=True)
    ws = _provision(client, prov["key"]).json()["workspace_id"]
    assert client.delete(f"/api/v1/workspaces/{ws}", headers=_bearer(prov["key"])).status_code == 403


def test_a_revoked_key_can_no_longer_delete(client, world):
    prov = _mint_provisioner(client, world, can_delete_workspaces=True)
    ws = _provision(client, prov["key"]).json()["workspace_id"]
    client.delete(f"/api/v1/provision/workspaces/{ws}/token", headers=_bearer(prov["key"]))
    client.delete(f"/api/v1/users/me/provisioner-keys/{prov['id']}", headers=_bearer(world["jwt"]))
    assert _delete(client, prov["key"], ws, confirm_name="harness kb").status_code == 401


def test_the_key_listing_shows_whether_deletion_is_enabled(client, world):
    plain = _mint_provisioner(client, world)
    deleter = _mint_provisioner(client, world, can_delete_workspaces=True)
    flags = {k["id"]: k["can_delete_workspaces"] for k in
             client.get("/api/v1/users/me/provisioner-keys", headers=_bearer(world["jwt"])).json()}
    assert flags == {plain["id"]: False, deleter["id"]: True}


# ─── routing and the database ────────────────────────────────────────────────

@pytest.mark.parametrize("method,path,allowed", [
    ("POST", "/api/v1/provision/workspaces", True),
    ("GET", "/api/v1/provision/workspaces", True),
    ("GET", "/api/v1/provision/quota", True),
    ("DELETE", "/api/v1/provision/workspaces/ws_abc", True),
    ("DELETE", "/api/v1/provision/workspaces/ws_abc/token", True),
    ("PUT", "/api/v1/provision/workspaces", False),
    ("POST", "/api/v1/provision/quota", False),
    ("GET", "/api/v1/provision/workspaces/ws_abc", False),
    ("POST", "/api/v1/provision/workspaces/ws_abc/token", False),
    ("DELETE", "/api/v1/provision/workspaces/ws_abc/token/x", False),
    ("DELETE", "/api/v1/provision/workspaces/", False),
    ("DELETE", "/api/v1/provision", False),
    ("GET", "/api/v1/provision/quota/", False),
    ("GET", "/api/v1/workspaces", False),
    ("POST", "/mcp", False),
    ("GET", "/api/v1/users/me/provisioner-keys", False),
])
def test_the_provisioner_route_table(method, path, allowed):
    from core.deps import _provisioner_route_allowed
    assert _provisioner_route_allowed(method, path) is allowed


def test_the_unique_index_stops_a_duplicate_idempotency_key_but_allows_many_nulls(client, world, db_conn):
    import psycopg2
    prov = _mint_provisioner(client, world)
    ids = [_provision_idem(client, prov["key"], "dup").json()["workspace_id"]]
    other = _provision(client, prov["key"]).json()["workspace_id"]       # a second workspace with a NULL request id
    third = _provision(client, prov["key"]).json()["workspace_id"]       # and a third: NULLs never collide
    cur = db_conn.cursor()
    with pytest.raises(psycopg2.errors.UniqueViolation):
        cur.execute("UPDATE workspaces SET provision_request_id = 'dup' WHERE id = %s", (other,))
    assert ids and third


def test_can_delete_workspaces_defaults_to_false_for_every_key_type(db_conn, world):
    cur = db_conn.cursor()
    cur.execute("SELECT count(*) AS n FROM api_keys WHERE can_delete_workspaces AND key_type <> 'provisioner'")
    assert cur.fetchone()["n"] == 0
    cur.execute("SELECT is_nullable, column_default FROM information_schema.columns "
                "WHERE table_name = 'api_keys' AND column_name = 'can_delete_workspaces'")
    col = cur.fetchone()
    assert col["is_nullable"] == "NO" and "false" in col["column_default"]

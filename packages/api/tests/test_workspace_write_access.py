"""require_ws_access write semantics across visibility x role (ws_spec_plan/mem_85a249ea).

Before the fix a viewer passed write=True on a *private* workspace, because the
editor check only existed in a branch private workspaces never reach.
"""
import os
import sys
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.workspaces import require_ws_access

OWNER = "usr_owner"


def _call(visibility, role, *, write=False, required_role=None):
    """role: None (non-member), 'owner', 'viewer' or 'editor'; role='anon' means user=None."""
    cur = MagicMock()
    ws = {"id": "ws_1", "visibility": visibility, "owner_id": OWNER}
    if role == "anon":
        user = None
        cur.fetchone.side_effect = [ws]
    elif role == "owner":
        user = {"sub": OWNER}
        cur.fetchone.side_effect = [ws]
    else:
        user = {"sub": "usr_other"}
        cur.fetchone.side_effect = [ws, ({"role": role} if role else None)]
    return require_ws_access(cur, "ws_1", user, write=write, required_role=required_role)


def _status(visibility, role, **kw):
    try:
        _call(visibility, role, **kw)
    except HTTPException as exc:
        return exc.status_code
    return 200


# ─── the fix: private + write ────────────────────────────────────────────────

@pytest.mark.parametrize("role,expected", [
    ("owner", 200),
    ("editor", 200),
    ("viewer", 403),
    (None, 403),
    ("anon", 403),
])
def test_private_workspace_write(role, expected):
    assert _status("private", role, write=True) == expected


def test_private_viewer_write_refusal_names_the_role_requirement():
    with pytest.raises(HTTPException) as exc:
        _call("private", "viewer", write=True)
    assert exc.value.detail == "Editor or Admin role required"


@pytest.mark.parametrize("role", ["owner", "editor", "viewer"])
def test_private_workspace_read_is_unchanged(role):
    assert _status("private", role, write=False) == 200


@pytest.mark.parametrize("role", [None, "anon"])
def test_private_workspace_read_still_requires_membership(role):
    assert _status("private", role, write=False) == 403


# ─── behaviour that must not move ────────────────────────────────────────────

@pytest.mark.parametrize("visibility", ["restricted", "public", "conditional_public"])
@pytest.mark.parametrize("role,expected", [
    ("owner", 200),
    ("editor", 200),
    ("viewer", 403),
    (None, 403),
])
def test_other_visibilities_write_unchanged(visibility, role, expected):
    assert _status(visibility, role, write=True) == expected


def test_public_workspace_read_still_open_to_anyone():
    assert _status("public", "anon", write=False) == 200
    assert _status("public", None, write=False) == 200


def test_restricted_workspace_read_still_needs_membership():
    assert _status("restricted", "viewer", write=False) == 200
    assert _status("restricted", None, write=False) == 403


@pytest.mark.parametrize("visibility", ["private", "restricted"])
def test_required_role_path_is_unchanged(visibility):
    # required_role='editor' still lets an editor in and keeps a viewer out ...
    assert _status(visibility, "editor", write=True, required_role="editor") == 200
    assert _status(visibility, "viewer", write=True, required_role="editor") == 403
    # ... and 'admin' still excludes an editor; the owner counts as admin.
    assert _status(visibility, "editor", write=True, required_role="admin") == 403
    assert _status(visibility, "owner", write=True, required_role="admin") == 200


def test_required_role_denial_keeps_its_structured_detail():
    with pytest.raises(HTTPException) as exc:
        _call("private", "viewer", write=True, required_role="editor")
    assert exc.value.detail == {"error": "insufficient_role", "required": "editor", "actual": "viewer"}

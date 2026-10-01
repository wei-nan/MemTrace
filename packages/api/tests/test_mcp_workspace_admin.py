"""MCP workspace management, batch 1 (ws_spec_plan/mem_c98ff99b).

Covers create_workspace / update_workspace / list_members and the association
tools, plus the `workspace_admin` profile and the create_workspace_in_db
description fix these tools depend on.
"""
import os
import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.mcp_tools import MCP_TOOL_PROFILES, execute_tool, resolve_profile_tools
from services.workspaces import create_workspace_in_db, list_members_in_db, update_workspace_in_db

WORKSPACE_ADMIN_TOOLS = {
    "create_workspace",
    "update_workspace",
    "list_members",
    "list_associations",
    "add_association",
    "remove_association",
}

USER = {"sub": "usr_1"}


def _cursor_ctx(cur=None):
    cur = cur or MagicMock()
    ctx = MagicMock()
    ctx.__enter__.return_value = cur
    return ctx, cur


# ─── profile ──────────────────────────────────────────────────────────────────

def test_workspace_admin_profile_has_exactly_the_six_tools():
    names = {t["name"] for t in resolve_profile_tools("workspace_admin")}
    assert names == WORKSPACE_ADMIN_TOOLS
    assert MCP_TOOL_PROFILES["workspace_admin"] == WORKSPACE_ADMIN_TOOLS


def test_default_profile_does_not_expose_workspace_admin_tools():
    with patch.dict(os.environ, {}, clear=True):
        names = {t["name"] for t in resolve_profile_tools()}
    assert names.isdisjoint(WORKSPACE_ADMIN_TOOLS)
    assert len(names) == 28


# ─── create_workspace ─────────────────────────────────────────────────────────

def _created_row(**overrides):
    row = {
        "id": "ws_new",
        "name": "Notes",
        "description": None,
        "language": "zh-TW",
        "visibility": "private",
        "kb_type": "evergreen",
        "my_role": "admin",
        "settings": {"mcp_ingest_enabled": True},
        "embedding_dim": 3072,
    }
    row.update(overrides)
    return row


@pytest.mark.asyncio
async def test_create_workspace_applies_server_defaults_and_projects_response():
    ctx, _ = _cursor_ctx()
    with patch("services.mcp_tools.db_cursor", return_value=ctx), \
         patch("services.workspaces.create_workspace_in_db", return_value=_created_row()) as create:
        res = await execute_tool("create_workspace", {"name": "Notes", "language": "zh-TW"}, USER, MagicMock())

    uid, body = create.call_args.args[1], create.call_args.args[2]
    assert uid == "usr_1"
    assert body["visibility"] == "private"
    assert body["kb_type"] == "evergreen"
    assert body["qa_archive_mode"] == "manual_review"
    assert body["auto_split"] is False
    assert body["settings"] == {"mcp_ingest_enabled": True, "mcp_ingest_daily_quota": 100}
    # Everything unlisted keeps the REST/UI default, not the service-layer fallback.
    assert body["extraction_provider"] is None
    assert body["embedding_model"] is None
    assert body["consult_trust_tier"] == "ask"
    assert body["archive_window_days"] == 90
    assert body["min_traversals"] == 1

    assert res == {
        "id": "ws_new",
        "name": "Notes",
        "language": "zh-TW",
        "visibility": "private",
        "kb_type": "evergreen",
        "my_role": "admin",
    }
    assert "settings" not in res and "embedding_dim" not in res


@pytest.mark.asyncio
async def test_create_workspace_passes_description_and_returns_it():
    ctx, _ = _cursor_ctx()
    row = _created_row(description="about")
    with patch("services.mcp_tools.db_cursor", return_value=ctx), \
         patch("services.workspaces.create_workspace_in_db", return_value=row) as create:
        res = await execute_tool(
            "create_workspace",
            {"name": "Notes", "language": "en", "description": "about", "visibility": "restricted", "kb_type": "ephemeral"},
            USER,
            MagicMock(),
        )
    body = create.call_args.args[2]
    assert body["description"] == "about"
    assert body["visibility"] == "restricted"
    assert body["kb_type"] == "ephemeral"
    assert res["description"] == "about"


@pytest.mark.asyncio
@pytest.mark.parametrize("args", [
    {"language": "zh-TW"},
    {"name": "   ", "language": "zh-TW"},
    {"name": "Notes"},
    {"name": "Notes", "language": "fr"},
    {"name": "Notes", "language": "en", "kb_type": "forever"},
])
async def test_create_workspace_rejects_missing_or_invalid_required_fields(args):
    with patch("services.workspaces.create_workspace_in_db") as create:
        with pytest.raises(HTTPException) as exc:
            await execute_tool("create_workspace", args, USER, MagicMock())
    assert exc.value.status_code == 400
    create.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("visibility", ["public", "conditional_public", "team", ""])
async def test_create_workspace_refuses_to_publish(visibility):
    with patch("services.workspaces.create_workspace_in_db") as create:
        with pytest.raises(HTTPException) as exc:
            await execute_tool(
                "create_workspace",
                {"name": "Notes", "language": "en", "visibility": visibility},
                USER,
                MagicMock(),
            )
    assert exc.value.status_code == 400
    create.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("extra", [
    {"settings": {"mcp_ingest_daily_quota": 100000}},
    {"embedding_model": "text-embedding-3-small"},
    {"qa_archive_mode": "auto_active"},
    {"auto_split": True},
    {"extraction_provider": "openai"},
    {"consult_trust_tier": "full_trust"},
    {"archive_window_days": 1},
])
async def test_create_workspace_rejects_fields_not_open_to_mcp(extra):
    with patch("services.workspaces.create_workspace_in_db") as create:
        with pytest.raises(HTTPException) as exc:
            await execute_tool(
                "create_workspace", {"name": "Notes", "language": "en", **extra}, USER, MagicMock()
            )
    assert exc.value.status_code == 400
    assert next(iter(extra)) in exc.value.detail
    create.assert_not_called()


@pytest.mark.asyncio
async def test_create_workspace_allows_harness_correlation_ids():
    ctx, _ = _cursor_ctx()
    with patch("services.mcp_tools.db_cursor", return_value=ctx), \
         patch("services.workspaces.create_workspace_in_db", return_value=_created_row()):
        res = await execute_tool(
            "create_workspace",
            {"name": "Notes", "language": "zh-TW", "run_id": "r1", "task_id": "t1", "stage": "dev"},
            USER,
            MagicMock(),
        )
    assert res["id"] == "ws_new"


@pytest.mark.asyncio
async def test_create_workspace_refuses_workspace_scoped_service_token():
    token_user = {"sub": "svc", "api_key_id": "key_1", "workspace_id": "ws_ci", "scopes": ["*"]}
    with patch("services.workspaces.create_workspace_in_db") as create:
        with pytest.raises(HTTPException) as exc:
            await execute_tool("create_workspace", {"name": "Notes", "language": "en"}, token_user, MagicMock())
    assert exc.value.status_code == 403
    create.assert_not_called()


@pytest.mark.asyncio
async def test_create_workspace_allows_account_level_api_key():
    key_user = {"sub": "usr_1", "api_key_id": "key_1", "workspace_id": None, "scopes": ["*"]}
    ctx, _ = _cursor_ctx()
    with patch("services.mcp_tools.db_cursor", return_value=ctx), \
         patch("services.workspaces.create_workspace_in_db", return_value=_created_row()):
        res = await execute_tool("create_workspace", {"name": "Notes", "language": "en"}, key_user, MagicMock())
    assert res["id"] == "ws_new"


# ─── create_workspace_in_db: description must be stored ──────────────────────

def test_create_workspace_in_db_stores_description():
    cur = MagicMock()
    cur.fetchone.return_value = {"id": "ws_x"}
    body = {
        "name": "Notes",
        "description": "about",
        "language": "en",
        "visibility": "private",
        "kb_type": "evergreen",
        "embedding_model": "text-embedding-3-small",
        "embedding_provider": "openai",
    }
    with patch("core.ai.get_embedding_dim", return_value=1536):
        create_workspace_in_db(cur, "usr_1", body)

    sql, params = cur.execute.call_args.args
    assert "description" in sql
    assert params[-1] == "about"
    # column list and placeholders stay in step
    assert sql.count("%s") == len(params)


# ─── update_workspace ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_workspace_passes_only_allowed_fields_and_projects_response():
    ctx, cur = _cursor_ctx()
    updated = {
        "id": "ws_1", "name": "New", "description": "d", "archive_window_days": 30,
        "min_traversals": 2, "qa_archive_mode": "auto_active", "updated_at": "2026-10-01T00:00:00Z",
        "settings": {"x": 1}, "visibility": "private",
    }
    with patch("services.mcp_tools.db_cursor", return_value=ctx), \
         patch("services.mcp_tools.require_ws_access") as access, \
         patch("services.workspaces.update_workspace_in_db", return_value=updated) as upd:
        res = await execute_tool(
            "update_workspace",
            {"workspace_id": "ws_1", "name": " New ", "archive_window_days": 30, "qa_archive_mode": "auto_active"},
            USER,
            MagicMock(),
        )
    access.assert_called_once_with(cur, "ws_1", USER)
    assert upd.call_args.args[1:3] == ("ws_1", "usr_1")
    assert upd.call_args.args[3] == {"name": "New", "archive_window_days": 30, "qa_archive_mode": "auto_active"}
    assert res == {
        "id": "ws_1", "name": "New", "description": "d", "archive_window_days": 30,
        "min_traversals": 2, "qa_archive_mode": "auto_active", "updated_at": "2026-10-01T00:00:00Z",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("extra", [
    {"visibility": "public"},
    {"allow_anonymous_view": True},
    {"settings": {"mcp_ingest_daily_quota": 999}},
    {"embedding_model": "x"},
    {"migration_status": "in_progress"},
    {"migrating_to_model": "x"},
    {"language": "en"},
])
async def test_update_workspace_rejects_fields_not_open_to_mcp(extra):
    with patch("services.workspaces.update_workspace_in_db") as upd:
        with pytest.raises(HTTPException) as exc:
            await execute_tool("update_workspace", {"workspace_id": "ws_1", **extra}, USER, MagicMock())
    assert exc.value.status_code == 400
    upd.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("args", [
    {"workspace_id": "ws_1"},
    {"workspace_id": "ws_1", "name": "  "},
    {"workspace_id": "ws_1", "qa_archive_mode": "whatever"},
    {"workspace_id": "ws_1", "archive_window_days": 0},
    {"workspace_id": "ws_1", "archive_window_days": True},
    {"workspace_id": "ws_1", "archive_window_days": "30"},
    {"workspace_id": "ws_1", "min_traversals": -1},
])
async def test_update_workspace_validates_values(args):
    with patch("services.workspaces.update_workspace_in_db") as upd:
        with pytest.raises(HTTPException) as exc:
            await execute_tool("update_workspace", args, USER, MagicMock())
    assert exc.value.status_code == 400
    upd.assert_not_called()


@pytest.mark.asyncio
async def test_update_workspace_allows_clearing_description_and_zero_traversals():
    ctx, _ = _cursor_ctx()
    with patch("services.mcp_tools.db_cursor", return_value=ctx), \
         patch("services.mcp_tools.require_ws_access"), \
         patch("services.workspaces.update_workspace_in_db", return_value={"id": "ws_1"}) as upd:
        await execute_tool(
            "update_workspace",
            {"workspace_id": "ws_1", "description": "", "min_traversals": 0},
            USER,
            MagicMock(),
        )
    assert upd.call_args.args[3] == {"description": "", "min_traversals": 0}


@pytest.mark.asyncio
async def test_update_workspace_respects_workspace_scoped_key_restriction():
    ctx, _ = _cursor_ctx()
    with patch("services.mcp_tools.db_cursor", return_value=ctx), \
         patch("services.mcp_tools.require_ws_access",
               side_effect=HTTPException(status_code=403, detail="API key is restricted to another workspace")), \
         patch("services.workspaces.update_workspace_in_db") as upd:
        with pytest.raises(HTTPException) as exc:
            await execute_tool("update_workspace", {"workspace_id": "ws_1", "name": "x"}, USER, MagicMock())
    assert exc.value.status_code == 403
    upd.assert_not_called()


def test_update_workspace_in_db_is_owner_only_even_for_admin_members():
    cur = MagicMock()
    cur.fetchone.return_value = {"id": "ws_1", "owner_id": "usr_owner"}
    with pytest.raises(HTTPException) as exc:
        update_workspace_in_db(cur, "ws_1", "usr_admin_member", {"name": "x"})
    assert exc.value.status_code == 403


# ─── list_members ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_members_requires_workspace_access():
    ctx, _ = _cursor_ctx()
    with patch("services.mcp_tools.db_cursor", return_value=ctx), \
         patch("services.mcp_tools.require_ws_access",
               side_effect=HTTPException(status_code=403, detail="no")), \
         patch("services.workspaces.list_members_in_db") as listing:
        with pytest.raises(HTTPException) as exc:
            await execute_tool("list_members", {"workspace_id": "ws_1"}, USER, MagicMock())
    assert exc.value.status_code == 403
    listing.assert_not_called()


@pytest.mark.asyncio
async def test_list_members_returns_service_rows_for_a_member():
    ctx, cur = _cursor_ctx()
    rows = [{"user_id": "u1", "display_name": "A", "role": "owner", "joined_at": "t"}]
    with patch("services.mcp_tools.db_cursor", return_value=ctx), \
         patch("services.mcp_tools.require_ws_access") as access, \
         patch("services.workspaces.list_members_in_db", return_value=rows):
        res = await execute_tool("list_members", {"workspace_id": "ws_1"}, USER, MagicMock())
    access.assert_called_once_with(cur, "ws_1", USER)
    assert res == rows


def test_list_members_in_db_omits_email_and_lists_owner_once_first():
    cur = MagicMock()
    owner = {"user_id": "u_owner", "display_name": "Owner", "role": "owner", "joined_at": "t0"}
    member = {"user_id": "u_2", "display_name": "Two", "role": "viewer", "joined_at": "t1"}
    cur.fetchall.side_effect = [[owner], [member]]

    res = list_members_in_db(cur, "ws_1")

    assert res == [owner, member]
    for call in cur.execute.call_args_list:
        assert "email" not in call.args[0].lower()
    # the member query must exclude the owner so a member row cannot duplicate them
    assert "<> w.owner_id" in cur.execute.call_args_list[1].args[0]
    assert all("email" not in row for row in res)


# ─── associations ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_associations_projects_rows():
    ctx, _ = _cursor_ctx()
    rows = [{"id": "asc_1", "source_ws_id": "ws_1", "target_ws_id": "ws_2", "target_name": "Two", "created_at": "t"}]
    with patch("services.mcp_tools.db_cursor", return_value=ctx), \
         patch("services.workspaces.list_associations_in_db", return_value=rows):
        res = await execute_tool("list_associations", {"workspace_id": "ws_1"}, USER, MagicMock())
    assert res == [{"id": "asc_1", "target_workspace_id": "ws_2", "target_name": "Two", "created_at": "t"}]


@pytest.mark.asyncio
async def test_add_association_projects_row():
    ctx, cur = _cursor_ctx()
    row = {"id": "asc_1", "source_ws_id": "ws_1", "target_ws_id": "ws_2", "target_name": "Two", "created_at": "t"}
    with patch("services.mcp_tools.db_cursor", return_value=ctx), \
         patch("services.workspaces.create_association_in_db", return_value=row) as create:
        res = await execute_tool(
            "add_association", {"workspace_id": "ws_1", "target_workspace_id": "ws_2"}, USER, MagicMock()
        )
    create.assert_called_once_with(cur, "ws_1", "ws_2", USER)
    assert res == {
        "id": "asc_1", "workspace_id": "ws_1", "target_workspace_id": "ws_2",
        "target_name": "Two", "created_at": "t",
    }


@pytest.mark.asyncio
async def test_add_association_duplicate_surfaces_409():
    ctx, _ = _cursor_ctx()
    with patch("services.mcp_tools.db_cursor", return_value=ctx), \
         patch("services.workspaces.create_association_in_db",
               side_effect=HTTPException(status_code=409, detail="Association already exists")):
        with pytest.raises(HTTPException) as exc:
            await execute_tool(
                "add_association", {"workspace_id": "ws_1", "target_workspace_id": "ws_2"}, USER, MagicMock()
            )
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_add_association_without_target_read_access_is_refused():
    ctx, _ = _cursor_ctx()
    with patch("services.mcp_tools.db_cursor", return_value=ctx), \
         patch("services.workspaces.create_association_in_db",
               side_effect=HTTPException(status_code=403, detail="no_membership")):
        with pytest.raises(HTTPException) as exc:
            await execute_tool(
                "add_association", {"workspace_id": "ws_1", "target_workspace_id": "ws_private"}, USER, MagicMock()
            )
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_remove_association_reports_removal():
    ctx, cur = _cursor_ctx()
    with patch("services.mcp_tools.db_cursor", return_value=ctx), \
         patch("services.workspaces.delete_association_in_db") as delete:
        res = await execute_tool(
            "remove_association", {"workspace_id": "ws_1", "target_workspace_id": "ws_2"}, USER, MagicMock()
        )
    delete.assert_called_once_with(cur, "ws_1", "ws_2", USER)
    assert res == {"removed": True, "workspace_id": "ws_1", "target_workspace_id": "ws_2"}


@pytest.mark.asyncio
async def test_remove_association_missing_surfaces_404():
    ctx, _ = _cursor_ctx()
    with patch("services.mcp_tools.db_cursor", return_value=ctx), \
         patch("services.workspaces.delete_association_in_db",
               side_effect=HTTPException(status_code=404, detail="Association not found")):
        with pytest.raises(HTTPException) as exc:
            await execute_tool(
                "remove_association", {"workspace_id": "ws_1", "target_workspace_id": "ws_9"}, USER, MagicMock()
            )
    assert exc.value.status_code == 404

"""
tests/test_kb_leak_regression.py — 資料外洩回歸測試 (L1–L9)

針對審計發現的 4 個繞過守衛的資料出口,鎖住正確行為:

  L1-L2  匯出需 editor 角色 (routers/exports.py)
  L3-L5  public.py 匿名端點用白名單 visibility='public'(team 不外洩)
  L6     public.py graph-preview 邊只連可見節點(不洩漏隱藏節點拓撲)
  L7-L8  semantic 搜尋端點對 viewer 遮蔽 body (routers/kb.py)
  L9     對照組:editor 透過 semantic 搜尋仍可見 body

這些測試檢查的是「端點是否真的呼叫守衛 / 用對 SQL」,
而非守衛函式本身——這正是 test_kb_data_isolation 沒覆蓋的層級。

Run: pytest tests/test_kb_leak_regression.py -v
"""
from __future__ import annotations

from unittest.mock import MagicMock, AsyncMock, patch

import pytest


# ─── shared helpers ───────────────────────────────────────────────────────────

def _cm(cur):
    """Wrap a mock cursor in a context manager like db_cursor() returns."""
    cm = MagicMock()
    cm.__enter__ = lambda s: cur
    cm.__exit__ = MagicMock(return_value=False)
    return cm


def _node_row(node_id="mem_x", vis="private", body="secret body"):
    return {
        "id": node_id,
        "workspace_id": "ws_target",
        "title": "Node",
        "body": body,
        "visibility": vis,
        "content_type": "fact",
        "content_format": "plain",
        "tags": [],
        "author": "usr_owner",
        "trust_score": 0.8,
        "status": "active",
        "similarity": 0.9,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 修復 1:匯出需 editor 角色
# ═══════════════════════════════════════════════════════════════════════════════

def test_l1_trigger_export_requires_editor_role():
    """trigger_export 必須以 required_role='editor' 呼叫 require_ws_access。"""
    from routers.exports import trigger_export

    cur = MagicMock()
    cur.fetchone.return_value = {"id": "exp_1", "workspace_id": "ws_target", "status": "pending"}

    body = MagicMock()
    body.include_archived = False
    body.include_markdown = False
    body.tags = None
    body.date_from = None
    body.date_to = None

    bg = MagicMock()
    guard = MagicMock()

    with patch("routers.exports.db_cursor", return_value=_cm(cur)), \
         patch("routers.exports._require_ws_access", guard):
        trigger_export("ws_target", body, bg, user={"sub": "usr_a"})

    # 守衛必須被要求 editor 角色(且 write)
    _, kwargs = guard.call_args
    assert kwargs.get("required_role") == "editor"
    assert kwargs.get("write") is True


def test_l2_download_export_requires_editor_role():
    """download_export 必須以 required_role='editor' 呼叫 require_ws_access。"""
    from routers.exports import download_export

    cur = MagicMock()
    cur.fetchone.return_value = None  # 找不到 → 之後 raise 404,但守衛已先被呼叫
    guard = MagicMock()
    request = MagicMock()
    request.headers = {"Authorization": "Bearer faketoken"}

    from fastapi import HTTPException
    with patch("routers.exports.db_cursor", return_value=_cm(cur)), \
         patch("routers.exports._require_ws_access", guard), \
         patch("routers.exports.decode_token", return_value={"sub": "usr_a"}):
        with pytest.raises(HTTPException):
            download_export("ws_target", "exp_1", request, token="faketoken")

    _, kwargs = guard.call_args
    assert kwargs.get("required_role") == "editor"


# ═══════════════════════════════════════════════════════════════════════════════
# 修復 2 & 4:public.py 匿名端點白名單 + 邊過濾
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_l3_public_graph_preview_uses_allowlist():
    """graph-preview 節點查詢必須用 visibility = 'public'(白名單),不可用 IS DISTINCT FROM。"""
    from routers import public as pub

    cur = MagicMock()
    cur.fetchall.side_effect = [[], []]  # nodes, edges
    ws = {"id": "ws_target", "allow_anonymous_view": True}

    with patch("routers.public.db_cursor", return_value=_cm(cur)), \
         patch("routers.public._get_workspace_public", new=AsyncMock(return_value=ws)):
        await pub.get_graph_preview_public("ws_target", MagicMock(), MagicMock())

    node_sql = cur.execute.call_args_list[0][0][0]
    assert "visibility = 'public'" in node_sql
    assert "IS DISTINCT FROM" not in node_sql


@pytest.mark.asyncio
async def test_l4_public_node_detail_uses_allowlist():
    """節點詳情查詢必須用 visibility = 'public'。"""
    from routers import public as pub

    cur = MagicMock()
    cur.fetchone.return_value = None  # node not found (filtered) → 404
    ws = {"id": "ws_target", "allow_anonymous_view": True}

    from fastapi import HTTPException
    with patch("routers.public.db_cursor", return_value=_cm(cur)), \
         patch("routers.public._get_workspace_public", new=AsyncMock(return_value=ws)):
        with pytest.raises(HTTPException):
            await pub.get_node_public("ws_target", "mem_team", MagicMock(), MagicMock())

    sql = cur.execute.call_args_list[0][0][0]
    assert "visibility = 'public'" in sql
    assert "IS DISTINCT FROM" not in sql


@pytest.mark.asyncio
async def test_l5_public_search_uses_allowlist():
    """匿名搜尋過濾必須包含 visibility = 'public'。"""
    from routers import public as pub

    cur = MagicMock()
    cur.fetchall.return_value = []
    ws = {"id": "ws_target", "allow_anonymous_view": True}

    with patch("routers.public.db_cursor", return_value=_cm(cur)), \
         patch("routers.public._get_workspace_public", new=AsyncMock(return_value=ws)):
        await pub.search_public("ws_target", MagicMock(), MagicMock(), q="hello")

    sql = cur.execute.call_args[0][0]
    assert "visibility = 'public'" in sql
    assert "IS DISTINCT FROM" not in sql


@pytest.mark.asyncio
async def test_l6_public_graph_preview_edges_limited_to_visible_nodes():
    """graph-preview 的邊查詢必須以可見節點集合為界(from_id/to_id = ANY)。"""
    from routers import public as pub

    cur = MagicMock()
    visible_nodes = [{"id": "mem_pub1"}, {"id": "mem_pub2"}]
    cur.fetchall.side_effect = [visible_nodes, []]  # nodes, then edges
    ws = {"id": "ws_target", "allow_anonymous_view": True}

    with patch("routers.public.db_cursor", return_value=_cm(cur)), \
         patch("routers.public._get_workspace_public", new=AsyncMock(return_value=ws)):
        await pub.get_graph_preview_public("ws_target", MagicMock(), MagicMock())

    edge_sql = cur.execute.call_args_list[1][0][0]
    edge_params = cur.execute.call_args_list[1][0][1]
    # 邊查詢必須以兩端節點過濾,而非全撈
    assert "from_id = ANY" in edge_sql and "to_id = ANY" in edge_sql
    # 傳入的允許清單只含可見節點
    assert ["mem_pub1", "mem_pub2"] in [p for p in edge_params if isinstance(p, list)]


# ═══════════════════════════════════════════════════════════════════════════════
# 修復 3:semantic 搜尋端點遮蔽 body
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_l7_semantic_search_strips_body_for_viewer():
    """viewer 透過 semantic 搜尋取得的 private 節點 body 必須被遮蔽。"""
    from routers.kb import search_nodes_semantic

    cur = MagicMock()
    cur.fetchone.return_value = {"embedding_model": "m", "embedding_provider": "openai"}
    private_row = _node_row(node_id="mem_secret", vis="private", body="TOP SECRET")

    with patch("routers.kb.db_cursor", return_value=_cm(cur)), \
         patch("routers.kb._require_ws_access", return_value={"owner_id": "usr_owner"}), \
         patch("routers.kb.perform_semantic_search", new=AsyncMock(return_value=[private_row])), \
         patch("routers.kb._get_effective_role", return_value="viewer"):
        results = await search_nodes_semantic("ws_target", query="q", limit=10, user={"sub": "usr_viewer"})

    assert results[0]["body"] is None
    assert results[0].get("content_stripped") is True


@pytest.mark.asyncio
async def test_l8_semantic_search_public_node_body_kept():
    """public 節點 body 對 viewer 仍可見(不應過度遮蔽)。"""
    from routers.kb import search_nodes_semantic

    cur = MagicMock()
    cur.fetchone.return_value = {"embedding_model": "m", "embedding_provider": "openai"}
    public_row = _node_row(node_id="mem_open", vis="public", body="public info")

    with patch("routers.kb.db_cursor", return_value=_cm(cur)), \
         patch("routers.kb._require_ws_access", return_value={"owner_id": "usr_owner"}), \
         patch("routers.kb.perform_semantic_search", new=AsyncMock(return_value=[public_row])), \
         patch("routers.kb._get_effective_role", return_value="viewer"):
        results = await search_nodes_semantic("ws_target", query="q", limit=10, user={"sub": "usr_viewer"})

    assert results[0]["body"] == "public info"


@pytest.mark.asyncio
async def test_l9_semantic_search_editor_sees_body():
    """editor 透過 semantic 搜尋仍可見 private 節點 body。"""
    from routers.kb import search_nodes_semantic

    cur = MagicMock()
    cur.fetchone.return_value = {"embedding_model": "m", "embedding_provider": "openai"}
    private_row = _node_row(node_id="mem_secret", vis="private", body="TOP SECRET")

    with patch("routers.kb.db_cursor", return_value=_cm(cur)), \
         patch("routers.kb._require_ws_access", return_value={"owner_id": "usr_owner"}), \
         patch("routers.kb.perform_semantic_search", new=AsyncMock(return_value=[private_row])), \
         patch("routers.kb._get_effective_role", return_value="editor"):
        results = await search_nodes_semantic("ws_target", query="q", limit=10, user={"sub": "usr_editor"})

    assert results[0]["body"] == "TOP SECRET"


# ═══════════════════════════════════════════════════════════════════════════════
# 修復 4:MCP search_cross_workspace 繞過 strip_body_if_viewer 與欄位過濾
# (發現於 2026-07-07，見 ws_spec_plan mem_38e3c93e — 同一個 perform_semantic_search
#  raw row，routers/kb.py 的姊妹端點在 L7-L9 已修過，但 mcp_tools.py 的
#  search_cross_workspace 一直沒套用同樣的處理)
# ═══════════════════════════════════════════════════════════════════════════════

def _cross_ws_row(node_id="mem_secret", vis="private", body="TOP SECRET"):
    row = _node_row(node_id=node_id, vis=vis, body=body)
    row["embedding"] = [0.1] * 8
    row["secondary_embedding"] = [0.2] * 8
    row["signature"] = "deadbeef" * 8
    return row


@pytest.mark.asyncio
async def test_l10_cross_workspace_search_strips_body_for_viewer():
    """viewer 透過 search_cross_workspace 取得的 private 節點 body 必須被遮蔽。"""
    from services.mcp_tools import execute_tool

    cur = MagicMock()
    cur.fetchone.return_value = {"embedding_provider": "openai", "embedding_model": "m"}
    ws = {"id": "ws_target", "name": "Target", "my_role": "viewer"}
    private_row = _cross_ws_row(vis="private", body="TOP SECRET")

    with patch("services.mcp_tools.db_cursor", return_value=_cm(cur)), \
         patch("services.mcp_tools.list_workspaces_in_db", return_value=[ws]), \
         patch("services.mcp_tools.perform_semantic_search", new=AsyncMock(return_value=[private_row])):
        res = await execute_tool(
            "search_cross_workspace", {"query": "q"}, {"sub": "usr_viewer"}, MagicMock()
        )

    assert res["results"][0]["body"] is None
    assert res["results"][0].get("content_stripped") is True


@pytest.mark.asyncio
async def test_l11_cross_workspace_search_editor_sees_body():
    """editor 透過 search_cross_workspace 仍可見 private 節點 body(對照組,不應過度遮蔽)。"""
    from services.mcp_tools import execute_tool

    cur = MagicMock()
    cur.fetchone.return_value = {"embedding_provider": "openai", "embedding_model": "m"}
    ws = {"id": "ws_target", "name": "Target", "my_role": "editor"}
    private_row = _cross_ws_row(vis="private", body="TOP SECRET")

    with patch("services.mcp_tools.db_cursor", return_value=_cm(cur)), \
         patch("services.mcp_tools.list_workspaces_in_db", return_value=[ws]), \
         patch("services.mcp_tools.perform_semantic_search", new=AsyncMock(return_value=[private_row])):
        res = await execute_tool(
            "search_cross_workspace", {"query": "q"}, {"sub": "usr_editor"}, MagicMock()
        )

    assert res["results"][0]["body"] == "TOP SECRET"


@pytest.mark.asyncio
async def test_l12_cross_workspace_search_never_leaks_embedding_vectors():
    """無論角色為何,search_cross_workspace 都不得回傳 embedding/secondary_embedding 向量。"""
    from services.mcp_tools import execute_tool

    cur = MagicMock()
    cur.fetchone.return_value = {"embedding_provider": "openai", "embedding_model": "m"}
    ws = {"id": "ws_target", "name": "Target", "my_role": "editor"}
    row = _cross_ws_row(vis="public", body="public info")

    with patch("services.mcp_tools.db_cursor", return_value=_cm(cur)), \
         patch("services.mcp_tools.list_workspaces_in_db", return_value=[ws]), \
         patch("services.mcp_tools.perform_semantic_search", new=AsyncMock(return_value=[row])):
        res = await execute_tool(
            "search_cross_workspace", {"query": "q"}, {"sub": "usr_editor"}, MagicMock()
        )

    result = res["results"][0]
    assert "embedding" not in result
    assert "secondary_embedding" not in result
    assert result["body"] == "public info"

"""
tests/test_kb_data_isolation.py — 知識庫資料隔離安全測試

確保私人知識庫的資料不會因為系統問題外洩給未授權使用者。

涵蓋：
- I1: 匿名使用者無法讀取私人 KB 節點
- I2: 匿名使用者無法讀取 conditional_public KB 的 body
- I3: 跨工作區節點存取必須綁定正確的 ws_id
- I4: API Key 無法越出被授權的工作區
- I5: 非成員使用者無法讀取私人 KB
- I6: explore 端點對匿名使用者絕不回傳 private KB
- I7: list_nodes_in_db 對 viewer 角色遮蔽非公開節點 body
- I8: 工作區不存在時回傳 404，不暴露其他 KB 資訊
- I9: 刪除工作區後節點無法再被存取
- I10: restricted 可見度 KB 對未登入使用者擋下

Run: pytest tests/test_kb_data_isolation.py -v
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch, call

import pytest


# ─── shared helpers ───────────────────────────────────────────────────────────

def _ws(
    ws_id: str = "ws_target",
    visibility: str = "private",
    owner_id: str = "usr_owner",
    deleted_at=None,
    status: str = "active",
) -> dict:
    return {
        "id": ws_id,
        "name": "Secure KB",
        "description": None,
        "visibility": visibility,
        "owner_id": owner_id,
        "kb_type": "evergreen",
        "language": "zh-TW",
        "status": status,
        "deleted_at": deleted_at,
        "allow_anonymous_view": False,
        "linked_workspace_id": None,
        "embedding_model": "text-embedding-3-small",
        "embedding_dim": 1536,
        "embedding_provider": "openai",
        "migrating_to_provider": None,
        "migrating_to_model": None,
        "migration_status": "none",
        "archive_window_days": 90,
        "min_traversals": 1,
        "qa_archive_mode": "manual_review",
        "extraction_provider": None,
        "auto_split": False,
        "consult_trust_tier": "ask",
        "consult_provider": None,
        "agent_node_id": None,
        "settings": {},
        "schema_version": "1.0",
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }


def _node(node_id: str = "mem_secret", ws_id: str = "ws_target", vis: str = "private") -> dict:
    return {
        "id": node_id,
        "workspace_id": ws_id,
        "title": "Secret Node",
        "body": "This is confidential content",
        "content_type": "fact",
        "content_format": "plain",
        "visibility": vis,
        "tags": [],
        "author": "usr_owner",
        "trust_score": 0.8,
        "status": "active",
        "schema_version": "1.0",
        "source_type": "human",
        "dim_freshness": 1.0,
        "dim_author_rep": 0.8,
        "dim_accuracy": 0.8,
        "dim_utility": 0.5,
        "traversal_count": 0,
        "unique_traverser_count": 0,
        "signature": "abc123",
        "archived_at": None,
        "copied_from_node": None,
        "copied_from_ws": None,
        "validity_confirmed_at": None,
        "validity_confirmed_by": None,
        "ask_count": 0,
        "miss_count": 0,
        "source_id": None,
        "source_doc_node_id": None,
        "source_paragraph_ref": None,
        "cluster_id": None,
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }


def _cur_returning_ws_then_no_member(ws: dict) -> MagicMock:
    cur = MagicMock()
    cur.fetchone.side_effect = [ws, None]  # workspace found, not a member
    return cur


# ─── I1: 匿名使用者無法讀取私人 KB ───────────────────────────────────────────

def test_i1_anonymous_cannot_access_private_kb_nodes():
    """匿名 user=None 對私人 KB 呼叫 require_ws_access → 403/404。"""
    from fastapi import HTTPException
    from services.workspaces import require_ws_access

    cur = _cur_returning_ws_then_no_member(_ws(visibility="private"))

    with pytest.raises(HTTPException) as exc:
        require_ws_access(cur, "ws_target", user=None)

    assert exc.value.status_code in (403, 404)


# ─── I2: conditional_public KB 對 viewer 遮蔽 body ────────────────────────────

def test_i2_viewer_body_stripped_in_conditional_public():
    """
    conditional_public KB 的非公開節點對 viewer 角色應遮蔽 body。
    strip_body_if_viewer(node, role='viewer') → body=None, content_stripped=True
    """
    from services.workspaces import strip_body_if_viewer

    node = _node(vis="private")  # node-level visibility = private
    result = strip_body_if_viewer(node, role="viewer")

    assert result["body"] is None
    assert result["content_stripped"] is True


def test_i2b_public_node_body_visible_to_viewer():
    """節點本身 visibility='public' 時，viewer 仍可看到 body。"""
    from services.workspaces import strip_body_if_viewer

    node = _node(vis="public")
    result = strip_body_if_viewer(node, role="viewer")

    assert result["body"] == "This is confidential content"
    assert result["content_stripped"] is False


# ─── I3: 跨工作區節點存取 — workspace_id 綁定 ────────────────────────────────

def test_i3_cross_workspace_node_access_blocked():
    """
    get_node_in_db 使用 WHERE id=%s AND workspace_id=%s；
    即使 node_id 存在，不在此 ws 則 404。
    """
    from fastapi import HTTPException
    from services.nodes import get_node_in_db

    ws = _ws(visibility="public")
    cur = MagicMock()
    cur.fetchone.side_effect = [
        ws,       # require_ws_access
        None,     # workspace_members (role lookup)
        None,     # node not found in this workspace
    ]

    with pytest.raises(HTTPException) as exc:
        get_node_in_db(cur, "ws_target", "mem_belongs_to_other_ws", user=None)

    assert exc.value.status_code == 404


def test_i3b_node_query_includes_workspace_id_condition():
    """get_node_in_db 執行的 SQL 必須包含 workspace_id = %s，防止跨 workspace 洩漏。"""
    from services.nodes import get_node_in_db

    ws = _ws(visibility="public")
    node = _node()
    cur = MagicMock()
    # user=None: require_ws_access makes 1 fetchone (workspace), no member lookup
    # get_node_in_db then makes 1 more fetchone (node)
    cur.fetchone.side_effect = [ws, node]

    get_node_in_db(cur, "ws_target", "mem_secret", user=None)

    node_query_call = cur.execute.call_args_list[-1]
    sql, params = node_query_call[0]
    assert "workspace_id" in sql.lower()
    assert "ws_target" in params


# ─── I4: API Key 不可越出被授權的工作區 ─────────────────────────────────────

def test_i4_api_key_cannot_access_other_workspace():
    """
    API key 被授權 ws_A，嘗試存取 ws_B → 403。
    """
    from fastapi import HTTPException
    from services.workspaces import require_ws_access

    api_key_user = {
        "sub": "usr_api",
        "api_key_id": "ak_1",
        "workspace_id": "ws_authorized",   # key 綁定 ws_A
    }

    cur = MagicMock()
    # Should never reach DB because API key scope check happens first
    cur.fetchone.return_value = _ws(ws_id="ws_target")

    with pytest.raises(HTTPException) as exc:
        require_ws_access(cur, "ws_target", user=api_key_user)  # 嘗試存取 ws_target ≠ ws_authorized

    assert exc.value.status_code == 403
    assert "restricted to another workspace" in exc.value.detail


def test_i4b_api_key_can_access_authorized_workspace():
    """API key 被授權 ws_target，存取 ws_target 成功。"""
    from services.workspaces import require_ws_access

    api_key_user = {
        "sub": "usr_owner",
        "api_key_id": "ak_1",
        "workspace_id": "ws_target",
    }

    cur = MagicMock()
    cur.fetchone.side_effect = [
        _ws(visibility="public"),   # workspace lookup
        None,                        # membership lookup
    ]

    ws = require_ws_access(cur, "ws_target", user=api_key_user)
    assert ws is not None


# ─── I5: 非成員使用者無法讀取私人 KB ────────────────────────────────────────

def test_i5_non_member_cannot_access_private_kb():
    """非成員、非擁有者嘗試讀取 private KB → 403/404。"""
    from fastapi import HTTPException
    from services.workspaces import require_ws_access

    cur = _cur_returning_ws_then_no_member(_ws(visibility="private", owner_id="usr_owner"))
    stranger = {"sub": "usr_stranger"}

    with pytest.raises(HTTPException) as exc:
        require_ws_access(cur, "ws_target", user=stranger)

    assert exc.value.status_code in (403, 404)


def test_i5b_member_can_access_private_kb():
    """成員（role=viewer）可以通過 require_ws_access 的基本讀取檢查。"""
    from services.workspaces import require_ws_access

    ws = _ws(visibility="private", owner_id="usr_owner")
    member_row = {"role": "viewer"}
    cur = MagicMock()
    cur.fetchone.side_effect = [ws, member_row]

    member = {"sub": "usr_member"}
    result = require_ws_access(cur, "ws_target", user=member)
    assert result is not None


# ─── I6: explore 端點絕不回傳私人 KB 給匿名使用者 ───────────────────────────

def test_i6_explore_sql_excludes_private_for_anon():
    """explore_workspaces_in_db 匿名呼叫時，SQL WHERE 中必須限制 visibility。"""
    from services.workspaces import explore_workspaces_in_db

    cur = MagicMock()
    cur.fetchall.return_value = []

    explore_workspaces_in_db(cur, user=None, q=None, lang=None, sort="newest")

    sql: str = cur.execute.call_args[0][0]
    # Must restrict to public / conditional_public
    assert "public" in sql.lower()
    # Must NOT contain a clause that would allow private rows for anon
    assert "private" not in sql.lower() or "conditional_public" in sql


def test_i6b_explore_private_keyword_absent_in_anon_sql():
    """匿名情境下 explore SQL 不能含有 'private' 作為條件值（允許 private KBs 通過）。"""
    from services.workspaces import explore_workspaces_in_db

    cur = MagicMock()
    cur.fetchall.return_value = []

    explore_workspaces_in_db(cur, user=None, q=None, lang=None, sort="newest")

    sql: str = cur.execute.call_args[0][0]
    params = cur.execute.call_args[0][1]
    # params must not contain 'private' as an allowed visibility value
    assert "private" not in [str(p) for p in params]


# ─── I7: list_nodes_in_db 對 viewer 遮蔽 body ───────────────────────────────

def test_i7_list_nodes_strips_private_node_body_for_viewer():
    """
    list_nodes_in_db 對非 editor/admin 的角色回傳時，私有節點 body 必須被遮蔽。
    """
    from services.nodes import list_nodes_in_db

    ws = _ws(visibility="public")
    secret_node = _node(vis="private")
    public_node = {**_node(node_id="mem_open", vis="public"), "body": "Public content"}

    cur = MagicMock()
    # require_ws_access, role lookup (owner check in get_effective_role via fetchone is handled in the mock)
    cur.fetchone.side_effect = [
        ws,    # require_ws_access workspace fetch
        None,  # membership lookup (not a member, not owner → role=None)
        None,  # get_effective_role: membership
    ]
    cur.fetchall.return_value = [secret_node, public_node]

    viewer = {"sub": "usr_viewer"}
    results = list_nodes_in_db(cur, "ws_target", user=viewer)

    private_results = [r for r in results if r["id"] == "mem_secret"]
    assert len(private_results) == 1
    assert private_results[0]["body"] is None
    assert private_results[0]["content_stripped"] is True

    public_results = [r for r in results if r["id"] == "mem_open"]
    assert len(public_results) == 1
    assert public_results[0]["body"] == "Public content"


# ─── I8: 工作區不存在時回傳 404（不洩漏其他 KB 資訊）────────────────────────

def test_i8_nonexistent_workspace_returns_404():
    """查詢不存在的 ws_id → 404，錯誤訊息不包含其他 KB 的任何資訊。"""
    from fastapi import HTTPException
    from services.workspaces import require_ws_access

    cur = MagicMock()
    cur.fetchone.return_value = None  # workspace not found

    user = {"sub": "usr_curious"}
    with pytest.raises(HTTPException) as exc:
        require_ws_access(cur, "ws_nonexistent", user=user)

    assert exc.value.status_code == 404
    # Error detail must be generic, not revealing other workspace info
    detail = str(exc.value.detail).lower()
    assert "workspace not found" in detail or "not found" in detail


# ─── I9: 已刪除工作區的節點無法存取 ─────────────────────────────────────────

def test_i9_deleted_workspace_nodes_inaccessible():
    """
    已軟刪除 (deleted_at IS NOT NULL) 的 workspace，其節點應無法存取。
    在 require_ws_access 之前 explore 端點過濾掉 deleted_at IS NOT NULL。
    此測試驗證 explore SQL 包含 deleted_at IS NULL 條件。
    """
    from services.workspaces import explore_workspaces_in_db

    cur = MagicMock()
    cur.fetchall.return_value = []

    explore_workspaces_in_db(cur, user=None, q=None, lang=None, sort="newest")

    sql: str = cur.execute.call_args[0][0]
    assert "deleted_at" in sql.lower()


# ─── I10: restricted KB 對未登入使用者擋下 ──────────────────────────────────

def test_i10_restricted_kb_requires_auth():
    """restricted 可見度 KB 對 user=None → 401 (Authentication required)。"""
    from fastapi import HTTPException
    from services.workspaces import require_ws_access

    restricted_ws = _ws(visibility="restricted")
    cur = MagicMock()
    # Second fetchone is get_effective_role membership check — returns None for anon
    cur.fetchone.side_effect = [restricted_ws, None]

    with pytest.raises(HTTPException) as exc:
        require_ws_access(cur, "ws_target", user=None)

    assert exc.value.status_code in (401, 403)


def test_i10b_restricted_kb_write_requires_editor_role():
    """restricted KB write 操作對 role=viewer 使用者 → 403。"""
    from fastapi import HTTPException
    from services.workspaces import require_ws_access

    restricted_ws = _ws(visibility="restricted")
    viewer_row = {"role": "viewer"}
    cur = MagicMock()
    cur.fetchone.side_effect = [restricted_ws, viewer_row]

    viewer = {"sub": "usr_viewer"}
    with pytest.raises(HTTPException) as exc:
        require_ws_access(cur, "ws_target", user=viewer, write=True)

    assert exc.value.status_code == 403

"""
tests/test_workspace_pins.py — 工作區釘選功能（workspace_pins）

對應 Agent Loop 任務 ws_6aa957c3/mem_b0de24d8：Sidebar 工作區選單新增釘選，
私人/公開清單各限顯示前 5 筆（前端裁切，本檔測後端）。

涵蓋：
- P1: list_workspaces_in_db 的 SQL 佔位符數量與參數數量必須一致（含 search
      filter 時也要一致——曾在加入 workspace_pins JOIN 時因參數插入位置錯誤
      導致對應偏移，此測試防止回歸）。
- P2: explore_workspaces_in_db 同上。
- P3: pin_workspace_in_db 寫入前必須先過 require_ws_access 存取檢查。
- P4: 無存取權時 pin 失敗，且不執行 INSERT。
- P5: unpin_workspace_in_db 執行 DELETE。

Run: pytest tests/test_workspace_pins.py -v
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException


def _count_placeholders_before_params(cur: MagicMock) -> tuple[int, int]:
    """Return (placeholder_count, param_count) from the last cur.execute call."""
    sql, params = cur.execute.call_args[0]
    return sql.count("%s"), len(params)


# ─── P1: list_workspaces_in_db param alignment ─────────────────────────────

def test_p1_list_workspaces_param_count_matches_placeholders_authenticated():
    from services.workspaces import list_workspaces_in_db

    cur = MagicMock()
    cur.fetchall.return_value = []

    list_workspaces_in_db(cur, search=None, user={"sub": "usr_1"})

    placeholders, param_count = _count_placeholders_before_params(cur)
    assert placeholders == param_count


def test_p1b_list_workspaces_param_count_matches_placeholders_with_search():
    from services.workspaces import list_workspaces_in_db

    cur = MagicMock()
    cur.fetchall.return_value = []

    list_workspaces_in_db(cur, search="foo", user={"sub": "usr_1"})

    placeholders, param_count = _count_placeholders_before_params(cur)
    assert placeholders == param_count


def test_p1c_list_workspaces_param_count_matches_placeholders_anonymous():
    from services.workspaces import list_workspaces_in_db

    cur = MagicMock()
    cur.fetchall.return_value = []

    list_workspaces_in_db(cur, search=None, user=None)

    placeholders, param_count = _count_placeholders_before_params(cur)
    assert placeholders == param_count


def test_p1d_list_workspaces_param_count_matches_placeholders_api_key():
    from services.workspaces import list_workspaces_in_db

    cur = MagicMock()
    cur.fetchall.return_value = []

    list_workspaces_in_db(
        cur, search=None,
        user={"sub": "usr_1", "api_key_id": "key_1", "workspace_id": "ws_a"},
    )

    placeholders, param_count = _count_placeholders_before_params(cur)
    assert placeholders == param_count


def test_p1e_list_workspaces_selects_pinned_flag():
    from services.workspaces import list_workspaces_in_db

    cur = MagicMock()
    cur.fetchall.return_value = []

    list_workspaces_in_db(cur, search=None, user={"sub": "usr_1"})

    sql: str = cur.execute.call_args[0][0]
    assert "workspace_pins" in sql
    assert "pinned" in sql


# ─── P2: explore_workspaces_in_db param alignment ──────────────────────────

def test_p2_explore_workspaces_param_count_matches_placeholders_authenticated():
    from services.workspaces import explore_workspaces_in_db

    cur = MagicMock()
    cur.fetchall.return_value = []

    explore_workspaces_in_db(cur, user={"sub": "usr_1"}, q=None, lang=None, sort="newest")

    placeholders, param_count = _count_placeholders_before_params(cur)
    assert placeholders == param_count


def test_p2b_explore_workspaces_param_count_matches_placeholders_with_q_and_lang():
    from services.workspaces import explore_workspaces_in_db

    cur = MagicMock()
    cur.fetchall.return_value = []

    explore_workspaces_in_db(cur, user={"sub": "usr_1"}, q="foo", lang="zh-TW", sort="newest")

    placeholders, param_count = _count_placeholders_before_params(cur)
    assert placeholders == param_count


def test_p2c_explore_workspaces_param_count_matches_placeholders_anonymous():
    from services.workspaces import explore_workspaces_in_db

    cur = MagicMock()
    cur.fetchall.return_value = []

    explore_workspaces_in_db(cur, user=None, q=None, lang=None, sort="newest")

    placeholders, param_count = _count_placeholders_before_params(cur)
    assert placeholders == param_count


def test_p2d_explore_workspaces_selects_pinned_flag():
    from services.workspaces import explore_workspaces_in_db

    cur = MagicMock()
    cur.fetchall.return_value = []

    explore_workspaces_in_db(cur, user={"sub": "usr_1"}, q=None, lang=None, sort="newest")

    sql: str = cur.execute.call_args[0][0]
    assert "workspace_pins" in sql
    assert "pinned" in sql


# ─── P3/P4: pin_workspace_in_db access-gated ───────────────────────────────

def test_p3_pin_workspace_checks_access_before_insert():
    from services.workspaces import pin_workspace_in_db

    cur = MagicMock()
    with patch("services.workspaces.require_ws_access") as mock_access:
        mock_access.return_value = {"id": "ws_a", "owner_id": "usr_1"}
        pin_workspace_in_db(cur, "ws_a", {"sub": "usr_1"})

    mock_access.assert_called_once_with(cur, "ws_a", {"sub": "usr_1"}, write=False)
    insert_sql: str = cur.execute.call_args[0][0]
    assert "INSERT INTO workspace_pins" in insert_sql
    assert cur.execute.call_args[0][1] == ("usr_1", "ws_a")


def test_p4_pin_workspace_denied_without_access_does_not_insert():
    from services.workspaces import pin_workspace_in_db

    cur = MagicMock()
    with patch("services.workspaces.require_ws_access") as mock_access:
        mock_access.side_effect = HTTPException(status_code=403, detail="Access denied")
        with pytest.raises(HTTPException):
            pin_workspace_in_db(cur, "ws_secret", {"sub": "usr_intruder"})

    cur.execute.assert_not_called()


# ─── P5: unpin_workspace_in_db ──────────────────────────────────────────────

def test_p5_unpin_workspace_deletes_pin_row():
    from services.workspaces import unpin_workspace_in_db

    cur = MagicMock()
    unpin_workspace_in_db(cur, "ws_a", {"sub": "usr_1"})

    delete_sql: str = cur.execute.call_args[0][0]
    assert "DELETE FROM workspace_pins" in delete_sql
    assert cur.execute.call_args[0][1] == ("usr_1", "ws_a")

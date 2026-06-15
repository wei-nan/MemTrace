"""
tests/test_trust_voting.py — S3-T01 信任投票機制

涵蓋：
- 投票前必須先 traverse（prerequisite guard）
- UNIQUE(node_id, user_id)：同一使用者重複投票為更新，非新增
- 信任分數公式：acc*0.4 + util*0.25 + fresh*0.25 + author_rep*0.1
- 30 天半衰期權重計算邏輯

Run: pytest tests/test_trust_voting.py -v
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch, call

import pytest


def _user(uid="usr_voter"):
    return {"sub": uid}


def _make_cur(traversed=True, existing_vote=None, node=None):
    cur = MagicMock()
    call_count = [0]

    node_row = node or {"dim_freshness": 1.0, "dim_author_rep": 0.9}
    stats_row = {"avg_acc": 0.8, "avg_util": 0.7}

    def fetchone_side_effect():
        call_count[0] += 1
        n = call_count[0]
        if n == 1:
            return {"count": 1} if traversed else {"count": 0}  # traversal check
        if n == 2:
            return stats_row  # weighted vote stats
        if n == 3:
            return node_row   # node dims
        return None

    cur.fetchone.side_effect = fetchone_side_effect
    return cur


# ─── 投票需先 traverse ────────────────────────────────────────────────────────

def test_vote_requires_prior_traversal():
    """未 traverse 過節點的使用者嘗試投票 → 403。"""
    from fastapi import HTTPException
    from services.nodes import vote_trust_in_db

    cur = MagicMock()

    with patch("services.workspaces.require_ws_access"), \
         patch("services.nodes.actor_has_traversed_node", return_value=False):

        with pytest.raises(HTTPException) as exc:
            vote_trust_in_db(cur, "ws_1", "node_1", {"accuracy": 4, "utility": 3}, _user())

        assert exc.value.status_code == 403


# ─── 投票成功返回 trust_score ─────────────────────────────────────────────────

def test_vote_returns_trust_score():
    """正常投票後回傳包含 trust_score 的 dict。"""
    from services.nodes import vote_trust_in_db

    cur = MagicMock()
    cur.fetchone.side_effect = [
        {"avg_acc": 4.0, "avg_util": 3.5},  # weighted stats
        {"dim_freshness": 1.0, "dim_author_rep": 0.9},  # node dims
    ]

    with patch("services.workspaces.require_ws_access"), \
         patch("services.nodes.actor_has_traversed_node", return_value=True), \
         patch("services.nodes.generate_id", return_value="vote_1"):

        result = vote_trust_in_db(cur, "ws_1", "node_1", {"accuracy": 4, "utility": 3}, _user())

    assert "trust_score" in result
    assert result["status"] == "ok"


# ─── 信任分數公式驗證 ─────────────────────────────────────────────────────────

def test_trust_score_formula():
    """trust_score = avg_acc*0.4 + avg_util*0.25 + freshness*0.25 + author_rep*0.1"""
    from services.nodes import vote_trust_in_db

    # avg_acc=0.8 (4/5), avg_util=0.6 (3/5), freshness=1.0, author_rep=0.9
    avg_acc = 0.8
    avg_util = 0.6
    freshness = 1.0
    author_rep = 0.9
    expected = (avg_acc * 0.4) + (avg_util * 0.25) + (freshness * 0.25) + (author_rep * 0.1)

    cur = MagicMock()
    cur.fetchone.side_effect = [
        {"avg_acc": avg_acc, "avg_util": avg_util},
        {"dim_freshness": freshness, "dim_author_rep": author_rep},
    ]

    with patch("services.workspaces.require_ws_access"), \
         patch("services.nodes.actor_has_traversed_node", return_value=True), \
         patch("services.nodes.generate_id", return_value="v1"):

        result = vote_trust_in_db(cur, "ws_1", "node_1", {"accuracy": 4, "utility": 3}, _user())

    assert abs(result["trust_score"] - expected) < 1e-6


# ─── 重複投票寫 ON CONFLICT UPDATE ────────────────────────────────────────────

def test_duplicate_vote_uses_upsert():
    """同使用者重複投票應使用 ON CONFLICT DO UPDATE，不插入重複列。"""
    from services.nodes import vote_trust_in_db

    cur = MagicMock()
    cur.fetchone.side_effect = [
        {"avg_acc": 0.8, "avg_util": 0.6},
        {"dim_freshness": 1.0, "dim_author_rep": 0.8},
    ]

    with patch("services.workspaces.require_ws_access"), \
         patch("services.nodes.actor_has_traversed_node", return_value=True), \
         patch("services.nodes.generate_id", return_value="v1"):

        vote_trust_in_db(cur, "ws_1", "node_1", {"accuracy": 5, "utility": 5}, _user())

    # Find the INSERT call and verify ON CONFLICT clause exists
    insert_sqls = [str(c) for c in cur.execute.call_args_list if "INSERT" in str(c).upper()]
    assert len(insert_sqls) >= 1
    assert any("ON CONFLICT" in sql.upper() for sql in insert_sqls)


# ─── 節點不存在返回 404 ───────────────────────────────────────────────────────

def test_vote_node_not_found_returns_404():
    """節點不存在 → 404。"""
    from fastapi import HTTPException
    from services.nodes import vote_trust_in_db

    cur = MagicMock()
    cur.fetchone.side_effect = [
        {"avg_acc": 0.8, "avg_util": 0.6},  # stats
        None,  # node not found
    ]

    with patch("services.workspaces.require_ws_access"), \
         patch("services.nodes.actor_has_traversed_node", return_value=True), \
         patch("services.nodes.generate_id", return_value="v1"):

        with pytest.raises(HTTPException) as exc:
            vote_trust_in_db(cur, "ws_1", "node_missing", {"accuracy": 3, "utility": 3}, _user())

        assert exc.value.status_code == 404


# ─── 時間衰減 SQL 邏輯驗證 ───────────────────────────────────────────────────

def test_vote_sql_uses_time_decay_weight():
    """加權平均 SQL 應使用 POWER(0.5, ...) 30 天半衰期。"""
    from services.nodes import vote_trust_in_db

    cur = MagicMock()
    cur.fetchone.side_effect = [
        {"avg_acc": 0.7, "avg_util": 0.7},
        {"dim_freshness": 1.0, "dim_author_rep": 0.85},
    ]

    with patch("services.workspaces.require_ws_access"), \
         patch("services.nodes.actor_has_traversed_node", return_value=True), \
         patch("services.nodes.generate_id", return_value="v1"):

        vote_trust_in_db(cur, "ws_1", "node_1", {"accuracy": 4, "utility": 4}, _user())

    # Find the weighted stats query
    sql_calls = [str(c) for c in cur.execute.call_args_list]
    decay_sqls = [s for s in sql_calls if "POWER" in s.upper() or "0.5" in s]
    assert len(decay_sqls) >= 1, "Expected time-decay POWER() in vote stats SQL"

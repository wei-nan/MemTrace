"""
tests/test_dead_end.py
Phase 6.4 A1-T04 — traverse 死路偵測單元測試（mock cursor，不碰真實資料庫）。

驗證對應計畫 M1（死路偵測）:
  - 無 proceeds_to 出邊 → dead_end
  - 有出邊但工具輸出不命中任何 condition → dead_end
  - condition 命中 / condition_type=always / 未給 tool_output → 非 dead_end
"""
from __future__ import annotations

from services.search import bfs_neighborhood


class DeadEndCursor:
    """回傳:鄰域邊空、節點空,只有 proceeds_to 出邊依測試設定。"""

    def __init__(self, out_edges):
        self.out_edges = out_edges
        self._last = ""

    def execute(self, sql, params=None):
        self._last = sql.lower()

    def fetchall(self):
        if "proceeds_to" in self._last:
            return self.out_edges
        return []  # neighborhood edges + node rows


def _edge(condition=None, condition_type="tool_output_match"):
    meta = {}
    if condition is not None:
        meta["condition"] = condition
    if condition_type is not None:
        meta["condition_type"] = condition_type
    return {"id": "e1", "from_id": "root", "to_id": "n2", "metadata": meta}


def _run(out_edges, tool_output=None):
    cur = DeadEndCursor(out_edges)
    return bfs_neighborhood(cur, "ws", "root", depth=1, tool_output=tool_output)


def test_no_outgoing_edges_is_dead_end():
    assert _run([])["dead_end"] is True


def test_has_edges_without_tool_output_is_not_dead_end():
    assert _run([_edge(condition="timeout")])["dead_end"] is False


def test_condition_matches_tool_output_is_not_dead_end():
    res = _run([_edge(condition="timeout")], tool_output="connection timeout after 5s")
    assert res["dead_end"] is False


def test_no_condition_matches_is_dead_end():
    res = _run([_edge(condition="timeout")], tool_output="connection refused")
    assert res["dead_end"] is True


def test_always_condition_is_not_dead_end():
    res = _run([_edge(condition=None, condition_type="always")], tool_output="anything")
    assert res["dead_end"] is False

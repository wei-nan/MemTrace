"""
tests/test_consult.py
Phase 6.4 Track A/C — consult() 路由邏輯 + synthesizer 單元測試（mock DB，不碰真實資料庫）。

驗證對應計畫:
  V1 propose-only（safe/ask 不直寫圖）
  V3 信任分級（ask vs full_trust 分流；risky 無視信任層級）
  D5 安全閘正交（dangerous 硬擋、risky 強制升級）
  A3 synthesizer consensus / divergent
"""
from __future__ import annotations

import json
from contextlib import contextmanager, ExitStack
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from services.consult import consult, synthesize_responses


# ─── Fake cursor that answers by inspecting the executed SQL ──────────────────

class FakeCursor:
    def __init__(self, stuck_node, session_count=0, proposal_status="dismissed", answer_nodes=None):
        self.stuck_node = stuck_node
        self.session_count = session_count
        self.proposal_status = proposal_status
        self.answer_nodes = answer_nodes or []
        self._last = ""
        self.executed: list[str] = []

    def execute(self, sql, params=None):
        self._last = sql.lower()
        self.executed.append(sql)

    def fetchone(self):
        s = self._last
        if "count(*)" in s:
            return {"count": self.session_count}
        if "from memory_nodes where id" in s:
            return self.stuck_node
        if "content_type = 'gap'" in s:
            return None  # no pre-existing gap node
        if "from audit_proposals where id" in s:
            return {"status": self.proposal_status}
        return None

    def fetchall(self):
        if "answered_by" in self._last:
            return self.answer_nodes
        return []


def _proposal_json():
    return json.dumps({
        "action": "create_node_and_edge",
        "new_node": {
            "title": "Check application logs",
            "content_type": "procedural",
            "body": "tail -n 50 /var/log/app.log",
            "tags": ["log", "diag"],
        },
        "edge_metadata": {"condition": "timeout", "condition_type": "tool_output_match"},
        "reason": "Inspect logs to find the failure cause.",
    })


async def _run_consult(
    *,
    trust_tier="ask",
    safety_class="safe",
    synthesis="consensus",
    session_count=0,
    mode="generate",
):
    """Run consult() with every external collaborator mocked. Returns (result, mocks)."""
    stuck_node = {
        "id": "node_stuck",
        "title": "Connection failed — initial diagnosis",
        "body": "Run telnet host 80",
        "tags": ["net"],
        "content_type": "procedural",
    }
    fake_cur = FakeCursor(stuck_node, session_count=session_count)

    @contextmanager
    def fake_db_cursor(*a, **k):
        yield fake_cur

    workspace = {
        "id": "ws_test",
        "settings": {},  # quota defaults to 10
        "consult_provider": None,
        "consult_trust_tier": trust_tier,
    }

    with ExitStack() as stack:
        p = lambda target, **kw: stack.enter_context(patch(f"services.consult.{target}", **kw))
        p("db_cursor", new=fake_db_cursor)
        p("require_ws_access", new=MagicMock(return_value=workspace))
        p("resolve_provider", new=MagicMock(return_value=MagicMock()))
        p("record_usage", new=MagicMock())  # usage logging opens its own DB cursor
        rsc_mock = AsyncMock(return_value=(_proposal_json(), 100))
        p("run_single_consult", new=rsc_mock)
        p("synthesize_responses", new=AsyncMock(return_value=(synthesis, "reason")))
        p("classify_safety", new=AsyncMock(return_value=safety_class))
        p("asyncio", new=MagicMock(sleep=AsyncMock()))
        create_proposal = stack.enter_context(
            patch("services.consult.create_proposal", new=MagicMock(return_value={"id": "prop_x"}))
        )
        notify = stack.enter_context(
            patch("services.consult.send_consult_notification", new=MagicMock())
        )
        create_node = stack.enter_context(
            patch("services.nodes.create_node_in_db", new=MagicMock(return_value={"id": "node_new"}))
        )
        create_edge = stack.enter_context(
            patch("services.edges.create_edge_in_db", new=MagicMock(return_value={"id": "edge_new"}))
        )

        result = await consult(
            ws_id="ws_test",
            stuck_node_id="node_stuck",
            problem_context="connection timeout after 5s",
            mode=mode,
            user={"sub": "user_1"},
        )
        return result, {
            "create_proposal": create_proposal,
            "notify": notify,
            "create_node": create_node,
            "create_edge": create_edge,
            "run_single_consult": rsc_mock,
        }


# ─── consult() routing tests ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dangerous_is_hard_blocked():
    """D5: dangerous 產出硬擋，記 gap node，不建提案、不自動合入。"""
    result, m = await _run_consult(safety_class="dangerous", trust_tier="full_trust")
    assert result["status"] == "blocked"
    assert result["classification"] == "dangerous"
    m["create_node"].assert_called_once()           # gap node written
    m["create_proposal"].assert_not_called()         # not escalated to a normal proposal
    m["create_edge"].assert_not_called()             # never merged into the graph
    m["notify"].assert_called_once()


@pytest.mark.asyncio
async def test_risky_forces_escalation_even_in_full_trust():
    """D5 正交性: risky 即使在 full_trust 也強制拉人，不自動合入（fail-closed）。"""
    result, m = await _run_consult(safety_class="risky", trust_tier="full_trust")
    m["create_proposal"].assert_called_once()        # escalated to audit proposal
    m["create_node"].assert_not_called()             # NOT auto-merged despite full_trust
    m["create_edge"].assert_not_called()
    # proposal status polled as 'dismissed' → fail-closed
    assert result["status"] == "blocked"
    assert result["classification"] == "risky"


@pytest.mark.asyncio
async def test_safe_ask_is_propose_only():
    """V1 + V3: safe + ask → 進審核佇列，圖不變（propose-only）。"""
    result, m = await _run_consult(safety_class="safe", trust_tier="ask")
    assert result["status"] == "escalated"
    assert result["classification"] == "safe"
    m["create_proposal"].assert_called_once()
    m["create_node"].assert_not_called()             # graph untouched until human approves
    m["create_edge"].assert_not_called()


@pytest.mark.asyncio
async def test_safe_full_trust_auto_merges():
    """V3: safe + full_trust → 自動建節點 + proceeds_to edge（圖自我修復）。"""
    result, m = await _run_consult(safety_class="safe", trust_tier="full_trust")
    assert result["status"] == "merged"
    assert result["new_node_id"] == "node_new"
    m["create_node"].assert_called_once()
    m["create_edge"].assert_called_once()
    m["create_proposal"].assert_not_called()         # auto-merge bypasses the queue
    # 事後通知 "已新增"
    m["notify"].assert_called_once()
    assert m["notify"].call_args.kwargs["action_taken"] == "auto_merged"


@pytest.mark.asyncio
async def test_divergent_escalates_without_auto_merge():
    """A3: synthesizer 判定 divergent → 升級給人，不自動選答案，即使 full_trust。"""
    result, m = await _run_consult(safety_class="safe", synthesis="divergent", trust_tier="full_trust")
    assert result["status"] == "escalated"
    m["create_proposal"].assert_called_once()
    m["create_node"].assert_not_called()


@pytest.mark.asyncio
async def test_budget_exceeded_downgrades_to_gap():
    """D7: 超過每日 consult 上限 → 不呼叫大模型，只記 gap node。"""
    result, m = await _run_consult(session_count=10)  # quota default = 10
    assert result["status"] == "budget_exceeded"
    m["create_node"].assert_called_once()             # gap node registered
    m["run_single_consult"].assert_not_called()       # model never called


@pytest.mark.asyncio
async def test_answered_inquiry_returns_existing_answers_without_model_call():
    stuck_node = {
        "id": "node_stuck",
        "title": "Already answered issue",
        "body": "What should happen next?",
        "tags": ["done"],
        "content_type": "inquiry",
    }
    fake_cur = FakeCursor(
        stuck_node,
        answer_nodes=[
            {
                "id": "mem_answer",
                "title": "Existing answer",
                "body": "Use the existing resolved procedure.",
                "content_type": "procedural",
            }
        ],
    )

    @contextmanager
    def fake_db_cursor(*a, **k):
        yield fake_cur

    workspace = {
        "id": "ws_test",
        "settings": {},
        "consult_provider": None,
        "consult_trust_tier": "ask",
    }

    with ExitStack() as stack:
        stack.enter_context(patch("services.consult.db_cursor", new=fake_db_cursor))
        stack.enter_context(patch("services.consult.require_ws_access", new=MagicMock(return_value=workspace)))
        run_single = stack.enter_context(patch("services.consult.run_single_consult", new=AsyncMock()))

        result = await consult(
            ws_id="ws_test",
            stuck_node_id="node_stuck",
            problem_context="same already resolved condition",
            mode="generate",
            user={"sub": "user_1"},
        )

    assert result["status"] == "already_answered"
    assert result["answer_nodes"][0]["id"] == "mem_answer"
    run_single.assert_not_called()
    executed_sql = "\n".join(fake_cur.executed).lower()
    assert "insert into consult_sessions" in executed_sql


# ─── synthesize_responses tests ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_synthesize_single_response_is_consensus():
    res, _ = await synthesize_responses("ws", "u", ["only one"])
    assert res == "consensus"


@pytest.mark.asyncio
async def test_synthesize_divergent_verdict():
    with patch("services.consult.resolve_provider", new=MagicMock(return_value=MagicMock())), \
         patch("services.consult.record_usage", new=MagicMock()), \
         patch("services.consult.chat_completion",
               new=AsyncMock(return_value=('{"synthesis_result": "divergent", "reasoning": "conflict"}', 50))):
        res, reason = await synthesize_responses("ws", "u", ["a", "b"])
    assert res == "divergent"


@pytest.mark.asyncio
async def test_synthesize_provider_unavailable_defaults_consensus():
    from core.ai import AIProviderUnavailable
    with patch("services.consult.resolve_provider", side_effect=AIProviderUnavailable("no key")):
        res, _ = await synthesize_responses("ws", "u", ["a", "b"])
    assert res == "consensus"

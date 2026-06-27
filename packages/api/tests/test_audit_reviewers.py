"""
tests/test_audit_reviewers.py
Phase 6.2 B4–B5 T12–T19 — audit_proposals service + 7 大 Reviewer 整合測試
"""
from __future__ import annotations

import pytest
from services.audit_proposals import (
    create_proposal,
    list_proposals,
    mark_proposal_read,
    resolve_proposal,
    get_node_audit_summary,
    DAILY_QUOTA_PER_REVIEWER,
)
from jobs.audit_reviewers import (
    reviewer_deduper,
    reviewer_tag_normalizer,
    reviewer_edge_auditor,
    reviewer_trust_calibrator,
    reviewer_coverage_gap_detector,
    reviewer_source_decay_monitor,
    reviewer_integrity_auditor,
    reviewer_secret_scanner,
    run_all_reviewers_for_workspace,
)


# ─── Unit Tests (Mocked DB) ───────────────────────────────────────────────────

class TestCreateProposalUnit:
    """audit_proposals.create_proposal 單元測試（mock DB cursor）。"""

    def _make_cur(self, quota_cnt=0, return_row=None):
        from unittest.mock import MagicMock
        cur = MagicMock()
        # _has_open_duplicate 查詢 -> fetchone 回傳 None（無重複）
        # _quota_ok 查詢 -> fetchone 回傳 {"cnt": quota_cnt}
        # create_proposal INSERT -> fetchone 回傳 return_row
        cur.fetchone.side_effect = [
            None,
            {"cnt": quota_cnt},
            return_row or {
                "id": "prop_001",
                "workspace_id": "ws_test",
                "reviewer": "deduper",
                "category": "duplicate",
                "target_ids": ["n1", "n2"],
                "reasoning": "test",
                "evidence": {},
                "suggested_action": {},
                "severity": "low",
                "status": "pending",
                "created_at": "2026-01-01",
                "resolved_at": None,
                "resolved_by": None,
            },
        ]
        return cur

    def test_create_proposal_within_quota(self):
        cur = self._make_cur(quota_cnt=0)
        result = create_proposal(
            cur, "ws_test", "deduper", "duplicate",
            ["n1", "n2"], "重複節點", severity="mid"
        )
        assert result is not None
        assert result["id"] == "prop_001"

    def test_create_proposal_quota_exceeded(self):
        cur = self._make_cur(quota_cnt=DAILY_QUOTA_PER_REVIEWER)
        result = create_proposal(
            cur, "ws_test", "deduper", "duplicate",
            ["n1", "n2"], "重複節點"
        )
        assert result is None  # quota 已滿應回傳 None

    def test_create_proposal_skips_duplicate(self):
        # _has_open_duplicate 找到既有 pending 提案 -> 直接回傳 None，不進 quota / INSERT
        from unittest.mock import MagicMock
        cur = MagicMock()
        cur.fetchone.side_effect = [{"exists": 1}]
        result = create_proposal(
            cur, "ws_test", "deduper", "duplicate",
            ["n1", "n2"], "重複節點"
        )
        assert result is None


# ─── Integration Tests (Real DB) ─────────────────────────────────────────────

@pytest.mark.integration
class TestAuditProposalsIntegration:

    def test_audit_proposals_table_exists(self, db_transaction):
        conn = db_transaction
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'audit_proposals' AND column_name = 'severity'
                """
            )
            row = cur.fetchone()
        assert row is not None
        assert row["column_name"] == "severity"

    def test_proposal_reads_table_exists(self, db_transaction):
        conn = db_transaction
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'proposal_reads' AND column_name = 'user_id'
                """
            )
            row = cur.fetchone()
        assert row is not None

    def test_create_and_list_proposals(self, db_transaction):
        conn = db_transaction
        ws_id = "ws_spec0001"
        with conn.cursor() as cur:
            prop = create_proposal(
                cur, ws_id, "deduper", "duplicate",
                ["node_a", "node_b"], "Test duplicate",
                evidence={"similarity": 0.95},
                severity="mid",
            )
            assert prop is not None
            assert prop["status"] == "pending"
            assert prop["severity"] == "mid"

            results = list_proposals(cur, ws_id, status="pending")
            ids = [r["id"] for r in results]
            assert prop["id"] in ids

    def test_quota_enforcement(self, db_transaction):
        conn = db_transaction
        ws_id = "ws_spec0001"
        with conn.cursor() as cur:
            # 先寫入 DAILY_QUOTA_PER_REVIEWER 筆（直接 INSERT 繞過 create_proposal 以加速測試）
            for i in range(DAILY_QUOTA_PER_REVIEWER):
                cur.execute(
                    """
                    INSERT INTO audit_proposals (id, workspace_id, reviewer, category, target_ids, reasoning, severity)
                    VALUES (%s, %s, 'test_quota', 'test', '{}', 'seed', 'low')
                    """,
                    (f"prop_seed_{i:03d}", ws_id),
                )

            # 現在 create_proposal 應回傳 None（quota 已滿）。用唯一 target_ids 避免被去重
            # 短路，確保命中的是 quota 防線而非 dedup 防線。
            result = create_proposal(
                cur, ws_id, "test_quota", "test", ["overflow_node"], "overflow", severity="low"
            )
            assert result is None

    def test_create_proposal_dedups_identical(self, db_transaction):
        """同一 (reviewer, category, target_ids) 重複送出時只留一列；不同 target 仍可建立。"""
        conn = db_transaction
        ws_id = "ws_spec0001"
        with conn.cursor() as cur:
            p1 = create_proposal(
                cur, ws_id, "safety_queue", "async_safety", ["dup_node"], "first"
            )
            p2 = create_proposal(
                cur, ws_id, "safety_queue", "async_safety", ["dup_node"], "second"
            )
            assert p1 is not None
            assert p2 is None  # 重複被去重

            matching = [
                r for r in list_proposals(cur, ws_id, status="pending", reviewer="safety_queue")
                if r["target_ids"] == ["dup_node"]
            ]
            assert len(matching) == 1

            # 指向不同節點的發現不應被誤殺
            p3 = create_proposal(
                cur, ws_id, "safety_queue", "async_safety", ["other_node"], "third"
            )
            assert p3 is not None

    def test_mark_proposal_read_and_summary(self, db_transaction):
        conn = db_transaction
        ws_id = "ws_spec0001"
        node_id = "node_audit_test"
        user_id = "user_tester"
        with conn.cursor() as cur:
            prop = create_proposal(
                cur, ws_id, "deduper", "duplicate",
                [node_id], "test summary", severity="high",
            )
            assert prop is not None

            # 未讀前 unread_count 應 = 1
            summary = get_node_audit_summary(cur, ws_id, node_id, user_id)
            assert summary["total_count"] == 1
            assert summary["unread_count"] == 1
            assert summary["max_severity"] == "high"

            # 標記已讀後 unread_count 應 = 0
            mark_proposal_read(cur, prop["id"], user_id)
            summary2 = get_node_audit_summary(cur, ws_id, node_id, user_id)
            assert summary2["unread_count"] == 0

    def test_resolve_proposal(self, db_transaction):
        conn = db_transaction
        ws_id = "ws_spec0001"
        with conn.cursor() as cur:
            prop = create_proposal(
                cur, ws_id, "edge_auditor", "dangling_edge",
                ["edge_x"], "stale edge", severity="mid",
            )
            assert prop is not None

            resolved = resolve_proposal(cur, prop["id"], "admin_user", "accepted")
            assert resolved is not None
            assert resolved["status"] == "accepted"
            assert resolved["resolved_by"] == "admin_user"


@pytest.mark.integration
class TestReviewersIntegration:
    """各 Reviewer 整合測試：確認能在 real DB 執行而不報錯，並且有適當的提案輸出。"""

    def test_reviewer_tag_normalizer_no_crash(self, db_transaction):
        conn = db_transaction
        ws_id = "ws_spec0001"
        with conn.cursor() as cur:
            count = reviewer_tag_normalizer(cur, ws_id)
            assert isinstance(count, int)
            assert count >= 0

    def test_reviewer_edge_auditor_no_crash(self, db_transaction):
        conn = db_transaction
        ws_id = "ws_spec0001"
        with conn.cursor() as cur:
            count = reviewer_edge_auditor(cur, ws_id)
            assert isinstance(count, int)
            assert count >= 0

    def test_reviewer_trust_calibrator_no_crash(self, db_transaction):
        conn = db_transaction
        ws_id = "ws_spec0001"
        with conn.cursor() as cur:
            count = reviewer_trust_calibrator(cur, ws_id)
            assert isinstance(count, int)
            assert count >= 0

    def test_reviewer_coverage_gap_detector_no_crash(self, db_transaction):
        conn = db_transaction
        ws_id = "ws_spec0001"
        with conn.cursor() as cur:
            count = reviewer_coverage_gap_detector(cur, ws_id)
            assert isinstance(count, int)
            assert count >= 0

    def test_reviewer_source_decay_monitor_no_crash(self, db_transaction):
        conn = db_transaction
        ws_id = "ws_spec0001"
        with conn.cursor() as cur:
            count = reviewer_source_decay_monitor(cur, ws_id)
            assert isinstance(count, int)
            assert count >= 0

    def test_reviewer_deduper_detects_similar_nodes(self, db_transaction):
        """取兩個現有節點，把它們的 embedding 更新為相同向量，確認 deduper 能偵測到。"""
        conn = db_transaction
        ws_id = "ws_spec0001"
        vec_str = "[" + ",".join(["0.01"] * 1536) + "]"
        with conn.cursor() as cur:
            # 取出 ws_spec0001 中任意兩個有 embedding 的節點 ID
            cur.execute(
                """
                SELECT id FROM memory_nodes
                WHERE workspace_id = %s AND status = 'active'
                ORDER BY id
                LIMIT 2
                """,
                (ws_id,),
            )
            rows = cur.fetchall()
            if len(rows) < 2:
                pytest.skip("ws_spec0001 沒有足夠節點可供測試")

            node_id_a = rows[0]["id"]
            node_id_b = rows[1]["id"]

            # 將兩個節點的 embedding 更新為完全相同的向量（similarity = 1.0 > 0.92）
            cur.execute(
                "UPDATE memory_nodes SET embedding = %s::vector WHERE id = %s",
                (vec_str, node_id_a),
            )
            cur.execute(
                "UPDATE memory_nodes SET embedding = %s::vector WHERE id = %s",
                (vec_str, node_id_b),
            )

            count = reviewer_deduper(cur, ws_id)
            assert count >= 1

            # 確認提案已寫入且包含這兩個節點
            list_proposals_res = list_proposals(cur, ws_id, status="pending", reviewer="deduper")
            target_proposals = [
                p for p in list_proposals_res
                if node_id_a in p["target_ids"] or node_id_b in p["target_ids"]
            ]
            assert len(target_proposals) >= 1
            assert target_proposals[0]["category"] == "duplicate"

    def test_reviewer_integrity_auditor_no_crash(self, db_transaction):
        conn = db_transaction
        ws_id = "ws_spec0001"
        with conn.cursor() as cur:
            count = reviewer_integrity_auditor(cur, ws_id)
            assert isinstance(count, int)
            assert count >= 0

    def test_reviewer_integrity_auditor_detects_missing_embedding(self, db_transaction):
        """把一個 active 節點的 embedding 清空且 created_at 設為 10 天前，確認被 flag。"""
        conn = db_transaction
        ws_id = "ws_spec0001"
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM memory_nodes WHERE workspace_id = %s AND status = 'active' ORDER BY id LIMIT 1",
                (ws_id,),
            )
            row = cur.fetchone()
            if not row:
                pytest.skip("ws_spec0001 沒有可用節點")
            node_id = row["id"]

            cur.execute(
                "UPDATE memory_nodes SET embedding = NULL, created_at = now() - INTERVAL '10 days' WHERE id = %s",
                (node_id,),
            )

            count = reviewer_integrity_auditor(cur, ws_id)
            assert count >= 1

            props = list_proposals(cur, ws_id, status="pending", reviewer="integrity_auditor")
            missing_emb = [p for p in props if p["category"] == "missing_embedding"]
            assert any(node_id in p["target_ids"] for p in missing_emb)

    def test_reviewer_integrity_auditor_idempotent(self, db_transaction):
        """同一缺陷連跑兩次，第二次不應重複提案（pending 去重）。"""
        conn = db_transaction
        ws_id = "ws_spec0001"
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM memory_nodes WHERE workspace_id = %s AND status = 'active' ORDER BY id LIMIT 1",
                (ws_id,),
            )
            row = cur.fetchone()
            if not row:
                pytest.skip("ws_spec0001 沒有可用節點")
            cur.execute(
                "UPDATE memory_nodes SET embedding = NULL, created_at = now() - INTERVAL '10 days' WHERE id = %s",
                (row["id"],),
            )
            first = reviewer_integrity_auditor(cur, ws_id)
            second = reviewer_integrity_auditor(cur, ws_id)
            assert first >= 1
            assert second == 0  # 第二輪全被冪等檢查擋下

    def test_reviewer_secret_scanner_detects_leaked_key(self, db_transaction):
        """節點 body 夾帶 AWS key 形狀的字串，應被 secret_scanner flag 為 leaked_secret。"""
        conn = db_transaction
        ws_id = "ws_spec0001"
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM memory_nodes WHERE workspace_id = %s AND status = 'active' ORDER BY id LIMIT 1",
                (ws_id,),
            )
            row = cur.fetchone()
            if not row:
                pytest.skip("ws_spec0001 沒有可用節點")
            node_id = row["id"]
            cur.execute(
                "UPDATE memory_nodes SET body = %s WHERE id = %s",
                ("Deploy creds: AKIAIOSFODNN7EXAMPLE should never be stored here", node_id),
            )
            count = reviewer_secret_scanner(cur, ws_id)
            assert count >= 1
            props = list_proposals(cur, ws_id, status="pending", reviewer="secret_scanner")
            assert any(node_id in p["target_ids"] and p["category"] == "leaked_secret" for p in props)

    def test_run_all_reviewers_returns_dict(self, db_transaction):
        """run_all_reviewers_for_workspace 應回傳 dict，各 reviewer 有整數結果。"""
        conn = db_transaction
        ws_id = "ws_spec0001"
        with conn.cursor() as cur:
            summary = run_all_reviewers_for_workspace(cur, ws_id)
        assert isinstance(summary, dict)
        # 9 個 reviewers，每個都應有整數值（>=0 表示成功，-1 表示錯誤）
        expected_keys = {
            "deduper", "tag_normalizer", "edge_auditor",
            "embedding_consistency", "trust_calibrator",
            "coverage_gap_detector", "source_decay_monitor",
            "integrity_auditor", "secret_scanner",
        }
        assert expected_keys == set(summary.keys())
        for k, v in summary.items():
            assert isinstance(v, int), f"reviewer {k} returned non-int: {v}"

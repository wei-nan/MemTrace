"""
services/audit_proposals.py — AI 審查員提案服務 (Phase 6.2 B4-T12)

提供提案的建立（含每日 Quota 限額）、查詢、已讀標記等核心功能。
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from core.security import generate_id

logger = logging.getLogger(__name__)

# 每個 workspace 每位 reviewer 每日最多寫入的提案數
DAILY_QUOTA_PER_REVIEWER = 20


def _quota_ok(cur, workspace_id: str, reviewer: str) -> bool:
    """檢查今日該 reviewer 在此 workspace 是否尚有 quota 剩餘。"""
    cur.execute(
        """
        SELECT COUNT(*) AS cnt
        FROM audit_proposals
        WHERE workspace_id = %s
          AND reviewer = %s
          AND created_at >= date_trunc('day', now() AT TIME ZONE 'UTC')
        """,
        (workspace_id, reviewer),
    )
    row = cur.fetchone()
    cnt = row["cnt"] if row else 0
    return int(cnt) < DAILY_QUOTA_PER_REVIEWER


def create_proposal(
    cur,
    workspace_id: str,
    reviewer: str,
    category: str,
    target_ids: List[str],
    reasoning: str,
    evidence: Optional[Dict[str, Any]] = None,
    suggested_action: Optional[Dict[str, Any]] = None,
    severity: str = "low",
) -> Optional[Dict[str, Any]]:
    """
    寫入一筆 audit proposal。
    若今日該 reviewer 已達 DAILY_QUOTA_PER_REVIEWER 上限則跳過並回傳 None。
    """
    if not _quota_ok(cur, workspace_id, reviewer):
        logger.info(
            "Daily quota reached for reviewer=%s workspace=%s — skipping proposal",
            reviewer,
            workspace_id,
        )
        return None

    proposal_id = generate_id("prop")
    cur.execute(
        """
        INSERT INTO audit_proposals (
            id, workspace_id, reviewer, category, target_ids,
            reasoning, evidence, suggested_action, severity
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING *
        """,
        (
            proposal_id,
            workspace_id,
            reviewer,
            category,
            target_ids,
            reasoning,
            json.dumps(evidence or {}),
            json.dumps(suggested_action or {}),
            severity,
        ),
    )
    row = cur.fetchone()
    return dict(row) if row else None


def list_proposals(
    cur,
    workspace_id: str,
    status: str = "pending",
    severity: Optional[str] = None,
    reviewer: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """查詢 workspace 的 audit proposals（支援按 status / severity / reviewer 篩選）。"""
    conditions = ["workspace_id = %s", "status = %s"]
    params: List[Any] = [workspace_id, status]

    if severity:
        conditions.append("severity = %s")
        params.append(severity)
    if reviewer:
        conditions.append("reviewer = %s")
        params.append(reviewer)

    params.extend([limit, offset])
    cur.execute(
        f"""
        SELECT *
        FROM audit_proposals
        WHERE {' AND '.join(conditions)}
        ORDER BY
            CASE severity WHEN 'high' THEN 0 WHEN 'mid' THEN 1 ELSE 2 END,
            created_at DESC
        LIMIT %s OFFSET %s
        """,
        params,
    )
    return [dict(r) for r in cur.fetchall()]


def mark_proposal_read(cur, proposal_id: str, user_id: str) -> bool:
    """標記指定 proposal 為已讀（冪等操作）。回傳 True 表示成功。"""
    cur.execute(
        """
        INSERT INTO proposal_reads (proposal_id, user_id)
        VALUES (%s, %s)
        ON CONFLICT (proposal_id, user_id) DO NOTHING
        """,
        (proposal_id, user_id),
    )
    return True


def resolve_proposal(cur, proposal_id: str, user_id: str, action: str) -> Optional[Dict[str, Any]]:
    """
    解決一筆 proposal（action: 'accepted' | 'dismissed'）。
    同時自動標記為已讀。
    """
    if action not in ("accepted", "dismissed"):
        raise ValueError(f"Invalid action: {action}")

    cur.execute(
        """
        UPDATE audit_proposals
        SET status = %s, resolved_at = now(), resolved_by = %s
        WHERE id = %s AND status = 'pending'
        RETURNING *
        """,
        (action, user_id, proposal_id),
    )
    row = cur.fetchone()
    if row:
        mark_proposal_read(cur, proposal_id, user_id)
    return dict(row) if row else None


def get_node_audit_summary(cur, workspace_id: str, node_id: str, user_id: str) -> Dict[str, Any]:
    """
    取得節點的 audit 摘要（供前端 badge 使用）。
    回傳：max_severity、total_count、unread_count
    """
    cur.execute(
        """
        SELECT
            MAX(CASE ap.severity WHEN 'high' THEN 3 WHEN 'mid' THEN 2 ELSE 1 END) AS max_sev_int,
            COUNT(ap.id) AS total_count,
            COUNT(ap.id) FILTER (
                WHERE NOT EXISTS (
                    SELECT 1 FROM proposal_reads pr
                    WHERE pr.proposal_id = ap.id AND pr.user_id = %s
                )
            ) AS unread_count
        FROM audit_proposals ap
        WHERE ap.workspace_id = %s
          AND ap.status = 'pending'
          AND %s = ANY(ap.target_ids)
        """,
        (user_id, workspace_id, node_id),
    )
    row = cur.fetchone()
    if not row or row["total_count"] == 0:
        return {"max_severity": None, "total_count": 0, "unread_count": 0}

    sev_map = {3: "high", 2: "mid", 1: "low", None: None}
    return {
        "max_severity": sev_map.get(row["max_sev_int"]),
        "total_count": int(row["total_count"]),
        "unread_count": int(row["unread_count"]),
    }

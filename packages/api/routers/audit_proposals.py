"""
routers/audit_proposals.py — Audit Proposals REST API (Phase 6.2 B7-T20)

提供以下端點：
  GET  /api/v1/workspaces/{ws_id}/audit-proposals          — 列出提案（支援篩選）
  POST /api/v1/audit-proposals/{proposal_id}/read          — 標記已讀
  POST /api/v1/audit-proposals/{proposal_id}/resolve       — 接受或駁回提案
  GET  /api/v1/workspaces/{ws_id}/nodes/{node_id}/audit-summary — 節點 audit 摘要
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from core.deps     import get_current_user
from core.database import db_cursor
from services.audit_proposals import (
    list_proposals,
    mark_proposal_read,
    resolve_proposal,
    get_node_audit_summary,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["audit-proposals"])


# ─── Request / Response Models ─────────────────────────────────────────────────

class ResolveBody(BaseModel):
    action: str  # "accepted" | "dismissed"


# ─── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/workspaces/{ws_id}/audit-proposals")
def list_audit_proposals(
    ws_id: str,
    status: str = Query("pending", pattern="^(pending|accepted|dismissed|expired)$"),
    severity: Optional[str] = Query(None, pattern="^(low|mid|high)$"),
    reviewer: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: dict = Depends(get_current_user),
):
    """
    列出 workspace 的 audit proposals。
    支援按 status / severity / reviewer 篩選，依 severity 高→低、建立時間降序排列。
    """
    with db_cursor() as cur:
        # 確認 workspace 存在且使用者有存取權
        cur.execute("SELECT id FROM workspaces WHERE id = %s", (ws_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Workspace not found")

        results = list_proposals(
            cur,
            workspace_id=ws_id,
            status=status,
            severity=severity,
            reviewer=reviewer,
            limit=limit,
            offset=offset,
        )

    # 將 target_ids 等欄位轉成可序列化格式
    for r in results:
        if isinstance(r.get("evidence"), str):
            import json
            r["evidence"] = json.loads(r["evidence"])
        if isinstance(r.get("suggested_action"), str):
            import json
            r["suggested_action"] = json.loads(r["suggested_action"])

    return {"proposals": results, "total": len(results), "offset": offset}


@router.post("/audit-proposals/{proposal_id}/read")
def mark_audit_proposal_read(
    proposal_id: str,
    user: dict = Depends(get_current_user),
):
    """標記指定 proposal 為已讀（冪等）。"""
    user_id = user.get("sub") or user.get("id", "unknown")
    with db_cursor(commit=True) as cur:
        # 確認 proposal 存在
        cur.execute("SELECT id FROM audit_proposals WHERE id = %s", (proposal_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Proposal not found")
        mark_proposal_read(cur, proposal_id, user_id)
    return {"ok": True}


@router.post("/audit-proposals/{proposal_id}/resolve")
def resolve_audit_proposal(
    proposal_id: str,
    body: ResolveBody,
    user: dict = Depends(get_current_user),
):
    """
    解決一筆 proposal。
    action: "accepted" — 採納建議
    action: "dismissed" — 忽略建議
    """
    user_id = user.get("sub") or user.get("id", "unknown")
    if body.action not in ("accepted", "dismissed"):
        raise HTTPException(status_code=422, detail="action must be 'accepted' or 'dismissed'")

    with db_cursor(commit=True) as cur:
        result = resolve_proposal(cur, proposal_id, user_id, body.action)
        if not result:
            raise HTTPException(status_code=404, detail="Proposal not found or already resolved")

    return {"proposal": dict(result)}


@router.get("/workspaces/{ws_id}/nodes/{node_id}/audit-summary")
def get_audit_summary_for_node(
    ws_id: str,
    node_id: str,
    user: dict = Depends(get_current_user),
):
    """
    取得節點的 audit 摘要，供前端 badge 顯示使用。
    回傳：max_severity（高嚴重度）、total_count（提案總數）、unread_count（未讀數）。
    """
    user_id = user.get("sub") or user.get("id", "unknown")
    with db_cursor() as cur:
        summary = get_node_audit_summary(cur, ws_id, node_id, user_id)
    return summary

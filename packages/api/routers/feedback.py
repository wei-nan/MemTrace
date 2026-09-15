"""
routers/feedback.py — MVP 意見回饋 / bug report：提交、自助查詢、管理員總覽。

  POST /api/v1/feedback         — 已登入使用者提交（bug-report 或 feature-request）
  GET  /api/v1/feedback/mine    — 僅回傳呼叫者本人提交過的紀錄
  GET  /api/v1/feedback/all     — 僅限系統管理員，回傳所有使用者的回饋（含提交者資訊）

寫入頻率限制沿用 core.ratelimit.RateLimitMiddleware 既有的 write tier
（/api/ 下的所有非 GET 請求皆自動套用），不另建限流機制。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from core.database import db_cursor
from core.deps import get_current_user, require_system_admin
from models.feedback import AdminFeedbackItem, FeedbackCreate, FeedbackCreateResponse, FeedbackItem
from services.feedback import (
    create_feedback_node,
    feedback_type_from_tags,
    list_all_feedback,
    list_my_feedback,
)

router = APIRouter(prefix="/api/v1/feedback", tags=["feedback"])


@router.post("", response_model=FeedbackCreateResponse, status_code=201)
def submit_feedback(body: FeedbackCreate, user: dict = Depends(get_current_user)):
    with db_cursor(commit=True) as cur:
        node = create_feedback_node(cur, user["sub"], body.type, body.title, body.body)
    return FeedbackCreateResponse(id=node["id"], status=node["resolution_status"])


@router.get("/mine", response_model=list[FeedbackItem])
def get_my_feedback(user: dict = Depends(get_current_user)):
    with db_cursor() as cur:
        rows = list_my_feedback(cur, user["sub"])
    return [
        FeedbackItem(
            id=row["id"],
            type=feedback_type_from_tags(row.get("tags")),
            title=row["title"],
            resolution_status=row["resolution_status"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


@router.get("/all", response_model=list[AdminFeedbackItem])
def get_all_feedback(user: dict = Depends(require_system_admin)):
    with db_cursor() as cur:
        rows = list_all_feedback(cur)
    return [
        AdminFeedbackItem(
            id=row["id"],
            type=feedback_type_from_tags(row.get("tags")),
            title=row["title"],
            body=row["body"],
            resolution_status=row["resolution_status"],
            created_at=row["created_at"],
            author_id=row["author_id"],
            author_name=row.get("author_name"),
            author_email=row.get("author_email"),
        )
        for row in rows
    ]

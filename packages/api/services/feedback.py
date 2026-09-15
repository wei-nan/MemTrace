"""
services/feedback.py — MVP 意見回饋 / bug report 機制。

不建立平行資料表：每筆 feedback 沿用既有 node/workspace 模型，存成
ws_feedback（系統層級 workspace，非使用者當前瀏覽的 KB，避免污染其資料）
底下 content_type=inquiry 的節點，以 tags（feedback + bug-report /
feature-request）區分種類，resolution_status 沿用既有欄位（MVP 只用
'open'）。ws_feedback 與其擁有者帳號採 lazy create-if-not-exists，仿照
system:safety（services/safety_provisioning.py）的既有系統帳號慣例，
不另加 migration。
"""
from __future__ import annotations

from services.nodes import create_node_in_db

FEEDBACK_WORKSPACE_ID = "ws_feedback"
FEEDBACK_SYSTEM_USER_ID = "system:feedback"

FEEDBACK_TYPES = ("bug-report", "feature-request")


def ensure_feedback_workspace(cur) -> str:
    """Create-if-not-exists ws_feedback，owner 為系統帳號 system:feedback。"""
    cur.execute("SELECT id FROM workspaces WHERE id = %s", (FEEDBACK_WORKSPACE_ID,))
    if cur.fetchone():
        return FEEDBACK_WORKSPACE_ID

    cur.execute("SELECT id FROM users WHERE id = %s", (FEEDBACK_SYSTEM_USER_ID,))
    if not cur.fetchone():
        cur.execute(
            """
            INSERT INTO users (id, display_name, email, email_verified)
            VALUES (%s, %s, %s, true)
            ON CONFLICT (id) DO NOTHING
            """,
            (FEEDBACK_SYSTEM_USER_ID, "System Feedback", "feedback@memtrace.local"),
        )

    cur.execute(
        """
        INSERT INTO workspaces (id, name, language, visibility, kb_type, owner_id, qa_archive_mode)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO NOTHING
        """,
        (
            FEEDBACK_WORKSPACE_ID, "使用者回饋", "zh-TW", "private", "evergreen",
            FEEDBACK_SYSTEM_USER_ID, "manual_review",
        ),
    )
    return FEEDBACK_WORKSPACE_ID


def create_feedback_node(cur, user_id: str, feedback_type: str, title: str, body: str) -> dict:
    """建立一筆 feedback 節點，回傳建立後的 row（含 id / resolution_status）。"""
    if feedback_type not in FEEDBACK_TYPES:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"type must be one of {FEEDBACK_TYPES}")

    ws_id = ensure_feedback_workspace(cur)
    node_data = {
        "title": title,
        "content_type": "inquiry",
        "content_format": "plain",
        "body": body,
        "tags": ["feedback", feedback_type],
        "visibility": "private",
        "author": user_id,
        "source_type": "human",
        "resolution_status": "open",
    }
    return create_node_in_db(cur, ws_id, node_data)


def list_my_feedback(cur, user_id: str) -> list[dict]:
    """僅回傳呼叫者本人在 ws_feedback 提交的節點（author-scoped）。"""
    cur.execute(
        """
        SELECT id, tags, title, resolution_status, created_at
        FROM memory_nodes
        WHERE workspace_id = %s AND author = %s AND status = 'active'
          AND 'feedback' = ANY(tags)
        ORDER BY created_at DESC
        """,
        (FEEDBACK_WORKSPACE_ID, user_id),
    )
    return cur.fetchall()


def list_all_feedback(cur) -> list[dict]:
    """管理員用：回傳 ws_feedback 底下所有回饋節點，含提交者資訊。"""
    cur.execute(
        """
        SELECT n.id, n.tags, n.title, n.body, n.resolution_status, n.created_at,
               n.author AS author_id, u.display_name AS author_name, u.email AS author_email
        FROM memory_nodes n
        LEFT JOIN users u ON u.id = n.author
        WHERE n.workspace_id = %s AND n.status = 'active'
          AND 'feedback' = ANY(n.tags)
        ORDER BY n.created_at DESC
        """,
        (FEEDBACK_WORKSPACE_ID,),
    )
    return cur.fetchall()


def feedback_type_from_tags(tags: list[str]) -> str:
    for t in FEEDBACK_TYPES:
        if t in (tags or []):
            return t
    return "unknown"

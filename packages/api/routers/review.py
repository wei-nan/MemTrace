from __future__ import annotations

from typing import List, Optional
import json

from fastapi import APIRouter, Depends, HTTPException

from core.ai_review import DEFAULT_AI_REVIEW_PROMPT, require_owner, run_ai_review_for_item
from core.database import db_cursor
from core.diff import build_node_diff
from core.security import generate_id
from core.deps import get_current_user
from models.kb import NodeResponse
from models.review import (
    AIReviewerCreate,
    AIReviewerResponse,
    AIReviewerUpdate,
    ReviewQueueResponse,
    ReviewUpdate,
)
from routers.kb import (
    _create_node_in_db,
    _delete_node_in_db,
    _get_effective_role,
    _node_row_to_snapshot,
    _require_ws_access,
    _strip_body_if_viewer,
    _update_node_in_db,
    _write_node_revision,
)

router = APIRouter(prefix="/api/v1/workspaces", tags=["review"])


def _strip_review_for_role(item: dict, role: Optional[str]) -> dict:
    item = dict(item)
    item["can_review"] = role in ("editor", "admin")
    if role in ("editor", "admin"):
        return item
    node_data = dict(item.get("node_data") or {})
    before = dict(item.get("before_snapshot") or {}) if item.get("before_snapshot") else None
    for target in [node_data, before]:
        if target is None:
            continue
        target["body_zh"] = ""
        target["body_en"] = ""
    diff_summary = dict(item.get("diff_summary") or {})
    fields = dict(diff_summary.get("fields") or {})
    for body_field in ("body_zh", "body_en"):
        if body_field in fields:
            fields[body_field] = {
                "type": "text",
                "before": "",
                "after": "",
                "line_diff": [{"op": "keep", "text": "[redacted for viewer]"}],
            }
    diff_summary["fields"] = fields
    item["node_data"] = node_data
    item["before_snapshot"] = before
    item["diff_summary"] = diff_summary
    return item


def _apply_review_item(cur, item: dict):
    ws_id = item["workspace_id"]
    change_type = item["change_type"]
    node_data = item["node_data"] or {}
    if change_type == "create":
        node = _create_node_in_db(cur, ws_id, node_data)
    elif change_type == "update":
        target_node_id = item["target_node_id"]
        if not target_node_id:
            raise HTTPException(status_code=400, detail="Update review missing target node")
        node = _update_node_in_db(cur, ws_id, target_node_id, node_data, node_data.get("author") or item.get("proposer_id") or "system")
    elif change_type == "delete":
        target_node_id = item["target_node_id"]
        if not target_node_id:
            raise HTTPException(status_code=400, detail="Delete review missing target node")
        deleted = _delete_node_in_db(cur, ws_id, target_node_id)
        return None, deleted
    else:
        raise HTTPException(status_code=400, detail="Unsupported change type")
    return node, None


@router.get("/{ws_id}/review-queue", response_model=List[ReviewQueueResponse])
def list_review_queue(ws_id: str, status: str = "pending", user: dict = Depends(get_current_user)):
    with db_cursor() as cur:
        ws = _require_ws_access(cur, ws_id, user)
        role = _get_effective_role(cur, ws_id, ws["owner_id"], user["sub"])
        cur.execute(
            """
            SELECT * FROM review_queue
            WHERE workspace_id = %s AND status = %s
            ORDER BY created_at ASC
            """,
            (ws_id, status),
        )
        return [_strip_review_for_role(row, role) for row in cur.fetchall()]


@router.patch("/review-queue/{id}", response_model=ReviewQueueResponse)
def update_review_item(id: str, body: ReviewUpdate, user: dict = Depends(get_current_user)):
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT * FROM review_queue WHERE id = %s", (id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Review item not found")
        _require_ws_access(cur, row["workspace_id"], user, write=True, required_scope="kb:write")
        updates = {}
        if body.node_data is not None:
            merged_node = body.node_data
            updates["node_data"] = json.dumps(merged_node, ensure_ascii=False)
            updates["diff_summary"] = json.dumps(build_node_diff(row["before_snapshot"], merged_node, row["change_type"]), ensure_ascii=False)
        if body.suggested_edges is not None:
            updates["suggested_edges"] = json.dumps(body.suggested_edges, ensure_ascii=False)
        if body.review_notes is not None:
            updates["review_notes"] = body.review_notes
        if not updates:
            row["can_review"] = True
            return row
        set_clause = ", ".join(f"{k} = %s" for k in updates)
        cur.execute(f"UPDATE review_queue SET {set_clause} WHERE id = %s RETURNING *", list(updates.values()) + [id])
        updated = cur.fetchone()
        updated["can_review"] = True
        return updated


VALID_EDGE_RELATIONS = {"depends_on", "extends", "related_to", "contradicts", "answered_by", "similar_to", "queried_via_mcp"}

def _create_suggested_edges(cur, ws_id: str, from_node_id: str, suggested_edges: list):
    """Resolve to_title_en references and insert edges where target node exists."""
    for e in suggested_edges:
        to_title = e.get("to_title_en")
        relation = e.get("relation", "related_to")
        # Normalize unsupported relation types to avoid DB enum violation
        if relation not in VALID_EDGE_RELATIONS:
            relation = "related_to"
        if not to_title:
            continue
        cur.execute(
            """
            SELECT id FROM memory_nodes
            WHERE workspace_id = %s
              AND LOWER(title_en) = LOWER(%s)
            LIMIT 1
            """,
            (ws_id, to_title),
        )
        target = cur.fetchone()
        if not target:
            continue
        to_id = target["id"]
        if to_id == from_node_id:
            continue
        # Skip if edge already exists in either direction
        cur.execute(
            """
            SELECT 1 FROM edges
            WHERE workspace_id = %s
              AND ((from_id = %s AND to_id = %s) OR (from_id = %s AND to_id = %s))
            LIMIT 1
            """,
            (ws_id, from_node_id, to_id, to_id, from_node_id),
        )
        if cur.fetchone():
            continue
        cur.execute(
            """
            INSERT INTO edges (id, workspace_id, from_id, to_id, relation, weight, status)
            VALUES (%s, %s, %s, %s, %s, 1.0, 'active')
            """,
            (generate_id("edge"), ws_id, from_node_id, to_id, relation),
        )


@router.post("/review-queue/{id}/accept", response_model=Optional[NodeResponse])
def accept_review_item(id: str, user: dict = Depends(get_current_user)):
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT * FROM review_queue WHERE id = %s", (id,))
        item = cur.fetchone()
        if not item:
            raise HTTPException(status_code=404, detail="Review item not found")
        if item["status"] != "pending":
            raise HTTPException(status_code=400, detail=f"Item is already {item['status']}")
        _require_ws_access(cur, item["workspace_id"], user, write=True, required_scope="kb:write")
        node, deleted = _apply_review_item(cur, item)
        if node:
            _write_node_revision(
                cur,
                node["id"],
                item["workspace_id"],
                _node_row_to_snapshot(node),
                node["signature"],
                item["proposer_type"],
                item["proposer_id"],
                id,
            )
            # Set initial dim_accuracy based on source_type, recompute trust_score
            source_type = (item.get("node_data") or {}).get("source_type", item.get("proposer_type", "human"))
            dim_accuracy = 0.8 if source_type in ("ai_generated", "ai") else 1.0
            cur.execute(
                """
                UPDATE memory_nodes
                SET
                    dim_accuracy = %s,
                    trust_score = (
                        %s             * 0.40 +
                        dim_freshness  * 0.25 +
                        dim_utility    * 0.25 +
                        dim_author_rep * 0.10
                    )
                WHERE id = %s
                """,
                (dim_accuracy, dim_accuracy, node["id"]),
            )
            # Create edges from suggested_edges (to_title_en resolved at ingest time)
            suggested = item.get("suggested_edges") or []
            if suggested:
                _create_suggested_edges(cur, item["workspace_id"], node["id"], suggested)
        cur.execute(
            "UPDATE review_queue SET status = 'accepted', reviewer_type = 'human', reviewer_id = %s, reviewed_at = now() WHERE id = %s",
            (user["sub"], id),
        )
        return node


@router.post("/review-queue/{id}/reject")
def reject_review_item(id: str, user: dict = Depends(get_current_user)):
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT workspace_id, status FROM review_queue WHERE id = %s", (id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Review item not found")
        _require_ws_access(cur, row["workspace_id"], user, write=True, required_scope="kb:write")
        if row["status"] != "pending":
            raise HTTPException(status_code=400, detail=f"Item is already {row['status']}")
        cur.execute(
            "UPDATE review_queue SET status = 'rejected', reviewer_type = 'human', reviewer_id = %s, reviewed_at = now() WHERE id = %s",
            (user["sub"], id),
        )
        return {"message": "Rejected"}


@router.post("/{ws_id}/review-queue/accept-all")
def accept_all_review_items(ws_id: str, user: dict = Depends(get_current_user)):
    with db_cursor(commit=True) as cur:
        _require_ws_access(cur, ws_id, user, write=True, required_scope="kb:write")
        cur.execute("SELECT id FROM review_queue WHERE workspace_id = %s AND status = 'pending'", (ws_id,))
        ids = [row["id"] for row in cur.fetchall()]
    count = 0
    for rid in ids:
        try:
            accept_review_item(rid, user)
            count += 1
        except Exception:
            continue
    return {"accepted_count": count}


@router.post("/{ws_id}/review-queue/reject-all")
def reject_all_review_items(ws_id: str, user: dict = Depends(get_current_user)):
    with db_cursor(commit=True) as cur:
        _require_ws_access(cur, ws_id, user, write=True, required_scope="kb:write")
        cur.execute(
            "UPDATE review_queue SET status = 'rejected', reviewer_type = 'human', reviewer_id = %s, reviewed_at = now() WHERE workspace_id = %s AND status = 'pending'",
            (user["sub"], ws_id),
        )
        return {"message": "All pending items rejected"}


@router.post("/{ws_id}/review-queue/ai-prescreen")
async def run_ai_prescreen(ws_id: str, user: dict = Depends(get_current_user)):
    with db_cursor() as cur:
        _require_ws_access(cur, ws_id, user, write=True, required_scope="kb:write")
        cur.execute("SELECT id FROM review_queue WHERE workspace_id = %s AND status = 'pending' ORDER BY created_at ASC", (ws_id,))
        ids = [row["id"] for row in cur.fetchall()]
    processed = 0
    for review_id in ids:
        result = await run_ai_review_for_item(review_id)
        if result is not None:
            processed += 1
    return {"processed_count": processed}


@router.get("/{ws_id}/ai-reviewers", response_model=List[AIReviewerResponse])
def list_ai_reviewers(ws_id: str, user: dict = Depends(get_current_user)):
    with db_cursor() as cur:
        require_owner(cur, ws_id, user)
        cur.execute("SELECT * FROM ai_reviewers WHERE workspace_id = %s ORDER BY created_at ASC", (ws_id,))
        return cur.fetchall()


@router.post("/{ws_id}/ai-reviewers", response_model=AIReviewerResponse, status_code=201)
def create_ai_reviewer(ws_id: str, body: AIReviewerCreate, user: dict = Depends(get_current_user)):
    with db_cursor(commit=True) as cur:
        require_owner(cur, ws_id, user)
        reviewer_id = generate_id("airev")
        cur.execute(
            """
            INSERT INTO ai_reviewers (
                id, workspace_id, name, provider, model, system_prompt,
                auto_accept_threshold, auto_reject_threshold, enabled
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (
                reviewer_id,
                ws_id,
                body.name,
                body.provider,
                body.model,
                body.system_prompt or DEFAULT_AI_REVIEW_PROMPT,
                body.auto_accept_threshold,
                body.auto_reject_threshold,
                body.enabled,
            ),
        )
        return cur.fetchone()


@router.patch("/{ws_id}/ai-reviewers/{id}", response_model=AIReviewerResponse)
def update_ai_reviewer(ws_id: str, id: str, body: AIReviewerUpdate, user: dict = Depends(get_current_user)):
    updates = body.model_dump(exclude_none=True)
    with db_cursor(commit=True) as cur:
        require_owner(cur, ws_id, user)
        if not updates:
            cur.execute("SELECT * FROM ai_reviewers WHERE workspace_id = %s AND id = %s", (ws_id, id))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="AI reviewer not found")
            return row
        set_clause = ", ".join(f"{k} = %s" for k in updates)
        cur.execute(f"UPDATE ai_reviewers SET {set_clause} WHERE workspace_id = %s AND id = %s RETURNING *", list(updates.values()) + [ws_id, id])
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="AI reviewer not found")
        return row


@router.delete("/{ws_id}/ai-reviewers/{id}", status_code=204)
def delete_ai_reviewer(ws_id: str, id: str, user: dict = Depends(get_current_user)):
    with db_cursor(commit=True) as cur:
        require_owner(cur, ws_id, user)
        cur.execute("DELETE FROM ai_reviewers WHERE workspace_id = %s AND id = %s", (ws_id, id))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="AI reviewer not found")


# ─── C5: AI Reviewer Profiles (Rules) ─────────────────────────────────────────

from pydantic import BaseModel

class ReviewerProfile(BaseModel):
    auto_accept_threshold: float = 0.9
    auto_reject_threshold: float = 0.3
    require_human_for_types: List[str] = []

@router.get("/{ws_id}/reviewer-profiles", response_model=ReviewerProfile)
def get_reviewer_profile(ws_id: str, user: dict = Depends(get_current_user)):
    with db_cursor() as cur:
        _require_ws_access(cur, ws_id, user)
        cur.execute("SELECT settings FROM workspaces WHERE id = %s", (ws_id,))
        ws = cur.fetchone()
        settings = ws.get("settings") or {}
        profile = settings.get("reviewer_profile", {})
        return ReviewerProfile(
            auto_accept_threshold=profile.get("auto_accept_threshold", 0.9),
            auto_reject_threshold=profile.get("auto_reject_threshold", 0.3),
            require_human_for_types=profile.get("require_human_for_types", [])
        )

@router.put("/{ws_id}/reviewer-profiles", response_model=ReviewerProfile)
def update_reviewer_profile(ws_id: str, body: ReviewerProfile, user: dict = Depends(get_current_user)):
    with db_cursor(commit=True) as cur:
        _require_ws_access(cur, ws_id, user, write=True, required_scope="kb:write")
        cur.execute("SELECT settings FROM workspaces WHERE id = %s", (ws_id,))
        ws = cur.fetchone()
        settings = ws.get("settings") or {}
        settings["reviewer_profile"] = body.model_dump()
        cur.execute("UPDATE workspaces SET settings = %s WHERE id = %s", (json.dumps(settings), ws_id))
        return body

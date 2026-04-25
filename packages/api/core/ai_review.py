import json
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import HTTPException

from core.ai import AIProviderError, AIProviderUnavailable, chat_completion, record_usage, resolve_provider
from core.database import db_cursor


DEFAULT_AI_REVIEW_PROMPT = """You are an AI reviewer for a collaborative knowledge graph.
Review the proposed node change and return strict JSON:
{
  "decision": "accept" | "reject" | "comment",
  "confidence": 0.0-1.0,
  "reasoning": "short explanation"
}

Prefer accept only for well-scoped, internally consistent, low-risk changes.
Prefer reject for hallucinations, contradictions, empty edits, or destructive changes without justification.
Use comment when uncertain."""


def _parse_ai_review_response(raw: str) -> dict[str, Any]:
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("AI review response was not valid JSON")
    payload = json.loads(raw[start : end + 1])
    decision = payload.get("decision")
    confidence = float(payload.get("confidence", 0))
    reasoning = str(payload.get("reasoning", "")).strip()
    if decision not in {"accept", "reject", "comment"}:
        raise ValueError("AI review decision invalid")
    return {
        "decision": decision,
        "confidence": max(0.0, min(1.0, confidence)),
        "reasoning": reasoning,
    }


async def run_ai_review_for_item(review_id: str) -> Optional[dict[str, Any]]:
    with db_cursor() as cur:
        cur.execute("SELECT * FROM review_queue WHERE id = %s", (review_id,))
        item = cur.fetchone()
        if not item or item["status"] != "pending":
            return None

        cur.execute(
            "SELECT * FROM ai_reviewers WHERE workspace_id = %s AND enabled = TRUE ORDER BY created_at ASC",
            (item["workspace_id"],),
        )
        reviewers = cur.fetchall()

    applied_result = None
    for reviewer in reviewers:
        reviewer_id = f"airev:{reviewer['provider']}:{reviewer['model']}:{reviewer['id']}"
        try:
            resolved = resolve_provider(
                item["proposer_id"] or "",
                "extraction",
                reviewer["provider"],
                reviewer["model"],
            )
        except AIProviderUnavailable:
            continue

        messages = [
            {"role": "system", "content": reviewer["system_prompt"] or DEFAULT_AI_REVIEW_PROMPT},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "change_type": item["change_type"],
                        "target_node_id": item["target_node_id"],
                        "before_snapshot": item["before_snapshot"],
                        "after_snapshot": item["node_data"],
                        "diff_summary": item["diff_summary"],
                        "source_info": item["source_info"],
                        "proposer_type": item["proposer_type"],
                        "proposer_meta": item["proposer_meta"],
                    },
                    ensure_ascii=False,
                ),
            },
        ]

        try:
            raw, tokens = await chat_completion(resolved, messages, max_tokens=600, temperature=0.1)
            parsed = _parse_ai_review_response(raw)
            record_usage(resolved, "extraction", tokens, item["workspace_id"], item["target_node_id"])
        except (AIProviderError, ValueError):
            continue

        ai_review = {
            **parsed,
            "reviewer_id": reviewer_id,
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
        }

        with db_cursor(commit=True) as cur:
            cur.execute(
                "UPDATE review_queue SET ai_review = %s WHERE id = %s RETURNING *",
                (json.dumps(ai_review), review_id),
            )
            row = cur.fetchone()

            if parsed["decision"] == "accept" and parsed["confidence"] >= float(reviewer["auto_accept_threshold"]):
                cur.execute(
                    "UPDATE review_queue SET status = 'accepted', reviewer_type = 'ai', reviewer_id = %s, reviewed_at = now() WHERE id = %s",
                    (reviewer_id, review_id),
                )
            elif parsed["decision"] == "reject" and parsed["confidence"] >= float(reviewer["auto_reject_threshold"]):
                cur.execute(
                    "UPDATE review_queue SET status = 'rejected', reviewer_type = 'ai', reviewer_id = %s, reviewed_at = now() WHERE id = %s",
                    (reviewer_id, review_id),
                )

        applied_result = dict(row)
        break

    return applied_result


def require_owner(cur, ws_id: str, user: dict):
    cur.execute("SELECT owner_id FROM workspaces WHERE id = %s", (ws_id,))
    ws = cur.fetchone()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if ws["owner_id"] != user["sub"]:
        raise HTTPException(status_code=403, detail="Only workspace owner can manage AI reviewers")
    return ws


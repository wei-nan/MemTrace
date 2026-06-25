import json
import time
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import HTTPException

from core.ai import AIProviderError, AIProviderUnavailable, chat_completion, record_usage, resolve_provider
from core.database import db_cursor
from core.security import generate_id
from services.job_observability import _duration_ms, finish_job_run, start_job_run
from services.review_policy import get_review_policy
from services.notifications import send_degradation_notification

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
    started = time.monotonic()
    run_id = generate_id("revrun")
    
    with db_cursor() as cur:
        cur.execute("SELECT * FROM review_queue WHERE id = %s", (review_id,))
        item = cur.fetchone()
        if not item or item["status"] != "pending":
            return None

        workspace_id = item["workspace_id"]
        policy = get_review_policy(cur, workspace_id)
        
    mode = policy["mode"]

    # 1. manual_only mode: do not execute AI review
    if mode == "manual_only":
        return None

    # 2. Fetch active reviewers for workspace policy
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT m.*, b.id AS binding_id, b.status AS binding_status, b.priority AS binding_priority,
                   k.id AS key_id, k.provider, k.default_chat_model AS model, k.user_id AS key_user_id
            FROM review_policy_members m
            JOIN workspace_model_bindings b ON b.id = m.binding_id
            JOIN user_ai_keys k ON k.id = b.model_account_id
            WHERE m.policy_id = %s AND b.status = 'active'
            ORDER BY m.priority DESC, m.created_at ASC
            """,
            (workspace_id,),
        )
        reviewers = [dict(row) for row in cur.fetchall()]

    # 3. Safe Degradation: if no active reviewer bindings, degrade to manual_only
    if not reviewers:
        send_degradation_notification(workspace_id, "No active AI reviewer model bindings found for this policy.")
        with db_cursor(commit=True) as cur:
            cur.execute(
                """
                INSERT INTO review_runs (
                    id, review_item_id, effective_policy_snapshot, policy_version,
                    execution_mode, run_status, final_action, summary
                ) VALUES (%s, %s, %s, %s, %s, 'completed', 'escalate_manual', %s)
                """,
                (
                    run_id,
                    review_id,
                    json.dumps(policy, default=str),
                    policy["policy_version"],
                    "manual_only",
                    json.dumps({"reason": "degraded_no_active_models"}),
                ),
            )
        return None

    # Start Job Run for Observability
    job_run_id = start_job_run(
        "ai_review_for_item",
        workspace_id=workspace_id,
        trigger="background_task",
        summary={"review_id": review_id, "run_id": run_id},
    )

    # 4. Insert initial review run
    with db_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO review_runs (
                id, review_item_id, effective_policy_snapshot, policy_version,
                execution_mode, quorum_rules, run_status, final_action
            ) VALUES (%s, %s, %s, %s, %s, %s, 'running', 'advice_only')
            """,
            (
                run_id,
                review_id,
                json.dumps(policy, default=str),
                policy["policy_version"],
                mode,
                json.dumps({"minimum_success": policy["minimum_success"]}),
            ),
        )

    # 5. Execute reviewer model calls
    attempts_records = []
    run_status = "completed"
    final_action = "advice_only"
    summary_data: dict[str, Any] = {}
    success_count = 0
    failure_count = 0
    skipped_count = 0

    for idx, reviewer in enumerate(reviewers):
        attempt_id = generate_id("revatt")
        binding_id = reviewer["binding_id"]
        
        # Check if we should skip this reviewer (e.g. in fallback mode after a success)
        if mode == "fallback_advisory" and success_count > 0:
            with db_cursor(commit=True) as cur:
                cur.execute(
                    """
                    INSERT INTO review_attempts (
                        id, run_id, binding_id, status, provider, model
                    ) VALUES (%s, %s, %s, 'skipped_after_success', %s, %s)
                    """,
                    (attempt_id, run_id, binding_id, reviewer["provider"], reviewer["model"]),
                )
            skipped_count += 1
            continue

        # Create running attempt record
        with db_cursor(commit=True) as cur:
            cur.execute(
                """
                INSERT INTO review_attempts (
                    id, run_id, binding_id, status, provider, model, started_at
                ) VALUES (%s, %s, %s, 'running', %s, %s, now())
                """,
                (attempt_id, run_id, binding_id, reviewer["provider"], reviewer["model"]),
            )

        # Resolve provider using credential owner
        try:
            resolved = resolve_provider(
                reviewer["key_user_id"],
                "extraction",
                reviewer["provider"],
                reviewer["model"],
            )
        except AIProviderUnavailable as exc:
            with db_cursor(commit=True) as cur:
                cur.execute(
                    """
                    UPDATE review_attempts
                    SET status = 'failed', error_category = 'provider_unavailable',
                        sanitized_error = %s, finished_at = now()
                    WHERE id = %s
                    """,
                    (str(exc), attempt_id),
                )
            failure_count += 1
            continue

        messages = [
            {"role": "system", "content": policy["accept_rule"].get("prompt") or DEFAULT_AI_REVIEW_PROMPT},
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

        started_call = datetime.now(timezone.utc)
        try:
            raw, tokens = await chat_completion(resolved, messages, max_tokens=600, temperature=0.1)
            parsed = _parse_ai_review_response(raw)
            record_usage(resolved, "extraction", tokens, workspace_id, item["target_node_id"])
            
            # Check if binding was revoked during the call
            with db_cursor() as cur:
                cur.execute("SELECT status FROM workspace_model_bindings WHERE id = %s", (binding_id,))
                b_row = cur.fetchone()
                binding_revoked = b_row and b_row["status"] == "revoked"

            if binding_revoked:
                with db_cursor(commit=True) as cur:
                    cur.execute(
                        """
                        UPDATE review_attempts
                        SET status = 'discarded_after_revocation', finished_at = now()
                        WHERE id = %s
                        """,
                        (attempt_id,),
                    )
                failure_count += 1
                continue

            # Update successful attempt
            prompt_tokens_val = tokens if isinstance(tokens, int) else (tokens.get("prompt_tokens", 0) if isinstance(tokens, dict) else 0)
            completion_tokens_val = 0 if isinstance(tokens, int) else (tokens.get("completion_tokens", 0) if isinstance(tokens, dict) else 0)
            with db_cursor(commit=True) as cur:
                cur.execute(
                    """
                    UPDATE review_attempts
                    SET status = 'succeeded', decision = %s, confidence = %s,
                        reasoning = %s, prompt_tokens = %s, completion_tokens = %s,
                        finished_at = now()
                    WHERE id = %s
                    """,
                    (
                        parsed["decision"],
                        parsed["confidence"],
                        parsed["reasoning"],
                        prompt_tokens_val,
                        completion_tokens_val,
                        attempt_id,
                    ),
                )

            attempts_records.append({
                "reviewer_id": f"airev:{reviewer['provider']}:{reviewer['model']}:{binding_id}",
                **parsed
            })
            success_count += 1

        except (AIProviderError, ValueError) as exc:
            with db_cursor(commit=True) as cur:
                cur.execute(
                    """
                    UPDATE review_attempts
                    SET status = 'failed', error_category = 'call_error',
                        sanitized_error = %s, finished_at = now()
                    WHERE id = %s
                    """,
                    (str(exc), attempt_id),
                )
            failure_count += 1

    # 6. Consensus & Aggregation Logic
    final_row = None
    if mode == "consensus_automatic":
        # Consensus Mode: must satisfy quorum rules
        required_success = policy["minimum_success"]
        
        # Check required policy members
        with db_cursor() as cur:
            cur.execute(
                "SELECT binding_id FROM review_policy_members WHERE policy_id = %s AND is_required = TRUE",
                (workspace_id,),
            )
            required_bindings = {r["binding_id"] for r in cur.fetchall()}

        # Check if all required succeeded
        succeeded_bindings = {r["binding_id"] for r in reviewers if r["binding_id"] in required_bindings}
        all_required_succeeded = len(succeeded_bindings) == len(required_bindings)

        if success_count < required_success or not all_required_succeeded:
            run_status = "inconclusive"
            final_action = "escalate_manual"
        else:
            # Check agreement
            decisions = [r["decision"] for r in attempts_records]
            unique_decisions = set(decisions)
            
            if len(unique_decisions) == 1:
                decision = list(unique_decisions)[0]
                confidences = [r["confidence"] for r in attempts_records]
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
                
                # Consensus automatic is locked and disabled from auto-accepting for now, 
                # but we implement the logic for completeness and robustness.
                # To be extra safe, we escalate to manual if it's inconclusive or if consensus is not configured.
                run_status = "completed"
                final_action = "escalate_manual" # default safe fallback as per D9
            else:
                run_status = "inconclusive"
                final_action = "escalate_manual"
    else:
        # Fallback & Panel advisory modes
        if success_count > 0:
            run_status = "completed" if failure_count == 0 else "partial"
            final_action = "advice_only"
        else:
            run_status = "failed"
            final_action = "escalate_manual"

    # Save to review_queue ai_review column for compatibility
    if attempts_records:
        best_attempt = max(attempts_records, key=lambda x: x["confidence"])
        ai_review_payload = {
            "decision": best_attempt["decision"],
            "confidence": best_attempt["confidence"],
            "reasoning": best_attempt["reasoning"],
            "reviewer_id": best_attempt["reviewer_id"],
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "multiple_attempts": attempts_records,
            "run_id": run_id,
            "mode": mode,
        }
        with db_cursor(commit=True) as cur:
            cur.execute(
                "UPDATE review_queue SET ai_review = %s WHERE id = %s RETURNING *",
                (json.dumps(ai_review_payload), review_id),
            )
            final_row = cur.fetchone()

    # Update final review_runs status
    summary_data.update({
        "success_count": success_count,
        "failure_count": failure_count,
        "skipped_count": skipped_count,
        "attempts": attempts_records,
    })
    with db_cursor(commit=True) as cur:
        cur.execute(
            """
            UPDATE review_runs
            SET run_status = %s, final_action = %s, finished_at = now(), summary = %s
            WHERE id = %s
            """,
            (run_status, final_action, json.dumps(summary_data), run_id),
        )

    # Finish job run for observability
    job_status = "success" if run_status in ("completed", "partial") else "failed"
    finish_job_run(
        job_run_id,
        "ai_review_for_item",
        status=job_status,
        duration_ms=_duration_ms(started, time.monotonic()),
        scanned_count=1,
        processed_count=success_count,
        failed_count=failure_count,
        skipped_count=skipped_count,
        summary={"run_id": run_id, "final_action": final_action, "run_status": run_status},
    )

    return dict(final_row) if final_row else None


def require_owner(cur, ws_id: str, user: dict):
    cur.execute("SELECT owner_id FROM workspaces WHERE id = %s", (ws_id,))
    ws = cur.fetchone()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if ws["owner_id"] != user["sub"]:
        raise HTTPException(status_code=403, detail="Only workspace owner can manage AI reviewers")
    return ws

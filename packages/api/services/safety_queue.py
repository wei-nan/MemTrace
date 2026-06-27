"""Async safety review queue for node write events."""
from __future__ import annotations

import json
import logging
import time
from typing import Any, Optional

from core.database import db_cursor
from core.security import generate_id
from services.job_observability import _duration_ms, finish_job_run, start_job_run
from services.safety_review import classify_safety
from services.contradiction import detect_and_flag_contradictions

logger = logging.getLogger(__name__)


def _json(data: Optional[dict[str, Any]]) -> str:
    return json.dumps(data or {})


def enqueue_safety_review(
    cur,
    *,
    workspace_id: str,
    node_id: str,
    event_type: str,
    event_id: str,
    source: str = "node_event",
    risk_hint: Optional[str] = None,
    priority: int = 50,
) -> Optional[dict[str, Any]]:
    queue_id = generate_id("safeq")
    cur.execute(
        """
        INSERT INTO safety_review_queue (
            id, event_id, workspace_id, node_id, event_type, source, risk_hint, priority
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (event_id) DO NOTHING
        RETURNING *
        """,
        (queue_id, event_id, workspace_id, node_id, event_type, source, risk_hint, priority),
    )
    row = cur.fetchone()
    return dict(row) if row else None


def list_safety_review_queue(
    cur,
    *,
    workspace_id: str,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    conditions = ["workspace_id = %s"]
    params: list[Any] = [workspace_id]
    if status:
        conditions.append("status = %s")
        params.append(status)
    params.extend([limit, offset])
    cur.execute(
        f"""
        SELECT id, event_id, workspace_id, node_id, event_type, source, risk_hint,
               status, priority, attempts, max_attempts, next_run_at, lease_until,
               last_error, result, created_at, updated_at
        FROM safety_review_queue
        WHERE {' AND '.join(conditions)}
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
        """,
        params,
    )
    return [dict(row) for row in cur.fetchall()]


async def process_safety_review_queue_job(limit: int = 25) -> None:
    started = time.monotonic()

    # Resolve the safety provider once up front so we can annotate job run summaries
    ai_provider_info: dict[str, Any] = {}
    try:
        from core.ai import resolve_provider
        resolved = resolve_provider(user_id="system:safety", feature="chat")
        ai_provider_info = {
            "ai_provider": resolved.provider.__class__.__name__.lower().replace("provider", ""),
            "ai_model": resolved.model,
        }
    except Exception:
        ai_provider_info = {"ai_provider": "unavailable", "ai_model": None}

    run_id = start_job_run(
        "safety_review_queue",
        trigger="scheduler",
        summary={"limit": limit, **ai_provider_info},
    )
    processed = 0
    created = 0
    failed = 0
    skipped = 0
    try:
        with db_cursor(commit=True) as cur:
            cur.execute(
                """
                UPDATE safety_review_queue
                SET status = 'processing',
                    attempts = attempts + 1,
                    lease_until = now() + interval '5 minutes',
                    updated_at = now()
                WHERE id IN (
                    SELECT id
                    FROM safety_review_queue
                    WHERE attempts < max_attempts
                      AND (
                        (status IN ('queued', 'failed') AND next_run_at <= now())
                        OR (status = 'processing' AND lease_until IS NOT NULL AND lease_until < now())
                      )
                    ORDER BY priority ASC, next_run_at ASC, created_at ASC
                    LIMIT %s
                    FOR UPDATE SKIP LOCKED
                )
                RETURNING *
                """,
                (limit,),
            )
            jobs = [dict(row) for row in cur.fetchall()]

        for job in jobs:
            try:
                with db_cursor(commit=True) as cur:
                    cur.execute(
                        """
                        SELECT id, workspace_id, title, body, content_type, status
                        FROM memory_nodes
                        WHERE id = %s AND workspace_id = %s
                        """,
                        (job["node_id"], job["workspace_id"]),
                    )
                    node = cur.fetchone()
                    if not node or node["status"] != "active":
                        cur.execute(
                            """
                            UPDATE safety_review_queue
                            SET status = 'skipped', result = %s, updated_at = now()
                            WHERE id = %s
                            """,
                            (_json({"reason": "node_not_active"}), job["id"]),
                        )
                        skipped += 1
                        continue
                proposal = {
                    "title": node["title"],
                    "body": node["body"],
                    "content_type": node["content_type"],
                    "suggested_action": {"event_type": job["event_type"], "source": job["source"]},
                }
                classification = await classify_safety(proposal, job["workspace_id"])
                result = {"classification": classification}

                # 'undetermined' = the check could not run (e.g. safety LLM down).
                # Never mark such a node 'done'/clean — requeue with backoff, and only
                # after exhausting attempts mark it 'failed' AND surface a proposal so
                # the node is visibly admitted-but-unchecked rather than silently passed.
                if classification == "undetermined":
                    with db_cursor(commit=True) as cur:
                        if job["attempts"] >= job["max_attempts"]:
                            from services.audit_proposals import create_proposal
                            create_proposal(
                                cur=cur,
                                workspace_id=job["workspace_id"],
                                reviewer="safety_queue",
                                category="safety_undetermined",
                                target_ids=[job["node_id"]],
                                reasoning=(
                                    "Safety check could not run (provider unavailable) after "
                                    "max attempts; node was admitted WITHOUT a safety verdict."
                                ),
                                evidence={"classification": "undetermined", "event_type": job["event_type"]},
                                suggested_action={"action": "manual_safety_review", "node_id": job["node_id"]},
                                severity="mid",
                            )
                            cur.execute(
                                """
                                UPDATE safety_review_queue
                                SET status = 'failed', result = %s, lease_until = NULL, updated_at = now()
                                WHERE id = %s
                                """,
                                (_json(result), job["id"]),
                            )
                            failed += 1
                        else:
                            cur.execute(
                                """
                                UPDATE safety_review_queue
                                SET status = 'queued',
                                    next_run_at = now() + (attempts * interval '1 minute'),
                                    lease_until = NULL,
                                    result = %s,
                                    updated_at = now()
                                WHERE id = %s
                                """,
                                (_json(result), job["id"]),
                            )
                            skipped += 1
                    continue

                # Admission-time contradiction detection (runs on every active node
                # write, independent of the safety verdict). Best-effort: a failure
                # here must not block the safety verdict from being recorded.
                try:
                    with db_cursor(commit=True) as cur:
                        result["contradiction"] = await detect_and_flag_contradictions(
                            cur, job["workspace_id"], job["node_id"]
                        )
                except Exception as exc:
                    logger.warning("Contradiction detection failed: node=%s error=%s", job["node_id"], exc)

                with db_cursor(commit=True) as cur:
                    if classification in ("risky", "dangerous"):
                        from services.audit_proposals import create_proposal
                        created_prop = create_proposal(
                            cur=cur,
                            workspace_id=job["workspace_id"],
                            reviewer="safety_queue",
                            category="async_safety",
                            target_ids=[job["node_id"]],
                            reasoning=f"Async safety queue classified node as '{classification}'.",
                            evidence={"classification": classification, "event_type": job["event_type"]},
                            suggested_action={"action": "review_or_archive", "node_id": job["node_id"]},
                            severity="high" if classification == "dangerous" else "mid",
                        )
                        if created_prop:
                            result["audit_proposal_id"] = created_prop["id"]
                            created += 1
                    elif classification == "safe":
                        # 「已檢查且通過」軌跡：讓 safe 結果在 UI 可見而非靜默。
                        # 量大易吵，故走 emit_notification 的 group 機制，使用者可在
                        # notification_preferences 關閉 'safety_passed' 群組退訂。
                        from services.notifications import emit_notification
                        try:
                            emit_notification(
                                cur,
                                workspace_id=job["workspace_id"],
                                category="safety_passed",
                                severity="low",
                                title=f"安全檢查通過：{node['title']}",
                                body=f"event_type={job['event_type']}",
                                source_type="safety_queue",
                                source_id=job["event_id"],
                                target_node_id=job["node_id"],
                                group="safety_passed",
                            )
                        except Exception as exc:
                            logger.warning(
                                "safety_passed notification failed: node=%s error=%s",
                                job["node_id"], exc,
                            )
                    cur.execute(
                        """
                        UPDATE safety_review_queue
                        SET status = 'done', result = %s, lease_until = NULL, updated_at = now()
                        WHERE id = %s
                        """,
                        (_json(result), job["id"]),
                    )
                processed += 1
            except Exception as exc:
                logger.warning("Safety queue job failed: id=%s error=%s", job["id"], exc)
                failed += 1
                with db_cursor(commit=True) as cur:
                    cur.execute(
                        """
                        UPDATE safety_review_queue
                        SET status = CASE WHEN attempts >= max_attempts THEN 'failed' ELSE 'queued' END,
                            last_error = %s,
                            next_run_at = now() + (attempts * interval '1 minute'),
                            lease_until = NULL,
                            updated_at = now()
                        WHERE id = %s
                        """,
                        (str(exc), job["id"]),
                    )
        finish_job_run(
            run_id,
            "safety_review_queue",
            status="success",
            duration_ms=_duration_ms(started, time.monotonic()),
            scanned_count=len(jobs),
            processed_count=processed,
            created_count=created,
            skipped_count=skipped,
            failed_count=failed,
            summary={"limit": limit, **ai_provider_info},
        )
    except Exception as exc:
        finish_job_run(
            run_id,
            "safety_review_queue",
            status="failed",
            duration_ms=_duration_ms(started, time.monotonic()),
            processed_count=processed,
            created_count=created,
            skipped_count=skipped,
            failed_count=failed + 1,
            error=str(exc),
            summary={"limit": limit, **ai_provider_info},
        )
        raise

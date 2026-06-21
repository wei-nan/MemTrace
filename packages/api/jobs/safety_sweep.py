import os
import time
import logging
from services.job_observability import start_job_run, finish_job_run, _duration_ms
from core.database import db_cursor
from services.safety_review import classify_safety_rules

logger = logging.getLogger(__name__)

def _get_safety_sweep_interval_seconds() -> int:
    seconds = os.environ.get("SAFETY_SWEEP_INTERVAL_SECONDS")
    if seconds is not None:
        return int(seconds)
    hours = os.environ.get("SAFETY_SWEEP_INTERVAL_HOURS")
    return int(hours) * 3600 if hours is not None else 86400


SAFETY_SWEEP_INTERVAL_SECONDS = _get_safety_sweep_interval_seconds()
SAFETY_SWEEP_BATCH_SIZE       = int(os.environ.get("SAFETY_SWEEP_BATCH_SIZE", 500))

def _sweep_workspace(cur, workspace_id: str, batch_size: int) -> dict:
    # Read progress offset
    cur.execute("SELECT value FROM system_state WHERE key = %s",
                (f"safety_sweep_offset:{workspace_id}",))
    row = cur.fetchone()
    offset = int(row["value"]) if row else 0

    # Fetch active procedural nodes
    cur.execute("""
        SELECT id, title, body, author FROM memory_nodes
        WHERE workspace_id = %s AND content_type = 'procedural' AND status = 'active'
        ORDER BY id
        LIMIT %s OFFSET %s
    """, (workspace_id, batch_size, offset))
    nodes = cur.fetchall()

    flagged = 0
    for node in nodes:
        combined = f"{node['title']}\n{node['body']}"
        classification = classify_safety_rules(combined)

        if classification in ("risky", "dangerous"):
            # Check if an audit proposal already exists for this node to avoid duplication (idempotency)
            cur.execute(
                """
                SELECT id FROM audit_proposals
                WHERE workspace_id = %s AND reviewer = 'safety_sweep' AND %s = ANY(target_ids)
                LIMIT 1
                """,
                (workspace_id, node["id"])
            )
            if cur.fetchone():
                continue

            from services.audit_proposals import create_proposal
            create_proposal(
                cur=cur,
                workspace_id=workspace_id,
                reviewer="safety_sweep",
                category="historical_safety",
                target_ids=[node["id"]],
                reasoning=f"Historical node sweep flagged this node as '{classification}'. Contains potential system modification or destructive commands.",
                evidence={"classification": classification, "snippet": node["body"][:200]},
                suggested_action={"action": "review_or_archive", "node_id": node["id"]},
                severity="high" if classification == "dangerous" else "mid"
            )
            flagged += 1

    # Update offset; if the batch has fewer nodes than batch_size, it means we scanned all nodes, reset to 0
    next_offset = offset + len(nodes) if len(nodes) == batch_size else 0
    cur.execute("""
        INSERT INTO system_state (key, value) VALUES (%s, %s)
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now()
    """, (f"safety_sweep_offset:{workspace_id}", str(next_offset)))

    return {"scanned": len(nodes), "flagged": flagged}

def safety_sweep_job() -> None:
    started = time.monotonic()
    run_id = start_job_run("safety_sweep", trigger="scheduler",
                           summary={"batch_size": SAFETY_SWEEP_BATCH_SIZE})
    total_scanned = total_flagged = failed = 0
    try:
        with db_cursor() as cur:
            cur.execute("SELECT id FROM workspaces WHERE status = 'active'")
            workspaces = [r["id"] for r in cur.fetchall()]

        for ws_id in workspaces:
            ws_run_id = start_job_run("safety_sweep", workspace_id=ws_id,
                                      trigger="scheduler", update_heartbeat=False)
            ws_started = time.monotonic()
            try:
                with db_cursor(commit=True) as cur:
                    result = _sweep_workspace(cur, ws_id, SAFETY_SWEEP_BATCH_SIZE)
                total_scanned += result["scanned"]
                total_flagged += result["flagged"]
                finish_job_run(ws_run_id, "safety_sweep", status="success",
                               duration_ms=_duration_ms(ws_started, time.monotonic()),
                               scanned_count=result["scanned"], created_count=result["flagged"],
                               update_heartbeat=False)
            except Exception as exc:
                failed += 1
                logger.exception("Error during safety sweep for workspace %s: %s", ws_id, exc)
                finish_job_run(ws_run_id, "safety_sweep", status="failed",
                               error=str(exc), update_heartbeat=False)

        finish_job_run(run_id, "safety_sweep", status="success" if failed == 0 else "failed",
                       duration_ms=_duration_ms(started, time.monotonic()),
                       scanned_count=total_scanned, created_count=total_flagged, failed_count=failed)
    except Exception as exc:
        logger.exception("Global safety sweep job error: %s", exc)
        finish_job_run(run_id, "safety_sweep", status="failed", error=str(exc))

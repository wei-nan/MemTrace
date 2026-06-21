"""
services/contradiction.py — admission-time contradiction detection.

Generalizes the qa-archiver-only contradiction check (nodes.py) to every node
write: when a new factual/preference node semantically conflicts with an existing
active node, we mark THIS node 'conflicted', create a contradicts edge, and raise
an audit proposal. All detected contradictions are flagged; conflicts against a
high-trust (>0.9) node are escalated to high severity (MCP safety boundary).

Decision (2026-06-20): admit-but-conflicted (fail-open write, but the conflicting
node cannot masquerade as truth until a human resolves it via resolve_conflict).
"""
from __future__ import annotations

import json
import logging
import re

from core.ai import resolve_provider, chat_completion, AIProviderUnavailable
from core.security import generate_id
from services.audit_proposals import create_proposal

logger = logging.getLogger(__name__)

# Candidates above this cosine similarity are sent to the LLM for a contradiction verdict.
CONTRADICTION_SIM_THRESHOLD = 0.80
CONTRADICTION_CANDIDATES = 5
HIGH_TRUST = 0.9


def _clean_json(raw: str) -> dict:
    return json.loads(re.sub(r"```json|```", "", raw).strip())


async def detect_and_flag_contradictions(cur, ws_id: str, node_id: str) -> dict:
    """
    Returns a summary dict with status in
    {'done','skipped','undetermined'} and (for 'done') a 'flagged' count.
    Best-effort + fail-open: never raises into the caller's processing loop.
    """
    cur.execute(
        """
        SELECT id, title, body, content_type, embedding, status, trust_score
        FROM memory_nodes
        WHERE id = %s AND workspace_id = %s
        """,
        (node_id, ws_id),
    )
    node = cur.fetchone()
    if not node or node["status"] != "active":
        return {"status": "skipped", "reason": "node_not_active"}
    if node["content_type"] not in ("factual", "preference"):
        return {"status": "skipped", "reason": "not_checkable_type"}
    if not node["embedding"]:
        return {"status": "skipped", "reason": "no_embedding"}

    try:
        resolved = resolve_provider(user_id="system:safety", feature="chat")
    except (AIProviderUnavailable, Exception) as e:
        logger.warning("Contradiction check could not run (provider unavailable): %s", e)
        return {"status": "undetermined", "reason": "provider_unavailable"}

    cur.execute(
        """
        SELECT id, title, body, trust_score,
               (1 - (embedding <=> %s::vector)) AS similarity
        FROM memory_nodes
        WHERE workspace_id = %s
          AND id != %s
          AND status = 'active'
          AND content_type IN ('factual', 'preference')
          AND embedding IS NOT NULL
          AND (1 - (embedding <=> %s::vector)) >= %s
        ORDER BY similarity DESC
        LIMIT %s
        """,
        (node["embedding"], ws_id, node_id, node["embedding"], CONTRADICTION_SIM_THRESHOLD, CONTRADICTION_CANDIDATES),
    )
    candidates = cur.fetchall()

    flagged = 0
    for cand in candidates:
        # Skip if a contradicts edge already exists in either direction.
        cur.execute(
            """
            SELECT 1 FROM edges
            WHERE workspace_id = %s AND relation = 'contradicts' AND status = 'active'
              AND ((from_id = %s AND to_id = %s) OR (from_id = %s AND to_id = %s))
            LIMIT 1
            """,
            (ws_id, node_id, cand["id"], cand["id"], node_id),
        )
        if cur.fetchone():
            continue

        try:
            prompt = (
                "判斷以下兩段陳述是否互相矛盾：\n"
                f"A: {node['body']}\nB: {cand['body']}\n\n"
                "請以 JSON 格式回傳，包含 'contradicts' (boolean) 與 'reason' (string)。"
            )
            raw, _ = await chat_completion(resolved, [{"role": "user", "content": prompt}])
            res = _clean_json(raw)
        except Exception as exc:
            logger.warning("Contradiction LLM judgment failed (node=%s cand=%s): %s", node_id, cand["id"], exc)
            continue

        if not res.get("contradicts"):
            continue

        target_trust = float(cand["trust_score"] or 0.0)
        reason = res.get("reason")

        cur.execute(
            """
            INSERT INTO edges (id, workspace_id, from_id, to_id, relation, weight, status, metadata)
            VALUES (%s, %s, %s, %s, 'contradicts', 0.5, 'active', %s)
            ON CONFLICT DO NOTHING
            """,
            (generate_id("edge"), ws_id, node_id, cand["id"], json.dumps({"reason": reason})),
        )
        # Decision: admit-but-conflicted — the new node stays in the graph but cannot
        # be treated as truth until resolved.
        cur.execute(
            "UPDATE memory_nodes SET status = 'conflicted' WHERE id = %s AND workspace_id = %s",
            (node_id, ws_id),
        )
        create_proposal(
            cur,
            workspace_id=ws_id,
            reviewer="contradiction_detector",
            category="contradiction",
            target_ids=[node_id, cand["id"]],
            reasoning=(
                f"新節點與既有節點「{cand['title']}」(trust={target_trust:.2f}) 內容矛盾："
                f"{reason}。已標記新節點 conflicted 並建立 contradicts edge。"
            ),
            evidence={"reason": reason, "target_trust": target_trust, "similarity": float(cand["similarity"])},
            suggested_action={"action": "resolve_conflict", "node_id": node_id, "contradicts_with": cand["id"]},
            severity="high" if target_trust > HIGH_TRUST else "mid",
        )
        flagged += 1

    return {"status": "done", "flagged": flagged, "candidates": len(candidates)}

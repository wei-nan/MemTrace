import re
import json
import logging
import time
from typing import Literal, Dict, Any, Optional

from core.database import db_cursor
from core.ai import resolve_provider, chat_completion, AIProviderUnavailable
from services.job_observability import _duration_ms, finish_job_run, start_job_run

logger = logging.getLogger(__name__)

# Compile dangerous patterns (deny-list)
DANGEROUS_PATTERNS = [
    r"\brm\s+-rf\b",
    r"\bdrop\s+(?:table|database|schema)\b",
    r"\btruncate\s+(?:table|database)\b",
    r"\bmkfs\b",
    r"\bdd\s+if=",
    r">\s*/dev/(?:null|sd|hd|zero)",
    r"\bchmod\s+(?:-r\s+)?777\b",
    r"\bcurl\s+.*\s*\|\s*(?:bash|sh)\b",
    r"\bwget\s+.*\s*\|\s*(?:bash|sh)\b",
    r"\beval\s+\(.*curl.*\)",
    r"\bsh\s+<.*\bcurl\b",
]

# Compile risky patterns (system modifying)
RISKY_PATTERNS = [
    r"\bsudo\b",
    r"\bsystemctl\b",
    r"\bservice\s+\w+\s+(?:start|stop|restart|reload|enable|disable)\b",
    r"\bapt-get\b",
    r"\byum\b",
    r"\bpip\s+install\b",
    r"\bnpm\s+install\b",
    r"\bdocker\s+(?:run|exec|stop|rm)\b",
    r"\bdocker-compose\b",
    r"\breboot\b",
    r"\bshutdown\b",
    r"\binit\s+[0-6]\b",
    r"\bpasswd\b",
    r"\buserdel\b",
    r"\bgroupdel\b",
    r"\bchown\b",
    r"\bchmod\b",
    r"\bkill\s+-[0-9]+\b",
    r"\bkillall\b",
]

def classify_safety_rules(text: str) -> Optional[Literal['risky', 'dangerous']]:
    """
    Perform fast rule-based checks on the text.
    Returns 'dangerous' or 'risky' if matched, otherwise None.
    """
    # Normalize text: lowercase and strip extra spacing
    normalized = text.lower()
    
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, normalized):
            logger.warning(f"Safety Rule Triggered (dangerous): {pattern}")
            return "dangerous"
            
    for pattern in RISKY_PATTERNS:
        if re.search(pattern, normalized):
            logger.info(f"Safety Rule Triggered (risky): {pattern}")
            return "risky"
            
    return None

async def classify_safety(proposal: dict, ws_id: str) -> Literal['safe', 'risky', 'dangerous']:
    """
    Classify a proposed consult change or node/edge payload.
    Returns: 'safe', 'risky', or 'dangerous' (fail-closed).
    """
    title = proposal.get("title") or ""
    body = proposal.get("body") or ""
    content_type = proposal.get("content_type") or "factual"
    suggested_action = proposal.get("suggested_action") or {}
    
    # Check if the proposal only recommends/points to existing nodes (always safe)
    # If the proposal has no new body content or is pure linkage, it is safe.
    if not body and not title and suggested_action:
        return "safe"
        
    combined_text = f"{title}\n{body}"
    
    # 1. Rule-based checks (Dangerous & Risky deny-lists)
    rule_result = classify_safety_rules(combined_text)
    if rule_result == "dangerous":
        return "dangerous"
    if rule_result == "risky":
        return "risky"
        
    # If the proposal is not procedural (e.g. factual, preference), and has no commands, it is likely safe.
    if content_type != "procedural" and not any(cmd in combined_text for cmd in ["$", "sudo", "bin", "sh", "run"]):
        return "safe"
        
    # 2. LLM-assisted Safety Check
    try:
        resolved = resolve_provider(user_id="system:safety", feature="chat")
    except (AIProviderUnavailable, Exception) as e:
        logger.warning(f"system:safety LLM provider unavailable: {e}. Falling back to rules (fail-closed).")
        # In case LLM is unavailable:
        # For procedural nodes, since we can't verify safety via LLM, treat as risky to be safe.
        if content_type == "procedural":
            return "risky"
        return "safe"
        
    system_prompt = (
        "You are a strict security auditor. Categorize the given knowledge item/command proposal into one of three classifications:\n"
        "1. 'safe': The text is pure information, background explanation, or instructions without any system-changing shell commands/scripts.\n"
        "2. 'risky': The text contains system commands that modify system configurations, packages, services, or run code, but are NOT destructive or malicious.\n"
        "3. 'dangerous': The text contains commands or steps that are destructive (e.g., rm -rf, drop tables, credential theft, system formatting, privilege escalation).\n\n"
        "Respond ONLY in valid JSON format: {\"classification\": \"safe\" | \"risky\" | \"dangerous\", \"reason\": \"...\"}"
    )
    
    user_msg = f"Proposal Title: {title}\nProposal Body:\n{body}"
    
    try:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg}
        ]
        
        # High temperature is bad for classification, lock at 0.1
        response_text, _ = await chat_completion(
            resolved=resolved,
            messages=messages,
            max_tokens=256,
            temperature=0.1
        )
        
        # Parse JSON from response
        # Clean potential markdown block formatting
        cleaned_response = re.sub(r"```json|```", "", response_text).strip()
        data = json.loads(cleaned_response)
        classification = data.get("classification", "risky")
        
        if classification not in ("safe", "risky", "dangerous"):
            classification = "risky"
            
        # Ensure that LLM does not override rules (if we classified as risky/dangerous earlier, we shouldn't reach here anyway, but safeguard it)
        return classification
    except Exception as e:
        logger.error(f"Error during LLM safety classification: {e}. Defaulting to risky (fail-closed).")
        return "risky"

def run_historical_safety_sweep(cur, limit: int = 100) -> Dict[str, Any]:
    """
    Sweep existing procedural nodes containing commands and flag them into audit_proposals (propose-only).
    Does not delete/modify nodes directly (D3).
    """
    started = time.monotonic()
    run_id = start_job_run(
        "safety_sweep",
        trigger="manual_or_maintenance",
        summary={"limit": limit},
    )
    flagged_count = 0
    nodes = []
    # Fetch active procedural nodes
    try:
        cur.execute(
            """
            SELECT id, workspace_id, title, body, author
            FROM memory_nodes
            WHERE content_type = 'procedural' AND status = 'active'
            LIMIT %s
            """,
            (limit,)
        )
        nodes = cur.fetchall()

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
                    (node["workspace_id"], node["id"])
                )
                if cur.fetchone():
                    continue

                from services.audit_proposals import create_proposal
                create_proposal(
                    cur=cur,
                    workspace_id=node["workspace_id"],
                    reviewer="safety_sweep",
                    category="historical_safety",
                    target_ids=[node["id"]],
                    reasoning=f"Historical node sweep flagged this node as '{classification}'. Contains potential system modification or destructive commands.",
                    evidence={"classification": classification, "snippet": node["body"][:200]},
                    suggested_action={"action": "review_or_archive", "node_id": node["id"]},
                    severity="high" if classification == "dangerous" else "mid"
                )
                flagged_count += 1

        result = {"scanned": len(nodes), "flagged": flagged_count}
        finish_job_run(
            run_id,
            "safety_sweep",
            status="success",
            duration_ms=_duration_ms(started, time.monotonic()),
            scanned_count=len(nodes),
            created_count=flagged_count,
            summary=result,
        )
        return result
    except Exception as exc:
        finish_job_run(
            run_id,
            "safety_sweep",
            status="failed",
            duration_ms=_duration_ms(started, time.monotonic()),
            scanned_count=len(nodes),
            created_count=flagged_count,
            failed_count=1,
            error=str(exc),
            summary={"limit": limit},
        )
        raise

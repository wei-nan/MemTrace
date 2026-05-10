import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from core.ai import strip_fences
from services.nodes import propose_change as _propose_change

logger = logging.getLogger(__name__)

def parse_ai_proposals(text: str) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Extract JSON proposals from AI response text.
    Returns (cleaned_text, list_of_proposals).
    """
    answer = text
    proposals = []
    
    # Try to find JSON block
    if "```json" in text:
        parts = text.split("```json")
        answer = parts[0].strip()
        json_part = parts[1].split("```")[0].strip()
        try:
            proposals = json.loads(json_part)
            if not isinstance(proposals, list):
                if isinstance(proposals, dict):
                    proposals = [proposals]
                else:
                    proposals = []
        except Exception as e:
            logger.warning(f"Failed to parse AI proposals JSON: {e}")
            proposals = []
    
    return answer, proposals

def apply_ai_proposals_to_db(
    cur, 
    ws_id: str, 
    proposals: List[Dict[str, Any]], 
    original_query: str = ""
) -> List[Dict[str, Any]]:
    """
    Save AI proposals to the review queue.
    Returns a list of created review items info.
    """
    results = []
    for p in proposals:
        op = p.get("operation", "update")
        if op not in ("create", "update", "delete"):
            op = "update"
            
        try:
            rid = _propose_change(
                cur,
                ws_id,
                op,
                p.get("target_node_ids", [None])[0],
                p.get("proposed"),
                "ai",
                "chat_assistant",
                proposer_meta={"source": "chat", "original_query": original_query},
                source_info=f"AI Chat Proposal: {p.get('reason', 'No reason provided')}"
            )
            results.append({
                "review_queue_id": rid, 
                "operation": op, 
                "reason": p.get("reason")
            })
        except Exception as e:
            logger.error(f"Failed to save AI proposal: {e}")
            
    return results

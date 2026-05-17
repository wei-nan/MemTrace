import json
import logging
from typing import Dict

from core.ai import chat_completion, resolve_provider, RESTRUCTURE_SYSTEM, strip_fences
from core.database import db_cursor

logger = logging.getLogger(__name__)


CHAR_THRESHOLD = 600

async def estimate_complexity(node_data: Dict, ws_id: str, user_id: str, threshold: int = 600) -> Dict:
    """
    P4.8-S9-3b: Estimate if a node is too complex/large and suggest a split if so.
    Uses RESTRUCTURE_SYSTEM prompt for the decomposition proposal.
    """
    body_zh = node_data.get("body_zh") or ""
    body_en = node_data.get("body_en") or ""
    total_chars = len(body_zh) + len(body_en)
    
    if total_chars < threshold:
        return {"is_complex": False, "char_count": total_chars}
    
    # Resolve provider for the specific workspace
    with db_cursor() as cur:
        cur.execute("SELECT extraction_provider FROM workspaces WHERE id = %s", (ws_id,))
        ws_row = cur.fetchone()
    ws_prov = ws_row["extraction_provider"] if ws_row else None
    
    try:
        resolved = resolve_provider(user_id, "extraction", preferred_provider=ws_prov)
        
        # Prepare content for LLM
        node_json = json.dumps([{
            "id": node_data.get("id"),
            "title_zh": node_data.get("title_zh"),
            "title_en": node_data.get("title_en"),
            "body_zh": body_zh,
            "body_en": body_en,
            "content_type": node_data.get("content_type")
        }], ensure_ascii=False)
        
        messages = [
            {"role": "system", "content": RESTRUCTURE_SYSTEM},
            {"role": "user", "content": f"Analyze this node for potential split:\n{node_json}"}
        ]
        
        response_text, tokens = await chat_completion(resolved, messages)
        json_text = strip_fences(response_text)
        proposals = json.loads(json_text)
        
        # Filter for split operations
        split_proposals = [p for p in proposals if p.get("operation") == "split"]
        
        return {
            "is_complex": len(split_proposals) > 0,
            "char_count": total_chars,
            "split_proposals": split_proposals
        }
    except Exception as e:
        logger.error(f"Error estimating complexity for node {node_data.get('id')}: {e}")
    
    return {"is_complex": True, "char_count": total_chars, "split_proposals": []}


import logging
from typing import List, Optional
import json
from core.database import db_cursor
from core.security import generate_id
from core.ai import resolve_provider, chat_completion, strip_fences
from services.nodes import create_node_full_with_dedup

logger = logging.getLogger(__name__)

async def generate_cluster_summary(cur, ws_id: str, node_ids: List[str], user_id: str) -> Optional[str]:
    """
    S4-T01: Generate a hierarchical summary for a group of nodes.
    Creates a new 'summary' node and links it to the members via 'extends'.
    """
    if not node_ids:
        return None
        
    # 1. Fetch node content
    cur.execute(
        "SELECT id, title_en, title_zh, body_en, body_zh FROM memory_nodes WHERE id = ANY(%s) AND workspace_id = %s",
        (node_ids, ws_id)
    )
    nodes = cur.fetchall()
    if not nodes:
        return None
        
    # 2. Prepare prompt for LLM
    context = ""
    for n in nodes:
        context += f"Node ID: {n['id']}\nTitle (EN): {n['title_en']}\nTitle (ZH): {n['title_zh']}\nBody (EN): {n['body_en']}\nBody (ZH): {n['body_zh']}\n---\n"
        
    prompt = f"""
You are a knowledge architect. Below is a group of related knowledge nodes from a graph.
Please synthesize them into a concise, high-level summary node.

GUIDELINES:
1. Provide a title that encompasses the entire cluster.
2. The body should be a coherent summary that integrates the information from all nodes.
3. Preserve key technical terms.
4. Return the result in JSON format with fields: title_en, title_zh, body_en, body_zh.

CONTEXT:
{context}
"""

    try:
        # Use a reasoning model if available, otherwise default
        resolved = resolve_provider(user_id, "chat")
        messages = [{"role": "user", "content": prompt}]
        response_text, _ = await chat_completion(resolved, messages)
        data = json.loads(strip_fences(response_text))
        
        # 3. Create the summary node
        node_payload = {
            "title_en": data.get("title_en", "Summary Node"),
            "title_zh": data.get("title_zh", "摘要節點"),
            "body_en": data.get("body_en", ""),
            "body_zh": data.get("body_zh", ""),
            "content_type": "context",
            "source_type": "ai",
            "tags": ["summary", "hierarchical"],
            "trust_score": 0.9
        }
        
        # Create the node (bypassing dedup for summary nodes as they are unique to the cluster)
        new_node, _, _ = await create_node_full_with_dedup(cur, ws_id, node_payload, {"sub": user_id}, force_create=True)
        new_id = new_node["id"]
        
        # 4. Link summary to all cluster members via 'extends' (Summary extends the details)
        # Or better: Members 'extends' the Summary? 
        # Usually, Summary is the root, and details extend it.
        # So: Member -> extends -> Summary
        for nid in node_ids:
            cur.execute(
                """
                INSERT INTO edges (id, workspace_id, from_id, to_id, relation, weight)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
                """,
                (generate_id("edge"), ws_id, nid, new_id, "extends", 0.9)
            )
            
        return new_id
        
    except Exception as e:
        logger.error(f"Failed to generate cluster summary: {e}")
        return None

async def find_clusters_by_tag(cur, ws_id: str, min_nodes: int = 3) -> List[List[str]]:
    """
    Find groups of nodes that share the same tag.
    """
    cur.execute(
        "SELECT id, tags FROM memory_nodes WHERE workspace_id = %s AND status = 'active'",
        (ws_id,)
    )
    rows = cur.fetchall()
    
    tag_map = {}
    for r in rows:
        for tag in (r["tags"] or []):
            if tag not in tag_map: tag_map[tag] = []
            tag_map[tag].append(r["id"])
            
    clusters = [ids for tag, ids in tag_map.items() if len(ids) >= min_nodes and tag not in ["summary", "hierarchical"]]
    return clusters

async def complement_languages(cur, ws_id: str, node_id: str, user_id: str) -> bool:
    """
    S4-T02: Reconcile ZH/EN content. If one is missing, use AI to translate/generate.
    """
    cur.execute(
        "SELECT title_zh, title_en, body_zh, body_en FROM memory_nodes WHERE id = %s AND workspace_id = %s",
        (node_id, ws_id)
    )
    node = cur.fetchone()
    if not node: return False
    
    # Check if anything is missing
    missing_en = not node["title_en"] or not node["body_en"]
    missing_zh = not node["title_zh"] or not node["body_zh"]
    
    if not missing_en and not missing_zh:
        return True # Nothing to do
        
    prompt = f"""
You are a translation and localization expert.
Below is a knowledge node with content in only one language (or partially missing).
Please provide the missing parts to ensure the node has complete ZH (Traditional Chinese) and EN (English) content.

CURRENT CONTENT:
Title (ZH): {node['title_zh']}
Title (EN): {node['title_en']}
Body (ZH): {node['body_zh']}
Body (EN): {node['body_en']}

Return the result in JSON format with fields: title_en, title_zh, body_en, body_zh.
Maintain the same meaning and technical accuracy.
"""

    try:
        resolved = resolve_provider(user_id, "chat")
        messages = [{"role": "user", "content": prompt}]
        response_text, _ = await chat_completion(resolved, messages)
        data = json.loads(strip_fences(response_text))
        
        cur.execute(
            """
            UPDATE memory_nodes 
            SET title_en = %s, title_zh = %s, body_en = %s, body_zh = %s, updated_at = NOW()
            WHERE id = %s AND workspace_id = %s
            """,
            (data["title_en"], data["title_zh"], data["body_en"], data["body_zh"], node_id, ws_id)
        )
        return True
    except Exception as e:
        logger.error(f"Failed to complement languages for {node_id}: {e}")
        return False

async def suggest_missing_edges(cur, ws_id: str, threshold: float = 0.85) -> List[dict]:
    """
    S4-T03: Find node pairs with high similarity but no existing edge.
    Returns a list of suggested edges.
    """
    # This is expensive for large KBs. For now, we do a top-N cross-comparison.
    cur.execute(
        "SELECT id, embedding FROM memory_nodes WHERE workspace_id = %s AND embedding IS NOT NULL AND status = 'active' LIMIT 200",
        (ws_id,)
    )
    nodes = cur.fetchall()
    
    suggestions = []
    # O(N^2) comparison - limited to 200 nodes for demonstration
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            # In SQL, similarity = 1 - (e1 <=> e2)
            # We'll use a simpler approach: fetch similarities from DB for each node
            pass
            
    # Better approach: for each node, find top neighbors and check if edges exist
    for node in nodes:
        cur.execute(
            """
            SELECT id, (1 - (embedding <=> %s::vector)) AS similarity
            FROM memory_nodes
            WHERE workspace_id = %s AND id != %s AND embedding IS NOT NULL AND status = 'active'
              AND (1 - (embedding <=> %s::vector)) >= %s
            ORDER BY similarity DESC LIMIT 5
            """,
            (node["embedding"], ws_id, node["id"], node["embedding"], threshold)
        )
        neighbors = cur.fetchall()
        for nb in neighbors:
            # Check if edge already exists
            cur.execute(
                "SELECT 1 FROM edges WHERE workspace_id = %s AND ((from_id = %s AND to_id = %s) OR (from_id = %s AND to_id = %s))",
                (ws_id, node["id"], nb["id"], nb["id"], node["id"])
            )
            if not cur.fetchone():
                suggestions.append({
                    "from_id": node["id"],
                    "to_id": nb["id"],
                    "relation": "similar_to",
                    "similarity": nb["similarity"]
                })
                
    return suggestions[:20] # Return top 20 suggestions

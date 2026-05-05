from typing import Optional
from core.security import generate_id

def get_or_create_agent_node(ws_id: str, cur) -> str:
    """取得 workspace 的 agent 代表節點，不存在則建立 (P4.5-1B-0)。"""
    cur.execute("SELECT agent_node_id FROM workspaces WHERE id = %s", (ws_id,))
    row = cur.fetchone()
    if row and row["agent_node_id"]:
        return row["agent_node_id"]
    
    agent_id = generate_id("node")
    cur.execute("""
        INSERT INTO memory_nodes
            (id, workspace_id, title_zh, title_en, content_type, status,
             source_type, dim_author_rep, author, visibility, content_format)
        VALUES (%s, %s, %s, %s, 'context', 'active', 'mcp', 0.0, 'system', 'private', 'plain')
    """, (agent_id, ws_id, "(Workspace Agent)", "(Workspace Agent)"))
    
    cur.execute("UPDATE workspaces SET agent_node_id = %s WHERE id = %s", (agent_id, ws_id))
    return agent_id

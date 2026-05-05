from core.security import generate_id, compute_signature

def get_or_create_agent_node(ws_id: str, cur) -> str:
    """取得 workspace 的 agent 代表節點，不存在則建立 (P4.5-1B-0)。"""
    cur.execute("SELECT agent_node_id FROM workspaces WHERE id = %s", (ws_id,))
    row = cur.fetchone()
    if row and row["agent_node_id"]:
        return row["agent_node_id"]
    
    agent_id = generate_id("node")
    title = "(Workspace Agent)"
    # P4.5-2B-1: Compute signature for agent node
    sig = compute_signature(
        {"en": title, "zh": title},
        {"type": "context", "format": "plain", "body": {"en": "", "zh": ""}},
        [],
        "system"
    )
    
    cur.execute("""
        INSERT INTO memory_nodes
            (id, workspace_id, title_zh, title_en, content_type, status,
             source_type, dim_author_rep, author, visibility, content_format, signature)
        VALUES (%s, %s, %s, %s, 'context', 'active', 'mcp', 0.0, 'system', 'private', 'plain', %s)
    """, (agent_id, ws_id, title, title, sig))
    
    cur.execute("UPDATE workspaces SET agent_node_id = %s WHERE id = %s", (agent_id, ws_id))
    return agent_id

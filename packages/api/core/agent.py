from core.security import generate_id, compute_signature

def get_or_create_agent_node(ws_id: str, cur) -> str:
    """取得 workspace 的 agent 代表節點，不存在則建立 (P4.5-1B-0)。

    agent node 是系統 actor，不是知識內容（node_class='system_actor'），其生命週期
    不受 Decay 歸檔管轄。若既有節點曾被誤歸檔，這裡將它恢復為 active，而不是沿用
    archived node——否則它錨定的大量 queried_via_mcp telemetry 邊會被資料品質檢查
    誤判為「指向已停用節點」的廢棄連結（mem_f2314f73 / mem_819815b4）。
    """
    cur.execute("SELECT agent_node_id FROM workspaces WHERE id = %s", (ws_id,))
    row = cur.fetchone()
    if row and row["agent_node_id"]:
        agent_id = row["agent_node_id"]
        # 既有 agent node：確保它仍是 active 的系統 actor；被誤歸檔則恢復。
        cur.execute(
            "UPDATE memory_nodes "
            "SET status = 'active', archived_at = NULL, node_class = 'system_actor' "
            "WHERE id = %s AND workspace_id = %s "
            "AND (status <> 'active' OR node_class <> 'system_actor')",
            (agent_id, ws_id),
        )
        return agent_id

    agent_id = generate_id("node")
    title = "(Workspace Agent)"
    # P4.5-2B-1: Compute signature for agent node
    sig = compute_signature(
        title,
        {"type": "context", "format": "plain", "body": ""},
        [],
        "system"
    )

    cur.execute("""
        INSERT INTO memory_nodes
            (id, workspace_id, title, body, content_type, status, node_class,
             source_type, dim_author_rep, author, visibility, content_format, signature)
        VALUES (%s, %s, %s, '', 'context', 'active', 'system_actor', 'mcp', 0.0, 'system', 'private', 'plain', %s)
    """, (agent_id, ws_id, title, sig))

    cur.execute("UPDATE workspaces SET agent_node_id = %s WHERE id = %s", (agent_id, ws_id))
    return agent_id

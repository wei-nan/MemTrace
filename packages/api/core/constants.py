# 共用常數（相似度門檻）
# Phase 4.5 常數

# search miss 時避免為相同主題重複建 gap 節點
SEARCH_MISS_DEDUP = 0.92

# inquiry 節點命中 FAQ 快取的最低相似度
FAQ_CACHE_HIT = 0.88

# 比對新答案與既有節點是否矛盾的候選門檻
CONTRADICTION_CHECK = 0.85

# 兩個 inquiry 節點建立 `similar_to` 邊的最低相似度
SIMILAR_INQUIRY_LINK = 0.70

# ─── Relation / Content Type 合法值（單一來源）────────────────────────────────
# 所有 router 與 service 應從此 import，不得在本地重複定義
VALID_RELATIONS: frozenset = frozenset({
    "depends_on",
    "extends",
    "related_to",
    "contradicts",
    "answered_by",
    "similar_to",
    "queried_via_mcp",  # DEPRECATED: retrieval telemetry no longer written; node-level
                        # MCP access now lives in traversal_log keyed by real actor_id.
                        # Retained for backward compatibility (relation_type DB enum value
                        # cannot be dropped). See ws_spec_plan/mem_ea840fad.
    "extracted_from",   # P61-T01: knowledge node → document node
    "proceeds_to",      # Phase 6.3: conditional next step in troubleshooting graph
})

# ─── Edge class（語意 / 系統 / telemetry）──────────────────────────────────────
# 知識圖只放知識：telemetry（查詢痕跡，如 queried_via_mcp）不是決策脈絡，不應污染
# data-quality checker、top_edges 與預設 traversal。relation → edge_class 的單一來源。
# 註：queried_via_mcp 已 deprecated 且不再寫入（node 級存取改記 traversal_log）；此映射
# 保留以正確分類任何殘存/外部歷史邊。見 ws_spec_plan/mem_ea840fad。
TELEMETRY_RELATIONS: frozenset = frozenset({"queried_via_mcp"})

# ─── 對稱關係（防反向重複）──────────────────────────────────────────────────────
# 這些關係語意上無方向（a related_to b == b related_to a），但邊存成有向，
# 唯一鍵 (from_id, to_id, relation) 擋不住反向。create_edge 對這些關係額外檢查
# 反向是否已存在，避免同一對節點被存成雙向重複邊。
# contradicts 雖也對稱，但其仲裁邏輯依賴 from/to 方向，故不納入。
SYMMETRIC_RELATIONS: frozenset = frozenset({"related_to", "similar_to"})

# ─── 具體/有向關係（生成紀律）──────────────────────────────────────────────────
# 這些關係帶明確語意，優於泛用 related_to。若同一對節點已有其中任一關係，
# create_edge 會拒絕再補一條 related_to（避免在具體邊上疊冗餘的泛用邊）。
SPECIFIC_RELATIONS: frozenset = frozenset({
    "depends_on", "extends", "answered_by", "contradicts", "proceeds_to", "extracted_from",
})


def edge_class_for_relation(relation: str) -> str:
    """Map a relation to its edge_class. Telemetry edges record retrieval history,
    not knowledge semantics, and are routed differently by checkers/top_edges/traversal."""
    if relation in TELEMETRY_RELATIONS:
        return "telemetry"
    return "semantic"


VALID_CONTENT_T: frozenset = frozenset({
    "factual",
    "procedural",
    "preference",
    "context",
    "inquiry",
    "document",         # P61-T01: document node (first-class in graph)
    "gap",              # Phase 6.2: gap node for knowledge gaps
})

VALID_KB_VIS: frozenset = frozenset({
    "public",
    "conditional_public",
    "restricted",
    "private",
})

VALID_NODE_VIS: frozenset = frozenset({
    "public",
    "team",
    "private",
})

VALID_FORMAT: frozenset = frozenset({"plain", "markdown"})

# ─── Canonical service description (single source of truth) ───────────────────
# Human-facing copy lives in packages/ui/src/i18n.ts (onboarding.purpose_* keys).
# This English version is delivered to AI agents via the MCP initialize response.
MCP_INSTRUCTIONS = (
    "MemTrace is a shared knowledge graph maintained jointly by humans, AI, and tools. "
    "Knowledge is structured into nodes and typed edges — relationships and paths preserve "
    "context so work can continue across conversations, agents, and tools.\n\n"
    "How to use this server effectively:\n"
    "• Call search_nodes before creating — avoid duplicates and surface existing context.\n"
    "• Traverse typed edges (related_to, depends_on, answered_by) to build full context.\n"
    "• create_node proposals enter a human review queue unless you hold write scope.\n"
    "• Log open questions as inquiry nodes; close them with answered_by edges once answered.\n"
    "• Include tags and a brief provenance note so humans can verify your contributions.\n\n"
    "Safety boundaries: never create nodes with personally identifiable information, "
    "credentials, or content that contradicts a node marked trust > 0.9 without flagging "
    "the contradiction explicitly using a contradicts edge."
)

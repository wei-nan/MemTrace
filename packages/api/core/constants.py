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
    "queried_via_mcp",
})

VALID_CONTENT_T: frozenset = frozenset({
    "factual",
    "procedural",
    "preference",
    "context",
    "inquiry",
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

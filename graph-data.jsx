// graph-data.jsx
// MemTrace knowledge-graph nodes — schema mirrors the real packages/ui types:
//   content_type ∈ factual | procedural | preference | context | inquiry
//   relation     ∈ depends_on | extends | related_to | contradicts | answered_by | similar_to | queried_via_mcp
//
// Each node also carries a `cluster` for the 2D grouped view's layout.

const CLUSTERS = [
  { id: "core",   color: "primary", label: "MemTrace 核心",      en: "Core Platform",   cx: 0.50, cy: 0.42, r: 0.16 },
  { id: "api",    color: "blue",    label: "API · Session",      en: "API & Sessions",  cx: 0.21, cy: 0.30, r: 0.14 },
  { id: "graph",  color: "teal",    label: "知識圖譜",            en: "Knowledge Graph", cx: 0.78, cy: 0.28, r: 0.14 },
  { id: "ai",     color: "violet",  label: "AI 代理 · MCP",       en: "AI Agent · MCP",  cx: 0.80, cy: 0.70, r: 0.15 },
  { id: "auth",   color: "amber",   label: "權限 · 角色",         en: "Access · Roles",  cx: 0.22, cy: 0.74, r: 0.13 },
  { id: "doc",    color: "rose",    label: "文件來源",            en: "Sources",         cx: 0.50, cy: 0.84, r: 0.13 },
];

// Each node: id, label (zh), en, cluster, content_type, trust (0..1)
const NODES = [
  // ── Core ─────────────────────────────────────────────
  { id: "n_core",       cluster: "core",  ct: "context",    label: "MemTrace 平台總覽",   en: "Platform overview",         trust: 0.94 },
  { id: "n_core_func",  cluster: "core",  ct: "factual",    label: "MemTrace 功能矩陣",   en: "Feature matrix",            trust: 0.82 },
  { id: "n_core_play",  cluster: "core",  ct: "procedural", label: "MemTrace Playbook",   en: "Playbook",                  trust: 0.70 },
  { id: "n_core_ai",    cluster: "core",  ct: "factual",    label: "MemTrace AI 功能",    en: "AI feature surface",        trust: 0.75 },
  { id: "n_core_token", cluster: "core",  ct: "factual",    label: "MEMTRACE_TOKEN 規範", en: "MEMTRACE_TOKEN spec",       trust: 0.62 },
  { id: "n_core_token_legacy", cluster:"core", ct: "context", label:"既存 MEMTRACE_TO…", en:"Legacy token notes",         trust: 0.40 },
  { id: "n_core_readme",cluster: "core",  ct: "procedural", label: "README 使用文件",      en: "README",                    trust: 0.55 },

  // ── API ──────────────────────────────────────────────
  { id: "n_api",        cluster: "api",   ct: "factual",    label: "API 金鑰 / Session",  en: "API key / session",         trust: 0.92 },
  { id: "n_api_schema", cluster: "api",   ct: "factual",    label: "API 金鑰欄位",         en: "Key schema",                trust: 0.78 },
  { id: "n_api_key",    cluster: "api",   ct: "factual",    label: "API Key 權限範圍",    en: "Key scope",                 trust: 0.72 },
  { id: "n_api_create", cluster: "api",   ct: "procedural", label: "API 金鑰簽發工具列",  en: "Issuance toolbar",          trust: 0.60 },
  { id: "n_api_create2",cluster: "api",   ct: "procedural", label: "API 金鑰建立行為",    en: "Creation flow",             trust: 0.55 },
  { id: "n_api_session",cluster: "api",   ct: "procedural", label: "Session 行為設計",    en: "Session behavior",          trust: 0.65 },
  { id: "n_api_q1",     cluster: "api",   ct: "inquiry",    label: "金鑰可否多重作用域?",  en: "Multi-scope keys?",         trust: 0.30 },

  // ── Graph ────────────────────────────────────────────
  { id: "n_graph",      cluster: "graph", ct: "factual",    label: "知識圖譜計量",         en: "Graph metrics",             trust: 0.92 },
  { id: "n_graph_func", cluster: "graph", ct: "factual",    label: "MemTrace 圖譜功能",   en: "Graph functionality",       trust: 0.80 },
  { id: "n_graph_edge", cluster: "graph", ct: "factual",    label: "EDGE_GUIDE 內容定義", en: "EDGE_GUIDE schema",         trust: 0.72 },
  { id: "n_graph_node", cluster: "graph", ct: "factual",    label: "NODE_GUIDE 內容定義", en: "NODE_GUIDE schema",         trust: 0.70 },
  { id: "n_graph_handle",cluster:"graph", ct: "procedural", label: "處理 createNode",     en: "createNode handler",        trust: 0.55 },
  { id: "n_graph_legend",cluster:"graph", ct: "preference", label: "圖譜圖例: 節點顏色",  en: "Legend pref",               trust: 0.48 },
  { id: "n_graph_iso",  cluster: "graph", ct: "procedural", label: "孤立節點清理流程",    en: "Isolated nodes",            trust: 0.62 },

  // ── AI Agent / MCP ───────────────────────────────────
  { id: "n_ai",         cluster: "ai",    ct: "factual",    label: "AI 代理工作流程",     en: "Agent workflow",            trust: 0.90 },
  { id: "n_ai_chat",    cluster: "ai",    ct: "procedural", label: "AI Chat 使用知識庫",  en: "AI chat surface",           trust: 0.75 },
  { id: "n_ai_init",    cluster: "ai",    ct: "procedural", label: "AI 代理建立節點必欄", en: "Required fields",           trust: 0.62 },
  { id: "n_ai_provider",cluster: "ai",    ct: "factual",    label: "AI Provider embed",   en: "Provider embed",            trust: 0.58 },
  { id: "n_mcp",        cluster: "ai",    ct: "factual",    label: "MCP 伺服器中的資源",  en: "MCP server resources",      trust: 0.78 },
  { id: "n_mcp_proto",  cluster: "ai",    ct: "factual",    label: "MCP 協議模式: SSE",   en: "MCP protocol modes",        trust: 0.60 },
  { id: "n_mcp_iter",   cluster: "ai",    ct: "procedural", label: "MCP 身份驗證",        en: "MCP auth",                  trust: 0.50 },
  { id: "n_ai_q1",      cluster: "ai",    ct: "inquiry",    label: "代理可否並行寫入?",   en: "Agent concurrent writes?",  trust: 0.35 },

  // ── Auth / Roles ─────────────────────────────────────
  { id: "n_auth",       cluster: "auth",  ct: "factual",    label: "管理角色與能力",      en: "Role admin",                trust: 0.86 },
  { id: "n_auth_list",  cluster: "auth",  ct: "factual",    label: "管理角色 / 角色概覽", en: "Role list",                 trust: 0.68 },
  { id: "n_auth_role",  cluster: "auth",  ct: "factual",    label: "工作區所有者角色",    en: "Workspace owner",           trust: 0.60 },
  { id: "n_auth_dele",  cluster: "auth",  ct: "procedural", label: "授權名角色能力",      en: "Delegated capabilities",    trust: 0.55 },
  { id: "n_auth_create",cluster: "auth",  ct: "procedural", label: "提名名角色能力",      en: "Nominated roles",           trust: 0.45 },
  { id: "n_auth_pref",  cluster: "auth",  ct: "preference", label: "預設新成員角色",      en: "Default member role",       trust: 0.40 },

  // ── Documents / Sources ──────────────────────────────
  { id: "n_doc",        cluster: "doc",   ct: "factual",    label: "來源文件節點驗證",    en: "Source node validation",    trust: 0.82 },
  { id: "n_doc_kind",   cluster: "doc",   ct: "factual",    label: "來源文件節點類型",    en: "Source kind enum",          trust: 0.68 },
  { id: "n_doc_split",  cluster: "doc",   ct: "procedural", label: "來源文件節點儲存",    en: "Storage method",            trust: 0.58 },
  { id: "n_doc_link",   cluster: "doc",   ct: "factual",    label: "來源格式參考表",      en: "Format reference",          trust: 0.50 },
  { id: "n_doc_ref",    cluster: "doc",   ct: "procedural", label: "節點來源追溯",        en: "Source traceability",       trust: 0.55 },
  { id: "n_doc_new",    cluster: "doc",   ct: "factual",    label: "新增內容類型",        en: "New content type",          trust: 0.48 },
];

// Compute spiral / packed positions per cluster for the 2D view.
(function layoutNodes() {
  const byCluster = {};
  for (const n of NODES) (byCluster[n.cluster] ||= []).push(n);
  for (const cl of CLUSTERS) {
    const list = byCluster[cl.id] || [];
    list.sort((a, b) => b.trust - a.trust);
    const n = list.length;
    list.forEach((node, i) => {
      if (i === 0) {
        node.x = cl.cx;
        node.y = cl.cy;
        return;
      }
      const ring = i < 4 ? 1 : i < 9 ? 2 : 3;
      const ringCount = ring === 1 ? Math.min(3, n - 1)
                      : ring === 2 ? Math.min(5, n - 4)
                      : Math.max(1, n - 9);
      const idxOnRing = ring === 1 ? i - 1 : ring === 2 ? i - 4 : i - 9;
      const baseAngle = ring === 1 ? -Math.PI / 2 : ring === 2 ? -Math.PI / 2 + 0.3 : 0;
      const angle = baseAngle + (idxOnRing / Math.max(1, ringCount)) * Math.PI * 2;
      const radius = cl.r * (ring === 1 ? 0.55 : ring === 2 ? 0.95 : 1.4);
      node.x = cl.cx + Math.cos(angle) * radius * 0.85;
      node.y = cl.cy + Math.sin(angle) * radius * 0.62;
    });
  }
})();

// Edges — with relation kinds matching the real schema.
const EDGES = [
  // Core spokes
  ["n_core", "n_core_func", "related_to"],
  ["n_core", "n_core_play", "related_to"],
  ["n_core", "n_core_ai", "related_to"],
  ["n_core", "n_core_token", "extends"],
  ["n_core_token", "n_core_token_legacy", "similar_to"],
  ["n_core", "n_core_readme", "related_to"],

  // API internal
  ["n_api", "n_api_schema", "extends"],
  ["n_api", "n_api_key", "related_to"],
  ["n_api", "n_api_session", "depends_on"],
  ["n_api_create", "n_api_create2", "similar_to"],
  ["n_api_key", "n_api_create", "related_to"],
  ["n_api_schema", "n_api_key", "similar_to"],
  ["n_api_q1", "n_api_key", "answered_by"],

  // Graph internal
  ["n_graph", "n_graph_func", "related_to"],
  ["n_graph", "n_graph_edge", "extends"],
  ["n_graph", "n_graph_node", "extends"],
  ["n_graph_node", "n_graph_handle", "depends_on"],
  ["n_graph_func", "n_graph_legend", "related_to"],
  ["n_graph", "n_graph_iso", "related_to"],

  // AI internal
  ["n_ai", "n_ai_chat", "related_to"],
  ["n_ai", "n_ai_init", "extends"],
  ["n_ai", "n_ai_provider", "depends_on"],
  ["n_ai", "n_mcp", "queried_via_mcp"],
  ["n_mcp", "n_mcp_proto", "extends"],
  ["n_mcp", "n_mcp_iter", "depends_on"],
  ["n_ai_q1", "n_ai_init", "answered_by"],

  // Auth internal
  ["n_auth", "n_auth_list", "related_to"],
  ["n_auth", "n_auth_role", "related_to"],
  ["n_auth", "n_auth_dele", "depends_on"],
  ["n_auth_dele", "n_auth_create", "similar_to"],
  ["n_auth_role", "n_auth_pref", "related_to"],
  ["n_auth_create", "n_auth_role", "contradicts"],

  // Doc internal
  ["n_doc", "n_doc_kind", "extends"],
  ["n_doc", "n_doc_split", "depends_on"],
  ["n_doc_kind", "n_doc_link", "related_to"],
  ["n_doc", "n_doc_ref", "related_to"],
  ["n_doc_ref", "n_doc_new", "similar_to"],

  // Inter-cluster
  ["n_core", "n_api", "related_to"],
  ["n_core", "n_graph", "related_to"],
  ["n_core", "n_ai", "related_to"],
  ["n_core_ai", "n_ai", "related_to"],
  ["n_api", "n_auth", "depends_on"],
  ["n_auth", "n_api_key", "related_to"],
  ["n_graph", "n_doc", "depends_on"],
  ["n_doc", "n_graph_node", "related_to"],
  ["n_ai", "n_graph", "queried_via_mcp"],
  ["n_mcp", "n_api", "depends_on"],
  ["n_core_func", "n_graph_func", "similar_to"],
  ["n_core_play", "n_ai", "related_to"],
];

// Color palettes for content types — mirrors GraphView3D.tsx NODE_BASE
const CONTENT_TYPES = [
  { id: "factual",    zh: "事實",  rgb: [99, 102, 241]  },  // indigo
  { id: "procedural", zh: "程序",  rgb: [34, 197, 94]   },  // green
  { id: "preference", zh: "偏好",  rgb: [245, 158, 11]  },  // amber
  { id: "context",    zh: "情境",  rgb: [100, 116, 139] },  // slate
  { id: "inquiry",    zh: "詢問",  rgb: [148, 163, 184] },  // light slate
];

const RELATIONS = [
  { id: "depends_on",      zh: "依賴",          color: "#818cf8", style: "solid"  },
  { id: "extends",         zh: "延伸",          color: "#4ade80", style: "solid"  },
  { id: "related_to",      zh: "關聯",          color: "#64748b", style: "dashed" },
  { id: "contradicts",     zh: "矛盾",          color: "#f87171", style: "solid"  },
  { id: "answered_by",     zh: "答覆於",        color: "#a78bfa", style: "dashed" },
  { id: "similar_to",      zh: "相似於",        color: "#94a3b8", style: "dashed" },
  { id: "queried_via_mcp", zh: "經由 MCP 查詢", color: "#2dd4bf", style: "solid"  },
];

window.MEMTRACE_DATA = { CLUSTERS, NODES, EDGES, CONTENT_TYPES, RELATIONS };

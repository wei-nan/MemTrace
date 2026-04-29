#!/usr/bin/env node
/**
 * MemTrace MCP Server
 *
 * Exposes the MemTrace knowledge graph as MCP tools so AI agents (e.g. Claude)
 * can query product specs without reading the raw SPEC.md document.
 *
 * Environment variables:
 *   MEMTRACE_API  — API base URL  (default: http://localhost:8000/api/v1)
 *   MEMTRACE_WS   — Workspace ID  (default: ws_spec0001)
 *   MEMTRACE_LANG — Display lang  (default: zh-TW)
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { SSEServerTransport } from "@modelcontextprotocol/sdk/server/sse.js";
import express, { type Request, type Response } from "express";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  ListResourcesRequestSchema,
  ReadResourceRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

// ── Config ────────────────────────────────────────────────────────────────────

const API_BASE = process.env.MEMTRACE_API ?? "http://localhost:8000/api/v1";
const WS_ID    = process.env.MEMTRACE_WS   ?? "ws_spec0001";
const LANG     = process.env.MEMTRACE_LANG ?? "zh-TW";
const TOKEN    = process.env.MEMTRACE_TOKEN ?? "";
const INTERNAL_TOKEN = process.env.MEMTRACE_INTERNAL_TOKEN ?? "";

// ── API helpers ───────────────────────────────────────────────────────────────

interface ApiNode {
  id: string;
  title_zh: string;
  title_en: string;
  content_type: string;
  body_zh: string;
  body_en: string;
  tags: string[];
  trust_score: number;
  traversal_count: number;
}

interface ApiEdge {
  id: string;
  from_id: string;
  to_id: string;
  relation: string;
  weight: number;
}

interface ApiFetchOptions {
  method?: string;
  body?: any;
}

async function apiFetch<T>(path: string, options?: ApiFetchOptions): Promise<T> {
  const url = `${API_BASE}${path}`;
  const headers: Record<string, string> = {};
  if (TOKEN) {
    headers["Authorization"] = `Bearer ${TOKEN}`;
  }
  
  const fetchOptions: RequestInit = { headers };
  if (options?.method) {
    fetchOptions.method = options.method;
  }
  if (options?.body) {
    fetchOptions.body = JSON.stringify(options.body);
    headers["Content-Type"] = "application/json";
  }
  
  const res = await fetch(url, fetchOptions);
  if (!res.ok) {
    let errText = await res.text();
    try {
      const parsed = JSON.parse(errText);
      if (res.status === 422 && Array.isArray(parsed.detail)) {
        errText = parsed.detail.map((err: any) => `${err.loc.join('.')}: ${err.msg}`).join(', ');
      }
    } catch {}
    throw new Error(`API ${res.status}: ${errText}`);
  }

  if (res.status === 204 || res.headers.get("content-length") === "0") {
    return null as unknown as T;
  }

  const contentType = res.headers.get("content-type");
  if (contentType && contentType.includes("application/json")) {
    return res.json() as Promise<T>;
  }
  return null as unknown as T;
}

const AVG_NODE_TOKENS = Number(process.env.MCP_AVG_NODE_TOKENS ?? "350");

async function logMcpQuery(payload: {
  workspace_id: string;
  tool_name: string;
  query_text?: string;
  result_node_count: number;
  estimated_tokens: number;
  provider?: string;
}) {
  if (!INTERNAL_TOKEN) return;
  try {
    await fetch(`${API_BASE}/internal/mcp-log`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${INTERNAL_TOKEN}`,
      },
      body: JSON.stringify(payload),
    });
  } catch {
    // Logging should never break the main tool call.
  }
}

function estimateNodeTokens(count: number) {
  return count * AVG_NODE_TOKENS;
}

function nodeTitle(n: ApiNode): string {
  return LANG === "zh-TW" ? n.title_zh : n.title_en;
}

function nodeBody(n: ApiNode): string {
  return LANG === "zh-TW" ? n.body_zh : n.body_en;
}

/** Render a single node as a compact markdown block */
function renderNode(n: ApiNode, includeBody = true): string {
  const lines = [
    `## [${n.id}] ${nodeTitle(n)}`,
    `- **type**: ${n.content_type}  **trust**: ${n.trust_score.toFixed(2)}  **traversals**: ${n.traversal_count}`,
    `- **tags**: ${n.tags.join(", ") || "—"}`,
  ];
  if (includeBody) {
    lines.push("", nodeBody(n) || "_（無內容）_");
  }
  return lines.join("\n");
}

// ── Documentation / Schema Guides ───────────────────────────────────────────

const NODE_GUIDE = `# MemTrace Node Schema

## 欄位規格 (Fields)
| 欄位 | 型別 | 必填 | 說明 |
|------|------|------|------|
| title_en | string | ✅ | 英文標題 |
| title_zh | string | 建議填 | 中文標題（支援中文搜尋） |
| content_type | enum | ✅ | 節點類型，見下方 |
| content_format | enum | ✅ | plain=純文字, markdown=Markdown |
| body_zh | string | 擇一必填 | 中文內容 |
| body_en | string | 擇一必填 | 英文內容 |
| tags | string[] | 選填 | 分類標籤 |
| visibility | enum | 選填 | public/team/private，預設 private |
| source_type | enum | ✅ (AI) | AI agent 必須填 "ai" |

## content_type 選擇規則
- **factual**: 陳述性事實（例：pgvector 支援 cosine similarity）
- **procedural**: 步驟、流程或指引（例：如何設定 Google OAuth）
- **preference**: 偏好、決策或特定選型（例：我們選擇 bcrypt 作為 hash 演算法）
- **context**: 背景、專案核心目標或設計初衷（例：採用雙語設計的原因）

## 建立最佳實踐 (Best Practices)
1. **先搜尋**: 建立前先用 \`search_nodes\` 確認無相似節點。
2. **單一性**: 一個節點只記錄一個獨立的概念。
3. **雙語化**: 盡量同時提供 中英文欄位，增加跨語言檢索能力。
4. **關聯性**: 使用 \`suggested_edges\` 參數在建立時一併提議關聯。
5. **品質回饋**: 讀取節點後，若發現資訊極具價值或有誤，應呼叫 \`vote_trust\` 調整信任分。
`;

const EDGE_GUIDE = `# MemTrace Edge Schema

## 關聯類型 (Relation Types)
- **depends_on**: 此節點依賴目標節點才能運作或理解。
- **extends**: 此節點是目標節點概念的進一步擴充或特化。
- **related_to**: 兩者相關，但沒有明確的先後或屬序關係。
- **contradicts**: 此節點與目標節點存在邏輯衝突或版本矛盾。

## 參數說明
- **weight**: 關聯強度 (0.1 至 1.0)。預設 1.0。
- **workspace_id**: 目標工作區 ID。

## 限制與細節
- 同一對節點 (A, B) 之間不能存在多條相同類型的邊（重複建立會回 409）。
- 若為 Editor 角色，建立邊的請求會進入 \`review_queue\` 待審核。
`;

const SCHEMA_GUIDE = `
${NODE_GUIDE}
---
${EDGE_GUIDE}
`;

// ── Tool implementations ──────────────────────────────────────────────────────

async function createNode(data: any, wsId: string = WS_ID): Promise<string> {
  if (!TOKEN) throw new Error("Write operations require MEMTRACE_TOKEN configuration.");
  const res = await apiFetch<any>(`/workspaces/${wsId}/nodes`, { method: "POST", body: data });
  
  await logMcpQuery({
    workspace_id: wsId,
    tool_name: "create_node",
    query_text: data.title_en || data.title_zh,
    result_node_count: 1,
    estimated_tokens: Math.floor(JSON.stringify(data).length / 4),
  });

  // Could return proposed review info if it was submitted to review queue
  if (res?.detail?.includes("submitted for review") || res?.review_id) {
    return `Proposed node creation. It has been queued for review.\n${JSON.stringify(res)}`;
  }
  return `Created node successfully:\n${JSON.stringify(res)}`;
}

async function updateNode(nodeId: string, data: any, wsId: string = WS_ID): Promise<string> {
  if (!TOKEN) throw new Error("Write operations require MEMTRACE_TOKEN configuration.");
  const res = await apiFetch<any>(`/workspaces/${wsId}/nodes/${nodeId}`, { method: "PATCH", body: data });
  
  await logMcpQuery({
    workspace_id: wsId,
    tool_name: "update_node",
    query_text: nodeId,
    result_node_count: 1,
    estimated_tokens: Math.floor(JSON.stringify(data).length / 4),
  });

  if (res?.detail?.includes("submitted for review") || res?.review_id) {
    return `Proposed node update for ${nodeId}. It has been queued for review.\n${JSON.stringify(res)}`;
  }
  return `Updated node ${nodeId} successfully:\n${JSON.stringify(res)}`;
}

async function deleteNode(nodeId: string, wsId: string = WS_ID): Promise<string> {
  if (!TOKEN) throw new Error("Write operations require MEMTRACE_TOKEN configuration.");
  
  await logMcpQuery({
    workspace_id: wsId,
    tool_name: "delete_node",
    query_text: nodeId,
    result_node_count: 0,
    estimated_tokens: 10, // Small constant for command overhead
  });

  // Use POST to submit delete suggestion ? No, delete endpoint handles it. Wait, the delete endpoint can return JSON.
  try {
    const res = await apiFetch<any>(`/workspaces/${wsId}/nodes/${nodeId}`, { method: "DELETE" });
    if (res?.detail?.includes("submitted for review") || res?.review_id) {
      return `Proposed node deletion for ${nodeId}. It has been queued for review.\n${JSON.stringify(res)}`;
    }
  } catch (err: any) {
    if (err.message.includes("202")) {
       return `Requested deletion for node ${nodeId}. Check review queue for pending review. (Status 202)`;
    }
    throw err;
  }
  return `Deleted node ${nodeId} successfully.`;
}

async function createEdge(fromId: string, toId: string, relation: string, weight: number = 1.0, wsId: string = WS_ID): Promise<string> {
  if (!TOKEN) throw new Error("Write operations require MEMTRACE_TOKEN configuration.");
  const payload = { from_id: fromId, to_id: toId, relation, weight };
  const res = await apiFetch<any>(`/workspaces/${wsId}/edges`, { method: "POST", body: payload });
  
  await logMcpQuery({
    workspace_id: wsId,
    tool_name: "create_edge",
    query_text: `${fromId} ${relation} ${toId}`,
    result_node_count: 0,
    estimated_tokens: 20,
  });

  return `Created edge from ${fromId} to ${toId} successfully:\n${JSON.stringify(res)}`;
}

async function traverseEdge(edgeId: string, context: string = "", wsId: string = WS_ID): Promise<string> {
  if (!TOKEN) throw new Error("Write operations require MEMTRACE_TOKEN configuration.");
  const payload: Record<string, string> = {};
  if (context) payload.context = context;
  await apiFetch<null>(`/edges/${edgeId}/traverse`, { method: "POST", body: payload });

  await logMcpQuery({
    workspace_id: wsId,
    tool_name: "traverse_edge",
    query_text: edgeId,
    result_node_count: 0,
    estimated_tokens: 10,
  });

  return `Traversal recorded for edge ${edgeId}. Co-access boost applied if both endpoints were recently visited.`;
}

async function confirmNodeValidity(nodeId: string, wsId: string = WS_ID): Promise<string> {
  if (!TOKEN) throw new Error("Write operations require MEMTRACE_TOKEN configuration.");
  const res = await apiFetch<any>(`/workspaces/${wsId}/nodes/${nodeId}/confirm-validity`, { method: "POST" });
  
  await logMcpQuery({
    workspace_id: wsId,
    tool_name: "confirm_node_validity",
    query_text: nodeId,
    result_node_count: 1,
    estimated_tokens: 15,
  });

  return `Confirmed validity for ${nodeId}:\n${JSON.stringify(res)}`;
}

async function voteTrust(nodeId: string, accuracy: number, utility: number, wsId: string = WS_ID): Promise<string> {
  if (!TOKEN) throw new Error("Write operations require MEMTRACE_TOKEN configuration.");
  const payload = { accuracy, utility };
  const res = await apiFetch<any>(`/workspaces/${wsId}/nodes/${nodeId}/vote-trust`, { method: "POST", body: payload });
  
  await logMcpQuery({
    workspace_id: wsId,
    tool_name: "vote_trust",
    query_text: `${nodeId} acc:${accuracy} util:${utility}`,
    result_node_count: 1,
    estimated_tokens: 20,
  });

  return `Voted for node ${nodeId} successfully:\n${JSON.stringify(res)}`;
}

async function listReviewQueue(status: string = "pending", wsId: string = WS_ID): Promise<string> {
  const params = new URLSearchParams({ status });
  const items = await apiFetch<any[]>(`/workspaces/${wsId}/review-queue?${params}`);
  
  await logMcpQuery({
    workspace_id: wsId,
    tool_name: "list_review_queue",
    query_text: status,
    result_node_count: items?.length ?? 0,
    estimated_tokens: Math.floor(JSON.stringify(items || []).length / 4),
  });

  if (!items || items.length === 0) return `0 review queue items found with status: ${status}.`;
  
  const lines = [`**${items.length}** item(s) in review queue (${status}):`];
  for (const item of items) {
    lines.push(`- [${item.id}] ${item.change_type} by ${item.proposer_type} (Target: ${item.target_node_id || 'New Node'}) at ${new Date(item.created_at).toLocaleString()}`);
  }
  return lines.join("\n");
}

async function searchNodes(query: string, limit = 8, wsId: string = WS_ID): Promise<string> {
  const params = new URLSearchParams({ q: query, limit: String(limit) });
  const nodes = await apiFetch<ApiNode[]>(
    `/workspaces/${wsId}/nodes?${params}`
  );
  await logMcpQuery({
    workspace_id: wsId,
    tool_name: "search_nodes",
    query_text: query,
    result_node_count: nodes.length,
    estimated_tokens: estimateNodeTokens(nodes.length),
  });
  if (nodes.length === 0) return `No nodes found for query: "${query}" in workspace ${wsId}`;
  return [
    `Found **${nodes.length}** node(s) matching "${query}":\n`,
    ...nodes.map((n) => renderNode(n, true)),
  ].join("\n\n---\n\n");
}

async function getNode(nodeId: string, wsId: string = WS_ID): Promise<string> {
  try {
    const n = await apiFetch<ApiNode>(`/workspaces/${wsId}/nodes/${nodeId}`);
    await logMcpQuery({
      workspace_id: wsId,
      tool_name: "get_node",
      query_text: nodeId,
      result_node_count: 1,
      estimated_tokens: estimateNodeTokens(1),
    });
    return renderNode(n, true);
  } catch {
    return `Node not found: ${nodeId} in workspace ${wsId}`;
  }
}

async function traverse(nodeId: string, depth = 1, wsId: string = WS_ID): Promise<string> {
  // Fetch the root node
  let root: ApiNode;
  try {
    root = await apiFetch<ApiNode>(`/workspaces/${wsId}/nodes/${nodeId}`);
  } catch {
    return `Node not found: ${nodeId} in workspace ${wsId}`;
  }

  // Fetch all edges connected to root
  const edges = await apiFetch<ApiEdge[]>(
    `/workspaces/${wsId}/edges?node_id=${nodeId}`
  );

  // Resolve neighbour node IDs
  const neighbourIds = [
    ...new Set(
      edges.map((e) => (e.from_id === nodeId ? e.to_id : e.from_id))
    ),
  ];

  // Fetch neighbours (parallel, best-effort)
  const neighbours = (
    await Promise.allSettled(
      neighbourIds.map((id) =>
        apiFetch<ApiNode>(`/workspaces/${wsId}/nodes/${id}`)
      )
    )
  )
    .filter((r): r is PromiseFulfilledResult<ApiNode> => r.status === "fulfilled")
    .map((r) => r.value);
  await logMcpQuery({
    workspace_id: wsId,
    tool_name: "traverse",
    query_text: nodeId,
    result_node_count: 1 + neighbours.length,
    estimated_tokens: estimateNodeTokens(1 + neighbours.length),
  });

  const neighbourMap = Object.fromEntries(neighbours.map((n) => [n.id, n]));

  // Build output
  const lines: string[] = [renderNode(root, true), "", "### Associations"];

  if (edges.length === 0) {
    lines.push("_No associations._");
  } else {
    for (const e of edges) {
      const otherId   = e.from_id === nodeId ? e.to_id   : e.from_id;
      const direction = e.from_id === nodeId ? "→" : "←";
      const other     = neighbourMap[otherId];
      const label     = other ? nodeTitle(other) : otherId;
      lines.push(
        `- ${direction} **[${e.relation}]** [${otherId}] ${label}` +
        (other ? ` _(${other.content_type})_` : "")
      );
    }
  }

  // If depth > 1, include full bodies of direct neighbours
  if (depth > 1 && neighbours.length > 0) {
    lines.push("", "### Neighbour Details");
    for (const n of neighbours) {
      lines.push("", renderNode(n, true));
    }
  }

  return lines.join("\n");
}

async function listByTag(tag: string, limit = 20, wsId: string = WS_ID): Promise<string> {
  const params = new URLSearchParams({ tag, limit: String(limit) });
  const nodes = await apiFetch<ApiNode[]>(
    `/workspaces/${wsId}/nodes?${params}`
  );
  await logMcpQuery({
    workspace_id: wsId,
    tool_name: "list_by_tag",
    query_text: tag,
    result_node_count: nodes.length,
    estimated_tokens: estimateNodeTokens(nodes.length),
  });
  if (nodes.length === 0) return `No nodes found with tag: "${tag}" in workspace ${wsId}`;
  return [
    `**${nodes.length}** node(s) tagged \`${tag}\`:\n`,
    ...nodes.map((n) => renderNode(n, false)),
  ].join("\n\n");
}

interface ApiWorkspace {
  id: string;
  name_zh: string;
  name_en: string;
  kb_type: string;
  visibility: string;
}

async function listWorkspaces(limit = 20): Promise<string> {
  const wsList = await apiFetch<ApiWorkspace[]>(`/workspaces`);
  
  await logMcpQuery({
    workspace_id: WS_ID,
    tool_name: "list_workspaces",
    query_text: `limit=${limit}`,
    result_node_count: 0,
    estimated_tokens: Math.floor(JSON.stringify(wsList || []).length / 4),
  });

  if (!wsList || wsList.length === 0) {
    return "0 workspace(s) accessible.";
  }
  
  const displayList = wsList.slice(0, limit);
  const lines: string[] = [
    `**${displayList.length}** workspace(s) accessible:`,
  ];
  
  for (const ws of displayList) {
    const wsName = LANG === "zh-TW" ? ws.name_zh : ws.name_en;
    lines.push(`- [${ws.id}] ${wsName} (${ws.kb_type} / ${ws.visibility})`);
  }
  
  return lines.join("\n");
}

// ── MCP Server setup ──────────────────────────────────────────────────────────

const server = new Server(
  { name: "memtrace-kb", version: "1.0.0" },
  { capabilities: { tools: {}, resources: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "search_nodes",
      description:
        "Search MemTrace knowledge base nodes by keyword. Returns matching nodes with full content. Use this to look up product specs, feature descriptions, and design decisions instead of reading SPEC.md.\nPass `workspace_id` to query a specific KB; omit to use the configured default (`MEMTRACE_WS`).",
      inputSchema: {
        type: "object" as const,
        properties: {
          query: { type: "string", description: "Search keyword (supports Chinese and English)" },
          limit: { type: "number", description: "Max results (default 8, max 20)" },
          workspace_id: { type: "string", description: "Target workspace ID (e.g. ws_abc123). Omit to use the server default (MEMTRACE_WS)." },
        },
        required: ["query"],
      },
    },
    {
      name: "get_node",
      description:
        "Retrieve a specific MemTrace knowledge node by its ID (e.g. mem_d001, mem_p003). Returns full content and metadata.\n" +
        "讀取完節點後，若確認內容正確且有用，建議呼叫 `vote_trust` 或 `confirm_node_validity` 回饋品質訊號，以維持知識圖的活性。\n" +
        "Pass `workspace_id` to query a specific KB; omit to use the configured default (`MEMTRACE_WS`).",
      inputSchema: {
        type: "object" as const,
        properties: {
          node_id: { type: "string", description: "Node ID, e.g. mem_d001" },
          workspace_id: { type: "string", description: "Target workspace ID (e.g. ws_abc123). Omit to use the server default (MEMTRACE_WS)." },
        },
        required: ["node_id"],
      },
    },
    {
      name: "traverse",
      description:
        "Get a node and its direct associations (upstream/downstream). Useful for understanding how concepts relate to each other. Set depth=2 to also include full content of neighbour nodes.\n" +
        "讀取完節點後，若確認內容正確且有用，建議呼叫 `vote_trust` 或 `confirm_node_validity` 回饋品質訊號，以維持知識圖的活性。\n" +
        "Pass `workspace_id` to query a specific KB; omit to use the configured default (`MEMTRACE_WS`).",
      inputSchema: {
        type: "object" as const,
        properties: {
          node_id: { type: "string", description: "Starting node ID" },
          depth: { type: "number", description: "1 = root+edge list only, 2 = include neighbour content (default 1)" },
          workspace_id: { type: "string", description: "Target workspace ID (e.g. ws_abc123). Omit to use the server default (MEMTRACE_WS)." },
        },
        required: ["node_id"],
      },
    },
    {
      name: "list_by_tag",
      description:
        "List all knowledge nodes with a specific tag. Common tags: ai, data-model, graph, auth, api, dev, architecture.\nPass `workspace_id` to query a specific KB; omit to use the configured default (`MEMTRACE_WS`).",
      inputSchema: {
        type: "object" as const,
        properties: {
          tag: { type: "string", description: "Tag to filter by, e.g. 'data-model'" },
          limit: { type: "number", description: "Max results (default 20)" },
          workspace_id: { type: "string", description: "Target workspace ID (e.g. ws_abc123). Omit to use the server default (MEMTRACE_WS)." },
        },
        required: ["tag"],
      },
    },
    {
      name: "create_node",
      description: `建立新的知識節點，進入 _propose_change 審核流程。

【建立前】建議先用 search_nodes 確認無重複節點。
【AI agent】必須帶 source_type: "ai"。
【body】body_zh / body_en 至少填一個。

content_type 選擇：
- factual     = 陳述性事實（例：pgvector 支援 cosine similarity）
- procedural  = 步驟流程（例：如何設定 Google OAuth）
- preference  = 偏好或決策（例：我們選擇 bcrypt）
- context     = 背景脈絡（例：採用雙語設計的原因）

回傳 201 = 直接建立完成；202 + review_id = 已進入審核佇列（editor 角色）。`,
      inputSchema: {
        type: "object" as const,
        properties: {
          title_zh: { type: "string" },
          title_en: { type: "string" },
          content_type: { 
            type: "string", 
            enum: ["factual", "procedural", "preference", "context"],
            description: "factual=事實知識 | procedural=步驟流程 | preference=偏好設定 | context=背景脈絡"
          },
          content_format: { 
            type: "string", enum: ["plain", "markdown"],
            description: "plain=純文字 | markdown=支援 Markdown 格式"
          },
          body_zh: { type: "string" },
          body_en: { type: "string" },
          tags: { type: "array", items: { type: "string" } },
          visibility: { 
            type: "string", enum: ["public", "team", "private"],
            description: "public=所有人可見 | team=工作區成員 | private=僅自己"
          },
          source_type: {
            type: "string", enum: ["human", "ai"],
            description: "呼叫者身份，AI 代理呼叫時務必傳 'ai'"
          },
          suggested_edges: {
            type: "array",
            description: "同時提議與既有節點的關聯（不立即建立，進入 review_queue）",
            items: {
              type: "object",
              properties: {
                to_id: { type: "string", description: "目標節點 ID，例如 mem_d001" },
                relation: { type: "string", enum: ["depends_on", "extends", "related_to", "contradicts"] },
                weight: { type: "number", description: "關聯強度 0.1–1.0，預設 1.0" }
              },
              required: ["to_id", "relation"]
            }
          },
          workspace_id: { type: "string", description: "Target workspace ID" }
        },
        required: ["title_en", "content_type", "content_format", "source_type"]
      }
    },
    {
      name: "update_node",
      description: "更新既有知識節點。只須傳入欲修改的欄位 (partial update)。使用 _propose_change 流程，編輯者提案會進入審核佇列。AI 修改請務必帶 source_type: 'ai'。",
      inputSchema: {
        type: "object" as const,
        properties: {
          node_id: { type: "string", description: "Target node ID" },
          title_zh: { type: "string" },
          title_en: { type: "string" },
          content_type: { type: "string", enum: ["factual", "procedural", "preference", "context"] },
          content_format: { type: "string", enum: ["plain", "markdown"] },
          body_zh: { type: "string" },
          body_en: { type: "string" },
          tags: { type: "array", items: { type: "string" } },
          visibility: { type: "string", enum: ["public", "team", "private"] },
          source_type: { type: "string", enum: ["human", "ai"] },
          suggested_edges: {
            type: "array",
            items: {
              type: "object",
              properties: {
                to_id: { type: "string" },
                relation: { type: "string", enum: ["depends_on", "extends", "related_to", "contradicts"] },
                weight: { type: "number" }
              },
              required: ["to_id", "relation"]
            }
          },
          workspace_id: { type: "string", description: "Target workspace ID" }
        },
        required: ["node_id", "source_type"]
      }
    },
    {
      name: "delete_node",
      description: "刪除既有知識節點。使用 _propose_change 流程，對 editor 角色而言是「提案刪除」，不立即執行，會進入 review_queue。AI 操作請注意此點。",
      inputSchema: {
        type: "object" as const,
        properties: {
          node_id: { type: "string", description: "Target node ID" },
          workspace_id: { type: "string", description: "Target workspace ID" }
        },
        required: ["node_id"]
      }
    },
    {
      name: "create_edge",
      description: `在兩個節點之間建立關聯邊。建立前請先確保節點存在 (用 get_node)。

relation 語意：
- depends_on：此節點依賴目標節點
- extends：擴展目標節點的概念
- related_to：相關但無明確依賴
- contradicts：與目標節點衝突或矛盾

請注意：同一對節點間相同 relation type 不重複，重複建立會回 409。`,
      inputSchema: {
        type: "object" as const,
        properties: {
          from_id: { type: "string", description: "來源節點 ID" },
          to_id: { type: "string", description: "目標節點 ID" },
          relation: { type: "string", enum: ["depends_on", "extends", "related_to", "contradicts"] },
          weight: { type: "number", description: "關聯強度 0.1–1.0，預設 1.0" },
          workspace_id: { type: "string" }
        },
        required: ["from_id", "to_id", "relation"]
      }
    },
    {
      name: "traverse_edge",
      description: "記錄一條邊被走訪，觸發 co-access boost 機制（若兩端節點在近期均被存取，邊的 weight 會提升）。AI agent 在沿邊推理後應呼叫此工具，讓圖的使用模式反映實際推理路徑。",
      inputSchema: {
        type: "object" as const,
        properties: {
          edge_id: { type: "string", description: "Edge ID to record traversal for" },
          context: { type: "string", description: "Optional description of why this edge was traversed" },
          workspace_id: { type: "string", description: "Target workspace ID (omit to use server default)" },
        },
        required: ["edge_id"],
      },
    },
    {
      name: "confirm_node_validity",
      description: "Mark a node as manually validity-confirmed in the target workspace.",
      inputSchema: {
        type: "object" as const,
        properties: {
          node_id: { type: "string", description: "Target node ID" },
          workspace_id: { type: "string", description: "Target workspace ID" }
        },
        required: ["node_id"]
      }
    },
    {
      name: "vote_trust",
      description: "對記憶節點進行品質評分。Accuracy 代表內容準確度，Utility 代表內容實用度。評分將直接影響節點的信任分數 (Trust Score)。",
      inputSchema: {
        type: "object" as const,
        properties: {
          node_id: { type: "string", description: "Target node ID" },
          accuracy: { type: "number", description: "1-5 分，準確度評分" },
          utility: { type: "number", description: "1-5 分，實用度評分" },
          workspace_id: { type: "string", description: "Target workspace ID" }
        },
        required: ["node_id", "accuracy", "utility"]
      }
    },
    {
      name: "list_review_queue",
      description: "列出工作區中待審核的提案項目，可確認 AI 提案是否已進入佇列。",
      inputSchema: {
        type: "object" as const,
        properties: {
          status: { type: "string", enum: ["pending", "accepted", "rejected"], description: "預設 pending" },
          workspace_id: { type: "string" }
        }
      }
    },
    {
      name: "list_workspaces",
      description: "List all accessible workspaces (requires valid MEMTRACE_TOKEN). Returns available workspace IDs and metadata.",
      inputSchema: {
        type: "object" as const,
        properties: {
          limit: { type: "number", description: "Max results (default 20)" },
        },
      },
    },
    {
      name: "list_empty_nodes",
      description: "列出工作區中 body 為空（中英文均缺）的節點，供 AI 發現並補充內容使用。",
      inputSchema: {
        type: "object" as const,
        properties: {
          limit: { type: "number", description: "最多回傳幾個（預設 10）" },
          workspace_id: { type: "string", description: "Target workspace ID (omit to use server default)" },
        },
      },
    },
    {
      name: "get_schema",
      description: "取得 MemTrace 節點與邊的完整規格、有效值列表與建立最佳實踐。不確定欄位格式時請先呼叫此工具。",
      inputSchema: {
        type: "object" as const,
        properties: {
          topic: {
            type: "string",
            enum: ["node", "edge", "all"],
            description: "查詢主題，預設 all"
          }
        }
      }
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (req) => {
  const { name, arguments: args } = req.params;
  try {
    let text: string;
    const wsId = args?.workspace_id ? String(args.workspace_id) : WS_ID;
    switch (name) {
      case "create_node": {
        const payload = Object.assign({}, args);
        delete payload.workspace_id;
        text = await createNode(payload, wsId);
        break;
      }
      case "update_node": {
        const payload = Object.assign({}, args);
        delete payload.workspace_id;
        delete payload.node_id;
        text = await updateNode(String(args?.node_id ?? ""), payload, wsId);
        break;
      }
      case "delete_node":
        text = await deleteNode(String(args?.node_id ?? ""), wsId);
        break;
      case "create_edge":
        text = await createEdge(String(args?.from_id), String(args?.to_id), String(args?.relation), Number(args?.weight ?? 1.0), wsId);
        break;
      case "traverse_edge":
        text = await traverseEdge(String(args?.edge_id ?? ""), args?.context ? String(args.context) : "", wsId);
        break;
      case "confirm_node_validity":
        text = await confirmNodeValidity(String(args?.node_id ?? ""), wsId);
        break;
      case "vote_trust":
        text = await voteTrust(String(args?.node_id), Number(args?.accuracy), Number(args?.utility), wsId);
        break;
      case "list_review_queue":
        text = await listReviewQueue(args?.status ? String(args.status) : "pending", wsId);
        break;
      case "search_nodes":
        text = await searchNodes(String(args?.query ?? ""), Number(args?.limit ?? 8), wsId);
        break;
      case "get_node":
        text = await getNode(String(args?.node_id ?? ""), wsId);
        break;
      case "traverse":
        text = await traverse(String(args?.node_id ?? ""), Number(args?.depth ?? 1), wsId);
        break;
      case "list_by_tag":
        text = await listByTag(String(args?.tag ?? ""), Number(args?.limit ?? 20), wsId);
        break;
      case "list_workspaces":
        text = await listWorkspaces(Number(args?.limit ?? 20));
        break;
      case "list_empty_nodes": {
        const wsId = args?.workspace_id ? String(args.workspace_id) : WS_ID;
        const limit = Number(args?.limit ?? 10);
        const nodes = await apiFetch<ApiNode[]>(
          `/workspaces/${wsId}/nodes?filter=empty_body&limit=${limit}`
        );
        await logMcpQuery({ workspace_id: wsId, tool_name: "list_empty_nodes", result_node_count: nodes.length, estimated_tokens: estimateNodeTokens(nodes.length) });
        if (nodes.length === 0) {
          text = "No empty-body nodes found in this workspace.";
        } else {
          text = [`**${nodes.length}** node(s) with empty body:\n`, ...nodes.map(n => renderNode(n, false))].join("\n\n");
        }
        break;
      }
      case "get_schema": {
        const topic = args?.topic ?? "all";
        if (topic === "node") text = NODE_GUIDE;
        else if (topic === "edge") text = EDGE_GUIDE;
        else text = SCHEMA_GUIDE;
        break;
      }
      default:
        return { content: [{ type: "text" as const, text: `Unknown tool: ${name}` }], isError: true };
    }
    return { content: [{ type: "text" as const, text }] };
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return { content: [{ type: "text" as const, text: `Error: ${msg}` }], isError: true };
  }
});

// ── Resources ────────────────────────────────────────────────────────────────

server.setRequestHandler(ListResourcesRequestSchema, async () => {
  const wsId = WS_ID;
  const nodes = await apiFetch<ApiNode[]>(`/workspaces/${wsId}/nodes?limit=50`);
  
  return {
    resources: [
      {
        uri: "memtrace://guide/node",
        name: "Node Creation Guide",
        description: "建立節點前必讀：欄位規格、content_type 選擇規則、建立最佳實踐",
        mimeType: "text/markdown",
      },
      {
        uri: "memtrace://guide/edge",
        name: "Edge Creation Guide",
        description: "建立關聯邊的規格：relation 類型語意、weight 範圍、限制條件",
        mimeType: "text/markdown",
      },
      ...nodes.map(n => ({
        uri: `memtrace://node/${n.id}`,
        name: nodeTitle(n),
        description: `Full content of node ${n.id} (${n.content_type})`,
        mimeType: "text/markdown",
      }))
    ],
  };
});

server.setRequestHandler(ReadResourceRequestSchema, async (req) => {
  const uri = req.params.uri;
  if (uri === "memtrace://guide/node") {
    return { contents: [{ uri, mimeType: "text/markdown", text: NODE_GUIDE }] };
  }
  if (uri === "memtrace://guide/edge") {
    return { contents: [{ uri, mimeType: "text/markdown", text: EDGE_GUIDE }] };
  }

  if (uri.startsWith("memtrace://node/")) {
    const nodeId = uri.replace("memtrace://node/", "");
    const n = await apiFetch<ApiNode>(`/workspaces/${WS_ID}/nodes/${nodeId}`);
    return { contents: [{ uri, mimeType: "text/markdown", text: renderNode(n, true) }] };
  }
  
  if (uri.startsWith("memtrace://tag/")) {
    const tag = uri.replace("memtrace://tag/", "");
    const nodes = await apiFetch<ApiNode[]>(`/workspaces/${WS_ID}/nodes?tag=${tag}&limit=50`);
    const text = nodes.map(n => renderNode(n, true)).join("\n\n---\n\n");
    return { contents: [{ uri, mimeType: "text/markdown", text }] };
  }

  throw new Error(`Unknown resource: ${uri}`);
});

// ── Start ─────────────────────────────────────────────────────────────────────

if (!TOKEN) {
  console.error("⚠️  WARNING: MEMTRACE_TOKEN is not set.");
  console.error("   You will only be able to query and list public workspaces.");
  console.error("   Write tools (create/update/delete) are disabled.");
}

const transportMode = process.env.MCP_TRANSPORT ?? "stdio";

if (transportMode === "sse") {
  const app = express();
  const port = Number(process.env.MCP_PORT) || 3001;
  const sessions = new Map<string, SSEServerTransport>();

  app.get("/sse", async (_req: Request, res: Response) => {
    const sessionId = crypto.randomUUID();
    console.log(`New SSE connection: ${sessionId}`);
    const transport = new SSEServerTransport(`/messages?sessionId=${sessionId}`, res);
    sessions.set(sessionId, transport);
    res.on("close", () => {
      sessions.delete(sessionId);
      console.log(`SSE session closed: ${sessionId}`);
    });
    await server.connect(transport);
  });

  app.post("/messages", async (req: Request, res: Response) => {
    const sessionId = req.query.sessionId as string;
    const transport = sessions.get(sessionId);
    if (!transport) {
      res.status(400).send("Session not found or expired");
      return;
    }
    await transport.handlePostMessage(req, res);
  });

  app.listen(port, () => {
    console.log(`MemTrace MCP Server (SSE) listening on port ${port}`);
    console.log(`SSE endpoint: http://localhost:${port}/sse`);
    console.log(`Message endpoint: http://localhost:${port}/messages`);
  });
} else {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("MemTrace MCP Server (Stdio) running...");
}

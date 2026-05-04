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
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
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

## Fields
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| title_en | string | ✅ | English title |
| title_zh | string | Recommended | Chinese title (supports Chinese search) |
| content_type | enum | ✅ | Node type, see below |
| content_format | enum | ✅ | plain=Plain text, markdown=Markdown |
| body_zh | string | One of body_* | Chinese content |
| body_en | string | One of body_* | English content |
| tags | string[] | Optional | Classification tags |
| visibility | enum | Optional | public/team/private, default is private |
| source_type | enum | ✅ (AI) | AI agents must use "ai" |

## content_type Rules
- **factual**: Declarative facts (e.g., pgvector supports cosine similarity)
- **procedural**: Steps, processes, or guides (e.g., how to configure Google OAuth)
- **preference**: Preferences, decisions, or technology choices (e.g., we chose bcrypt as the hash algorithm)
- **context**: Background, project core goals, or design intentions (e.g., reasons for adopting a bilingual design)

## Best Practices
1. **Search first**: Always use \`search_nodes\` before creating to avoid duplicates.
2. **Singularity**: One node should only record one independent concept.
3. **Bilingual**: Provide both Chinese and English fields when possible to increase cross-language retrieval capabilities.
4. **Relationships**: Use the \`suggested_edges\` parameter to propose connections upon creation.
5. **Quality feedback**: After reading a node, if the information is highly valuable or incorrect, call \`vote_trust\` to adjust the trust score.
`;

const EDGE_GUIDE = `# MemTrace Edge Schema

## Relation Types
- **depends_on**: This node relies on the target node to function or be understood.
- **extends**: This node is a further expansion or specialization of the target node's concept.
- **related_to**: The two are related, but without a clear precedence or hierarchy.
- **contradicts**: This node has a logical conflict or version contradiction with the target node.

## Parameter Descriptions
- **weight**: Connection strength (0.1 to 1.0). Default is 1.0.
- **workspace_id**: Target workspace ID.

## Constraints & Details
- Multiple edges of the same type cannot exist between the same pair of nodes (A, B) (duplicate creation returns 409).
- For Editor roles, edge creation requests will enter the \`review_queue\` pending approval.
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

function createServer(): Server {
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
        "After reading the node, if the content is verified as correct and useful, it is recommended to call `vote_trust` or `confirm_node_validity` to provide quality signals and maintain the knowledge graph's vitality.\n" +
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
        "After reading the node, if the content is verified as correct and useful, it is recommended to call `vote_trust` or `confirm_node_validity` to provide quality signals and maintain the knowledge graph's vitality.\n" +
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
      description: `Create a new knowledge node, entering the _propose_change review process.

[Before creating] It is recommended to use search_nodes first to confirm there are no duplicate nodes.
[AI agent] Must include source_type: "ai".
[body] At least one of body_zh / body_en must be provided.

content_type selection:
- factual     = Declarative facts (e.g., pgvector supports cosine similarity)
- procedural  = Steps or processes (e.g., how to configure Google OAuth)
- preference  = Preferences or decisions (e.g., we chose bcrypt)
- context     = Background context (e.g., reasons for adopting a bilingual design)

Returns 201 = Created immediately; 202 + review_id = Entered review queue (editor role).`,
      inputSchema: {
        type: "object" as const,
        properties: {
          title_zh: { type: "string" },
          title_en: { type: "string" },
          content_type: { 
            type: "string", 
            enum: ["factual", "procedural", "preference", "context"],
            description: "factual=Declarative facts | procedural=Steps or processes | preference=Preferences or decisions | context=Background context"
          },
          content_format: { 
            type: "string", enum: ["plain", "markdown"],
            description: "plain=Plain text | markdown=Markdown format supported"
          },
          body_zh: { type: "string" },
          body_en: { type: "string" },
          tags: { type: "array", items: { type: "string" } },
          visibility: { 
            type: "string", enum: ["public", "team", "private"],
            description: "public=Visible to all | team=Workspace members | private=Only me"
          },
          source_type: {
            type: "string", enum: ["human", "ai"],
            description: "Caller identity, AI agents MUST pass 'ai'"
          },
          suggested_edges: {
            type: "array",
            description: "Propose associations with existing nodes simultaneously (not created immediately, enters review_queue)",
            items: {
              type: "object",
              properties: {
                to_id: { type: "string", description: "Target node ID, e.g. mem_d001" },
                relation: { type: "string", enum: ["depends_on", "extends", "related_to", "contradicts"] },
                weight: { type: "number", description: "Connection strength 0.1-1.0, default 1.0" }
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
      description: "Update an existing knowledge node. Only pass the fields to modify (partial update). Uses _propose_change process; editor proposals will enter the review queue. AI modifications must include source_type: 'ai'.",
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
      description: "Delete an existing knowledge node. Uses _propose_change process; for editor roles this is a 'proposed deletion', not executed immediately, and will enter the review_queue. AI operations should note this.",
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
      description: `Create an edge between two nodes. Ensure the nodes exist before creating (use get_node).

Relation semantics:
- depends_on: This node depends on the target node
- extends: Extends the target node's concept
- related_to: Related but no explicit dependency
- contradicts: Conflicts or contradicts the target node

Note: Duplicate relations of the same type between the same pair of nodes are not allowed; duplicates will return 409.`,
      inputSchema: {
        type: "object" as const,
        properties: {
          from_id: { type: "string", description: "Source node ID" },
          to_id: { type: "string", description: "Target node ID" },
          relation: { type: "string", enum: ["depends_on", "extends", "related_to", "contradicts"] },
          weight: { type: "number", description: "Connection strength 0.1-1.0, default 1.0" },
          workspace_id: { type: "string" }
        },
        required: ["from_id", "to_id", "relation"]
      }
    },
    {
      name: "traverse_edge",
      description: "Record that an edge was traversed, triggering the co-access boost mechanism (if both endpoint nodes were recently accessed, the edge weight increases). AI agents should call this tool after reasoning along an edge, allowing the graph's usage patterns to reflect actual reasoning paths.",
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
      description: "Rate the quality of a knowledge node. Accuracy represents content correctness, Utility represents content usefulness. The rating directly affects the node's Trust Score.",
      inputSchema: {
        type: "object" as const,
        properties: {
          node_id: { type: "string", description: "Target node ID" },
          accuracy: { type: "number", description: "1-5 score, accuracy rating" },
          utility: { type: "number", description: "1-5 score, utility rating" },
          workspace_id: { type: "string", description: "Target workspace ID" }
        },
        required: ["node_id", "accuracy", "utility"]
      }
    },
    {
      name: "list_review_queue",
      description: "List pending proposals in the review queue for the workspace. Can be used to confirm if an AI proposal has entered the queue.",
      inputSchema: {
        type: "object" as const,
        properties: {
          status: { type: "string", enum: ["pending", "accepted", "rejected"], description: "Default is pending" },
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
      description: "List nodes in the workspace where the body is empty (both English and Chinese are missing), so AI can find them and supply content.",
      inputSchema: {
        type: "object" as const,
        properties: {
          limit: { type: "number", description: "Max results (default 10)" },
          workspace_id: { type: "string", description: "Target workspace ID (omit to use server default)" },
        },
      },
    },
    {
      name: "get_schema",
      description: "Get the complete schema, valid values, and best practices for creating MemTrace nodes and edges. Please call this tool first if you are unsure about the field formats.",
      inputSchema: {
        type: "object" as const,
        properties: {
          topic: {
            type: "string",
            enum: ["node", "edge", "all"],
            description: "Query topic, default is all"
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

  return server;
}

// ── Start ─────────────────────────────────────────────────────────────────────

if (!TOKEN) {
  console.error("⚠️  WARNING: MEMTRACE_TOKEN is not set.");
  console.error("   You will only be able to query and list public workspaces.");
  console.error("   Write tools (create/update/delete) are disabled.");
}

const transportMode = process.env.MCP_TRANSPORT ?? "stdio";

if (transportMode === "sse") {
  const app = express();
  app.use(express.json());
  const port = Number(process.env.MCP_PORT) || 3001;

  // ── Optional bearer-token guard ───────────────────────────────────────────
  const SSE_TOKEN = process.env.MEMTRACE_SSE_TOKEN ?? "";

  function checkBearerToken(req: Request, res: Response): boolean {
    if (!SSE_TOKEN) return true;
    const auth = req.headers["authorization"] ?? "";
    const provided = auth.startsWith("Bearer ") ? auth.slice(7).trim() : "";
    if (provided !== SSE_TOKEN) {
      res.status(401).json({ error: "Unauthorized" });
      return false;
    }
    return true;
  }

  // ── Streamable HTTP transport (MCP spec 2025-03-26, used by Cursor) ───────
  // Note: no app-level auth here — network access is restricted by Tailscale.
  // Sending 401 would trigger Cursor's OAuth discovery flow and cause errors.
  const streamableSessions = new Map<string, StreamableHTTPServerTransport>();

  app.all("/mcp", async (req: Request, res: Response) => {
    const sessionId = req.headers["mcp-session-id"] as string | undefined;

    // Route to existing session
    if (sessionId && streamableSessions.has(sessionId)) {
      const transport = streamableSessions.get(sessionId)!;
      await transport.handleRequest(req, res, req.body);
      return;
    }

    // Reject non-init requests without a valid session
    if (sessionId) {
      res.status(404).json({ error: "Session not found or expired" });
      return;
    }

    // New session: only POST initialize is allowed without session ID
    if (req.method !== "POST") {
      res.status(400).json({ error: "New sessions must be initialized via POST" });
      return;
    }

    const transport = new StreamableHTTPServerTransport({
      sessionIdGenerator: () => crypto.randomUUID(),
      onsessioninitialized: (sid) => {
        streamableSessions.set(sid, transport);
        console.log(`Streamable HTTP session created: ${sid}`);
      },
    });

    transport.onclose = () => {
      if (transport.sessionId) {
        streamableSessions.delete(transport.sessionId);
        console.log(`Streamable HTTP session closed: ${transport.sessionId}`);
      }
    };

    const server = createServer();
    await server.connect(transport);
    await transport.handleRequest(req, res, req.body);
  });

  // ── Legacy SSE transport (used by Claude Code / older clients) ────────────
  const sseSessions = new Map<string, SSEServerTransport>();

  app.get("/sse", async (req: Request, res: Response) => {
    if (!checkBearerToken(req, res)) return;
    const sessionId = crypto.randomUUID();
    console.log(`SSE session created: ${sessionId}`);
    const transport = new SSEServerTransport(`/messages?sessionId=${sessionId}`, res);
    sseSessions.set(sessionId, transport);
    res.on("close", () => {
      sseSessions.delete(sessionId);
      console.log(`SSE session closed: ${sessionId}`);
    });
    const server = createServer();
    await server.connect(transport);
  });

  app.post("/messages", async (req: Request, res: Response) => {
    const sessionId = req.query.sessionId as string;
    const transport = sseSessions.get(sessionId);
    if (!transport) {
      res.status(400).send("Session not found or expired");
      return;
    }
    await transport.handlePostMessage(req, res);
  });

  app.listen(port, () => {
    console.log(`MemTrace MCP Server (SSE) listening on port ${port}`);
    console.log(`  Streamable HTTP : http://localhost:${port}/mcp  (Cursor / modern clients, Tailscale-only)`);
    console.log(`  Legacy SSE      : http://localhost:${port}/sse  (Claude Code / older clients, token-guarded)`);
  });
} else {
  const transport = new StdioServerTransport();
  const server = createServer();
  await server.connect(transport);
  console.error("MemTrace MCP Server (Stdio) running...");
}

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
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

// ── Config ────────────────────────────────────────────────────────────────────

const API_BASE = process.env.MEMTRACE_API ?? "http://localhost:8000/api/v1";
const WS_ID    = process.env.MEMTRACE_WS   ?? "ws_spec0001";
const LANG     = process.env.MEMTRACE_LANG ?? "zh-TW";
const TOKEN    = process.env.MEMTRACE_TOKEN ?? "";

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
    const errText = await res.text();
    throw new Error(`API ${res.status}: ${errText}`);
  }
  const contentType = res.headers.get("content-type");
  if (contentType && contentType.includes("application/json")) {
    return res.json() as Promise<T>;
  }
  return null as unknown as T;
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

// ── Tool implementations ──────────────────────────────────────────────────────

async function createNode(data: any, wsId: string = WS_ID): Promise<string> {
  if (!TOKEN) throw new Error("Write operations require MEMTRACE_TOKEN configuration.");
  const res = await apiFetch<any>(`/workspaces/${wsId}/nodes`, { method: "POST", body: data });
  // Could return proposed review info if it was submitted to review queue
  if (res?.detail?.includes("submitted for review") || res?.review_id) {
    return `Proposed node creation. It has been queued for review.\n${JSON.stringify(res)}`;
  }
  return `Created node successfully:\n${JSON.stringify(res)}`;
}

async function updateNode(nodeId: string, data: any, wsId: string = WS_ID): Promise<string> {
  if (!TOKEN) throw new Error("Write operations require MEMTRACE_TOKEN configuration.");
  const res = await apiFetch<any>(`/workspaces/${wsId}/nodes/${nodeId}`, { method: "PATCH", body: data });
  if (res?.detail?.includes("submitted for review") || res?.review_id) {
    return `Proposed node update for ${nodeId}. It has been queued for review.\n${JSON.stringify(res)}`;
  }
  return `Updated node ${nodeId} successfully:\n${JSON.stringify(res)}`;
}

async function deleteNode(nodeId: string, wsId: string = WS_ID): Promise<string> {
  if (!TOKEN) throw new Error("Write operations require MEMTRACE_TOKEN configuration.");
  await apiFetch<any>(`/workspaces/${wsId}/nodes/${nodeId}`, { method: "DELETE" });
  return `Requested deletion for node ${nodeId}. Check review queue for pending review.`;
}

async function searchNodes(query: string, limit = 8, wsId: string = WS_ID): Promise<string> {
  const params = new URLSearchParams({ q: query, limit: String(limit) });
  const nodes = await apiFetch<ApiNode[]>(
    `/workspaces/${wsId}/nodes?${params}`
  );
  if (nodes.length === 0) return `No nodes found for query: "${query}" in workspace ${wsId}`;
  return [
    `Found **${nodes.length}** node(s) matching "${query}":\n`,
    ...nodes.map((n) => renderNode(n, true)),
  ].join("\n\n---\n\n");
}

async function getNode(nodeId: string, wsId: string = WS_ID): Promise<string> {
  try {
    const n = await apiFetch<ApiNode>(`/workspaces/${wsId}/nodes/${nodeId}`);
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
  { capabilities: { tools: {} } }
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
        "Retrieve a specific MemTrace knowledge node by its ID (e.g. mem_d001, mem_p003). Returns full content and metadata.\nPass `workspace_id` to query a specific KB; omit to use the configured default (`MEMTRACE_WS`).",
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
        "Get a node and its direct associations (upstream/downstream). Useful for understanding how concepts relate to each other. Set depth=2 to also include full content of neighbour nodes.\nPass `workspace_id` to query a specific KB; omit to use the configured default (`MEMTRACE_WS`).",
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
      description: "Create a new memory node. Uses the _propose_change flow.",
      inputSchema: {
        type: "object" as const,
        properties: {
          title_zh: { type: "string" },
          title_en: { type: "string" },
          content_type: { type: "string" },
          content_format: { type: "string" },
          body_zh: { type: "string" },
          body_en: { type: "string" },
          tags: { type: "array", items: { type: "string" } },
          visibility: { type: "string" },
          workspace_id: { type: "string", description: "Target workspace ID" }
        },
        required: ["title_en", "content_type", "content_format"]
      }
    },
    {
      name: "update_node",
      description: "Update an existing memory node. Uses the _propose_change flow.",
      inputSchema: {
        type: "object" as const,
        properties: {
          node_id: { type: "string", description: "Target node ID" },
          title_zh: { type: "string" },
          title_en: { type: "string" },
          content_type: { type: "string" },
          content_format: { type: "string" },
          body_zh: { type: "string" },
          body_en: { type: "string" },
          tags: { type: "array", items: { type: "string" } },
          visibility: { type: "string" },
          workspace_id: { type: "string", description: "Target workspace ID" }
        },
        required: ["node_id"]
      }
    },
    {
      name: "delete_node",
      description: "Delete an existing memory node. Uses the _propose_change flow.",
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
      name: "list_workspaces",
      description: "List all accessible workspaces (requires valid MEMTRACE_TOKEN). Returns available workspace IDs and metadata.",
      inputSchema: {
        type: "object" as const,
        properties: {
          limit: { type: "number", description: "Max results (default 20)" },
        },
      },
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
      default:
        return { content: [{ type: "text" as const, text: `Unknown tool: ${name}` }], isError: true };
    }
    return { content: [{ type: "text" as const, text }] };
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return { content: [{ type: "text" as const, text: `Error: ${msg}` }], isError: true };
  }
});

// ── Start ─────────────────────────────────────────────────────────────────────

if (!TOKEN) {
  console.error("⚠️  WARNING: MEMTRACE_TOKEN is not set.");
  console.error("   You will only be able to query and list public workspaces.");
  console.error("   Write tools (create/update/delete) are disabled.");
}

const transport = new StdioServerTransport();
await server.connect(transport);

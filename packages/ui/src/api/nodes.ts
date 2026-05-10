import { BASE, request } from './client';
import type { Edge } from './edges';

export interface Node {
  id: string;
  workspace_id: string;
  title_zh: string;
  title_en: string;
  content_type: string;
  content_format: string;
  body_zh: string;
  body_en: string;
  tags: string[];
  visibility: string;
  author: string;
  trust_score: number;
  dim_accuracy: number;
  dim_freshness: number;
  dim_utility: number;
  dim_author_rep: number;
  traversal_count: number;
  unique_traverser_count: number;
  created_at: string;
  updated_at?: string;
  signature: string;
  source_type: string;
  status: string;
  copied_from_node?: string;
  copied_from_ws?: string;
  archived_at?: string | null;
  validity_confirmed_at?: string | null;
  validity_confirmed_by?: string | null;
  content_stripped?: boolean;
  ask_count: number;
}

export interface NodeCreatePayload {
  title_zh: string;
  title_en: string;
  content_type: string;
  content_format: string;
  body_zh: string;
  body_en: string;
  tags: string[];
  visibility: string;
  copied_from_node?: string;
  copied_from_ws?: string;
}

export interface NodeRevisionMeta {
  id: string;
  node_id: string;
  workspace_id: string;
  revision_no: number;
  signature: string;
  proposer_type: "human" | "ai";
  proposer_id?: string | null;
  review_id?: string | null;
  created_at: string;
}

export interface NodeRevision extends NodeRevisionMeta {
  snapshot: NodeCreatePayload;
}

export interface NodeHealthScore {
  node_id: string;
  score: number;
  label: "healthy" | "warning" | "critical";
  reason: string;
}

export interface NeighborhoodResponse {
  root_id: string;
  depth: number;
  nodes: Node[];
  edges: Edge[];
  truncated: boolean;
  total_nodes: number;
}

export interface ValidityConfirmation {
  confirmed_at: string;
  confirmed_by: string;
}

export interface DiffTextEntry {
  op: "add" | "remove" | "keep";
  text: string;
}

export interface DiffField {
  type: "scalar" | "set" | "text";
  before?: unknown;
  after?: unknown;
  added?: string[];
  removed?: string[];
  line_diff?: DiffTextEntry[];
}

export interface DiffSummary {
  change_type: "create" | "update" | "delete";
  changed_fields: string[];
  field_count: number;
  fields: Record<string, DiffField>;
}

export interface ApiMessage {
  detail?: string;
  message?: string;
  review_id?: string;
  status?: string;
}

export const nodes = {
  list: (wsId: string, params?: Record<string, string | number>) => {
    const stringParams: Record<string, string> = {};
    if (params) {
      Object.entries(params).forEach(([k, v]) => { stringParams[k] = String(v); });
    }
    const qs = params ? `?${new URLSearchParams(stringParams).toString()}` : "";
    return request<Node[]>("GET", `${BASE}/workspaces/${wsId}/nodes${qs}`);
  },
  get: (wsId: string, nodeId: string) => request<Node>("GET", `${BASE}/workspaces/${wsId}/nodes/${nodeId}`),
  create: (wsId: string, data: NodeCreatePayload) => request<Node | ApiMessage>("POST", `${BASE}/workspaces/${wsId}/nodes`, data),
  update: (wsId: string, nodeId: string, data: Partial<NodeCreatePayload>) =>
    request<Node | ApiMessage>("PATCH", `${BASE}/workspaces/${wsId}/nodes/${nodeId}`, data),
  delete: (wsId: string, nodeId: string) => request("DELETE", `${BASE}/workspaces/${wsId}/nodes/${nodeId}`),
  traverse: (nodeId: string) => request("POST", `${BASE}/nodes/${nodeId}/traverse`),
  searchSemantic: (wsId: string, query: string, limit = 10) =>
    request<Node[]>("POST", `${BASE}/workspaces/${wsId}/nodes/search-semantic?query=${encodeURIComponent(query)}&limit=${limit}`),
  neighborhood: (wsId: string, nodeId: string, params?: { depth?: number; relation?: string; direction?: string; include_source?: boolean }) => {
    const qs = params ? `?${new URLSearchParams(params as any).toString()}` : "";
    return request<NeighborhoodResponse>("GET", `${BASE}/workspaces/${wsId}/nodes/${nodeId}/neighborhood${qs}`);
  },
  revisions: (wsId: string, nodeId: string) =>
    request<NodeRevisionMeta[]>("GET", `${BASE}/workspaces/${wsId}/nodes/${nodeId}/revisions`),
  revision: (wsId: string, nodeId: string, revisionNo: number) =>
    request<NodeRevision>("GET", `${BASE}/workspaces/${wsId}/nodes/${nodeId}/revisions/${revisionNo}`),
  diffRevisions: (wsId: string, nodeId: string, a: number, b: number) =>
    request<DiffSummary>("GET", `${BASE}/workspaces/${wsId}/nodes/${nodeId}/revisions/${a}/diff/${b}`),
  restoreRevision: (wsId: string, nodeId: string, revisionNo: number) =>
    request<ApiMessage>("POST", `${BASE}/workspaces/${wsId}/nodes/${nodeId}/revisions/${revisionNo}/restore`),
  confirmValidity: (wsId: string, nodeId: string) =>
    request<ValidityConfirmation>("POST", `${BASE}/workspaces/${wsId}/nodes/${nodeId}/confirm-validity`),
  archive: (wsId: string, nodeId: string) =>
    request<void>("POST", `${BASE}/workspaces/${wsId}/nodes/${nodeId}/archive`),
  restore: (wsId: string, nodeId: string) =>
    request<void>("POST", `${BASE}/workspaces/${wsId}/nodes/${nodeId}/restore`),
  bulkArchive: (wsId: string, nodeIds: string[]) =>
    request<{ archived_count: number }>("POST", `${BASE}/workspaces/${wsId}/nodes/bulk-archive`, { node_ids: nodeIds }),
  bulkDelete: (wsId: string, nodeIds: string[]) =>
    request<{ deleted_count: number }>("POST", `${BASE}/workspaces/${wsId}/nodes/bulk-delete`, { node_ids: nodeIds }),
  healthScores: (wsId: string) =>
    request<NodeHealthScore[]>("GET", `${BASE}/workspaces/${wsId}/nodes/health-scores`),
  suggestEdges: (wsId: string, nodeId: string) =>
    request<any[]>("POST", `${BASE}/workspaces/${wsId}/nodes/${nodeId}/suggest-edges`),
  voteTrust: (wsId: string, nodeId: string, data: { accuracy: number; utility: number }) =>
    request<{ status: string; trust_score: number }>("POST", `${BASE}/workspaces/${wsId}/nodes/${nodeId}/vote-trust`, data),
};

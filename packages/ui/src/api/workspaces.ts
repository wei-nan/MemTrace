import { BASE, request, authHeaders, writeHeaders } from './client';
import type { Node } from './nodes';

export interface Workspace {
  id: string;
  name_zh: string;
  name_en: string;
  visibility: string;
  kb_type: "evergreen" | "ephemeral";
  owner_id: string;
  created_at: string;
  updated_at: string;
  my_role: "admin" | "editor" | "viewer" | null;
  embedding_model: string;
  embedding_dim: number;
  qa_archive_mode: "auto_active" | "manual_review";
  extraction_provider: string | null;
  auto_split: boolean;
  settings: {
    node_complexity: {
      enabled: boolean;
      char_threshold: number;
      auto_split: boolean;
    };
    auto_dedup_threshold: number;
    mcp_ingest_enabled: boolean;
    mcp_ingest_daily_quota: number;
  };
}

export interface Member {
  user_id: string;
  display_name: string;
  email: string;
  role: string;
  joined_at: string;
}

export interface Invite {
  id: string;
  workspace_id: string;
  email?: string | null;
  role: string;
  token: string;
  inviter_id: string;
  created_at: string;
  expires_at: string;
  accepted_at: string | null;
  invite_url?: string | null;
}

export interface WorkspaceCloneJob {
  id: string;
  source_ws_id: string;
  target_ws_id: string;
  status: "pending" | "running" | "cancelling" | "cancelled" | "completed" | "failed";
  total_nodes: number;
  processed_nodes: number;
  is_fork: boolean;
  error_msg?: string;
  cancelled_at?: string;
  created_at: string;
  updated_at: string;
}

export interface GraphPreview {
  nodes: { preview_id: string; content_type: string }[];
  edges: { from_preview_id: string; to_preview_id: string; relation: string }[];
}

export interface WorkspaceAssociation {
  id: string;
  source_ws_id: string;
  target_ws_id: string;
  target_name_en: string;
  target_name_zh: string;
  created_at: string;
}

export interface JoinRequest {
  id: string;
  workspace_id: string;
  user_id: string;
  message: string | null;
  status: "pending" | "approved" | "rejected";
  requested_at: string;
  reviewed_at: string | null;
  reviewed_by: string | null;
}

export interface KBExportRequest {
  include_markdown?: boolean;
  include_archived?: boolean;
  tags?: string[];
  date_from?: string;
  date_to?: string;
}

export interface KBExport {
  id: string;
  workspace_id: string;
  status: "pending" | "processing" | "completed" | "failed";
  download_url?: string;
  file_path?: string;
  filter_params?: Record<string, unknown>;
  error_msg?: string;
  created_at: string;
  completed_at?: string;
}

export interface KBImportResponse {
  imported_nodes: number;
  skipped: number;
  failed: number;
  errors: string[];
}

export interface WorkspaceAnalytics {
  total_nodes: number;
  active_edges: number;
  orphan_node_count: number;
  avg_trust_score: number;
  faded_edge_ratio: number;
  monthly_traversal_count: number;
  kb_type: string;
  top_nodes: Array<{ id: string; title: string; traversal_count: number }>;
  kb_type_metrics: Record<string, number>;
  traversal_trend: Array<{ date: string; count: number }>;
}

export interface TokenEfficiency {
  avg_tokens_per_query: number;
  estimated_full_doc_tokens: number;
  savings_ratio: number;
  monthly_query_count: number;
}

export interface PersonalApiKey {
  id: string;
  name: string;
  prefix: string;
  created_at: string;
  last_used_at: string | null;
  expires_at: string | null;
  revoked_at: string | null;
  // Note: scopes and workspace_id removed in Phase 4.10.
  // Role is now inherited dynamically from workspace_members.
}

export interface PersonalApiKeyCreateResponse extends PersonalApiKey {
  key: string;
}

export const workspaces = {
  list: (search?: string) => request<Workspace[]>("GET", `${BASE}/workspaces${search ? `?search=${encodeURIComponent(search)}` : ""}`),
  create: (data: {
    name_zh: string;
    name_en: string;
    visibility: string;
    kb_type: "evergreen" | "ephemeral";
    embedding_model?: string;
    qa_archive_mode?: "auto_active" | "manual_review";
  }) =>
    request<Workspace>("POST", `${BASE}/workspaces`, data),
  get: (id: string) => request<Workspace>("GET", `${BASE}/workspaces/${id}`),
  members: (wsId: string) => request<Member[]>("GET", `${BASE}/workspaces/${wsId}/members`),
  invites: (wsId: string) => request<Invite[]>("GET", `${BASE}/workspaces/${wsId}/invites`),
  createInvite: (wsId: string, data: { email?: string; role: string; expires_in_days?: number }) =>
    request<Invite>("POST", `${BASE}/workspaces/${wsId}/invites`, data),
  acceptInvite: (token: string) => request("POST", `/workspaces/invites/${token}/accept`),
  deleteInvite: (id: string) => request("DELETE", `/workspaces/invites/${id}`),
  updateMember: (wsId: string, userId: string, role: string) =>
    request("PUT", `${BASE}/workspaces/${wsId}/members/${userId}`, { role }),
  removeMember: (wsId: string, userId: string) =>
    request("DELETE", `${BASE}/workspaces/${wsId}/members/${userId}`),
  detectLinks: (wsId: string) =>
    request<{ message: string; nodes_checked: number }>("POST", `${BASE}/workspaces/${wsId}/nodes/detect-links`),
  update: (wsId: string, data: Partial<{ 
    name_zh: string; 
    name_en: string; 
    visibility: string; 
    qa_archive_mode: string;
    auto_split: boolean;
    settings: any;
  }>) =>
    request<Workspace>("PATCH", `${BASE}/workspaces/${wsId}`, data),
  delete: (wsId: string) => request("DELETE", `${BASE}/workspaces/${wsId}`),
  clone: (wsId: string, data: { name_zh?: string; name_en?: string; new_embedding_model?: string; visibility?: string }) =>
    request<WorkspaceCloneJob>("POST", `${BASE}/workspaces/${wsId}/clone`, data),
  fork: (wsId: string, data: { name_zh: string; name_en: string; embedding_model?: string }) =>
    request<WorkspaceCloneJob>("POST", `${BASE}/workspaces/${wsId}/fork`, data),
  cancelCloneJob: (jobId: string) =>
    request("POST", `${BASE}/clone-jobs/${jobId}/cancel`),
  reembedAll: (wsId: string) =>
    request<{ queued: number }>("POST", `${BASE}/workspaces/${wsId}/reembed-all`),
  getCloneStatus: (wsId: string) =>
    request<WorkspaceCloneJob | null>("GET", `${BASE}/workspaces/${wsId}/clone-status`),
  graphPreview: (wsId: string) => request<GraphPreview>("GET", `${BASE}/workspaces/${wsId}/graph-preview`),
  listAssociations: (wsId: string) => request<WorkspaceAssociation[]>("GET", `${BASE}/workspaces/${wsId}/associations`),
  createAssociation: (wsId: string, targetWsId: string) =>
    request<WorkspaceAssociation>("POST", `${BASE}/workspaces/${wsId}/associations/${targetWsId}`),
  deleteAssociation: (wsId: string, targetWsId: string) =>
    request("DELETE", `${BASE}/workspaces/${wsId}/associations/${targetWsId}`),
  joinRequests: (wsId: string, status = "pending") =>
    request<JoinRequest[]>(`GET`, `${BASE}/workspaces/${wsId}/join-requests?status=${status}`),
  createJoinRequest: (wsId: string, message?: string) =>
    request<JoinRequest>("POST", `${BASE}/workspaces/${wsId}/join-requests`, { message }),
  approveJoinRequest: (wsId: string, reqId: string) =>
    request<JoinRequest>("POST", `${BASE}/workspaces/${wsId}/join-requests/${reqId}/approve`),
  rejectJoinRequest: (wsId: string, reqId: string) =>
    request<JoinRequest>("POST", `${BASE}/workspaces/${wsId}/join-requests/${reqId}/reject`),
  createExport: (wsId: string, data: KBExportRequest) =>
    request<KBExport>("POST", `${BASE}/workspaces/${wsId}/exports`, data),
  listExports: (wsId: string) => request<KBExport[]>("GET", `${BASE}/workspaces/${wsId}/exports`),
  getExport: (wsId: string, expId: string) => request<KBExport>("GET", `${BASE}/workspaces/${wsId}/exports/${expId}`),
  importKb: (wsId: string, file: File, conflictMode: 'skip' | 'overwrite' = 'skip') => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('conflict_mode', conflictMode);
    return fetch(`${BASE}/workspaces/${wsId}/imports`, {
      method: 'POST',
      headers: { ...authHeaders(), ...writeHeaders() },
      body: formData,
    }).then(async (res) => {
      if (!res.ok) throw new Error((await res.json().catch(() => ({ detail: res.statusText }))).detail ?? res.statusText);
      return res.json() as Promise<KBImportResponse>;
    });
  },
  analytics: (wsId: string) => request<WorkspaceAnalytics>("GET", `${BASE}/workspaces/${wsId}/analytics`),
  tokenEfficiency: (wsId: string) => request<TokenEfficiency>("GET", `${BASE}/workspaces/${wsId}/analytics/token-efficiency`),
  tableView: (wsId: string, params: { q?: string; filter?: string; limit?: number; offset?: number; sort_by?: string; order?: 'asc' | 'desc' }) => {
    const qs = new URLSearchParams(params as any).toString();
    return request<{ nodes: Node[]; total_count: number }>("GET", `${BASE}/workspaces/${wsId}/table-view?${qs}`);
  },
  listApiKeys: (wsId: string) => request<PersonalApiKey[]>("GET", `${BASE}/workspaces/${wsId}/api-keys`),
  createApiKey: (wsId: string, data: { name: string; scope: string }) =>
    request<PersonalApiKeyCreateResponse>("POST", `${BASE}/workspaces/${wsId}/api-keys`, { ...data, scopes: [data.scope] }),
  rotateApiKey: (wsId: string, keyId: string) =>
    request<PersonalApiKeyCreateResponse>("POST", `${BASE}/workspaces/${wsId}/api-keys/${keyId}/rotate`),
  revokeApiKey: (wsId: string, keyId: string) =>
    request("DELETE", `${BASE}/workspaces/${wsId}/api-keys/${keyId}`),
  getDecayStats: (wsId: string) => request<any>("GET", `${BASE}/workspaces/${wsId}/decay-stats`),
  getHealthReport: (ws_id: string) => request<any>("GET", `${BASE}/workspaces/${ws_id}/nodes/health`),
  topGaps: (ws_id: string) => request<Array<{ id: string; title_zh: string; title_en: string; status: string; ask_count: number }>>("GET", `${BASE}/workspaces/${ws_id}/stats/top-gaps`),
};

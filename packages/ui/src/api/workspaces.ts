import { BASE, request, authHeaders, writeHeaders } from './client';
import type { Node } from './nodes';

export interface ExploreWorkspace {
  id: string;
  name: string;
  description: string | null;
  language: "zh-TW" | "en";
  visibility: string;
  kb_type: "evergreen" | "ephemeral";
  owner_id: string;
  owner_display_name: string;
  node_count: number;
  created_at: string;
  my_role: "admin" | "editor" | "viewer" | null;
}

export interface Workspace {
  id: string;
  name: string;
  description?: string | null;
  language: "zh-TW" | "en";
  linked_workspace_id: string | null;
  visibility: string;
  kb_type: "evergreen" | "ephemeral";
  owner_id: string;
  created_at: string;
  updated_at: string;
  my_role: "admin" | "editor" | "viewer" | null;
  embedding_provider: string;
  embedding_model: string;
  embedding_dim: number;
  migration_status: "none" | "in_progress" | "completed" | "failed";
  migrating_to_provider: string | null;
  migrating_to_model: string | null;
  qa_archive_mode: "auto_active" | "manual_review";
  extraction_provider: string | null;
  auto_split: boolean;
  consult_trust_tier: "ask" | "full_trust";
  consult_provider: string | null;
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
  target_name: string;
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

export interface JobRun {
  id: string;
  job_name: string;
  workspace_id: string | null;
  trigger: string;
  status: 'running' | 'success' | 'failed' | 'skipped';
  started_at: string;
  finished_at: string | null;
  duration_ms: number | null;
  scanned_count: number | null;
  processed_count: number | null;
  created_count: number | null;
  skipped_count: number | null;
  failed_count: number | null;
  error: string | null;
  summary: Record<string, any> | null;
}

export interface SchedulerHeartbeat {
  job_name: string;
  status: string;
  last_run_at: string | null;
  last_success_at: string | null;
  last_failure_at: string | null;
  duration_ms: number | null;
  run_count: number;
  failure_count: number;
  last_run_id: string | null;
  last_error: string | null;
  metadata: Record<string, any> | null;
  updated_at: string;
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
  full_context_reduction_ratio: number;
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
  explore: (params?: { q?: string; lang?: string; sort?: 'newest' | 'nodes' }) => {
    const qs = new URLSearchParams();
    if (params?.q) qs.set('q', params.q);
    if (params?.lang) qs.set('lang', params.lang);
    if (params?.sort) qs.set('sort', params.sort);
    const query = qs.toString();
    return request<ExploreWorkspace[]>("GET", `${BASE}/workspaces/explore${query ? `?${query}` : ''}`);
  },
  create: (data: {
    name: string;
    language: "zh-TW" | "en";
    visibility: string;
    kb_type: "evergreen" | "ephemeral";
    embedding_model?: string;
    qa_archive_mode?: "auto_active" | "manual_review";
    auto_split?: boolean;
    extraction_provider?: string | null;
    settings?: {
      mcp_ingest_enabled?: boolean;
      mcp_ingest_daily_quota?: number;
    };
  }) =>
    request<Workspace>("POST", `${BASE}/workspaces`, data),
  get: (id: string) => request<Workspace>("GET", `${BASE}/workspaces/${id}`),
  members: (wsId: string) => request<Member[]>("GET", `${BASE}/workspaces/${wsId}/members`),
  invites: (wsId: string) => request<Invite[]>("GET", `${BASE}/workspaces/${wsId}/invites`),
  createInvite: (wsId: string, data: { email?: string; role: string; expires_in_days?: number }) =>
    request<Invite>("POST", `${BASE}/workspaces/${wsId}/invites`, data),
  acceptInvite: (token: string) => request("POST", `${BASE}/workspaces/invites/${token}/accept`),
  deleteInvite: (id: string) => request("DELETE", `${BASE}/workspaces/invites/${id}`),
  updateMember: (wsId: string, userId: string, role: string) =>
    request("PUT", `${BASE}/workspaces/${wsId}/members/${userId}`, { role }),
  removeMember: (wsId: string, userId: string) =>
    request("DELETE", `${BASE}/workspaces/${wsId}/members/${userId}`),
  detectLinks: (wsId: string) =>
    request<{ message: string; nodes_checked: number }>("POST", `${BASE}/workspaces/${wsId}/nodes/detect-links`),
  update: (wsId: string, data: Partial<{
    name: string;
    description: string | null;
    language: "zh-TW" | "en";
    visibility: string;
    qa_archive_mode: string;
    auto_split: boolean;
    migration_status: string;
    migrating_to_provider: string;
    migrating_to_model: string;
    settings: any;
    consult_trust_tier: "ask" | "full_trust";
    consult_provider: string | null;
  }>) =>
    request<Workspace>("PATCH", `${BASE}/workspaces/${wsId}`, data),
  delete: (wsId: string) => request("DELETE", `${BASE}/workspaces/${wsId}`),
  clone: (wsId: string, data: { name?: string; new_embedding_model?: string; visibility?: string }) =>
    request<WorkspaceCloneJob>("POST", `${BASE}/workspaces/${wsId}/clone`, data),
  fork: (wsId: string, data: { name: string; embedding_model?: string }) =>
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
  tableView: (wsId: string, params: { q?: string; filter?: string; limit?: number; offset?: number; sort_by?: string; order?: 'asc' | 'desc'; resolution_status?: string }) => {
    const cleanParams: any = {};
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null) {
        cleanParams[k] = String(v);
      }
    });
    const qs = new URLSearchParams(cleanParams).toString();
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
  topGaps: (ws_id: string) => request<Array<{ id: string; title: string; status: string; ask_count: number }>>("GET", `${BASE}/workspaces/${ws_id}/stats/top-gaps`),
  summarizeCluster: (wsId: string, nodeIds: string[]) => request<{ summary_node_id: string | null }>("POST", `${BASE}/workspaces/${wsId}/maintenance/summarize-cluster`, { node_ids: nodeIds }),
  complementLanguages: (wsId: string, nodeIds: string[]) => request<{ results: any[] }>("POST", `${BASE}/workspaces/${wsId}/maintenance/complement-languages`, { node_ids: nodeIds }),
  suggestEdges: (wsId: string, nodeId: string, limit = 5) => request<{ proposed: number }>("POST", `${BASE}/workspaces/${wsId}/maintenance/suggest-edges`, { node_id: nodeId, limit }),
  getFailedEmbeddings: (wsId: string) => request<{ count: number }>("GET", `${BASE}/workspaces/${wsId}/failed-embeddings`),
  retryFailedEmbeddings: (wsId: string) => request<{ queued: number }>("POST", `${BASE}/workspaces/${wsId}/retry-failed-embeddings`),
  jobRuns: (wsId: string, params?: { job_name?: string; status?: string; limit?: number; offset?: number }) => {
    const qs = new URLSearchParams();
    if (params?.job_name) qs.set('job_name', params.job_name);
    if (params?.status) qs.set('status', params.status);
    if (params?.limit != null) qs.set('limit', String(params.limit));
    if (params?.offset != null) qs.set('offset', String(params.offset));
    const q = qs.toString();
    return request<{ runs: JobRun[]; total: number; offset: number }>("GET", `${BASE}/workspaces/${wsId}/job-runs${q ? `?${q}` : ''}`);
  },
  schedulerHeartbeats: (wsId: string) =>
    request<{ heartbeats: SchedulerHeartbeat[]; total: number }>("GET", `${BASE}/workspaces/${wsId}/scheduler-heartbeats`),
};

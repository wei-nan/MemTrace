const BASE = "/api/v1";

function authHeaders(): HeadersInit {
  const token = localStorage.getItem("mt_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(path, {
    method,
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const auth = {
  register: (data: { display_name: string; email: string; password: string }) =>
    request<{ access_token: string }>("POST", "/auth/register", data),
  login: (data: { email: string; password: string }) =>
    request<{ access_token: string }>("POST", "/auth/login", data),
  logout: () => request("POST", "/auth/logout"),
  me: () => request<{ id: string; display_name: string; email: string; email_verified: boolean }>("GET", "/auth/me"),
  verifyEmail: (token: string) => request("POST", `/auth/verify-email/${token}`),
  resendVerification: () => request("POST", "/auth/resend-verification-email"),
  forgotPassword: (email: string) => request("POST", "/auth/forgot-password", { email }),
  resetPassword: (token: string, password: string) => request("POST", "/auth/reset-password", { token, new_password: password }),
  getOnboarding: () => request<Onboarding>("GET", "/auth/me/onboarding"),
  updateOnboarding: (data: Partial<Onboarding>) => request<Onboarding>("PATCH", "/auth/me/onboarding", data),
};

export const workspaces = {
  list: (search?: string) => request<Workspace[]>("GET", `${BASE}/workspaces${search ? `?search=${encodeURIComponent(search)}` : ""}`),
  create: (data: { name_zh: string; name_en: string; visibility: string; kb_type: "evergreen" | "ephemeral" }) =>
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
  update: (wsId: string, data: Partial<{ name_zh: string; name_en: string; visibility: string }>) =>
    request<Workspace>("PATCH", `${BASE}/workspaces/${wsId}`, data),
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
      headers: { ...authHeaders() },
      body: formData,
    }).then(async (res) => {
      if (!res.ok) throw new Error((await res.json().catch(() => ({ detail: res.statusText }))).detail ?? res.statusText);
      return res.json() as Promise<KBImportResponse>;
    });
  },
  analytics: (wsId: string) => request<WorkspaceAnalytics>("GET", `${BASE}/workspaces/${wsId}/analytics`),
  tokenEfficiency: (wsId: string) => request<TokenEfficiency>("GET", `${BASE}/workspaces/${wsId}/analytics/token-efficiency`),
};

export const nodes = {
  list: (wsId: string, params?: Record<string, string>) => {
    const qs = params ? `?${new URLSearchParams(params).toString()}` : "";
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
  healthScores: (wsId: string) =>
    request<NodeHealthScore[]>("GET", `${BASE}/workspaces/${wsId}/nodes/health-scores`),
};

export const edges = {
  list: (wsId: string, nodeId?: string) => request<Edge[]>("GET", `${BASE}/workspaces/${wsId}/edges${nodeId ? `?node_id=${nodeId}` : ""}`),
  create: (wsId: string, data: EdgeCreatePayload) => request<Edge>("POST", `${BASE}/workspaces/${wsId}/edges`, data),
  traverse: (edgeId: string, note?: string) => request("POST", `${BASE}/edges/${edgeId}/traverse`, { note }),
  rate: (edgeId: string, rating: number, note?: string) => request("POST", `${BASE}/edges/${edgeId}/rate`, { rating, note }),
  connectOrphans: (wsId: string) => request<{ message: string; orphan_count?: number }>("POST", `${BASE}/workspaces/${wsId}/edges/connect-orphans`),
};

export const ai = {
  listKeys: () => request<AIKey[]>("GET", `${BASE}/ai/keys`),
  createKey: (data: { provider: string; api_key: string }) => request<AIKey>("POST", `${BASE}/ai/keys`, data),
  deleteKey: (provider: string) => request("DELETE", `${BASE}/ai/keys/${provider}`),
  getCredits: () => request<CreditStatus>("GET", `${BASE}/ai/credits`),
  extract: (data: unknown) => request("POST", `${BASE}/ai/extract`, data),
  restructure: (data: unknown) => request("POST", `${BASE}/ai/restructure`, data),
  chat: (data: unknown) => request<ChatResponse>("POST", `${BASE}/ai/chat`, data),
  listModels: (provider: string) => request<ModelInfo[]>("GET", `${BASE}/ai/models/${provider}`),
};

export const review = {
  list: (wsId: string, status = "pending") => request<ReviewItem[]>("GET", `${BASE}/workspaces/${wsId}/review-queue?status=${status}`),
  update: (id: string, data: { node_data?: Record<string, unknown>; suggested_edges?: unknown[]; review_notes?: string }) =>
    request<ReviewItem>("PATCH", `${BASE}/workspaces/review-queue/${id}`, data),
  accept: (id: string) => request<Node | null>("POST", `${BASE}/workspaces/review-queue/${id}/accept`),
  reject: (id: string) => request("POST", `${BASE}/workspaces/review-queue/${id}/reject`),
  acceptAll: (wsId: string) => request<{ accepted_count: number }>("POST", `${BASE}/workspaces/${wsId}/review-queue/accept-all`),
  rejectAll: (wsId: string) => request("POST", `${BASE}/workspaces/${wsId}/review-queue/reject-all`),
  aiPrescreen: (wsId: string) => request<{ processed_count: number }>("POST", `${BASE}/workspaces/${wsId}/review-queue/ai-prescreen`),
};

export const aiReviewers = {
  list: (wsId: string) => request<AIReviewer[]>("GET", `${BASE}/workspaces/${wsId}/ai-reviewers`),
  create: (wsId: string, data: AIReviewerPayload) => request<AIReviewer>("POST", `${BASE}/workspaces/${wsId}/ai-reviewers`, data),
  update: (wsId: string, id: string, data: Partial<AIReviewerPayload>) =>
    request<AIReviewer>("PATCH", `${BASE}/workspaces/${wsId}/ai-reviewers/${id}`, data),
  delete: (wsId: string, id: string) => request("DELETE", `${BASE}/workspaces/${wsId}/ai-reviewers/${id}`),
};

export const ingest = {
  upload: (wsId: string, file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return fetch(`${BASE}/workspaces/${wsId}/ingest`, {
      method: "POST",
      headers: { ...authHeaders() },
      body: formData,
    }).then(async (res) => {
      if (!res.ok) throw new Error((await res.json().catch(() => ({ detail: res.statusText }))).detail ?? res.statusText);
      return res.json();
    });
  },
  url: (wsId: string, url: string) => request("POST", `${BASE}/workspaces/${wsId}/ingest/url`, { url }),
  getLogs: (wsId: string) => request<IngestionLog[]>("GET", `${BASE}/workspaces/${wsId}/ingest/logs`),
};

export const users = {
  apiKeys: {
    list: () => request<PersonalApiKey[]>("GET", `${BASE}/users/me/api-keys`),
    create: (data: { name: string; scopes: string[]; workspace_id?: string }) =>
      request<PersonalApiKeyCreateResponse>("POST", `${BASE}/users/me/api-keys`, data),
    revoke: (id: string) => request("DELETE", `${BASE}/users/me/api-keys/${id}`),
    rotate: (id: string) => request<PersonalApiKeyCreateResponse>("POST", `${BASE}/users/me/api-keys/${id}/rotate`),
  }
};

export interface ApiMessage {
  detail?: string;
  message?: string;
  review_id?: string;
  status?: string;
}

export interface PersonalApiKey {
  id: string;
  name: string;
  prefix: string;
  scopes: string[];
  workspace_id: string | null;
  created_at: string;
  last_used_at: string | null;
  expires_at: string | null;
  revoked_at: string | null;
}

export interface PersonalApiKeyCreateResponse extends PersonalApiKey {
  key: string;
}

export interface AIKey {
  id: string;
  provider: string;
  key_hint: string;
  created_at: string;
  last_used_at: string | null;
}

export interface ModelInfo {
  id: string;
  display_name: string;
}

export interface CreditStatus {
  has_own_key: { openai: boolean; anthropic: boolean; gemini: boolean };
}

export interface Workspace {
  id: string;
  name_zh: string;
  name_en: string;
  visibility: string;
  kb_type: "evergreen" | "ephemeral";
  owner_id: string;
  created_at: string;
  updated_at: string;
}

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
}

export interface ValidityConfirmation {
  confirmed_at: string;
  confirmed_by: string;
}

export interface NodeHealthScore {
  node_id: string;
  score: number;
  label: "healthy" | "warning" | "critical";
  reason: string;
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

export interface AIReviewResult {
  decision: "accept" | "reject" | "comment";
  confidence: number;
  reasoning: string;
  reviewer_id: string;
  reviewed_at: string;
}

export interface ReviewItem {
  id: string;
  workspace_id: string;
  can_review: boolean;
  change_type: "create" | "update" | "delete";
  target_node_id?: string | null;
  before_snapshot?: Partial<NodeCreatePayload> | null;
  node_data: Partial<NodeCreatePayload> & Record<string, unknown>;
  diff_summary: DiffSummary;
  suggested_edges: unknown[];
  status: string;
  source_info?: string;
  proposer_type: "human" | "ai";
  proposer_id?: string | null;
  proposer_meta?: Record<string, unknown> | null;
  reviewer_type?: "human" | "ai" | null;
  reviewer_id?: string | null;
  ai_review?: AIReviewResult | null;
  review_notes?: string | null;
  created_at: string;
  reviewed_at?: string | null;
}

export interface AIReviewerPayload {
  name: string;
  provider: string;
  model: string;
  system_prompt: string;
  auto_accept_threshold: number;
  auto_reject_threshold: number;
  enabled: boolean;
}

export interface AIReviewer extends AIReviewerPayload {
  id: string;
  workspace_id: string;
  created_at: string;
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

export interface Onboarding {
  completed: boolean;
  steps_done: string[];
  steps_skipped: string[];
  first_kb_id: string | null;
}

export interface Edge {
  id: string;
  workspace_id: string;
  from_id: string;
  to_id: string;
  relation: string;
  weight: number;
  co_access_count: number;
  traversal_count: number;
  rating_avg: number | null;
  rating_count: number;
  status: string;
  last_co_accessed: string;
}

export interface EdgeCreatePayload {
  from_id: string;
  to_id: string;
  relation: string;
  weight: number;
  half_life_days: number;
}

export interface GraphPreview {
  nodes: { preview_id: string; content_type: string }[];
  edges: { from_preview_id: string; to_preview_id: string; relation: string }[];
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

export interface IngestionLog {
  id: string;
  filename: string;
  status: "processing" | "completed" | "failed";
  error_msg?: string;
  chunks_total?: number;   // null when document fits in one chunk
  chunks_done?: number;
  created_at: string;
  completed_at?: string;
}

export interface ChatRequest {
  workspace_id: string;
  message: string;
  history?: { role: string; content: string }[];
}

export interface WorkspaceAssociation {
  id: string;
  source_ws_id: string;
  target_ws_id: string;
  target_name_en: string;
  target_name_zh: string;
  created_at: string;
}

export interface TraversalTrendPoint {
  date: string;
  count: number;
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
  traversal_trend: TraversalTrendPoint[];
}

export interface TokenEfficiency {
  avg_tokens_per_query: number;
  estimated_full_doc_tokens: number;
  savings_ratio: number;
  monthly_query_count: number;
}

export interface ProposedChange {
  operation: string;
  target_node_ids: string[];
  reason: string;
  proposed: unknown;
}

export interface ChatResponse {
  answer: string;
  proposals: ProposedChange[];
  source_nodes: Array<{ title_zh?: string; title_en?: string }>;
  tokens_used: number;
}

export interface BackupConfig {
  enabled: boolean;
  path: string;
  interval_hours: number;
  keep_count: number;
  last_backup_at?: string;
  last_backup_file?: string;
  last_backup_status?: string;
}

export const system = {
  getBackupConfig: () => request<BackupConfig>("GET", `${BASE}/system/backup-config`),
  updateBackupConfig: (data: Partial<Pick<BackupConfig, "enabled" | "path" | "interval_hours" | "keep_count">>) =>
    request<BackupConfig>("PATCH", `${BASE}/system/backup-config`, data),
  runBackup: () => request<{ message: string }>("POST", `${BASE}/system/backup/run`),
};

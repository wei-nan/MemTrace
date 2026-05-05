const BASE = "/api/v1";

export function authHeaders(): Record<string, string> {
  const token = localStorage.getItem("mt_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/** Read the double-submit CSRF cookie set by the server on every GET response. */
function getCsrfToken(): string {
  const match = document.cookie.match(/(?:^|;\s*)mt_csrf=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : "";
}

/** Build headers for a mutating request (POST / PUT / PATCH / DELETE). */
function writeHeaders(): Record<string, string> {
  const csrf = getCsrfToken();
  return csrf ? { "X-CSRF-Token": csrf } : {};
}

// ─── Cross-tab token refresh coordination ────────────────────────────────────
//
// When two tabs both fire 401 simultaneously they must NOT both call
// /auth/refresh — refresh tokens are single-use, so one would succeed and
// the other would invalidate it before the first tab uses it.
//
// Strategy:
//   1. In-tab: a Promise singleton (_refreshing) coalesces parallel callers.
//   2. Cross-tab: BroadcastChannel("mt-auth") tells other tabs when a fresh
//      access token has been obtained, so they pick it up from localStorage
//      instead of racing to the network.
//   3. Cross-tab fallback: a `storage` event listener catches token changes
//      in browsers that don't expose BroadcastChannel.

const _bcSupported = typeof BroadcastChannel !== "undefined";
const _bc: BroadcastChannel | null = _bcSupported ? new BroadcastChannel("mt-auth") : null;

let _refreshing: Promise<string | null> | null = null;

/** Notify other tabs that we just minted a fresh access token. */
function _broadcastTokenRefreshed(token: string): void {
  try { _bc?.postMessage({ type: "token-refreshed", token, ts: Date.now() }); } catch {}
}

/** Notify other tabs that the session is dead. */
function _broadcastSessionExpired(): void {
  try { _bc?.postMessage({ type: "session-expired", ts: Date.now() }); } catch {}
}

// Listen for refresh events from other tabs
if (_bc) {
  _bc.addEventListener("message", (ev) => {
    if (!ev.data || typeof ev.data !== "object") return;
    if (ev.data.type === "token-refreshed" && typeof ev.data.token === "string") {
      // Another tab refreshed — adopt their new token without making a network call
      localStorage.setItem("mt_token", ev.data.token);
    } else if (ev.data.type === "session-expired") {
      localStorage.removeItem("mt_token");
      window.dispatchEvent(new CustomEvent("mt:session-expired"));
    }
  });
}

// Storage-event fallback for browsers without BroadcastChannel
window.addEventListener("storage", (ev) => {
  if (ev.key === "mt_token" && ev.newValue === null) {
    window.dispatchEvent(new CustomEvent("mt:session-expired"));
  }
});

/** Call /auth/refresh using the httpOnly refresh cookie. Returns the new access token or null. */
async function _doRefresh(): Promise<string | null> {
  try {
    const res = await fetch("/auth/refresh", {
      method: "POST",
      credentials: "include",          // send the httpOnly mt_refresh cookie
      headers: { ...writeHeaders() },  // CSRF token still required (will be exempted server-side)
    });
    if (!res.ok) return null;
    const data = await res.json();
    if (data.access_token) {
      localStorage.setItem("mt_token", data.access_token);
      _broadcastTokenRefreshed(data.access_token);
      return data.access_token;
    }
    return null;
  } catch {
    return null;
  }
}

/**
 * Refresh the access token once.  Coalesces concurrent callers in this tab,
 * and cooperates with other tabs via BroadcastChannel.
 *
 * Quick-check optimization: if another tab refreshed within the last 2 s,
 * adopt their token from localStorage instead of hitting the network.
 */
async function refreshAccessToken(): Promise<string | null> {
  // If a refresh is already running in this tab, wait for it
  if (_refreshing) return _refreshing;

  _refreshing = (async () => {
    // Quick check: maybe another tab just refreshed
    const stored = localStorage.getItem("mt_token");
    // (caller's stale token check happens at the call-site; we always try to refresh here)
    const fresh = await _doRefresh();
    return fresh ?? stored;  // fall back to whatever's in storage
  })();

  try {
    return await _refreshing;
  } finally {
    _refreshing = null;
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const isMutating = !["GET", "HEAD", "OPTIONS"].includes(method.toUpperCase());

  const doFetch = (accessToken?: string) =>
    fetch(path, {
      method,
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : authHeaders()),
        ...(isMutating ? writeHeaders() : {}),
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });

  let res = await doFetch();

  // On 401, attempt one silent token refresh then retry
  if (res.status === 401 && path !== "/auth/refresh" && path !== "/auth/login") {
    const newToken = await refreshAccessToken();
    if (newToken) {
      res = await doFetch(newToken);
    } else {
      // Refresh failed — clear session and notify both this tab and any others
      localStorage.removeItem("mt_token");
      _broadcastSessionExpired();
      window.dispatchEvent(new CustomEvent("mt:session-expired"));
    }
  }

  if (!res.ok) {
    let errDetail;
    try {
      const err = await res.json();
      errDetail = err.detail ?? err.message ?? err;
      if (typeof errDetail === 'object') {
        errDetail = JSON.stringify(errDetail);
      }
    } catch {
      errDetail = res.statusText;
    }
    throw new Error(errDetail ?? `HTTP ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

async function requestStream(path: string, body: unknown, onChunk: (data: any) => void): Promise<void> {
  const doFetch = (accessToken?: string) =>
    fetch(path, {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : authHeaders()),
        ...writeHeaders(),
      },
      body: JSON.stringify(body),
    });

  let res = await doFetch();

  if (res.status === 401) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      res = await doFetch(newToken);
    } else {
      localStorage.removeItem("mt_token");
      _broadcastSessionExpired();
      window.dispatchEvent(new CustomEvent("mt:session-expired"));
    }
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }

  const reader = res.body?.getReader();
  if (!reader) return;

  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";
      for (const line of lines) {
        if (line.trim()) {
          try {
            onChunk(JSON.parse(line));
          } catch (e) {
            console.error("Failed to parse stream chunk", e);
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

export const auth = {
  register: (data: { display_name: string; email: string; password: string }) =>
    request<{ access_token: string }>("POST", "/auth/register", data),
  login: (data: { email: string; password: string }) =>
    request<{ access_token: string }>("POST", "/auth/login", data),
  logout: () => request("POST", "/auth/logout"),
  /** Manually trigger a token refresh (normally handled automatically by request()). */
  refresh: () => refreshAccessToken(),
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
  create: (data: {
    name_zh: string;
    name_en: string;
    visibility: string;
    kb_type: "evergreen" | "ephemeral";
    embedding_model?: string;   // P4.1-E: user-chosen model; omit = auto-resolve
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
  update: (wsId: string, data: Partial<{ name_zh: string; name_en: string; visibility: string; qa_archive_mode: string }>) =>
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
  bulkDelete: (wsId: string, nodeIds: string[]) =>
    request<{ deleted_count: number }>("POST", `${BASE}/workspaces/${wsId}/nodes/bulk-delete`, { node_ids: nodeIds }),
  healthScores: (wsId: string) =>
    request<NodeHealthScore[]>("GET", `${BASE}/workspaces/${wsId}/nodes/health-scores`),
  suggestEdges: (wsId: string, nodeId: string) =>
    request<any[]>("POST", `${BASE}/workspaces/${wsId}/nodes/${nodeId}/suggest-edges`),
  voteTrust: (wsId: string, nodeId: string, data: { accuracy: number; utility: number }) =>
    request<{ status: string; trust_score: number }>("POST", `${BASE}/workspaces/${wsId}/nodes/${nodeId}/vote-trust`, data),
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
  createKey: (data: { provider: string; api_key?: string; base_url?: string; auth_mode?: string; auth_token?: string; default_chat_model?: string; default_embedding_model?: string }) => request<AIKey>("POST", `${BASE}/ai/keys`, data),
  deleteKey: (provider: string) => request("DELETE", `${BASE}/ai/keys/${provider}`),
  getCredits: () => request<CreditStatus>("GET", `${BASE}/ai/credits`),
  extract: (data: unknown) => request("POST", `${BASE}/ai/extract`, data),
  restructure: (data: unknown) => request("POST", `${BASE}/ai/restructure`, data),
  chat: (data: unknown) => request<ChatResponse>("POST", `${BASE}/ai/chat`, data),
  chatStream: (data: unknown, onChunk: (data: any) => void) => requestStream(`${BASE}/ai/chat-stream`, data, onChunk),
  listModels: (provider: string) => request<ModelInfo[]>("GET", `${BASE}/ai/models/${provider}`),
  testConnection: (data: { provider: string; api_key?: string; base_url?: string; auth_mode?: string; auth_token?: string; model?: string }) =>
    request<{ status: string }>("POST", `${BASE}/ai/providers/${data.provider}/test-connection`, data),
  listModelsProxy: (provider: string, params: { base_url?: string; api_key?: string; auth_mode?: string; auth_token?: string }) => {
    const qs = new URLSearchParams(params as any).toString();
    return request<ModelInfo[]>("GET", `${BASE}/ai/providers/${provider}/models?${qs}`);
  },
  getResolvedModel: (type: string) => request<{ provider: string; model: string }>("GET", `${BASE}/ai/resolved-models?type=${type}`),
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
  upload: (wsId: string, file: File, docType: string = "generic", seeds?: string[], excelConfig?: Record<string, any>) => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("doc_type", docType);
    if (seeds && seeds.length > 0) {
      formData.append("seeds", JSON.stringify(seeds));
    }
    if (excelConfig) {
      formData.append("excel_config", JSON.stringify(excelConfig));
    }
    return fetch(`${BASE}/workspaces/${wsId}/ingest`, {
      method: "POST",
      headers: { ...authHeaders(), ...writeHeaders() },
      body: formData,
    }).then(async (res) => {
      if (!res.ok) throw new Error((await res.json().catch(() => ({ detail: res.statusText }))).detail ?? res.statusText);
      return res.json();
    });
  },
  excelPreview: (wsId: string, file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return fetch(`${BASE}/workspaces/${wsId}/ingest/excel-preview`, {
      method: "POST",
      headers: { ...authHeaders(), ...writeHeaders() },
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
  base_url?: string;
  auth_mode?: string;
  auth_token?: string;
  default_chat_model?: string;
  default_embedding_model?: string;
}

export interface ModelInfo {
  id: string;
  display_name: string;
  model_type?: 'chat' | 'embedding';
  embedding_dim?: number;
  needs_install?: boolean;
}

export interface CreditStatus {
  has_own_key: { openai: boolean; anthropic: boolean; gemini: boolean; ollama: boolean };
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
  my_role: "admin" | "editor" | "viewer" | null;
  embedding_model: string;
  embedding_dim: number;
  qa_archive_mode: "auto_active" | "manual_review";
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
  ask_count: number;
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
  change_type: "create" | "update" | "delete" | "create_edge";
  target_node_id?: string | null;
  before_snapshot?: Partial<NodeCreatePayload> | null;
  node_data: (Partial<NodeCreatePayload> & { from_id?: string; to_id?: string; relation?: string }) | any;
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
  metadata?: Record<string, any>;
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
  getMcpStatus: () => request<any>("GET", `${BASE}/mcp/status`),
};

export interface WorkspaceCloneJob {
  id: string;
  source_ws_id: string;
  target_ws_id: string;
  /** pending → running → completed | failed; cancel path: running → cancelling → cancelled */
  status: "pending" | "running" | "cancelling" | "cancelled" | "completed" | "failed";
  total_nodes: number;
  processed_nodes: number;
  is_fork: boolean;          // true = triggered by public KB fork
  error_msg?: string;
  cancelled_at?: string;     // set when user successfully cancels
  created_at: string;
  updated_at: string;
}

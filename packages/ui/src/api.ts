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

// ── Auth ──────────────────────────────────────────────────────────────────────
export const auth = {
  register: (data: { display_name: string; email: string; password: string }) =>
    request<{ access_token: string }>("POST", "/auth/register", data),
  login: (data: { email: string; password: string }) =>
    request<{ access_token: string }>("POST", "/auth/login", data),
  logout: () => request("POST", "/auth/logout"),
  me: () => request<{ id: string; display_name: string; email: string; email_verified: boolean }>("GET", "/auth/me"),
  verifyEmail: (token: string) => request("POST", `/auth/verify-email/${token}`),
  resendVerification: () => request("POST", "/auth/resend-verification-email"),
  getOnboarding: () => request<Onboarding>("GET", "/auth/me/onboarding"),
  updateOnboarding: (data: Partial<Onboarding>) => request<Onboarding>("PATCH", "/auth/me/onboarding", data),
};

// ── Workspaces ────────────────────────────────────────────────────────────────
export const workspaces = {
  list: () => request<Workspace[]>("GET", `${BASE}/workspaces`),
  create: (data: { name_zh: string; name_en: string; visibility: string; kb_type: 'evergreen' | 'ephemeral' }) =>
    request<Workspace>("POST", `${BASE}/workspaces`, data),
  get: (id: string) => request<Workspace>("GET", `${BASE}/workspaces/${id}`),
  members: (wsId: string) => request<Member[]>("GET", `${BASE}/workspaces/${wsId}/members`),
  invites: (wsId: string) => request<Invite[]>("GET", `${BASE}/workspaces/${wsId}/invites`),
  createInvite: (wsId: string, data: { email: string; role: string }) => 
    request<Invite>("POST", `${BASE}/workspaces/${wsId}/invites`, data),
  acceptInvite: (token: string) => request("POST", `/workspaces/invites/${token}/accept`),
  deleteInvite: (id: string) => request("DELETE", `/workspaces/invites/${id}`),
  updateMember: (wsId: string, userId: string, role: string) =>
    request("PUT", `${BASE}/workspaces/${wsId}/members/${userId}`, { role }),
  removeMember: (wsId: string, userId: string) =>
    request("DELETE", `${BASE}/workspaces/${wsId}/members/${userId}`),
};

// ── Nodes ─────────────────────────────────────────────────────────────────────
export const nodes = {
  list: (wsId: string, params?: Record<string, string>) => {
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    return request<Node[]>("GET", `${BASE}/workspaces/${wsId}/nodes${qs}`);
  },
  get: (wsId: string, nodeId: string) =>
    request<Node>("GET", `${BASE}/workspaces/${wsId}/nodes/${nodeId}`),
  create: (wsId: string, data: NodeCreatePayload) =>
    request<Node>("POST", `${BASE}/workspaces/${wsId}/nodes`, data),
  update: (wsId: string, nodeId: string, data: Partial<NodeCreatePayload>) =>
    request<Node>("PATCH", `${BASE}/workspaces/${wsId}/nodes/${nodeId}`, data),
  delete: (wsId: string, nodeId: string) =>
    request("DELETE", `${BASE}/workspaces/${wsId}/nodes/${nodeId}`),
  traverse: (nodeId: string) =>
    request("POST", `${BASE}/nodes/${nodeId}/traverse`),
  searchSemantic: (wsId: string, query: string, limit: number = 10) =>
    request<Node[]>("POST", `${BASE}/workspaces/${wsId}/nodes/search-semantic?query=${encodeURIComponent(query)}&limit=${limit}`),
};

// ── Edges ─────────────────────────────────────────────────────────────────────
export const edges = {
  list: (wsId: string, nodeId?: string) => {
    const qs = nodeId ? `?node_id=${nodeId}` : "";
    return request<Edge[]>("GET", `${BASE}/workspaces/${wsId}/edges${qs}`);
  },
  create: (wsId: string, data: EdgeCreatePayload) =>
    request<Edge>("POST", `${BASE}/workspaces/${wsId}/edges`, data),
  traverse: (edgeId: string, note?: string) =>
    request("POST", `${BASE}/edges/${edgeId}/traverse`, { note }),
  rate: (edgeId: string, rating: number, note?: string) =>
    request("POST", `${BASE}/edges/${edgeId}/rate`, { rating, note }),
};

// ── AI Keys & Credits ─────────────────────────────────────────────────────────
export const ai = {
  listKeys: () => request<AIKey[]>("GET", `${BASE}/ai/keys`),
  createKey: (data: { provider: string; api_key: string }) =>
    request<AIKey>("POST", `${BASE}/ai/keys`, data),
  deleteKey: (provider: string) =>
    request("DELETE", `${BASE}/ai/keys/${provider}`),
  getCredits: () => request<CreditStatus>("GET", `${BASE}/ai/credits`),
};

// ── Review Queue ──────────────────────────────────────────────────────────────
export const review = {
  list: (wsId: string, status = "pending") => 
    request<ReviewItem[]>("GET", `${BASE}/workspaces/${wsId}/review-queue?status=${status}`),
  update: (id: string, data: Partial<ReviewItem>) =>
    request<ReviewItem>("PATCH", `${BASE}/workspaces/review-queue/${id}`, data),
  accept: (id: string) => 
    request<Node>("POST", `${BASE}/workspaces/review-queue/${id}/accept`),
  reject: (id: string) => 
    request("POST", `${BASE}/workspaces/review-queue/${id}/reject`),
  acceptAll: (wsId: string) =>
    request<{ accepted_count: number }>("POST", `${BASE}/workspaces/${wsId}/review-queue/accept-all`),
  rejectAll: (wsId: string) =>
    request("POST", `${BASE}/workspaces/${wsId}/review-queue/reject-all`),
};

// ── Ingest ────────────────────────────────────────────────────────────────────
export const ingest = {
  upload: (wsId: string, file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return fetch(`${BASE}/workspaces/${wsId}/ingest`, {
      method: "POST",
      headers: { ...authHeaders() },
      body: formData,
    }).then(res => {
      if (!res.ok) throw new Error("Upload failed");
      return res.json();
    });
  }
};

// ── Types ─────────────────────────────────────────────────────────────────────
export interface AIKey {
  id: string; provider: string; key_hint: string;
  created_at: string; last_used_at: string | null;
}
export interface CreditStatus {
  free_limit: number; free_used: number; free_remaining: number;
  has_own_key: { openai: boolean; anthropic: boolean };
}
export interface Workspace {
  id: string; name_zh: string; name_en: string; visibility: string;
  kb_type: 'evergreen' | 'ephemeral';
  owner_id: string; created_at: string; updated_at: string;
}
export interface Node {
  id: string; workspace_id: string; title_zh: string; title_en: string;
  content_type: string; content_format: string; body_zh: string; body_en: string;
  tags: string[]; visibility: string; author: string; trust_score: number;
  dim_accuracy: number; dim_freshness: number; dim_utility: number; dim_author_rep: number;
  traversal_count: number; unique_traverser_count: number;
  created_at: string; updated_at?: string; signature: string; source_type: string;
  copied_from_node?: string; copied_from_ws?: string;
}
export interface Member {
  user_id: string; display_name: string; email: string; role: string; joined_at: string;
}
export interface Invite {
  id: string; workspace_id: string; email: string; role: string; token: string;
  inviter_id: string; created_at: string; expires_at: string; accepted_at: string | null;
}
export interface ReviewItem {
  id: string; workspace_id: string; node_data: any; suggested_edges: any[];
  status: string; source_info: string; created_at: string;
}
export interface Onboarding {
  completed: boolean;
  steps_done: string[];
  steps_skipped: string[];
  first_kb_id: string | null;
}
export interface Edge {
  id: string; workspace_id: string; from_id: string; to_id: string;
  relation: string; weight: number; co_access_count: number;
  traversal_count: number; rating_avg: number | null; rating_count: number;
  last_co_accessed: string;
}
export interface NodeCreatePayload {
  title_zh: string; title_en: string; content_type: string;
  content_format: string; body_zh: string; body_en: string;
  tags: string[]; visibility: string;
}
export interface EdgeCreatePayload {
  from_id: string; to_id: string; relation: string;
  weight: number; half_life_days: number;
}

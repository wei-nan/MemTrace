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
};

// ── Workspaces ────────────────────────────────────────────────────────────────
export const workspaces = {
  list: () => request<Workspace[]>("GET", `${BASE}/workspaces`),
  create: (data: { name_zh: string; name_en: string; visibility: string }) =>
    request<Workspace>("POST", `${BASE}/workspaces`, data),
  get: (id: string) => request<Workspace>("GET", `${BASE}/workspaces/${id}`),
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

// ── Types ─────────────────────────────────────────────────────────────────────
export interface Workspace {
  id: string; name_zh: string; name_en: string; visibility: string;
  owner_id: string; created_at: string; updated_at: string;
}
export interface Node {
  id: string; workspace_id: string; title_zh: string; title_en: string;
  content_type: string; content_format: string; body_zh: string; body_en: string;
  tags: string[]; visibility: string; author: string; trust_score: number;
  dim_accuracy: number; dim_freshness: number; dim_utility: number; dim_author_rep: number;
  traversal_count: number; unique_traverser_count: number;
  created_at: string; updated_at?: string; signature: string; source_type: string;
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

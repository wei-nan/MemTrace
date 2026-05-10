import { BASE, request } from './client';

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

export const edges = {
  list: (wsId: string, nodeId?: string) => request<Edge[]>("GET", `${BASE}/workspaces/${wsId}/edges${nodeId ? `?node_id=${nodeId}` : ""}`),
  create: (wsId: string, data: EdgeCreatePayload) => request<Edge>("POST", `${BASE}/workspaces/${wsId}/edges`, data),
  traverse: (edgeId: string, note?: string) => request("POST", `${BASE}/edges/${edgeId}/traverse`, { note }),
  rate: (edgeId: string, rating: number, note?: string) => request("POST", `${BASE}/edges/${edgeId}/rate`, { rating, note }),
  connectOrphans: (wsId: string) => request<{ message: string; orphan_count?: number }>("POST", `${BASE}/workspaces/${wsId}/edges/connect-orphans`),
};

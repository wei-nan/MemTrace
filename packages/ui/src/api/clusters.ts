import { BASE, request } from './client';

export interface NodeCluster {
  id: string;
  workspace_id: string;
  name_zh: string;
  name_en: string;
  color: string;
  node_count: number;
  created_at: string;
  updated_at: string;
}

export const clusters = {
  list: (wsId: string) =>
    request<NodeCluster[]>('GET', `${BASE}/workspaces/${wsId}/clusters`),

  create: (wsId: string, data: { name_zh: string; name_en: string; color?: string }) =>
    request<NodeCluster>('POST', `${BASE}/workspaces/${wsId}/clusters`, data),

  update: (wsId: string, clusterId: string, data: Partial<{ name_zh: string; name_en: string; color: string }>) =>
    request<NodeCluster>('PATCH', `${BASE}/workspaces/${wsId}/clusters/${clusterId}`, data),

  delete: (wsId: string, clusterId: string) =>
    request('DELETE', `${BASE}/workspaces/${wsId}/clusters/${clusterId}`),

  assignNode: (wsId: string, nodeId: string, clusterId: string | null) =>
    request<{ ok: boolean }>('PATCH', `${BASE}/workspaces/${wsId}/nodes/${nodeId}/cluster`, { cluster_id: clusterId }),
};

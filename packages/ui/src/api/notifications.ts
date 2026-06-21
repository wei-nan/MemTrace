import { BASE, request } from './client';

export interface NotificationItem {
  id: string;
  workspace_id: string;
  recipient_id: string;
  source_type: string;
  source_id: string;
  category: string | null;
  severity: string | null;
  title: string;
  body: string | null;
  target_node_id: string | null;
  read_at: string | null;
  created_at: string;
}

export interface NotificationListResponse {
  notifications: NotificationItem[];
  unread_count: number;
  offset: number;
}

export type NotificationSeverity = 'high' | 'mid' | 'low' | 'review';

type ListParams = {
  workspace_id?: string;
  unread_only?: boolean;
  severity?: NotificationSeverity;
  limit?: number;
  offset?: number;
};

type DismissParams = {
  workspace_id?: string;
  read_only?: boolean;
  severity?: NotificationSeverity;
};

function buildQuery(params?: Record<string, string | number | boolean | undefined>): string {
  if (!params) return '';
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== false && v !== '') q.set(k, String(v));
  }
  const qs = q.toString();
  return qs ? `?${qs}` : '';
}

export const notifications = {
  list: (params?: ListParams) =>
    request<NotificationListResponse>('GET', `${BASE}/notifications${buildQuery(params)}`),
  unreadCount: (workspaceId?: string) =>
    request<{ unread_count: number }>(
      'GET',
      `${BASE}/notifications/unread_count${workspaceId ? `?workspace_id=${workspaceId}` : ''}`,
    ),
  markRead: (id: string) =>
    request<{ status: string }>('POST', `${BASE}/notifications/${id}/read`),
  markAllRead: (workspaceId?: string) =>
    request<{ status: string; updated: number }>(
      'POST',
      `${BASE}/notifications/read_all${workspaceId ? `?workspace_id=${workspaceId}` : ''}`,
    ),
  dismiss: (id: string) =>
    request<{ status: string }>('DELETE', `${BASE}/notifications/${id}`),
  dismissAll: (params?: DismissParams) =>
    request<{ status: string; deleted: number }>('DELETE', `${BASE}/notifications${buildQuery(params)}`),
};

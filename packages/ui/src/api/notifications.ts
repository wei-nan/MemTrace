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

interface ListParams {
  workspace_id?: string;
  unread_only?: boolean;
  limit?: number;
  offset?: number;
}

function buildQuery(params?: ListParams): string {
  if (!params) return '';
  const q = new URLSearchParams();
  if (params.workspace_id) q.set('workspace_id', params.workspace_id);
  if (params.unread_only) q.set('unread_only', 'true');
  if (params.limit != null) q.set('limit', String(params.limit));
  if (params.offset != null) q.set('offset', String(params.offset));
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
};

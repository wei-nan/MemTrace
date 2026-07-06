import { BASE, request } from './client';
import type { Workspace } from './workspaces';

export interface SystemAIKey {
  target: 'system' | 'safety';
  provider: string;
  key_hint: string;
  base_url?: string;
  auth_mode?: string;
  default_chat_model?: string;
  default_embedding_model?: string;
  last_used_at?: string;
}

export interface SystemAIKeyUpsert {
  target: 'system' | 'safety';
  provider: string;
  api_key?: string;
  base_url?: string;
  auth_mode?: string;
  auth_token?: string;
  default_chat_model?: string;
  default_embedding_model?: string;
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

export interface SystemUser {
  id: string;
  display_name: string;
  email: string;
  email_verified: boolean;
  is_platform_admin: boolean;
  created_at: string;
  last_login_at?: string | null;
  workspace_count: number;
}

export interface SystemUsersPage {
  users: SystemUser[];
  total: number;
  limit: number;
  offset: number;
}

export const system = {
  getBackupConfig: () => request<BackupConfig>("GET", `${BASE}/system/backup-config`),
  updateBackupConfig: (data: Partial<Pick<BackupConfig, "enabled" | "path" | "interval_hours" | "keep_count">>) =>
    request<BackupConfig>("PATCH", `${BASE}/system/backup-config`, data),
  runBackup: () => request<{ message: string }>("POST", `${BASE}/system/backup/run`),
  getMcpStatus: () => request<any>("GET", `${BASE}/api/v1/mcp/status`),
  registrations: (status: string) => request<any[]>("GET", `${BASE}/system/registrations?status=${status}`),
  approveRegistration: (id: string) => request("POST", `${BASE}/system/registrations/${id}/approve`),
  rejectRegistration: (id: string) => request("POST", `${BASE}/system/registrations/${id}/reject`),
  users: (params?: { q?: string; limit?: number; offset?: number }) => {
    const qs = new URLSearchParams();
    if (params?.q) qs.set('q', params.q);
    if (params?.limit != null) qs.set('limit', String(params.limit));
    if (params?.offset != null) qs.set('offset', String(params.offset));
    const query = qs.toString();
    return request<SystemUsersPage>("GET", `${BASE}/system/users${query ? `?${query}` : ''}`);
  },
  promoteUser: (userId: string) => request("POST", `${BASE}/system/promote`, { user_id: userId }),
  demoteUser: (userId: string) => request("POST", `${BASE}/system/demote`, { user_id: userId }),

  // System-level AI key management (admin only)
  listSystemAIKeys: () => request<SystemAIKey[]>("GET", `${BASE}/system/ai-keys`),
  upsertSystemAIKey: (data: SystemAIKeyUpsert) => request<SystemAIKey>("POST", `${BASE}/system/ai-keys`, data),
  deleteSystemAIKey: (target: 'system' | 'safety', provider: string) =>
    request("DELETE", `${BASE}/system/ai-keys/${target}/${provider}`),
  updateSystemAIKeyModel: (target: 'system' | 'safety', provider: string, models: { default_chat_model?: string; default_embedding_model?: string }) =>
    request("PATCH", `${BASE}/system/ai-keys/${target}/${provider}/model`, models),

  // ── System Monitor (admin only) ──────────────────────────────────────────
  monitorHeartbeats: () =>
    request<{ heartbeats: SystemSchedulerHeartbeat[] }>("GET", `${BASE}/system/monitor/scheduler-heartbeats`),
  monitorJobRuns: (params?: { job_name?: string; status?: string; workspace_id?: string; reviewer?: string; limit?: number; offset?: number }) => {
    const qs = new URLSearchParams();
    if (params?.job_name) qs.set('job_name', params.job_name);
    if (params?.status) qs.set('status', params.status);
    if (params?.workspace_id) qs.set('workspace_id', params.workspace_id);
    if (params?.reviewer) qs.set('reviewer', params.reviewer);
    if (params?.limit != null) qs.set('limit', String(params.limit));
    if (params?.offset != null) qs.set('offset', String(params.offset));
    const q = qs.toString();
    return request<{ runs: SystemJobRun[]; total: number; offset: number }>(
      "GET", `${BASE}/system/monitor/job-runs${q ? `?${q}` : ''}`
    );
  },
  monitorMcpLogs: (params?: { limit?: number; offset?: number }) => {
    const qs = new URLSearchParams();
    if (params?.limit != null) qs.set('limit', String(params.limit));
    if (params?.offset != null) qs.set('offset', String(params.offset));
    const q = qs.toString();
    return request<{ logs: SystemMcpLog[]; total: number; offset: number }>(
      "GET", `${BASE}/system/monitor/mcp-query-logs${q ? `?${q}` : ''}`
    );
  },
  monitorAiUsage: () =>
    request<{ usage: SystemAiUsage[] }>("GET", `${BASE}/system/monitor/ai-usage`),
};

export interface SystemSchedulerHeartbeat {
  job_name: string;
  status: 'running' | 'success' | 'failed' | 'skipped' | 'unknown';
  last_run_at: string | null;
  last_success_at: string | null;
  last_failure_at: string | null;
  duration_ms: number | null;
  run_count: number;
  failure_count: number;
  last_run_id: string | null;
  last_error: string | null;
  metadata: Record<string, any>;
  updated_at: string;
}

export interface SystemJobRun {
  id: string;
  job_name: string;
  workspace_id: string | null;
  workspace_name: string | null;
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

export interface SystemMcpLog {
  id: string;
  workspace_id: string;
  workspace_name: string | null;
  tool_name: string;
  query_text: string | null;
  result_node_count: number;
  estimated_tokens: number;
  created_at: string;
  provider: string | null;
}

export interface SystemAiUsage {
  workspace_id: string;
  workspace_name: string | null;
  year_month: string;
  token_count: number;
  last_updated: string;
}

export const kb = {
  getGraph: (wsId: string) => request<any>("GET", `${BASE}/public/workspaces/${wsId}/graph-preview`),
  getPublicInfo: (wsId: string) => request<Workspace>("GET", `${BASE}/public/workspaces/${wsId}`),
  applySplit: (wsId: string, reviewId: string, data: { proposals: any[] }) =>
    request("POST", `${BASE}/workspaces/${wsId}/review-queue/${reviewId}/apply-split`, data),
};

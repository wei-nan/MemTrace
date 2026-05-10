import { BASE, request } from './client';
import type { Workspace } from './workspaces';

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
  getMcpStatus: () => request<any>("GET", `${BASE}/api/v1/mcp/status`),
  registrations: (status: string) => request<any[]>("GET", `${BASE}/system/registrations?status=${status}`),
  approveRegistration: (id: string) => request("POST", `${BASE}/system/registrations/${id}/approve`),
  rejectRegistration: (id: string) => request("POST", `${BASE}/system/registrations/${id}/reject`),
};

export const kb = {
  getGraph: (wsId: string) => request<any>("GET", `${BASE}/public/workspaces/${wsId}/graph-preview`),
  getPublicInfo: (wsId: string) => request<Workspace>("GET", `${BASE}/public/workspaces/${wsId}`),
  applySplit: (wsId: string, reviewId: string, data: { proposals: any[] }) =>
    request("POST", `${BASE}/workspaces/${wsId}/review-queue/${reviewId}/apply-split`, data),
};

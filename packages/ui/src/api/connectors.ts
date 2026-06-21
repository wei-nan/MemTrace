import { BASE, request } from "./client";

export type ConnectorProvider = "google_drive" | "asana" | "github" | "gitlab";
export type ConnectorDirection = "inbound" | "outbound" | "bidirectional";

export interface ConnectorAccount {
  id: string;
  owner_user_id: string;
  provider: ConnectorProvider;
  provider_instance_url: string;
  provider_account_id: string;
  display_name: string | null;
  auth_type: "oauth" | "token" | "app";
  scopes: string[];
  status: "active" | "error" | "revoked";
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface ConnectorBinding {
  id: string;
  connector_account_id: string;
  workspace_id: string;
  external_container_type: string;
  external_container_id: string;
  external_container_name: string | null;
  sync_direction: ConnectorDirection;
  permissions: Record<string, unknown>;
  event_filters: Record<string, unknown>;
  enabled: boolean;
  provider: ConnectorProvider;
  provider_instance_url: string;
  provider_account_id: string;
  account_display_name: string | null;
  account_status: string;
  created_at: string;
  updated_at: string;
}

export interface ConnectorRun {
  id: string;
  binding_id: string;
  provider: ConnectorProvider;
  status: string;
  trigger: string;
  started_at: string;
  finished_at: string | null;
  scanned_count: number | null;
  created_count: number | null;
  updated_count: number | null;
  skipped_count: number | null;
  failed_count: number | null;
  error: string | null;
  summary: Record<string, unknown>;
}

export const connectors = {
  listAccounts: () =>
    request<ConnectorAccount[]>("GET", `${BASE}/users/me/connector-accounts`),
  createAccount: (data: {
    provider: ConnectorProvider;
    provider_account_id: string;
    provider_instance_url?: string;
    display_name?: string;
    auth_type?: "oauth" | "token" | "app";
    credential?: string;
    scopes?: string[];
  }) => request<ConnectorAccount>("POST", `${BASE}/users/me/connector-accounts`, data),
  revokeAccount: (accountId: string) =>
    request<Pick<ConnectorAccount, "id" | "status" | "updated_at">>(
      "DELETE",
      `${BASE}/users/me/connector-accounts/${accountId}`,
    ),
  listBindings: (workspaceId: string) =>
    request<ConnectorBinding[]>("GET", `${BASE}/workspaces/${workspaceId}/connector-bindings`),
  createBinding: (
    workspaceId: string,
    data: {
      connector_account_id: string;
      external_container_type: string;
      external_container_id: string;
      external_container_name?: string;
      sync_direction: ConnectorDirection;
    },
  ) => request<ConnectorBinding>("POST", `${BASE}/workspaces/${workspaceId}/connector-bindings`, data),
  updateBinding: (
    workspaceId: string,
    bindingId: string,
    data: Partial<Pick<ConnectorBinding, "enabled" | "sync_direction" | "permissions" | "event_filters">>,
  ) => request<ConnectorBinding>(
    "PATCH",
    `${BASE}/workspaces/${workspaceId}/connector-bindings/${bindingId}`,
    data,
  ),
  deleteBinding: (workspaceId: string, bindingId: string) =>
    request<void>("DELETE", `${BASE}/workspaces/${workspaceId}/connector-bindings/${bindingId}`),
  listRuns: (workspaceId: string) =>
    request<ConnectorRun[]>("GET", `${BASE}/workspaces/${workspaceId}/connector-runs`),
};

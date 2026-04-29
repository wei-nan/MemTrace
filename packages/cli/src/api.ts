import { readConfig } from "./store";
import chalk from "chalk";
// Use global fetch (Node 18+)

// Dynamic API base URL from env or config

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const cfg = readConfig();
  const baseUrl = process.env.MEMTRACE_API || cfg.api_url || "http://localhost:8000/api/v1";
  console.log(chalk.dim(`  [API] ${method} ${baseUrl}${path}`));
  const token = cfg.auth?.token;
  
  if (!token && !path.startsWith("/info") && path !== "/") {
    throw new Error("Authentication required. Run 'memtrace init' first.");
  }

  const res = await fetch(`${baseUrl}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { "Authorization": `Bearer ${token}` } : {})
    },
    body: body ? JSON.stringify(body) : undefined
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }

  return res.json() as Promise<T>;
}

export const api = {
  getInfo: () => {
    // The root "/" of the API (not /api/v1) holds the version
    // But since baseUrl is .../api/v1, we go up one level
    const cfg = readConfig();
    const baseUrl = (process.env.MEMTRACE_API || cfg.api_url || "http://localhost:8000/api/v1").replace(/\/api\/v1\/?$/, "");
    return fetch(`${baseUrl}/`).then(res => res.json()) as Promise<{ version: string }>;
  },
  getNode: (wsId: string, nodeId: string) => request<any>("GET", `/workspaces/${wsId}/nodes/${nodeId}`),
  createNode: (wsId: string, data: any) => request<any>("POST", `/workspaces/${wsId}/nodes`, data),
  searchNodes: (wsId: string, query: string) => request<any[]>("GET", `/workspaces/${wsId}/nodes-search?query=${encodeURIComponent(query)}`),
  listWorkspaces: () => request<any[]>("GET", "/workspaces"),
  saveAIKey: (data: { provider: string; api_key?: string; base_url?: string; auth_mode?: string; auth_token?: string }) => 
    request<any>("POST", "/ai/keys", data),
  testConnection: (provider: string, data: any) => 
    request<any>("POST", `/ai/providers/${provider}/test-connection`, data),
  listAIModels: (provider: string, params?: any) => {
    if (params) {
      const qs = new URLSearchParams(params).toString();
      return request<any[]>("GET", `/ai/providers/${provider}/models?${qs}`);
    }
    return request<any[]>("GET", `/ai/models/${provider}`);
  }
};

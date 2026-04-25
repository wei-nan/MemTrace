import { readConfig } from "./store";
import chalk from "chalk";
// Use global fetch (Node 18+)

// Dynamic API base URL from env or config

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const cfg = readConfig();
  const baseUrl = process.env.MEMTRACE_API || cfg.api_url || "http://localhost:8000/api/v1";
  console.log(chalk.dim(`  [API] ${method} ${baseUrl}${path}`));
  const token = cfg.auth?.token;
  
  if (!token) {
    throw new Error("Authentication required. Run 'memtrace init' first.");
  }

  const res = await fetch(`${baseUrl}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${token}`
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
  getNode: (wsId: string, nodeId: string) => request<any>("GET", `/workspaces/${wsId}/nodes/${nodeId}`),
  createNode: (wsId: string, data: any) => request<any>("POST", `/workspaces/${wsId}/nodes`, data),
  searchNodes: (wsId: string, query: string) => request<any[]>("GET", `/workspaces/${wsId}/nodes-search?query=${encodeURIComponent(query)}`),
  listWorkspaces: () => request<any[]>("GET", "/workspaces"),
  saveAIKey: (provider: string, apiKey: string) => request<any>("POST", "/ai/keys", { provider, api_key: apiKey }),
  listAIModels: (provider: string) => request<any[]>("GET", `/ai/models/${provider}`)
};

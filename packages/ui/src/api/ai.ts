import { BASE, request, requestStream } from './client';

export interface AIKey {
  id: string;
  provider: string;
  key_hint: string;
  created_at: string;
  last_used_at: string | null;
  base_url?: string;
  auth_mode?: string;
  auth_token?: string;
  default_chat_model?: string;
  default_embedding_model?: string;
}

export interface ModelInfo {
  id: string;
  display_name: string;
  model_type?: 'chat' | 'embedding';
  embedding_dim?: number;
  needs_install?: boolean;
}

export interface CreditStatus {
  has_own_key: { openai: boolean; anthropic: boolean; gemini: boolean; ollama: boolean };
}

export interface ProposedChange {
  operation: string;
  target_node_ids: string[];
  reason: string;
  proposed: unknown;
}

export interface ChatResponse {
  answer: string;
  proposals: ProposedChange[];
  source_nodes: Array<{ id?: string; title?: string }>;
  tokens_used: number;
}

export interface ChatSession {
  id: string;
  title: string;
  message_count: number;
  tokens_total: number;
  created_at: string;
  last_active_at: string;
  is_cold: boolean;
}

export interface ChatMessage {
  id: number;
  session_id: string;
  role: 'user' | 'assistant';
  content: string;
  source_node_ids: string[];
  tokens_used: number;
  created_at: string;
}

export const ai = {
  listKeys: () => request<AIKey[]>("GET", `${BASE}/ai/keys`),
  createKey: (data: { provider: string; api_key?: string; base_url?: string; auth_mode?: string; auth_token?: string; default_chat_model?: string; default_embedding_model?: string }) => request<AIKey>("POST", `${BASE}/ai/keys`, data),
  deleteKey: (provider: string) => request("DELETE", `${BASE}/ai/keys/${provider}`),
  getCredits: () => request<CreditStatus>("GET", `${BASE}/ai/credits`),
  extract: (data: unknown) => request("POST", `${BASE}/ai/extract`, data),
  restructure: (data: unknown) => request("POST", `${BASE}/ai/restructure`, data),
  chat: (data: unknown) => request<ChatResponse>("POST", `${BASE}/ai/chat`, data),
  chatStream: (data: unknown, onChunk: (data: any) => void, signal?: AbortSignal) => requestStream(`${BASE}/ai/chat-stream`, data, onChunk, signal),
  listModels: (provider: string) => request<ModelInfo[]>("GET", `${BASE}/ai/models/${provider}`),
  testConnection: (data: { provider: string; api_key?: string; base_url?: string; auth_mode?: string; auth_token?: string; model?: string }) =>
    request<{ status: string }>("POST", `${BASE}/ai/providers/${data.provider}/test-connection`, data),
  listModelsProxy: (provider: string, params: { base_url?: string; api_key?: string; auth_mode?: string; auth_token?: string }) => {
    const qs = new URLSearchParams(params as any).toString();
    return request<ModelInfo[]>("GET", `${BASE}/ai/providers/${provider}/models?${qs}`);
  },
  getResolvedModel: (type: string) => request<{ provider: string; model: string }>("GET", `${BASE}/ai/resolved-models?type=${type}`),
  upsertKey: (data: { provider: string; api_key?: string; base_url?: string; auth_mode?: string; auth_token?: string; default_chat_model?: string; default_embedding_model?: string }) => request<AIKey>("POST", `${BASE}/ai/keys`, data),

  // Phase 6 — Session management
  listSessions: (workspaceId: string, limit = 20) =>
    request<ChatSession[]>("GET", `${BASE}/ai/sessions?workspace_id=${workspaceId}&limit=${limit}`),
  getSessionMessages: (sessionId: string, limit = 20, beforeId?: number) => {
    const qs = beforeId ? `?limit=${limit}&before_id=${beforeId}` : `?limit=${limit}`;
    return request<ChatMessage[]>("GET", `${BASE}/ai/sessions/${sessionId}/messages${qs}`);
  },
  renameSession: (sessionId: string, title: string) =>
    request("PATCH", `${BASE}/ai/sessions/${sessionId}`, { title }),
  deleteSession: (sessionId: string) =>
    request("DELETE", `${BASE}/ai/sessions/${sessionId}`),
};

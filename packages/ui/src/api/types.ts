export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface Workspace {
  id: string;
  name_zh: string;
  name_en: string;
  visibility: string;
  kb_type: "evergreen" | "ephemeral";
  owner_id: string;
  created_at: string;
  updated_at: string;
  my_role: "admin" | "editor" | "viewer" | null;
  embedding_model: string;
  embedding_dim: number;
  qa_archive_mode: "auto_active" | "manual_review";
  extraction_provider: string | null;
}

export interface Node {
  id: string;
  workspace_id: string;
  title_zh: string;
  title_en: string;
  content_type: string;
  content_format: string;
  body_zh: string;
  body_en: string;
  tags: string[];
  visibility: string;
  author: string;
  trust_score: number;
  dim_accuracy: number;
  dim_freshness: number;
  dim_utility: number;
  dim_author_rep: number;
  traversal_count: number;
  unique_traverser_count: number;
  created_at: string;
  updated_at?: string;
  signature: string;
  source_type: string;
  status: string;
  copied_from_node?: string;
  copied_from_ws?: string;
  archived_at?: string | null;
  validity_confirmed_at?: string | null;
  validity_confirmed_by?: string | null;
  content_stripped?: boolean;
  ask_count: number;
}

export interface NodeCreatePayload {
  title_zh: string;
  title_en: string;
  content_type: string;
  content_format: string;
  body_zh: string;
  body_en: string;
  tags: string[];
  visibility: string;
  copied_from_node?: string;
  copied_from_ws?: string;
}

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

export interface Onboarding {
  completed: boolean;
  steps_done: string[];
  steps_skipped: string[];
  first_kb_id: string | null;
}

export interface PersonalApiKey {
  id: string;
  name: string;
  prefix: string;
  scopes: string[];
  workspace_id: string | null;
  created_at: string;
  last_used_at: string | null;
  expires_at: string | null;
  revoked_at: string | null;
}

export interface BackupConfig {
  enabled: boolean;
  path: string;
  interval_hours: number;
  keep_count: number;
  last_backup_at?: string;
  last_backup_status?: string;
  last_backup_file?: string;
}

export interface WorkspaceCloneJob {
  id: string;
  source_ws_id: string;
  target_ws_id: string;
  status: "pending" | "running" | "completed" | "failed" | "cancelling" | "cancelled";
  processed_nodes: number;
  total_nodes: number;
  is_fork: boolean;
  error_msg?: string;
}

export interface Member {
  user_id: string;
  display_name: string;
  email: string;
  role: string;
  joined_at: string;
}

export interface Invite {
  id: string;
  workspace_id: string;
  email?: string | null;
  role: string;
  token: string;
  inviter_id: string;
  created_at: string;
  expires_at: string;
  accepted_at: string | null;
  invite_url?: string | null;
}

export interface ReviewItem {
  id: string;
  workspace_id: string;
  can_review: boolean;
  change_type: "create" | "update" | "delete" | "create_edge" | "split_suggestion";
  target_node_id?: string | null;
  node_data: any;
  status: string;
  proposer_type: "human" | "ai";
  created_at: string;
}

export interface IngestionLog {
  id: string;
  filename: string;
  status: "pending" | "processing" | "completed" | "failed" | "cancelling" | "cancelled";
  error_msg?: string;
  chunks_total?: number;
  chunks_done?: number;
  created_at: string;
  completed_at?: string;
}

export interface GraphPreview {
  nodes: { preview_id: string; content_type: string }[];
  edges: { from_preview_id: string; to_preview_id: string; relation: string }[];
}

export interface ModelInfo {
  id: string;
  display_name: string;
  model_type?: 'chat' | 'embedding';
  embedding_dim?: number;
  needs_install?: boolean;
}

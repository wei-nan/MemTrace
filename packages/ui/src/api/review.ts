import { BASE, request } from './client';
import type { Node, NodeCreatePayload, DiffSummary } from './nodes';

export interface AIReviewResult {
  decision: "accept" | "reject" | "comment";
  confidence: number;
  reasoning: string;
  reviewer_id: string;
  reviewed_at: string;
}

export interface ReviewItem {
  id: string;
  workspace_id: string;
  can_review: boolean;
  change_type: "create" | "update" | "delete" | "create_edge" | "split_suggestion";
  target_node_id?: string | null;
  before_snapshot?: Partial<NodeCreatePayload> | null;
  node_data: (Partial<NodeCreatePayload> & { from_id?: string; to_id?: string; relation?: string }) | any;
  diff_summary: DiffSummary;
  suggested_edges: unknown[];
  status: string;
  source_info?: string;
  proposer_type: "human" | "ai";
  proposer_id?: string | null;
  proposer_meta?: Record<string, unknown> | null;
  reviewer_type?: "human" | "ai" | null;
  reviewer_id?: string | null;
  ai_review?: AIReviewResult | null;
  review_notes?: string | null;
  created_at: string;
  reviewed_at?: string | null;
}

export interface AIReviewerPayload {
  name: string;
  provider: string;
  model: string;
  system_prompt: string;
  auto_accept_threshold: number;
  auto_reject_threshold: number;
  enabled: boolean;
}

export interface AIReviewer extends AIReviewerPayload {
  id: string;
  workspace_id: string;
  created_at: string;
}

export interface ReviewPolicy {
  workspace_id: string;
  inherit_system_default: boolean;
  mode: "manual_only" | "fallback_advisory" | "panel_advisory" | "consensus_automatic";
  minimum_success: number;
  accept_rule: Record<string, any>;
  reject_rule: Record<string, any>;
  policy_version: number;
  updated_by?: string | null;
  updated_at: string;
}

export interface ModelBinding {
  id: string;
  workspace_id: string;
  model_account_id: string;
  source_scope: "system" | "user";
  offered_by: string;
  allowed_usages: string[];
  billing_owner: string;
  consent_status: "pending" | "approved" | "rejected";
  approval_status: "pending" | "approved" | "rejected";
  status: "offered" | "active" | "paused" | "revoked" | "unavailable" | "disabled_by_admin";
  priority: number;
  created_at: string;
  updated_at: string;
  revoked_at?: string | null;
  // joined fields:
  provider: string;
  model: string;
  key_hint: string;
  offered_by_name: string;
}

export interface ReviewPolicyUpdate {
  mode: string;
  inherit_system_default?: boolean;
  minimum_success?: number;
  accept_rule?: Record<string, any>;
  reject_rule?: Record<string, any>;
}

export interface ModelBindingCreate {
  model_account_id: string;
  allowed_usages: string[];
  priority?: number;
}

export interface ModelBindingUpdate {
  status?: string;
  priority?: number;
  allowed_usages?: string[];
}

export interface PolicyMember {
  policy_id: string;
  binding_id: string;
  priority: number;
  is_required: boolean;
  created_at: string;
  // joined fields:
  binding_status: string;
  provider: string;
  model: string;
  key_hint: string;
  offered_by_name: string;
}

export interface PolicyMemberUpdate {
  binding_id: string;
  priority: number;
  is_required: boolean;
}

export const review = {
  list: (wsId: string, status = "pending") => request<ReviewItem[]>("GET", `${BASE}/workspaces/${wsId}/review-queue?status=${status}`),
  update: (id: string, data: { node_data?: Record<string, unknown>; suggested_edges?: unknown[]; review_notes?: string }) =>
    request<ReviewItem>("PATCH", `${BASE}/workspaces/review-queue/${id}`, data),
  accept: (id: string) => request<Node | null>("POST", `${BASE}/workspaces/review-queue/${id}/accept`),
  reject: (id: string) => request("POST", `${BASE}/workspaces/review-queue/${id}/reject`),
  acceptAll: (wsId: string) => request<{ accepted_count: number }>("POST", `${BASE}/workspaces/${wsId}/review-queue/accept-all`),
  rejectAll: (wsId: string) => request("POST", `${BASE}/workspaces/${wsId}/review-queue/reject-all`),
  acceptBatch: (wsId: string, ids: string[]) => request<{ accepted_count: number }>("POST", `${BASE}/workspaces/${wsId}/review-queue/accept-batch`, { ids }),
  rejectBatch: (wsId: string, ids: string[]) => request<{ rejected_count: number }>("POST", `${BASE}/workspaces/${wsId}/review-queue/reject-batch`, { ids }),
  aiPrescreen: (wsId: string) => request<{ processed_count: number }>("POST", `${BASE}/workspaces/${wsId}/review-queue/ai-prescreen`),
  
  // Policy & Binding API
  getPolicy: (wsId: string) => request<ReviewPolicy>("GET", `${BASE}/workspaces/${wsId}/review-policy`),
  updatePolicy: (wsId: string, data: ReviewPolicyUpdate) => request<ReviewPolicy>("PUT", `${BASE}/workspaces/${wsId}/review-policy`, data),
  listBindings: (wsId: string) => request<ModelBinding[]>("GET", `${BASE}/workspaces/${wsId}/model-bindings`),
  createBinding: (wsId: string, data: ModelBindingCreate) => request<ModelBinding>("POST", `${BASE}/workspaces/${wsId}/model-bindings`, data),
  updateBinding: (wsId: string, bindingId: string, data: ModelBindingUpdate) => request<ModelBinding>("PATCH", `${BASE}/workspaces/${wsId}/model-bindings/${bindingId}`, data),
  deleteBinding: (wsId: string, bindingId: string) => request("DELETE", `${BASE}/workspaces/${wsId}/model-bindings/${bindingId}`),
  getPolicyMembers: (wsId: string) => request<PolicyMember[]>("GET", `${BASE}/workspaces/${wsId}/review-policy/members`),
  updatePolicyMembers: (wsId: string, members: PolicyMemberUpdate[]) => request<{ status: string }>("PUT", `${BASE}/workspaces/${wsId}/review-policy/members`, members),
};

export const aiReviewers = {
  list: (wsId: string) => request<AIReviewer[]>("GET", `${BASE}/workspaces/${wsId}/ai-reviewers`),
  create: (wsId: string, data: AIReviewerPayload) => request<AIReviewer>("POST", `${BASE}/workspaces/${wsId}/ai-reviewers`, data),
  update: (wsId: string, id: string, data: Partial<AIReviewerPayload>) =>
    request<AIReviewer>("PATCH", `${BASE}/workspaces/${wsId}/ai-reviewers/${id}`, data),
  delete: (wsId: string, id: string) => request("DELETE", `${BASE}/workspaces/${wsId}/ai-reviewers/${id}`),
};


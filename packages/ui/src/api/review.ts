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

export const review = {
  list: (wsId: string, status = "pending") => request<ReviewItem[]>("GET", `${BASE}/workspaces/${wsId}/review-queue?status=${status}`),
  update: (id: string, data: { node_data?: Record<string, unknown>; suggested_edges?: unknown[]; review_notes?: string }) =>
    request<ReviewItem>("PATCH", `${BASE}/workspaces/review-queue/${id}`, data),
  accept: (id: string) => request<Node | null>("POST", `${BASE}/workspaces/review-queue/${id}/accept`),
  reject: (id: string) => request("POST", `${BASE}/workspaces/review-queue/${id}/reject`),
  acceptAll: (wsId: string) => request<{ accepted_count: number }>("POST", `${BASE}/workspaces/${wsId}/review-queue/accept-all`),
  rejectAll: (wsId: string) => request("POST", `${BASE}/workspaces/${wsId}/review-queue/reject-all`),
  aiPrescreen: (wsId: string) => request<{ processed_count: number }>("POST", `${BASE}/workspaces/${wsId}/review-queue/ai-prescreen`),
};

export const aiReviewers = {
  list: (wsId: string) => request<AIReviewer[]>("GET", `${BASE}/workspaces/${wsId}/ai-reviewers`),
  create: (wsId: string, data: AIReviewerPayload) => request<AIReviewer>("POST", `${BASE}/workspaces/${wsId}/ai-reviewers`, data),
  update: (wsId: string, id: string, data: Partial<AIReviewerPayload>) =>
    request<AIReviewer>("PATCH", `${BASE}/workspaces/${wsId}/ai-reviewers/${id}`, data),
  delete: (wsId: string, id: string) => request("DELETE", `${BASE}/workspaces/${wsId}/ai-reviewers/${id}`),
};

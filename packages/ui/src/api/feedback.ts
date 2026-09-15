import { BASE, request } from './client';

export type FeedbackType = 'bug-report' | 'feature-request';

export interface FeedbackCreatePayload {
  type: FeedbackType;
  title: string;
  body: string;
}

export interface FeedbackCreateResponse {
  id: string;
  status: string;
}

export interface FeedbackItem {
  id: string;
  type: string;
  title: string;
  resolution_status: string;
  created_at: string;
}

export interface AdminFeedbackItem extends FeedbackItem {
  body: string;
  author_id: string;
  author_name: string | null;
  author_email: string | null;
}

export const feedback = {
  submit: (data: FeedbackCreatePayload) =>
    request<FeedbackCreateResponse>('POST', `${BASE}/feedback`, data),
  mine: () => request<FeedbackItem[]>('GET', `${BASE}/feedback/mine`),
  all: () => request<AdminFeedbackItem[]>('GET', `${BASE}/feedback/all`),
};

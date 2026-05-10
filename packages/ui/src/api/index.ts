import { auth } from './auth';
import { workspaces } from './workspaces';
import { nodes } from './nodes';
import { edges } from './edges';
import { ai } from './ai';
import { review, aiReviewers } from './review';
import { ingest } from './ingest';
import { system, kb } from './system';
import { request } from './client';
import type { PersonalApiKey, PersonalApiKeyCreateResponse } from './workspaces';

export * from './client';
export * from './auth';
export * from './workspaces';
export * from './nodes';
export * from './edges';
export * from './ai';
export * from './review';
export * from './ingest';
export * from './system';

export const users = {
  apiKeys: {
    list: () => request<PersonalApiKey[]>("GET", `/api/v1/users/me/api-keys`),
    create: (data: { name: string; scopes: string[]; workspace_id?: string }) =>
      request<PersonalApiKeyCreateResponse>("POST", `/api/v1/users/me/api-keys`, data),
    revoke: (id: string) => request("DELETE", `/api/v1/users/me/api-keys/${id}`),
    rotate: (id: string) => request<PersonalApiKeyCreateResponse>("POST", `/api/v1/users/me/api-keys/${id}/rotate`),
  }
};

export const api = {
  auth,
  workspaces,
  nodes,
  edges,
  ai,
  review,
  aiReviewers,
  ingest,
  users,
  system,
  kb,
};

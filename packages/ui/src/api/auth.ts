import { request, refreshAccessToken } from './client';

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface Onboarding {
  completed: boolean;
  steps_done: string[];
  steps_skipped: string[];
  first_kb_id: string | null;
}

export const auth = {
  register: (data: { email: string; purpose_note?: string }) =>
    request<{ message: string }>("POST", "/auth/register", data),
  login: (data: { email: string; password: string }) =>
    request<{ access_token: string }>("POST", "/auth/login", data),
  logout: () => request("POST", "/auth/logout"),
  refresh: () => refreshAccessToken(),
  me: () => request<{ id: string; display_name: string; email: string; email_verified: boolean }>("GET", "/auth/me"),
  verifyEmail: (token: string) => request("POST", `/auth/verify-email/${token}`),
  resendVerification: () => request("POST", "/auth/resend-verification-email"),
  registerWithInvite: (token: string, data: { email: string }) => request("POST", `/auth/register/invite/${token}`, data),
  verifyMagicLink: (token: string) => request<TokenResponse>("POST", "/auth/magic-link/verify", { token }),
  forgotPassword: (email: string) => request("POST", "/auth/forgot-password", { email }),
  resetPassword: (token: string, password: string) => request("POST", "/auth/reset-password", { token, new_password: password }),
  getOnboarding: () => request<Onboarding>("GET", "/auth/me/onboarding"),
  updateOnboarding: (data: Partial<Onboarding>) => request<Onboarding>("PATCH", "/auth/me/onboarding", data),
  updatePassword: (password: string) => request("POST", "/auth/me/password", { new_password: password }),
};

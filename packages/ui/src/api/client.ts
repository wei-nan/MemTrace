export const BASE = "/api/v1";

export function authHeaders(): Record<string, string> {
  const token = localStorage.getItem("mt_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/** Read the double-submit CSRF cookie set by the server on every GET response. */
export function getCsrfToken(): string {
  const match = document.cookie.match(/(?:^|;\s*)mt_csrf=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : "";
}

/** Build headers for a mutating request (POST / PUT / PATCH / DELETE). */
export function writeHeaders(): Record<string, string> {
  const csrf = getCsrfToken();
  return csrf ? { "X-CSRF-Token": csrf } : {};
}

// ─── Cross-tab token refresh coordination ────────────────────────────────────
const _bcSupported = typeof BroadcastChannel !== "undefined";
const _bc: BroadcastChannel | null = _bcSupported ? new BroadcastChannel("mt-auth") : null;

let _refreshing: Promise<string | null> | null = null;

function _broadcastTokenRefreshed(token: string): void {
  try { _bc?.postMessage({ type: "token-refreshed", token, ts: Date.now() }); } catch {}
}

function _broadcastSessionExpired(): void {
  try { _bc?.postMessage({ type: "session-expired", ts: Date.now() }); } catch {}
}

if (_bc) {
  _bc.addEventListener("message", (ev) => {
    if (!ev.data || typeof ev.data !== "object") return;
    if (ev.data.type === "token-refreshed" && typeof ev.data.token === "string") {
      localStorage.setItem("mt_token", ev.data.token);
    } else if (ev.data.type === "session-expired") {
      localStorage.removeItem("mt_token");
      window.dispatchEvent(new CustomEvent("mt:session-expired"));
    }
  });
}

window.addEventListener("storage", (ev) => {
  if (ev.key === "mt_token" && ev.newValue === null) {
    window.dispatchEvent(new CustomEvent("mt:session-expired"));
  }
});

async function _doRefresh(): Promise<string | null> {
  try {
    const res = await fetch("/auth/refresh", {
      method: "POST",
      credentials: "include",
      headers: { ...writeHeaders() },
    });
    if (!res.ok) return null;
    const data = await res.json();
    if (data.access_token) {
      localStorage.setItem("mt_token", data.access_token);
      _broadcastTokenRefreshed(data.access_token);
      return data.access_token;
    }
    return null;
  } catch {
    return null;
  }
}

export async function refreshAccessToken(): Promise<string | null> {
  if (_refreshing) return _refreshing;
  _refreshing = (async () => {
    const stored = localStorage.getItem("mt_token");
    const fresh = await _doRefresh();
    return fresh ?? stored;
  })();
  try {
    return await _refreshing;
  } finally {
    _refreshing = null;
  }
}

export async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const isMutating = !["GET", "HEAD", "OPTIONS"].includes(method.toUpperCase());
  const doFetch = (accessToken?: string) =>
    fetch(path, {
      method,
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : authHeaders()),
        ...(isMutating ? writeHeaders() : {}),
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });

  let res = await doFetch();

  if (res.status === 401 && path !== "/auth/refresh" && path !== "/auth/login") {
    const newToken = await refreshAccessToken();
    if (newToken) {
      res = await doFetch(newToken);
    } else {
      localStorage.removeItem("mt_token");
      _broadcastSessionExpired();
      window.dispatchEvent(new CustomEvent("mt:session-expired"));
    }
  }

  if (!res.ok) {
    let errDetail;
    try {
      const err = await res.json();
      errDetail = err.detail ?? err.message ?? err;
      if (typeof errDetail === 'object') errDetail = JSON.stringify(errDetail);
    } catch {
      errDetail = res.statusText;
    }
    throw new Error(errDetail ?? `HTTP ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export async function requestStream(path: string, body: unknown, onChunk: (data: any) => void): Promise<void> {
  const doFetch = (accessToken?: string) =>
    fetch(path, {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : authHeaders()),
        ...writeHeaders(),
      },
      body: JSON.stringify(body),
    });

  let res = await doFetch();

  if (res.status === 401) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      res = await doFetch(newToken);
    } else {
      localStorage.removeItem("mt_token");
      _broadcastSessionExpired();
      window.dispatchEvent(new CustomEvent("mt:session-expired"));
    }
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }

  const reader = res.body?.getReader();
  if (!reader) return;

  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";
      for (const line of lines) {
        if (line.trim()) {
          try {
            onChunk(JSON.parse(line));
          } catch (e) {
            console.error("Failed to parse stream chunk", e);
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

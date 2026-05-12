-- Phase 4.10 Knowledge Base Nodes
-- Covers: Account-Level API Key design, Magic Link mode restriction, Token refresh race fix

-- ─── UPDATE existing nodes to Phase 4.10 content ─────────────────────────────

UPDATE public.memory_nodes SET
  title_zh = '帳號層級 API 金鑰：建立與管理',
  title_en = 'Account-Level API Key: Create & Manage',
  content_type = 'procedural',
  content_format = 'markdown',
  body_zh = $zh$## 建立金鑰

`POST /api/v1/users/me/api-keys`

```json
{ "name": "My MCP Agent" }
```

**回應**（金鑰只顯示一次，請立即複製）：
```json
{
  "id": "key_xxx",
  "name": "My MCP Agent",
  "key": "mt_xxxxxxxx",
  "prefix": "mt_xxxx",
  "created_at": "..."
}
```

## 列出金鑰

`GET /api/v1/users/me/api-keys` — 回傳所有帳號金鑰（不回傳明文，只有 prefix）

## 輪替金鑰

`POST /api/v1/users/me/api-keys/{id}/rotate` — 舊金鑰立即失效，回傳新 key（同樣只顯示一次）

## 撤銷金鑰

`DELETE /api/v1/users/me/api-keys/{id}`

## 重要設計（Phase 4.10）

- **不綁定 workspace**、**不綁定固定 scope**
- 金鑰對所有知識庫都有效，權限在每次 API 呼叫時從 `workspace_members` 動態解析
- `key_type = 'account'`（與 §29 Workspace Service Token 的 `'service'` 區別）
- UI 路徑：Settings → MCP / API Keys$zh$,
  body_en = $en$## Create a Key

`POST /api/v1/users/me/api-keys`

```json
{ "name": "My MCP Agent" }
```

**Response** (key shown only once — copy it immediately):
```json
{
  "id": "key_xxx",
  "name": "My MCP Agent",
  "key": "mt_xxxxxxxx",
  "prefix": "mt_xxxx",
  "created_at": "..."
}
```

## List Keys

`GET /api/v1/users/me/api-keys` — returns all account keys (prefix only, no plaintext)

## Rotate a Key

`POST /api/v1/users/me/api-keys/{id}/rotate` — old key invalidated immediately; returns new key (shown once)

## Revoke a Key

`DELETE /api/v1/users/me/api-keys/{id}`

## Key Design (Phase 4.10)

- **Not bound to a workspace** or **fixed scopes**
- The key is valid across all knowledge bases; permissions are resolved dynamically per request from `workspace_members`
- `key_type = 'account'` (distinguished from §29 Workspace Service Token which uses 'service')
- UI path: Settings → MCP / API Keys$en$,
  tags = '{api-key,mcp,auth,account}',
  dim_freshness = 1.000,
  updated_at = '2026-05-11 00:00:00+00'
WHERE id = 'mem_1185cce5';

UPDATE public.memory_nodes SET
  title_zh = 'MCP 傳輸模式：SSE 與 Streamable HTTP',
  title_en = 'MCP Transport: SSE and Streamable HTTP',
  content_type = 'factual',
  content_format = 'markdown',
  body_zh = $zh$MemTrace API 同時支援兩種 MCP 傳輸模式：

## Streamable HTTP（推薦，新版）

**端點**：`POST /mcp`

單一 POST endpoint，客戶端直接送 JSON-RPC，伺服器回傳 JSON 結果。Cursor、Antigravity 等現代 MCP client 使用此模式。

```json
{
  "mcpServers": {
    "memtrace": {
      "type": "streamableHttp",
      "url": "https://<host>/mcp",
      "headers": { "Authorization": "Bearer mt_xxx" }
    }
  }
}
```

## SSE（舊版，向後相容）

**端點**：`GET /api/v1/mcp/sse`（開啟長連線）+ `POST /api/v1/mcp/messages?sessionId=xxx`（送訊息）

SSE 是單向串流，需要兩個配套端點完成雙向通訊。Server 在 SSE 連線建立後會發送 `endpoint` event 告知客戶端 POST URL：

```
event: endpoint
data: https://<host>/api/v1/mcp/messages?sessionId=<uuid>
```

## 認證

兩種模式都使用 `Authorization: Bearer <api_key>` 標頭，API 金鑰從 Settings → MCP / API Keys 取得。$zh$,
  body_en = $en$MemTrace API supports two MCP transport modes:

## Streamable HTTP (Recommended, Modern)

**Endpoint**: `POST /mcp`

Single POST endpoint — client sends JSON-RPC, server returns JSON. Used by Cursor, Antigravity, and other modern MCP clients.

```json
{
  "mcpServers": {
    "memtrace": {
      "type": "streamableHttp",
      "url": "https://<host>/mcp",
      "headers": { "Authorization": "Bearer mt_xxx" }
    }
  }
}
```

## SSE (Legacy, Backward Compatible)

**Endpoints**: `GET /api/v1/mcp/sse` (open stream) + `POST /api/v1/mcp/messages?sessionId=xxx` (send messages)

SSE is unidirectional, requiring two paired endpoints for bidirectional communication. After opening the SSE connection, the server sends an endpoint event with the POST URL.

## Authentication

Both modes use the `Authorization: Bearer <api_key>` header. API keys are created under Settings → MCP / API Keys.$en$,
  tags = '{mcp,transport,sse,streamable-http,api}',
  dim_freshness = 1.000,
  updated_at = '2026-05-11 00:00:00+00'
WHERE id = 'mem_526945e4';

-- ─── Node 1: Account-Level API Key Design Decision ───────────────────────────

INSERT INTO public.memory_nodes (
  id, schema_version, workspace_id, title_zh, title_en,
  content_type, content_format, body_zh, body_en,
  tags, visibility, author, created_at, updated_at,
  signature, source_type,
  trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep,
  votes_up, votes_down, verifications, traversal_count, unique_traverser_count,
  status, embedding, validity_confirmed_at, validity_confirmed_by, source_file
) VALUES (
  'mem_p410a', '1.0', 'ws_spec0001',
  '帳號層級 API 金鑰：設計決策（Phase 4.10）',
  'Account-Level API Key: Design Decision (Phase 4.10)',
  'preference', 'markdown',
  $zh$## 決策

Phase 4.10 將 MCP / API 金鑰從「工作區綁定 + 固定 scope」改為「帳號層級 + 動態角色繼承」。

## 舊設計問題

每個知識庫需要獨立金鑰，且 scope（`kb:read`、`kb:write`）在建立時固定，跨知識庫使用不方便且難以管理。

## key_type 區分器（Migration 048）

| key_type | 說明 |
|---|---|
| `account` | 帳號層級金鑰，動態繼承角色（新） |
| `service` | Workspace Service Token（§29），保留固定 scope |

## 動態角色解析（deps.py，每次 API 呼叫）

1. 從 request path 提取 `workspace_id`
2. 查 `workspace_members`（`user_id` + `workspace_id`）取得 `role`
3. 若為 workspace owner（`workspaces.owner_id`）則視為 `admin`
4. Path 不含 workspace（如 `/auth/me`）則 role = `None`

角色等級：`viewer` < `contributor` < `admin`（owner 視同 admin）

## 影響

- `RequireScope` 改為 `RequireRole`（`RequireScope` 僅保留給 §29 service token）
- 新增 `idx_wsm_user` 索引確保查詢效能
- UI Settings → MCP / API Keys 移除 scope / workspace selector$zh$,
  $en$## Decision

Phase 4.10 redesigns MCP / API keys from workspace-bound + fixed scope to account-level + dynamic role inheritance.

## Problem with Old Design

Each knowledge base required its own key, and scopes (kb:read, kb:write) were fixed at creation time — inconvenient across multiple workspaces.

## key_type Discriminator (Migration 048)

| key_type | Description |
|---|---|
| `account` | Account-level key, dynamic role inheritance (new) |
| `service` | Workspace Service Token (§29), retains fixed scopes |

## Dynamic Role Resolution (deps.py, per request)

1. Extract workspace_id from request path
2. Query workspace_members (user_id + workspace_id) for role
3. If user is workspace owner (workspaces.owner_id), treat as admin
4. No workspace in path (e.g. /auth/me) means role = None

Role hierarchy: viewer < contributor < admin (owner treated as admin)

## Impact

- RequireScope replaced by RequireRole (RequireScope kept only for §29 service tokens)
- idx_wsm_user index ensures performant role lookups
- UI Settings > MCP / API Keys removes scope/workspace selectors$en$,
  '{api-key,auth,rbac,phase-4,architecture}',
  'public', 'system',
  '2026-05-11 00:00:00+00', '2026-05-11 00:00:00+00',
  'p410a_account_level_api_key_design_decision',
  'ai',
  0.850, 0.920, 1.000, 0.880, 0.500,
  0, 0, 0, 0, 0,
  'active', NULL, NULL, NULL, NULL
) ON CONFLICT (id) DO NOTHING;

-- ─── Node 2: Magic Link Mode Restriction ─────────────────────────────────────

INSERT INTO public.memory_nodes (
  id, schema_version, workspace_id, title_zh, title_en,
  content_type, content_format, body_zh, body_en,
  tags, visibility, author, created_at, updated_at,
  signature, source_type,
  trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep,
  votes_up, votes_down, verifications, traversal_count, unique_traverser_count,
  status, embedding, validity_confirmed_at, validity_confirmed_by, source_file
) VALUES (
  'mem_p410m', '1.0', 'ws_spec0001',
  'Magic Link：僅限 invite_only 模式（Phase 4.10）',
  'Magic Link: Restricted to invite_only Mode (Phase 4.10)',
  'factual', 'markdown',
  $zh$## 機制

Magic Link 為無密碼登入：系統產生一次性 token（SHA-256 雜湊存 DB，15 分鐘效期），寄至使用者 email，點擊後驗證並核發 JWT session。

## Phase 4.10 限制

Magic Link 僅在 `MEMTRACE_REGISTRATION_MODE=invite_only` 時開放。

| registration_mode | Magic Link 可用？ |
|---|---|
| `open` | ❌ 403 magic_link_unavailable |
| `domain` | ❌ 403 |
| `approval` | ❌ 403 |
| `invite_only` | ✅ 可用 |
| `closed` | ❌ 403 |

## 後端 guard（routers/registration.py）

`POST /auth/magic-link/request` 與 `POST /auth/magic-link/verify` 兩個端點皆在開頭檢查：
若 `settings.registration_mode != "invite_only"` 則回傳 403 `magic_link_unavailable`。

## 前端感知

UI 透過 `GET /auth/config`（無需 auth）取得 `registration_mode`，
僅在 `invite_only` 時顯示「以 Email 連結登入」選項。

## 邀請流程

`invite_only` 模式下，workspace 邀請連結仍觸發 Magic Link（magic_link_tokens 含 invitation_id）。
其他模式下邀請連結改為導向一般 register 表單。$zh$,
  $en$## Mechanism

Magic Link is passwordless login: a one-time token (SHA-256 hash, 15-minute TTL) is emailed to the user; clicking it issues a JWT session.

## Phase 4.10 Restriction

Magic Link is only available when MEMTRACE_REGISTRATION_MODE=invite_only.

| registration_mode | Magic Link available? |
|---|---|
| open | 403 magic_link_unavailable |
| domain | 403 |
| approval | 403 |
| invite_only | available |
| closed | 403 |

## Backend Guard (routers/registration.py)

Both POST /auth/magic-link/request and POST /auth/magic-link/verify check at the start:
if settings.registration_mode != invite_only, return 403 magic_link_unavailable.

## Frontend Awareness

UI calls GET /auth/config (no auth) to get registration_mode,
and shows the magic link option only in invite_only mode.

## Invitation Flow

In invite_only mode, workspace invitation links still trigger Magic Link (magic_link_tokens includes invitation_id).
In other modes, invitation links redirect to the standard register form.$en$,
  '{auth,magic-link,registration,security}',
  'public', 'system',
  '2026-05-11 00:00:00+00', '2026-05-11 00:00:00+00',
  'p410m_magic_link_invite_only_restriction',
  'ai',
  0.850, 0.920, 1.000, 0.880, 0.500,
  0, 0, 0, 0, 0,
  'active', NULL, NULL, NULL, NULL
) ON CONFLICT (id) DO NOTHING;

-- ─── Node 3: Token Refresh Race Condition Fix ─────────────────────────────────

INSERT INTO public.memory_nodes (
  id, schema_version, workspace_id, title_zh, title_en,
  content_type, content_format, body_zh, body_en,
  tags, visibility, author, created_at, updated_at,
  signature, source_type,
  trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep,
  votes_up, votes_down, verifications, traversal_count, unique_traverser_count,
  status, embedding, validity_confirmed_at, validity_confirmed_by, source_file
) VALUES (
  'mem_p410t', '1.0', 'ws_spec0001',
  'JWT Token 刷新競態條件修復（authChecking 模式）',
  'JWT Token Refresh Race Condition Fix (authChecking Pattern)',
  'preference', 'markdown',
  $zh$## 問題

使用者長時間未使用後重新整理頁面，`workspaces.list()` 用過期的 token 發出請求。
後端 `get_current_user_optional` 將過期 token 視為匿名，回傳 200 + 公開知識庫，
而非 401（不觸發重試）。結果：第一次重新整理只看到公開知識庫，第二次才正常。

## 根本原因

`App.tsx` 原本同步設定 `authenticated = !!localStorage.getItem('mt_token')`，
導致 `workspaces.list()` 在 token 驗證前就觸發。

## 修法（App.tsx）

新增 `authChecking` state，在 token 驗證/刷新完成前阻擋所有資料載入：

1. `authChecking` 初始為 `true`，顯示 loading spinner
2. 非同步檢查 `isTokenStale()`：若過期則先 `refreshAccessToken()`
3. 刷新失敗 → 清除 token，`authChecking = false`，顯示登入頁
4. 驗證成功 → `authenticated = true`，`authChecking = false`，觸發資料載入

## isTokenStale()（client.ts）

解碼 JWT payload 的 `exp` 欄位，提前 60 秒視為過期，避免邊界競態。$zh$,
  $en$## Problem

After long inactivity, page refresh fires workspaces.list() with an expired token.
The backend get_current_user_optional treats expired tokens as anonymous and returns 200 + public KBs (not 401, so no retry).
Result: first refresh shows only public KBs; second refresh is correct.

## Root Cause

App.tsx synchronously set authenticated = !!localStorage.getItem(mt_token),
causing workspaces.list() to fire before token validation.

## Fix (App.tsx)

Added authChecking state to block all data loading until token validation completes:

1. authChecking starts true, shows loading spinner
2. Async check isTokenStale(): if stale, call refreshAccessToken() first
3. Refresh fails: clear token, authChecking = false, show login page
4. Validation succeeds: authenticated = true, authChecking = false, data loading proceeds

## isTokenStale() (client.ts)

Decodes JWT payload exp field with a 60-second buffer to avoid boundary race conditions.$en$,
  '{auth,frontend,jwt,race-condition,ux}',
  'public', 'system',
  '2026-05-11 00:00:00+00', '2026-05-11 00:00:00+00',
  'p410t_token_refresh_race_condition_fix',
  'ai',
  0.850, 0.920, 1.000, 0.850, 0.500,
  0, 0, 0, 0, 0,
  'active', NULL, NULL, NULL, NULL
) ON CONFLICT (id) DO NOTHING;

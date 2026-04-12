# MemTrace — 規格未實作項目 Backlog

> 產出日期：2026-04-11
> 審核基準：`SPEC.md` × 實際程式碼（packages/api、ui、mcp、core、cli、schema）
> 標記說明：✅ 已實作 ⬜ 未實作 🔧 部分實作（schema 或 stub 存在，邏輯缺失）

---

## 目錄

1. [Critical — 核心流程缺漏](#1-critical--核心流程缺漏)
2. [High — 重要功能](#2-high--重要功能)
3. [Medium — 品質與完整性](#3-medium--品質與完整性)
4. [Low — 錦上添花](#4-low--錦上添花)
5. [各層快速對照表](#5-各層快速對照表)

---

## 1. Critical — 核心流程缺漏

### 1.1 Review Queue（AI 審核佇列） ✅

**規格依據**：SPEC.md §4.2；`examples/spec-as-kb/nodes/mem_a003.json`

AI 擷取（extraction）的結果必須進入人工審核佇列，經確認後才能寫入知識庫。

**實作狀態**：

| 層 | 項目 | 狀態 |
|----|------|------|
| DB | `review_queue` 資料表 | ✅ |
| API | `POST /workspaces/{ws_id}/review-queue` — AI 擷取後寫入 | ✅ |
| API | `GET /workspaces/{ws_id}/review-queue` — 列出待審清單 | ✅ |
| API | `PATCH /review-queue/{id}` — 修改候選內容 | ✅ |
| API | `POST /review-queue/{id}/accept` — 接受並寫入 memory_nodes | ✅ |
| API | `POST /review-queue/{id}/reject` — 拒絕並標記 | ✅ |
| UI | 候選節點列表頁 | ✅ |
| UI | 逐筆 Accept / Edit / Reject 操作 | ✅ |
| UI | 批次操作（Accept All / Reject All） | ✅ |

---

### 1.2 Onboarding 新手引導流程 ✅

**規格依據**：SPEC.md §5.1；`mem_o001.json`、`mem_o002.json`

新使用者第一次登入應有 7 步驟引導。

**實作狀態**：

| 層 | 項目 | 狀態 |
|----|------|------|
| API | `GET /auth/me/onboarding` — 查詢進度 | ✅ |
| API | `PATCH /auth/me/onboarding` — 更新進度 | ✅ |
| UI | Onboarding wizard 元件（7 步驟） | ✅ |
| 內容 | ① 帳號建立 | ✅ |
| 內容 | ② Email 驗證 | ✅ |
| 內容 | ③ 命名第一個 KB（功能化） | ✅ |
| 內容 | ④ 選擇起點（上傳文件） | ✅ |
| 內容 | ⑤ AI provider 設定 | ✅ |
| 內容 | ⑥ 審核 AI 擷取節點（連動） | ✅ |
| 內容 | ⑦ 完成 + 快捷提示 | ✅ |

---

### 1.3 文件攝入（File Ingestion）

**規格依據**：SPEC.md §4.2；`mem_a002.json`

使用者上傳文件 → 後端解析 → 呼叫 AI 擷取節點 → 進入 Review Queue。

**缺少項目**：

| 層 | 項目 |
|----|------|
| API | `POST /workspaces/{ws_id}/ingest` — 接收 .md / .txt / .pdf / .docx 上傳 |
| API | 背景任務：文件解析 + 呼叫 AI extraction + 寫入 review_queue |
| UI | 拖拉上傳元件 |
| UI | 解析預覽（文件摘要 + 預期擷取節點數） |

---

### 1.4 Email 驗證 ✅

**規格依據**：SPEC.md §4.1；`mem_i001.json`

**實作狀態**：

| 層 | 項目 | 狀態 |
|----|------|------|
| API | `POST /auth/verify-email/{token}` | ✅ |
| API | `POST /auth/resend-verification-email` | ✅ |
| 邏輯 | 驗證 Email 實際發送 | ✅ |
| 邏輯 | Token 到期強制失效 | ✅ |
| UI | 重新發送驗證信按鈕 | ✅ |

---

### 1.5 Workspace 成員管理 API

**規格依據**：SPEC.md §5.2

**缺少項目**：

| 層 | 項目 |
|----|------|
| API | `GET /workspaces/{ws_id}/members` — 列出成員與角色 |
| API | `PUT /workspaces/{ws_id}/members/{user_id}` — 變更角色（viewer / editor / admin） |
| API | `DELETE /workspaces/{ws_id}/members/{user_id}` — 移除成員 |
| UI | 成員清單顯示 |
| UI | 角色變更下拉選單 |
| UI | 移除成員按鈕 |

---

### 1.6 知識主權與角色邊界 (Role-Based Access Control & Content Stripping)

**規格依據**：SPEC.md §1.1、§12.3、§12.6

維護知識作者主權，確保 Viewer 角色只能看見圖譜結構與標題，但不可抓取節點的詳細內容（需做後端過濾）；並修正目前後端缺漏的 Admin 寫入判定。

**缺少項目**：

| 層 | 項目 |
|----|------|
| API | **權限修補**：修正 `_require_ws_access` 邏輯，除了 `editor` 外，必須允許 `admin` 執行寫入 (write=True) |
| API | **資料過濾**：在節點讀取操作中（`GET /nodes`, `GET /nodes/{id}`），若連線使用者的角色為 `viewer`，自動在 Response 中剔除或清空 `body_zh` 與 `body_en` |
| UI | **鎖定狀態視覺化**：當節點內文因 `viewer` 角色被隱藏時，呈現「節點詳細資料僅限編輯者或管理員存取」鎖定狀態，並隱藏編輯與重構按鈕 |

---

## 2. High — 重要功能

### 2.1 Copy Node（跨工作區節點複製）

**規格依據**：SPEC.md §5.2；`mem_k003.json`

**缺少項目**：

| 層 | 項目 |
|----|------|
| API | `POST /workspaces/{ws_id}/nodes`（帶 `copied_from: { node_id, workspace_id }`） |
| CLI | `memtrace copy-node <node-id> --to <workspace-id>` |

> 備註：DB `memory_nodes.copied_from` 欄位已存在。

---

### 2.2 Workspace 邀請連結

**規格依據**：SPEC.md §5.2

**缺少項目**：

| 層 | 項目 |
|----|------|
| API | `POST /workspaces/{ws_id}/invites` — 建立帶 token 的邀請連結（含 expires_at） |
| API | `GET /workspaces/{ws_id}/invites` — 列出待確認邀請 |
| API | `POST /invites/{token}/accept` — 接受邀請，加入工作區 |
| API | `DELETE /invites/{token}` — 撤銷邀請 |
| UI | 產生邀請連結按鈕 |
| UI | 待確認邀請清單 |

> 備註：DB `workspace_invites` 資料表已存在。

---

### 2.3 Semantic Search（向量搜尋）

**規格依據**：SPEC.md §8.2

**缺少項目**：

| 層 | 項目 |
|----|------|
| API | 節點建立/更新時自動呼叫 embedding API，將向量存入 `embedding` 欄位 |
| API | `POST /workspaces/{ws_id}/nodes/search-semantic`（pgvector cosine similarity） |
| UI | 語意搜尋入口（切換 keyword / semantic 搜尋模式） |

> 備註：DB `memory_nodes.embedding vector(1536)` 欄位存在，但從未被填入。

---

### 2.4 節點歸檔排程

**規格依據**：SPEC.md §7.3；`mem_g003.json`

**缺少項目**：

| 層 | 項目 |
|----|------|
| 排程 | 背景任務定期呼叫 `apply_node_archiving()`（SQL function 已存在但未被呼叫） |
| 排程 | Ephemeral KB 加速 decay（規格：每 1 小時觸發，而非每日） |
| UI | 歸檔節點篩選顯示 |
| UI | 手動歸檔按鈕 |

---

### 2.5 MCP 寫入工具

**規格依據**：SPEC.md §4.3；`mem_i003.json`

**缺少項目**：

| 工具 | 說明 |
|------|------|
| `create_node` | 透過 MCP 建立新節點 |
| `update_node` | 更新節點內容 |
| `create_edge` | 建立節點間的邊 |
| `traverse_edge` | 記錄邊的 traversal，觸發 co-access boost |
| Resources | `memtrace://node/{id}` URI 讀取（MCP Resources 規範） |

---

### 2.6 有條件公開 (Conditional Public) 申請加入流程

**規格依據**：SPEC.md §12.5

**缺少項目**：

| 層 | 項目 |
|----|------|
| DB | 建立 `join_requests` 資料表 (schema 未套用或未寫入 SQL 初始化中) |
| API | `POST /workspaces/{ws_id}/join-requests` — 申請者送出要求 |
| API | `GET /workspaces/{ws_id}/join-requests` — Admin 檢視待審核要求 |
| API | `POST /workspaces/{ws_id}/join-requests/{id}/approve` — 核准並將成員以 default `viewer` 加入 |
| API | `POST /workspaces/{ws_id}/join-requests/{id}/reject` — 拒絕（並紀錄冷卻期 7 天） |
| UI | 入口：從公開/條件公開的搜尋結果頁面點擊申請 |
| UI | 管理：Admin 後台核准/拒絕介面 |

---

### 2.7 圖譜預覽 API (Graph Preview Mode)

**規格依據**：SPEC.md §12.2、§12.8

為 `conditional_public` 實作對未受邀者的「看見形狀與結構，但不能看到內容」的預覽。

**缺少項目**：

| 層 | 項目 |
|----|------|
| API | `GET /workspaces/{ws_id}/graph?preview=true` — 返回 Stripped graph payload（包含替換掉真實 Node IDs 為 `node_preview_N`，剔除標題與內文，僅保留位置及邊境類型） |
| UI | 在未登入或未取得存取權的狀態下，若存取 `conditional_public` KB，讀取預覽 API 並呈現視覺閹割版 2D/3D 圖譜 |

---

### 2.8 跨知識庫關聯 (Knowledge Base Associations)

**規格依據**：SPEC.md §18

允許不同知識庫建立明確連線，供 AI Agent 進行跨庫推斷（Cross-KB Reasoning）。

**缺少項目**：

| 層 | 項目 |
|----|------|
| DB | 建立 `workspace_associations` 資料表 |
| API | `GET /workspaces/{ws_id}/associations` — 列出關聯 KB |
| API | `POST /workspaces/{ws_id}/associations` — 新增關聯（限 admin） |
| API | `DELETE /workspaces/{ws_id}/associations/{target_ws_id}` — 移除關聯（限 admin） |
| UI | 知識庫關聯設定面板 |

---

### 2.9 AI 對話面板與即時提案 (AI Conversation Panel)

**規格依據**：SPEC.md §19

提供獨立的 AI 聊天介面，支援基於 Graph 的對答，並能在對話中直接產生節點編修提案（Edit Proposals）。

**缺少項目**：

| 層 | 項目 |
|----|------|
| API | `POST /api/v1/workspaces/{ws_id}/chat` — AI 對話端點，支援 `allow_edits` 參數產生提案，與跨庫查詢邊界控管 |
| API | 將對話所產生的 Proposal 操作整合至日常的 `review_queue` 中等待處理 |
| UI | 獨立的 AI Chat Panel 組件 |
| UI | 渲染對話中的 Inline 提案卡片（Accept / Edit / Reject） |

---

## 3. Medium — 品質與完整性

### 3.1 帳號安全機制

**規格依據**：SPEC.md §4.1；`mem_i001.json`

| 項目 | 狀態 | 說明 |
|------|------|------|
| 登入失敗鎖定 | ⬜ | 5 次失敗 → 鎖定 15 分鐘 |
| HaveIBeenPwned 檢查 | 🔧 | `check_password_policy()` 函式存在，但未呼叫外部 pwned API |
| API Key 輪換 | ⬜ | 缺少 `POST /auth/api-keys/{id}/rotate` |

---

### 3.2 API Key Scope 強制驗證

**規格依據**：SPEC.md §4.1；`mem_i002.json`

- DB `api_keys.scopes` 欄位定義了 `kb:read`、`kb:write`、`node:traverse`、`node:rate`
- **routers 中完全沒有 scope 驗證邏輯**，任何有效 key 可呼叫所有 endpoint
- 需在 `deps.py` 的 `verify_api_key()` 加入 scope 檢查，並在各 router decorator 標注所需 scope

---

### 3.3 Edge 視覺化缺漏

**規格依據**：SPEC.md §7.1；`mem_g001.json`

| 項目 | 說明 |
|------|------|
| Edge 粗細/透明度 | `weight` 值應反映在 GraphView 邊的視覺粗細或透明度 |
| Edge hover tooltip | 顯示 weight、half_life_days、co_access_count、min_weight |
| Co-access boost 動畫 | 邊被 boost 時應有視覺回饋（短暫高亮或動畫） |

---

### 3.4 Trust Score 詳細展示

**規格依據**：SPEC.md §5.1；`mem_d004.json`

- NodeEditor 目前只顯示綜合 trust_score
- 缺少 4 個維度拆解 tooltip：**accuracy / freshness / utility / author_rep**
- 缺少維度自動更新邏輯（例如節點被 traverse 時提升 utility）

---

### 3.5 MCP HTTP + SSE Transport

**規格依據**：SPEC.md §4.3；`mem_i003.json`

- 目前只支援 stdio transport
- 缺少 HTTP server + SSE endpoint（讓遠端 AI agent 連線，不需本地 `.mcp.json`）

---

### 3.6 MCP 多工作區支援

**規格依據**：架構需求；`mem_i003.json`

目前 MCP server 啟動時 `MEMTRACE_WS` 固定在環境變數，整個連線只能查詢單一工作區。要查詢其他知識庫需另起一個 MCP server 實例，且工具名稱會衝突（所有實例的工具都叫 `search_nodes` 等）。

**缺少項目**：

| 層 | 項目 |
|----|------|
| MCP | 在 `search_nodes`、`get_node`、`traverse`、`list_by_tag` 四個工具加入可選參數 `workspace_id` |
| MCP | 不傳 `workspace_id` 時沿用 `MEMTRACE_WS` 預設值（向下相容） |
| MCP | 新增工具 `list_workspaces` — 列出目前 API token 可存取的工作區清單 |
| Docs | README 說明多工作區設定方式（單一 server 實例搭配 `workspace_id` 參數） |

**目前 workaround**（可行但有侷限）：

```json
// .mcp.json：為每個知識庫啟動獨立實例
{
  "mcpServers": {
    "memtrace-spec":    { "command": "node", "args": ["packages/mcp/dist/index.js"], "env": { "MEMTRACE_WS": "ws_spec0001" } },
    "memtrace-project": { "command": "node", "args": ["packages/mcp/dist/index.js"], "env": { "MEMTRACE_WS": "ws_project_abc" } }
  }
}
```

侷限：工具名稱重複，AI agent 難以區分；每個 server 各自佔用一個 Node.js 行程。

---

### 3.7 原始文件保留 (Source Document Retrieval)

**規格依據**：SPEC.md §20

在攝入文件後，保留原始文件供溯源，但不污染標準的節點圖譜。

**缺少項目**：

| 層 | 項目 |
|----|------|
| DB | `content_type` ENUM 新增 `source_document` |
| UI | 特定檢視模式以呈現原始文件，實作相關邏輯將其從預設搜尋及 3D Node Map 中過濾隱藏 |

---

### 3.8 知識庫匯出與非同步封裝 (Export & Import API)

**規格依據**：SPEC.md §22

除了 CLI 的 export 指令，後端尚缺完整的非同步匯出工作佇列，用以產生包含節點、邊與 Markdown 文件的 `.memtrace` 壓縮檔。

**缺少項目**：

| 層 | 項目 |
|----|------|
| DB | 建立 `kb_exports` 資料表，用於追蹤非同步匯出任務 |
| API | `POST /workspaces/{ws_id}/exports` — 建立匯出任務 (支援 `--filter` 等 Scope 條件) |
| API | `GET /workspaces/{ws_id}/exports/{export_id}` — 檢查狀態與取得下載連結 |
| API | `POST /workspaces/{ws_id}/imports` — 處理 `.memtrace` 檔案上傳與資料卡片重建 |
| UI | 用戶端的「匯出設定中心 (Custom Export Panel)」與進度輪詢機制 |

---

## 4. Low — 錦上添花

### 4.1 CLI 補強

| 指令 | 狀態 | 說明 |
|------|------|------|
| `memtrace ingest <file>` | ⬜ | 上傳文件至 API ingest endpoint |
| `memtrace copy-node` | ⬜ | 見 §2.1 |
| `memtrace init` AI provider 步驟 | 🔧 | 互動流程不完整，缺少 AI provider 選擇與 key 驗證 |

---

### 4.2 背景排程補強

| 項目 | 說明 |
|------|------|
| 過期邀請清理 | 定期刪除 `workspace_invites` 中已過期的 token |
| Free Tier 月度重置 | 每月重置 AI 用量計數（規格有 `FREE_TOKEN_LIMIT`，但 `ai_usage_log` 資料表尚未建立） |

---

### 4.3 Core Library 補強

**位置**：`packages/core/src/`

| 項目 | 說明 |
|------|------|
| `contentTypeHalfLife()` | 依 content_type 回傳預設 half_life_days（目前只有 Python 端 hardcode） |
| Trust score 合成計算 | 從 4 個維度計算綜合分數的 TypeScript 函式 |
| 節點簽章驗證 | SHA-256 驗證節點內容是否被竄改（`mem_d005.json`） |

---

## 5. 各層快速對照表

| 層 | 已實作 | 未實作 / 部分實作 |
|----|--------|------------------|
| **API** | CRUD nodes/edges、Auth、Traversal、Edge rating、AI extract/embed/restructure、AI key 管理 | Review Queue、File Ingestion、Email 驗證、Copy Node、邀請連結、成員管理、Semantic Search、Scope 強制、帳號鎖定 |
| **UI** | Auth、GraphView 2D/3D、NodeEditor（含搜尋）、Workspace selector、Settings | Onboarding wizard、Review Queue UI、File upload、Semantic search、成員管理、邀請連結、Edge 視覺化、Trust 維度展示、歸檔管理 |
| **MCP** | search_nodes、get_node、traverse、list_by_tag（stdio） | 寫入工具、Resources、traverse_edge、HTTP+SSE、多工作區支援 |
| **CLI** | init、new、link、list、export、import | copy-node、ingest、AI provider 設定 |
| **排程** | apply_edge_decay（每日） | apply_node_archiving、Ephemeral 加速 decay、過期邀請清理、Free Tier 重置 |
| **Core** | decay.ts、id.ts、types.ts | contentTypeHalfLife、Trust 合成、簽章驗證 |
| **DB** | 主要 schema 完整 | review_queue 資料表、ai_usage_log 資料表、embedding 填入邏輯 |

---

## 建議實作順序

```
Phase A（下一個 sprint）
  ├── 角色存取邊界落實 (Admin權限修補 + Viewer節點過濾) ← 優先確保知識擁有者設計核心
  ├── Copy Node API + CLI           ← schema 完備，工作量小
  ├── Workspace 邀請連結 API        ← schema 完備，工作量小
  └── Email 驗證                   ← 安全必要項

Phase B
  ├── File Ingestion + Review Queue ← 成對實作，依賴關係強
  └── Semantic Search（embedding 填入 + search endpoint）

Phase C
  ├── Onboarding 新手引導優化       ← 已完成絕大部分，需後續串接 Review Queue
  ├── MCP 寫入工具
  ├── Conditional Public 預覽與申請流程 (Graph Preview + Join Requests)
  └── MCP 寫入工具

Phase D
  ├── API Key Scope 強制
  ├── 帳號安全（鎖定、pwned 檢查）
  ├── Edge 視覺化 + Trust UI 補強
  ├── MCP HTTP+SSE transport
  └── MCP 多工作區支援（workspace_id 參數 + list_workspaces 工具）
```

---

*此文件由 Claude Code 依規格審計自動產出，請定期與 `SPEC.md` 同步更新。*

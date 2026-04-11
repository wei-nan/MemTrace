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

### 1.1 Review Queue（AI 審核佇列）

**規格依據**：SPEC.md §4.2；`examples/spec-as-kb/nodes/mem_a003.json`

AI 擷取（extraction）的結果必須進入人工審核佇列，經確認後才能寫入知識庫。目前 extraction endpoint 存在，但結果直接落地，沒有審核關卡。

**缺少項目**：

| 層 | 項目 |
|----|------|
| DB | `review_queue` 資料表（candidate_id, node_data JSONB, status pending/accepted/rejected, suggested_edges） |
| API | `POST /workspaces/{ws_id}/review-queue` — AI 擷取後寫入候選節點 |
| API | `GET /workspaces/{ws_id}/review-queue` — 列出待審清單 |
| API | `PATCH /review-queue/{id}` — 修改候選內容 |
| API | `POST /review-queue/{id}/accept` — 接受並寫入 memory_nodes |
| API | `POST /review-queue/{id}/reject` — 拒絕並標記 |
| UI | 候選節點列表頁 |
| UI | 逐筆 Accept / Edit / Reject 操作 |
| UI | 批次操作（Accept All / Reject All） |

---

### 1.2 Onboarding 新手引導流程

**規格依據**：SPEC.md §5.1；`mem_o001.json`、`mem_o002.json`

新使用者第一次登入應有 7 步驟引導，目前完全缺失。

**缺少項目**：

| 層 | 項目 |
|----|------|
| API | `GET /auth/me/onboarding` — 查詢已完成/略過的步驟 |
| API | `PATCH /auth/me/onboarding` — 更新進度 |
| UI | Onboarding wizard 元件（7 步驟）：<br>① 帳號建立（已有）<br>② Email 驗證（缺）<br>③ 命名第一個 KB（缺引導）<br>④ 選擇起點（空白 or 上傳文件）<br>⑤ AI provider 設定（缺）<br>⑥ 審核 AI 擷取節點（缺，依賴 Review Queue）<br>⑦ 完成 + 快捷提示（缺） |

> 備註：DB 的 `users.onboarding` JSONB 欄位已存在，只缺 endpoint 與 UI。

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

### 1.4 Email 驗證

**規格依據**：SPEC.md §4.1；`mem_i001.json`

**缺少項目**：

| 層 | 項目 |
|----|------|
| API | `POST /auth/verify-email/{token}` |
| API | `POST /auth/resend-verification-email` |
| 邏輯 | 驗證 Email 實際發送（`routers/auth.py` 有 TODO 但未實作） |
| 邏輯 | 24 小時 token 到期強制失效 |
| UI | 驗證成功/失敗頁面 |
| UI | 重新發送驗證信按鈕 |

---

### 1.5 Workspace 成員管理 API

**規格依據**：SPEC.md §5.2

**缺少項目**：

| 層 | 項目 |
|----|------|
| API | `GET /workspaces/{ws_id}/members` — 列出成員與角色 |
| API | `PUT /workspaces/{ws_id}/members/{user_id}` — 變更角色（viewer / editor） |
| API | `DELETE /workspaces/{ws_id}/members/{user_id}` — 移除成員 |
| UI | 成員清單顯示 |
| UI | 角色變更下拉選單 |
| UI | 移除成員按鈕 |

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
| **MCP** | search_nodes、get_node、traverse、list_by_tag（stdio） | 寫入工具、Resources、traverse_edge、HTTP+SSE |
| **CLI** | init、new、link、list、export、import | copy-node、ingest、AI provider 設定 |
| **排程** | apply_edge_decay（每日） | apply_node_archiving、Ephemeral 加速 decay、過期邀請清理、Free Tier 重置 |
| **Core** | decay.ts、id.ts、types.ts | contentTypeHalfLife、Trust 合成、簽章驗證 |
| **DB** | 主要 schema 完整 | review_queue 資料表、ai_usage_log 資料表、embedding 填入邏輯 |

---

## 建議實作順序

```
Phase A（下一個 sprint）
  ├── Copy Node API + CLI           ← schema 完備，工作量小
  ├── Workspace 邀請連結 API        ← schema 完備，工作量小
  └── Email 驗證                   ← 安全必要項

Phase B
  ├── File Ingestion + Review Queue ← 成對實作，依賴關係強
  └── Semantic Search（embedding 填入 + search endpoint）

Phase C
  ├── Onboarding wizard             ← 依賴 B 的 Review Queue
  ├── 節點歸檔排程                  ← SQL function 已就緒
  └── MCP 寫入工具

Phase D
  ├── API Key Scope 強制
  ├── 帳號安全（鎖定、pwned 檢查）
  ├── Edge 視覺化 + Trust UI 補強
  └── MCP HTTP+SSE transport
```

---

*此文件由 Claude Code 依規格審計自動產出，請定期與 `SPEC.md` 同步更新。*

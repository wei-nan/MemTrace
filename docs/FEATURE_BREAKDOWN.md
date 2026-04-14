# MemTrace 功能實作展開細項 (Feature Breakdown) - Phase 2 Completed

這份文件將 Backlog 中的高階規格，展開為提供給前端 (UI)、後端 (API)、資料庫 (DB) 開發人員具體可執行的工作細項 (Subtasks)。

---

## 1. 知識主權與角色邊界限制 (Role-Based Content Stripping)

**目標**：確保 `viewer` 角色只能看見圖譜結構與標題，無法觀看/抓取節點內容；確保 `admin` 能正常寫入。

### 1.1 後端 (API) 開發細項
- [x] **修補 `_require_ws_access`**
  - **檔案**：`packages/api/routers/kb.py`
  - **修改**：在寫入權限的判斷區塊 (`if write:`) 中，將目前的 `member["role"] != "editor"` 改為 `member["role"] not in ["editor", "admin"]`。
- [x] **實作 Viewer 內文過濾器 Middleware 或 Utility**
  - **檔案**：`packages/api/routers/kb.py` 或 `nodes.py`
  - **修改**：在 `list_nodes` 與 `get_node` endpoint 的回傳前，檢查當前使用者的 Role。若為 `viewer`，則將 NodeObject 中的 `body_zh` 與 `body_en` 設定為空字串。
- [x] **編輯者建議模式 (Editor Suggestions)**
  - **修改**：`POST /nodes` 與 `PATCH /nodes` 若偵測到使用者為 `editor`，則不直接修改 DB，而是將變更封裝後送入 `review_queue` 並回傳 202。

### 1.2 前端 (UI) 開發細項
- [x] **節點瀏覽鎖定狀態判定**
  - **檔案**：對應的卡片檢視元件。
  - **修改**：在接收到 API 節點資料時，若 `body` 為空且使用者權限為 Viewer，渲染「鎖頭圖示」與提示字樣（例如："節點詳細內容僅限編輯者與管理員存取"）。
- [x] **隱藏寫入操作**
  - 若角色為 Viewer，隱藏「Save」、「Edit」、「Delete」、「AI Restructure」等任何會改變節點內容的按鈕。

---

## 2. 有條件公開與圖譜預覽 (Conditional Public & Graph Preview)

**目標**：未登入或未擁有權限的訪客，瀏覽 `conditional_public` 知識庫時，只能看見「圖譜的點線關係」無法得知任何 ID 標記與文字。並且可以一鍵提出加入申請。

### 2.1 後端 (API/DB) 開發細項
- [x] **Schema Migration**
  - **工作**：建立 `join_requests` 資料表。
- [x] **圖譜預覽端點 (`GET /workspaces/{ws_id}/graph-preview`)**
  - **邏輯**：驗證 `conditional_public`。脫水處理。
- [x] **加入申請端點 (Join Requests CRUD)**
  - `POST` / `GET` / `Approve` / `Reject` API 已實作。

### 2.2 前端 (UI) 開發細項
- [x] **Graph Preview 渲染模式**
  - 已實作 `GraphContainer` 403 自動切換預覽模式。
- [x] **申請加入與管理後台**
  - 已實作預覽橫幅與 Workspace Settings 中的審核分頁。

---

## 3. 非同步知識庫匯出機制 (KB Export Engine)

**目標**：背景打包完整的知識庫或部分節點成為 `.memtrace` 壓縮檔。

### 3.1 後端 (API/DB) 開發細項
- [ ] **Schema Migration**
  - 建立 `kb_exports` 資料表，包含 `id`, `workspace_id`, `status` ('pending', 'processing', 'completed', 'failed'), `download_url`, `created_at`。
- [ ] **背景任務實作**
  - **邏輯**：接收 Scope filter 條件，撈出目標 nodes 與雙方都在範圍內的 edges。解析內容生成 Markdown，並用 zipfile 寫成 `.memtrace` 壓縮檔。
- [ ] **API Endpoint**
  - `POST /workspaces/{ws_id}/exports`：觸發 FastAPI `BackgroundTasks`。
  - `GET /workspaces/{ws_id}/exports/{export_id}`：檢查進度並取得檔案。

### 3.2 前端 (UI) 開發細項
- [ ] **匯出操作面板**
  - 提供勾選範圍 (全部、按 Tag 過濾、匯出格式是否包含 Markdown)。
- [ ] **非同步輪詢機制**
  - 展示 Loading UI，並使用 `setInterval` 定期呼叫確認匯出狀態。

---

## 4. 跨庫關聯與 AI 面板 (KB Associations & Chat)

**目標**：讓知識庫之間產生連線，並允許向 AI 提問生成編修提案。

### 4.1 後端 (API) 開發細項
- [ ] **Associations CRUD**
  - 建立 `workspace_associations` 資料表操作 API。
- [ ] **AI Chat Endpoint** (`POST /workspaces/{ws_id}/chat`)
  - **Context 檢索**：做 Embedding 相似度檢索當前/關聯 WS 的節點。
  - **提案識別 (`allow_edits`)**：解析回覆產生 Proposals，送進 `review_queue`。

### 4.2 前端 (UI) 開發細項
- [ ] **獨立 AI 聊天模組**
  - 獨立訊息氣泡面板與 Inline 提案卡片 (`ProposalCard`)。

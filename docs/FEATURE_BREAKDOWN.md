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

## 3. 非同步知識庫匯出機制 (KB Export Engine) (Completed)

**目標**：背景打包完整的知識庫或部分節點成為 `.memtrace` 壓縮檔。

### 3.1 後端 (API/DB) 開發細項
- [x] **Schema Migration**
  - **工作**：建立 `kb_exports` 資料表，追蹤進度與下載連結。
- [x] **背景任務實作**
  - **邏輯**：背景打包 nodes (Markdown), edges (JSON), workspace metadata 為 `.memtrace` ZIP。
- [x] **API Endpoint**
  - `POST /workspaces/{ws_id}/exports`：觸發任務。
  - `GET /workspaces/{ws_id}/exports/{export_id}`：輪詢進度。

### 3.2 前端 (UI) 開發細項
- [x] **匯出操作面板**
  - 在 Workspace Settings 新增「資料匯出」分頁。
- [x] **非同步輪詢機制**
  - 實作每 5 秒輪詢。

---

## 4. 跨庫關聯與 AI 面板 (KB Associations & AI) (Completed)

**目標**：讓知識庫之間產生連線，並允許向 AI 提問生成編修提案。

### 4.1 後端 (API) 開發細項
- [x] **Associations CRUD**：已建立 `workspace_associations` 資料表與 API。
- [x] **AI Chat Endpoint**：實現跨庫檢索與優化提案解析。

### 4.2 前端 (UI) 開發細項
- [x] **AI 助手側邊面板**：支援對話與提案卡片展示。
- [x] **館際關聯管理**：在工作區設定中提供 ID 綁定功能。

### 4.3 AI 模型自選功能 (Completed)
- **目標**：讓使用者自行選擇 Provider 及模型。
- [x] **後端模型列表 API**：實作 `GET /ai/models/{provider}`。
- [x] **模型列表 Fallback 機制**：若未設金鑰，回傳預設的常用模型清單。
- [x] **前端模型選擇 UI**：在 AI 面板新增模型選單，並在請求中帶入 `preferred_model`。

### 4.4 API 金鑰提醒與限制 (Completed)
- **目標**：引導使用者提供自有金鑰。
- [x] **金鑰狀態偵測**：判斷當前 Provider 是否已有使用者金鑰。
- [x] **動態提示橫幅**：若未提供金鑰，在輸入框上方顯示「未設定金鑰」的註記與「去設定」連結。
- [x] **無金鑰鎖定**：若無自有金鑰，停用發送功能並顯示警告。

---

## 5. 節點變更確認、版本追蹤與人機審核 (Change Diff, Versioning & Hybrid Review)

**目標**：任何對知識庫節點的異動（無論來自人類或 AI）都必須：
1. 在套用前產生「結構化 diff」讓提案者與審核者可預覽；
2. 套用後保留有限版本歷史，可回溯與還原；
3. 支援人工審核與（可選）AI 預審雙軌，並對每筆審核保留 proposer / reviewer 身分與理由。

### 5.0 Proposer / Reviewer 模型

| 角色 | 來源 | 典型案例 |
|---|---|---|
| Human proposer | UI NodeEditor、MCP (human user context) | 一般編輯、viewer 建議 |
| AI proposer | Ingest pipeline、MCP (AI tool call)、AI Chat 「套用建議」 | 從檔案抽取、語意合併、衝突修補 |
| Human reviewer | Editor/Admin 於 ReviewQueue 介面 | 預設審核 |
| AI reviewer | Workspace 設定的 `ai_reviewers` 條目 | 自動預審、過濾明顯可接受/拒絕項 |

### 5.1 資料庫 (DB) 開發細項

- [x] **擴充 `review_queue` 欄位**
  - 檔案：`schema/sql/00X_change_review.sql`（新 migration）
  - 新增欄位：
    - `change_type TEXT NOT NULL DEFAULT 'create'` — `create` / `update` / `delete`
    - `target_node_id TEXT REFERENCES memory_nodes(id) ON DELETE CASCADE`（`update` / `delete` 必填）
    - `before_snapshot JSONB` — 提案產生時鎖定的當時節點狀態；`create` 為 `NULL`
    - `diff_summary JSONB` — 由後端預先計算好的欄位級 diff（見 5.2）
    - `proposer_type TEXT NOT NULL DEFAULT 'human'` — `human` / `ai`
    - `proposer_id TEXT` — user_id 或 `ai:<provider>:<model>` 或 `airev_<id>`
    - `proposer_meta JSONB` — `{ingest_job_id, prompt, confidence, reasoning, source_file}`
    - `reviewer_type TEXT` — `human` / `ai`（於 accept/reject 時填入）
    - `ai_review JSONB` — AI 預審結果 `{decision, confidence, reasoning, reviewer_id, reviewed_at}`
    - `review_notes TEXT`
  - Index：`(workspace_id, status, created_at)`、`(target_node_id)`
- [x] **建立 `node_revisions` 版本表**
  - 欄位：`id, node_id, workspace_id, revision_no, snapshot JSONB, signature, proposer_type, proposer_id, review_id, created_at`
  - `UNIQUE (node_id, revision_no)`；`revision_no` 每 node 遞增
  - Index：`(node_id, revision_no DESC)`
  - 保留策略：每 node 最多保留 10 版，寫入時於 trigger 或應用層刪除超出者
- [x] **建立 `ai_reviewers` 表**
  - 欄位：`id, workspace_id, name, provider, model, system_prompt, auto_accept_threshold NUMERIC, auto_reject_threshold NUMERIC, enabled BOOLEAN, created_at`
  - `UNIQUE (workspace_id, name)`

### 5.2 後端 (API) 開發細項

- [x] **重構 proposer 入口為統一內部函式**
  - 檔案：`packages/api/routers/kb.py`（新增 `_propose_change`）
  - 介面：`_propose_change(cur, ws_id, change_type, target_node_id, node_data, proposer_type, proposer_id, proposer_meta) -> review_id`
  - 負責：讀 `before_snapshot`、計算 `diff_summary`、寫入 `review_queue`、觸發 AI 預審背景任務
- [x] **改寫 `create_node` / `update_node` / `delete_node`**
  - Editor 分流與 AI 提案統一走 `_propose_change`
  - Admin / owner 直接套用時，仍寫入一筆 `node_revisions`（`review_id` 可為 NULL）
- [x] **Diff 計算工具**
  - 檔案：`packages/api/core/diff.py`
  - 欄位級比對：`title_zh/title_en/content_type/content_format/body_zh/body_en/tags/visibility`
  - Body 類輸出 `{type: 'text', before, after, line_diff: [...]}`（line-level）
  - Tags 輸出 `{type: 'set', added: [...], removed: [...]}`
  - 其他輸出 `{type: 'scalar', before, after}`
- [x] **AI Ingest 支援編輯既有節點**
  - 檔案：`packages/api/routers/ingest.py`
  - 抽取到的 candidate 先做相似度比對（embedding cosine ≥ 門檻或 title 精確比對）：
    - 命中 → `change_type='update'`、`target_node_id` = 命中節點
    - 未命中 → `change_type='create'`
  - 透過 `_propose_change` 寫入，`proposer_type='ai'`、`proposer_id=ai:<provider>:<model>`
- [ ] **MCP 寫入工具整合**
  - 檔案：`packages/mcp-server/...`（Phase 3 交付）
  - 所有節點異動工具（create/update/delete）走 `_propose_change`，依呼叫端身分標註 proposer_type
- [x] **AI Reviewer CRUD 端點**
  - `GET/POST /workspaces/{ws_id}/ai-reviewers`
  - `PATCH/DELETE /workspaces/{ws_id}/ai-reviewers/{id}`
  - 僅 owner 可管理；提供預設 system_prompt 模板
- [ ] **AI 預審背景任務**
  - 檔案：`packages/api/core/ai_review.py`
  - 流程：取 pending review → 組 prompt（含 change_type、diff_summary、既有節點上下文）→ 呼叫 LLM → 解析 `{decision, confidence, reasoning}`
  - 依 threshold 自動 accept / reject 或僅附加建議
  - 觸發時機：`_propose_change` 後 enqueue；也提供 `POST /workspaces/{ws_id}/review-queue/ai-prescreen` 手動批次
- [x] **Review accept 流程擴充**
  - 檔案：`packages/api/routers/review.py`
  - `accept_review_item` 依 `change_type` 分支 INSERT / UPDATE / DELETE `memory_nodes`
  - 套用後寫入 `node_revisions`（`revision_no = max+1`）並裁剪超出保留數
  - 記錄 `reviewer_type` / `reviewer_id`
- [x] **版本追蹤端點**
  - `GET /workspaces/{ws}/nodes/{id}/revisions` — 列表（meta only）
  - `GET /workspaces/{ws}/nodes/{id}/revisions/{rev}` — 單版快照
  - `GET /workspaces/{ws}/nodes/{id}/revisions/{a}/diff/{b}` — 任兩版 diff
  - `POST /workspaces/{ws}/nodes/{id}/revisions/{rev}/restore` — 以舊版為藍本走 `_propose_change`（update）
- [x] **Viewer 可見性**
  - Viewer 可列出 pending review 項目、看到 `change_type` / `proposer` / `diff_summary` 摘要，但 body 欄位依 `_strip_body_if_viewer` 規則遮蔽；不可 accept/reject

### 5.3 前端 (UI) 開發細項

- [x] **NodeEditor 送出前 Diff 確認 Modal**
  - 檔案：`packages/ui/src/NodeEditor.tsx`、新 `components/DiffPreviewModal.tsx`
  - 點 Save → 顯示欄位級 diff（body 行級、tags set diff、scalar before→after）
  - 確認後才呼叫 `nodes.create/update`
  - 建立模式顯示「將新增欄位摘要」
- [x] **ReviewQueue 強化**
  - 檔案：`packages/ui/src/ReviewQueue.tsx`
  - 每項顯示 proposer badge（🤖 AI model 名 / 👤 user）、change_type badge、diff 摺疊區
  - 若有 `ai_review`：顯示 decision badge + reasoning 引用、信心分數
  - 支援按 proposer_type / change_type 篩選
- [x] **AI Reviewer 設定頁**
  - 檔案：`packages/ui/src/workspace-settings/AIReviewerSettings.tsx`
  - 於 Workspace Settings 新增「AI 預審」分頁：列表、建立、編輯、啟停
  - 表單欄位：名稱、provider、model、system_prompt（含預設模板）、兩個 threshold、enabled
- [x] **節點歷史 (History) Tab**
  - 檔案：`packages/ui/src/NodeEditor.tsx`
  - Detail view 新增 History tab：列版本 meta（revision_no、proposer、created_at）
  - 點擊某版 → 與目前版本 diff；提供「還原為此版」按鈕（走 propose update）
- [x] **Viewer 變更可見性**
  - ReviewQueue 對 viewer 角色仍顯示列表與 diff 摘要（body 遮蔽）；隱藏 accept/reject 按鈕

### 5.4 驗收情境
- [x] Editor 從 UI 編輯節點 → 送出前看到 diff → 確認 → 進 review_queue → Admin 在 ReviewQueue 看到同一份 diff → Accept 後 `node_revisions` 新增一筆
- [ ] 上傳檔案 ingest → AI 抽取到與既有節點相似的條目 → 產生 `update` 提案（含 before/after）→ AI reviewer 信心 0.95 自動 accept → `node_revisions` 新增一筆、reviewer_type='ai'
- [ ] Owner 在節點 History tab 選 3 版前的快照 → Restore → 產生新的 update 提案（非直接覆寫）
- [x] 同一 node 累積超過 10 版 → 最舊版自動裁剪
- [x] Viewer 打開 ReviewQueue 可見項目列表與 diff 摘要，但 body 內容被遮蔽，且無法 accept/reject

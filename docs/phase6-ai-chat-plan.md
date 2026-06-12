# Phase 6 — AI 助手強化計畫

> 目標：為 AI Chat 加入伺服端對話持久化（Feature 1）與圖譜錨點上下文（Context Route C）。

---

## 現況盤點

### 架構限制

| 面向 | 現況 |
|------|------|
| 對話歷史 | 純客戶端管理，由前端每次傳入 `history[]`，server 不存儲 |
| 會話持久化 | 不存在，刷新頁面即全部消失 |
| 跨次上下文 | 完全遺失，每次對話從零開始 |
| 節點命中紀錄 | `source_nodes` 只存活於單次 stream，未持久化 |

### 可利用的現有基礎

| 資源 | 說明 |
|------|------|
| `retrieval_logs.trace_id` | 可串接同一次對話的多次檢索，但未實際使用 |
| `retrieval_logs.hit_node_ids` | 記錄每次查詢命中的節點 ID，是 Route C 的雛形 |
| `archive_qa_to_kb()` | 已能將 Q&A + `source_node_ids` 蒸餾成知識節點 |
| `consult_sessions` | 諮詢會話表（獨立功能），可作為 chat_sessions 設計參考 |
| `hybrid_retrieval_for_chat()` | 混合檢索入口，可擴充 `preferred_node_ids` 參數 |

---

## Feature 1 — 對話紀錄持久化

### 1.1 DB Schema

新增兩張 table（新增 migration 檔 `110_chat_sessions.sql`）：

```sql
-- 對話 session
CREATE TABLE chat_sessions (
  id              TEXT PRIMARY KEY,           -- generate_id("chs")
  workspace_id    TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  user_id         TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title           TEXT NOT NULL DEFAULT '',   -- 自動取自第一則訊息前 60 字
  anchored_node_ids TEXT[] NOT NULL DEFAULT '{}',  -- Route C：累積命中節點 ID
  message_count   INT NOT NULL DEFAULT 0,
  tokens_total    INT NOT NULL DEFAULT 0,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_active_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_chat_sessions_ws_user ON chat_sessions(workspace_id, user_id, last_active_at DESC);

-- 對話訊息
CREATE TABLE chat_messages (
  id              BIGSERIAL PRIMARY KEY,
  session_id      TEXT NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
  role            TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
  content         TEXT NOT NULL,
  source_node_ids TEXT[] NOT NULL DEFAULT '{}',  -- 本則 assistant 訊息命中的節點
  tokens_used     INT NOT NULL DEFAULT 0,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_chat_messages_session ON chat_messages(session_id, created_at ASC);
```

### 1.2 API 變更

#### `ChatRequest` 新增欄位

```python
class ChatRequest(BaseModel):
    # ... 現有欄位不變 ...
    session_id: str | None = None   # 傳入則繼續既有 session；不傳則自動建新 session
```

#### `chat-stream` endpoint 流程變更

```
收到 request
  │
  ├─ session_id 有值 → 從 DB 載入 chat_messages 作為 history（取代 body.history）
  │                    同時取出 anchored_node_ids 供 Route C 使用
  │
  └─ session_id 無值 → INSERT chat_sessions，回傳新 session_id
                        (在 stream 第一個 event 前 yield session_id event)

stream 結束後（background_tasks）：
  1. INSERT 兩筆 chat_messages（user + assistant）
  2. UPDATE chat_sessions SET
       anchored_node_ids = anchored_node_ids | source_node_ids (union),
       message_count += 2,
       tokens_total += total_tokens,
       last_active_at = now(),
       title = (若 message_count == 0，取 message[:60])
```

#### 新增 stream event

```json
{"type": "session", "session_id": "chs_xxxx"}
```
→ 在 `source_nodes` event 之前送出，讓前端能記錄 session_id。

#### 新增 REST endpoints

| Method | Path | 說明 |
|--------|------|------|
| `GET` | `/api/v1/ai/sessions?workspace_id=&limit=20` | 列出最近 N 筆 session（含最後一則訊息摘要） |
| `GET` | `/api/v1/ai/sessions/{session_id}/messages` | 取得 session 完整對話紀錄 |
| `PATCH` | `/api/v1/ai/sessions/{session_id}` | 修改 title |
| `DELETE` | `/api/v1/ai/sessions/{session_id}` | 刪除 session 與所有訊息 |

### 1.3 UI 變更（AiChatPanel）

#### 側欄 Session 列表
- `AiChatPanel` 左側加入可收合的 session 列表
- 顯示：session title、最後活躍時間、訊息數
- 操作：新增對話、切換、重命名（inline edit）、刪除
- 切換 session 時呼叫 `GET /sessions/{id}/messages` 還原完整對話

#### State 變更
```typescript
const [sessionId, setSessionId] = useState<string | null>(null);

// 收到 {"type": "session", "session_id": "..."} 時
setSessionId(chunk.session_id);

// 切換 session 時
setSessionId(targetSessionId);
setMessages(loadedMessages);  // 從 API 載入
```

#### Placeholder 更新
```
新對話（無 sessionId）→ 正常流程，自動建立 session
有 sessionId → 繼續該對話
```

---

## Context Route C — 圖譜錨點上下文

### 核心概念

每個 `chat_session` 累積一份 `anchored_node_ids`：  
**對話中被 AI 命中過的節點 ID union**。

下次在同一 session 發送訊息時，這些節點在混合檢索中獲得**分數提升**，確保 AI 的注意力持續圍繞本次對話已建立的脈絡。

### 實作方案

#### `hybrid_retrieval_for_chat()` 擴充

```python
async def hybrid_retrieval_for_chat(
    cur, workspace_ids, query, user_id,
    ws_embed_prov=None, ws_embed_model=None,
    anchor_node_ids: list[str] | None = None,   # ← 新增
    anchor_boost: float = 0.15,                  # ← 錨點加分權重
) -> list[dict]:
    ...
    # 在最終分數計算後，對 anchor_node_ids 中的節點額外加分
    if anchor_node_ids:
        anchor_set = set(anchor_node_ids)
        for node in results:
            if node["id"] in anchor_set:
                node["_score"] += anchor_boost
        results.sort(key=lambda n: n["_score"], reverse=True)
    ...
```

#### `chat-stream` 整合

```python
# 從 DB 載入 anchored_node_ids
anchored = []
if body.session_id:
    with db_cursor() as cur:
        cur.execute("SELECT anchored_node_ids FROM chat_sessions WHERE id = %s", (body.session_id,))
        row = cur.fetchone()
        if row:
            anchored = row["anchored_node_ids"] or []

source_nodes = await hybrid_retrieval_for_chat(
    cur, list(target_ids), body.message, user["sub"],
    ws_embed_prov=ws_embed_prov, ws_embed_model=ws_embed_model,
    anchor_node_ids=anchored,    # ← 傳入錨點
)
```

### 效果說明

| 情境 | 行為 |
|------|------|
| 新 session，第 1 則訊息 | 純語義 + 文字混合檢索，無偏好 |
| 同 session 後續訊息 | 先前命中的節點分數 +0.07，自然維持脈絡連貫性 |
| 換新 session | `anchored_node_ids` 重置為 `{}`，從全知識庫重新檢索 |
| 跨 session 查詢同一主題 | 不干擾，各 session 獨立錨點 |

> boost 初始值 **0.07**，待觀察後調整。

---

## 設計決策

### D1 — 冷熱資料分層

`chat_sessions` 依 `last_active_at` 區分冷熱：

| 狀態 | 條件 | 可瀏覽 | 可繼續對話 | 可重命名 / 刪除 |
|------|------|:------:|:----------:|:--------------:|
| **熱資料** | `last_active_at >= now() - 7 days` | ✓ | ✓ | ✓ |
| **冷資料** | `last_active_at < now() - 7 days` | ✓ | ✗ | ✓ |

**核心原則**：冷資料在系統 UI 中**永遠可見、永遠可查閱完整對話紀錄**，僅限制「繼續發送新訊息」這個動作。使用者隨時可以打開任一冷 session 閱讀歷史內容。

**DB 實作**：不需要額外欄位，直接在 API 層依 `last_active_at` 判斷；冷資料嘗試 `chat-stream` 時回傳 `403 session_frozen`。

**UI 實作**：
- 側欄將 session 分為「**最近 7 天**」與「**封存**」兩區塊，均顯示、均可點擊開啟
- 開啟冷 session 時完整顯示所有歷史訊息
- 輸入框以灰底顯示「此對話已封存，如需繼續請開啟新對話」，按鈕 disabled
- 可在封存 session 上點「以此為基礎開啟新對話」，自動帶入摘要作為新 session 的前置脈絡（Sprint C 功能）

**未來選項**：若儲存量成長過大，可在此基礎上加入 `archived_at` 欄位，對 90 天以上冷資料進行壓縮或分表。目前不實作，留作觀察。

---

### D2 — History 分頁載入

預設載入最近 **20 則**，前端可往前翻頁（cursor-based pagination）：

```
GET /api/v1/ai/sessions/{session_id}/messages
  ?limit=20              # 預設 20
  &before_id=<msg_id>   # cursor：載入此 id 之前的訊息（往前翻頁）
```

**chat-stream 載入邏輯**：
```python
# 載入最近 20 則作為 AI context（不一次全撈）
cur.execute("""
    SELECT role, content FROM chat_messages
    WHERE session_id = %s
    ORDER BY created_at DESC LIMIT 20
""", (body.session_id,))
history = list(reversed(cur.fetchall()))  # 還原正序傳給 AI
```

**UI 實作**：對話視窗頂端顯示「載入更早的訊息」按鈕，點擊後帶 `before_id` 向上追加。

---

### D3 — 錨點 Boost 值

初始值 **0.07**，寫死在 `hybrid_retrieval_for_chat()` 預設參數中，後續可透過 workspace settings 或環境變數調整，無需改程式碼。

---

### D4 — 匿名使用者

匿名訪客（未登入）**不建立也不持久化 session**。
- `chat-stream` 對匿名用戶維持現有行為（依賴客戶端 `history[]`）
- 不在 DB 中建立 `chat_sessions` 紀錄

---

### D5 — `body.history` 相容性與失效時程

**現況**：保留 `body.history` 參數，無 `session_id` 時繼續使用客戶端歷史，確保 MCP / SDK 整合不中斷。

**失效時程規劃**：

| 階段 | 時間點 | 動作 |
|------|--------|------|
| 目前 | Sprint A 上線 | `body.history` 繼續有效；有 `session_id` 時 server 端歷史優先，`body.history` 被忽略 |
| 警告期 | Sprint A + 3 個月 | API response header 加入 `Deprecation: body.history` 警告 |
| 失效 | Sprint A + 6 個月 | 移除 `body.history` 支援，所有 client 必須使用 `session_id` 機制 |

> MCP 整合需在失效前完成 session_id 遷移。

---

## 實作順序

```
Sprint A（DB + 基礎 API）
  ├─ 新增 migration 110_chat_sessions.sql
  ├─ chat-stream：session 建立 / 載入歷史（20 則）/ 持久化訊息
  ├─ 新增 session_id event
  ├─ 冷 session 的 403 session_frozen 防護
  └─ GET /sessions, GET /sessions/:id/messages（支援 before_id）

Sprint B（Route C + UI）
  ├─ hybrid_retrieval_for_chat 加入 anchor_boost (0.07)
  ├─ chat-stream：anchored_node_ids 更新
  ├─ AiChatPanel：session sidebar（熱/冷分區顯示）
  ├─ 往前翻頁（載入更早訊息）
  └─ session 切換 / 新增

Sprint C（收尾）
  ├─ PATCH /sessions/:id（重命名）
  ├─ DELETE /sessions/:id
  ├─ 自動 session title 生成（取第一則訊息前 60 字）
  ├─ token 統計顯示（每 session 用量）
  └─ Deprecation header for body.history
```

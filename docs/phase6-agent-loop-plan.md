# Phase 6 — Agent 小任務開發迴圈（記憶基底）

> 目標：把 MemTrace 當成一個由 Claude 驅動的多 agent 開發迴圈的**記憶基底**。
> agent 在外部 harness 跑迴圈，MemTrace 只負責供應「該做什麼 / 怎麼做」、收納「決定與結論」、並從使用回饋自我調校。
> 本階段先把**單 agent 脊椎**以**小任務**顆粒度跑通。

---

## 架構決策（討論收斂結果）

| # | 決策 | 說明 |
|---|------|------|
| A1 | MemTrace = 記憶（+ 可選 conductor），**不是 loop runtime** | 沙盒、多輪 tool-use 編排、context 管理全留外部 harness |
| A2 | **讀多寫少**，內容寫入一律人 gate | 圖先產製好、持續演化，但內容變更要人確認 |
| A3 | **Trusted agents**（同質、可信） | 多 agent / 異質信任分級**延後** |
| A4 | **兩速演化** | 內容寫入經人 gate；信心/使用寫入自動 |
| A5 | **脊椎先單 agent** | 多 agent 討論之後只加在「規劃」階段 |
| A6 | 顆粒度 = **小任務** | 一圈 = 一個可獨立完成、可獨立驗收的小變更 |
| A7 | 迴圈**執行狀態（run-state）不進知識圖** | 「這任務在測試階段」是 harness 的事，不是知識 |

---

## 現況盤點

### 可直接複用的既有基礎

| 資源 | 在迴圈中的角色 |
|------|----------------|
| `inquiry` content_type + `answered_by` 邊 | **缺口 / 問題 / 任務**的正規表示；被實作節點回答後以 `answered_by` 連入 |
| `review_queue` + AI reviewer fallback chain | **內容寫入的人 gate**（決定、結論的事實面） |
| `path_reinforcement_job` + `decay_job` + `inquiry_paths` | **兩速的自動側**：使用成功強化、未用衰減 |
| `ai_reviewers.auto_accept_threshold` / `auto_reject_threshold` | **決策分級**的承重機制（低風險自動放行） |
| `examples/spec-as-kb` + `003_seed_spec_kb.sql` | **期望狀態**來源：`缺口 = spec − 實作` 的被減數 |
| audit reviewers（`deduper` 等，每日） | residue 去重 / 圖的內向維護 loop |
| `packages/api/docs/mcp-contract.md` | 外部 agent 的接入面 |
| `ai_credit_ledger` + `AI_FREE_TOKEN_LIMIT` + 每 reviewer 日配額 | agent 預算 / 熔斷 |
| `process_node_events_job`（每 10s） | 既有 event bus，未來 conductor 觸發外部 harness 的掛點 |
| `proposer_id` / `proposer_type` | agent 身分**種子**；延後多 agent 不需改 schema |
| `procedural` content_type | **playbook** 的載體 |

### 缺口（本階段要做）

1. **定向層 / 情境索引**：situation → 該查哪個 playbook / 子圖（「要查什麼」）
2. **任務階層**：子任務攜帶父意圖（見 D2 — edge 取捨）
3. **residue 寫回**：結論吐出新的 pending `inquiry`（飛輪燃料）
4. **outcome 回報入口**：agent 用完記憶 → 餵 `path_reinforcement`
5. **5 個 MCP 工具**（下節）

---

## 最小切片：記憶側 5 個 MCP 工具

| 工具 | 方向 | 行為 | 底層複用 |
|------|------|------|----------|
| `get_next_task` | 讀 | 挑一個 pending `inquiry`，回傳「任務 + 祖先意圖 + spec 切片 + 開發 playbook」的 token 受限 context 包 | inquiry 節點 + spec-as-kb + procedural + 邊遍歷 |
| `get_playbook` | 讀 | 按情境取程序節點 | `procedural`（缺情境索引） |
| `propose_decision` | 寫（人 gate） | 把「下一步決定」送入 `review_queue` | review_queue |
| `submit_outcome` | 寫（自動） | 成效進 `path_reinforcement`；失敗順手標 playbook 送審 | path_reinforcement / inquiry_paths |
| `emit_residue` | 寫（自動，輕量） | 結論吐出新的 pending `inquiry` 節點 | inquiry 節點 |

> 對應的實驗知識庫見 `examples/agent-loop-kb/`，其中 `mem_loop900` / `mem_loop901` 就是這幾個工具的 seed 缺口。

---

## 工作項目

```
Sprint A — 記憶側脊椎（MCP 工具 + 實驗 KB）
  ├─ A1 seed 實驗知識庫 examples/agent-loop-kb/（本提交已含初版）
  ├─ A2 任務階層 edge 取捨拍板（D2）
  ├─ A3 get_next_task：挑 pending inquiry + 組 context 包
  ├─ A4 get_playbook：情境索引 → procedural 節點
  └─ A5 propose_decision：寫入 review_queue（人 gate）

Sprint B — 兩速回饋接通
  ├─ B1 submit_outcome → path_reinforcement（成功強化 / 失敗衰減）
  ├─ B2 失敗自動標記 playbook + 路徑送人複審
  └─ B3 emit_residue：結論自動建 pending inquiry（飛輪）

Sprint C — 人 gate 效率 + 決策分級
  ├─ C1 套用 auto_accept_threshold 做決策分級（D4）
  ├─ C2 review queue 批次審 / 同類提案合併呈現
  └─ C3 兩段式驗收：per-feature 整合檢查（D5）

Sprint D — 外部 harness 薄殼 + 收斂
  ├─ D1 單 planner + 單 developer 把脊椎跑通一圈
  ├─ D2 收斂裁決：複用 consult synthesizer 的「升級給人 vs 收斂」
  └─ D3 多 agent 討論「只」加在規劃階段
```

---

## 設計決策

### D1 — 缺口用 `inquiry` 節點，不新增 content_type
schema v1 的 `inquiry` + `answered_by` 就是缺口/問題機制（DB 另有 `gap` content_type 變體）。實驗統一用 `inquiry`（schema 正規），待觀察是否與 DB `gap` 收斂。

### D2 — 任務階層：`depends_on`（父子）+ `proceeds_to`（順序）
注意 schema 漂移：靜態檔 `schema/edge.v1.json` 的 enum **沒有** `proceeds_to` / `subtask_of`，但 **canonical `EdgeCreate` API（`models/kb.py`）實際接受 `proceeds_to`**。以 API 為準。

- **本階段**：子任務以 `depends_on` 指向父任務（攜帶意圖）；子任務間的先後以 `proceeds_to` 表達。
- **暫不引入** `subtask_of`：父子用 `depends_on` 已足夠，避免過早擴 enum + migration。
- 待辦：同步更新 `schema/edge.v1.json` 以消除與 API 的漂移。

### D3 — residue = 輕量 `inquiry`，自動建 pending
結論吐出的新缺口/問題自動建為 `status=pending` 的 `inquiry`，由規劃者下一輪分流，**不逐條當場攔人**（它是低風險內容寫入）。

### D4 — 決策分級沿用 reviewer 門檻
低風險類別（加 helper、改名、補測試、文件）信心足夠時自動放行；高風險（改公開介面、刪資料、動安全/權限、跨模組）一律人 gate。實作沿用 `auto_accept_threshold` / `auto_reject_threshold`，屬可調政策。

### D5 — 兩段式驗收
`per-task`（小、快、多半自動）+ `per-feature`（同一父 `inquiry` 的所有子任務完成時觸發整合檢查）。整合檢查依風險決定是否人 gate。

### D6 — outcome 只調權重、不改內容 → 不經人 gate
`submit_outcome` 走兩速的自動側；它不變更任何知識內容，只調 trust / 路徑權重，因此無需人確認。

---

## 延後 backlog（A3 之外，安全可延）

- per-agent 身分 / 認證（現用單一 trusted 憑證；`proposer_id` 已預留欄位，不鎖 schema）
- agent 信任分級、記憶污染防禦
- 多人 / 多 workspace 寫入隔離
- conductor：`process_node_events` 事件觸發外部 harness
- 多 agent 討論收斂的完整編排（先單 agent 脊椎）

---

## 接續

Sprint A–C 已完整、Sprint D 接縫到位。上述延後 backlog 連同 Sprint D 收斂時記下的 caveat / 偏離，已整理進下一階段：見 `docs/phase7-agent-loop-plan.md`。

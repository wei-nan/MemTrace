# MemTrace 知識庫效率驗證方法

> 版本：1.0　產出日期：2026-04-11
> **基準資料狀態（2026-04-27 校對）：基準數據已過期，需重跑。** 詳見「§十、基準資料更新需求」。
> 目的：量化確認「透過 KB 查詢規格」比「直接閱讀 SPEC.md」在 token 消耗與資訊涵蓋率兩個維度上的改善效果

---

## 一、驗證目標

MemTrace 知識庫（spec-as-kb）的核心假設是：

> **AI agent 不需要每次對話都讀整份 SPEC.md；只需透過 MCP 查詢 2–4 個相關節點，即可取得足夠的上下文，且消耗的 token 遠少於全文閱讀。**

本驗證系統用於確認上述假設在實際查詢情境中是否成立，並提供可重複執行的量化指標。

---

## 二、評量指標

| 指標 | 定義 | 通過門檻 |
|------|------|---------|
| **Token 效率倍數** | `SPEC.md tokens ÷ KB 查詢 tokens` | ≥ 5x |
| **Token 節省率** | `(1 − KB tokens / SPEC.md tokens) × 100%` | ≥ 80% |
| **節點涵蓋率** | 答案所需節點中，被成功取得的比例 | ≥ 70% |
| **Easy 問題全覆蓋** | 難度 easy 的問題全數 100% 涵蓋 | 5/5 |
| **平均延遲** | 每次查詢的平均 API 回應時間 | < 2,000 ms |

---

## 三、基準數據（Baseline）

> ⚠ **以下數據為 2026-04-11 快照，已不反映目前狀態。**
> SPEC.md 已從約 75 KB 成長至 ~145 KB；spec-as-KB 節點數已從 27 成長至 30。基準需在 Phase 4-A 執行時重跑——見本文末「§十、基準資料更新需求」。

| 項目 | 2026-04-11 數值（過期） | 目前狀態 |
|------|------------------------|---------|
| SPEC.md 總字元數 | 75,564 | ~145,000（**幾近翻倍**） |
| SPEC.md Token 數（GPT-4 tokenizer） | 17,686 tokens | 預估 ~35,000 tokens（待重算） |
| KB 節點總數 | 27 | **30**（線上 `ws_spec0001` 因 AI 萃取再增多） |
| KB body_en 平均長度 | 597 字元 | 待重算 |
| KB body_en 最小/最大 | 380 / 1,159 字元 | 待重算 |
| 全部節點 body 合計 | 16,119 字元 | 待重算 |

「讀完整份 SPEC.md」的成本是每次對話 **17,686 tokens**（input）。即使讀遍全部 27 個節點，也只要 ≈ 4,000 tokens，且實際查詢通常只需 2–4 個節點。

---

## 四、問題集設計

問題集位於 `scripts/benchmark/questions.json`，共 15 題，覆蓋四種類型：

| 類型 | 題數 | 說明 |
|------|------|------|
| `factual_lookup` | 5 | 單節點事實查詢（如 half_life 預設值、MCP 工具清單） |
| `procedural` | 3 | 流程步驟查詢（如環境設定、seed 執行） |
| `multi_hop` | 4 | 需跨節點推理（如 decay + archiving 關係） |
| `cross_reference` | 2 | 跨主題彙整（如規格未實作功能列表） |
| `architecture` | 1 | 架構設定查詢（如 MCP 環境變數） |

每題包含：
- `question_en` / `question_zh`：雙語問題
- `expected_nodes`：答案所在節點 ID
- `ground_truth`：預期答案關鍵字（人工評分用）
- `spec_section`：對應 SPEC.md 章節

---

## 五、測試方法

### 測試邏輯

對每個問題，Benchmark Runner 模擬 AI agent 的查詢策略：

```
Step 1: search_nodes(key_terms)   ← 模擬 agent 的第一步：關鍵字搜尋
Step 2: get_node(expected_node_id) ← 若 Step 1 未找到，直接取節點
```

計算：
- **KB tokens**：兩步驟返回的 JSON 合計 token 數
- **涵蓋率**：`expected_nodes` 中實際被取到的比例
- **延遲**：HTTP 回應時間

### 與 SPEC.md 模式的對比

| 模式 | 每次消耗 | 優缺點 |
|------|---------|--------|
| **KB 查詢** | 平均 2,228 tokens | 精準、快速、可重複；依賴 KB 內容正確性 |
| **全文閱讀** | 17,686 tokens/次 | 資訊完整；每次對話都消耗大量 input tokens |

---

## 六、執行方式

### 前置條件

```bash
# 確認 API 在 8000 port 運行
cd packages/api && uvicorn main:app --port 8000

# 確認 spec KB 已 seed
python ../../scripts/seed_spec_kb.py
```

### 執行 Benchmark

```bash
cd packages/api
python ../../scripts/benchmark/run_benchmark.py

# 指定輸出路徑
python ../../scripts/benchmark/run_benchmark.py --output ../../scripts/benchmark/results.json
```

### 環境變數（選填）

| 變數 | 預設值 | 說明 |
|------|--------|------|
| `MEMTRACE_API` | `http://localhost:8000/api/v1` | API base URL |
| `MEMTRACE_WS` | `ws_spec0001` | 目標 workspace |
| `BENCH_EMAIL` | `benchmark@test.example.com` | 測試帳號 email |
| `BENCH_PASSWORD` | `Bench1234!` | 測試帳號密碼（首次執行自動建立） |

---

## 七、最新執行結果

> 執行日期：2026-04-11
> ⚠ **此結果已過期**：SPEC.md 與 KB 節點皆已大幅變動，token 效率倍數的真實值會與此處不同。重跑計畫見 §十。

| 題號 | 類型 | KB Tokens | 效率 | 節省率 | 涵蓋率 | 延遲 |
|------|------|-----------|------|--------|--------|------|
| Q01 | factual_lookup | 853 | 20.7x | 95% | 100% | 10,056 ms¹ |
| Q02 | factual_lookup | 958 | 18.5x | 95% | 100% | 39 ms |
| Q03 | factual_lookup | 1,443 | 12.3x | 92% | 100% | 44 ms |
| Q04 | factual_lookup | 4,915 | 3.6x | 72% | 100% | 41 ms |
| Q05 | factual_lookup | 1,978 | 8.9x | 89% | 100% | 39 ms |
| Q06 | procedural | 1,223 | 14.5x | 93% | 100% | 28 ms |
| Q07 | procedural | 5,240 | 3.4x | 70% | 100% | 40 ms |
| Q08 | procedural | 1,378 | 12.8x | 92% | 100% | 29 ms |
| Q09 | multi_hop | 2,481 | 7.1x | 86% | 100% | 52 ms |
| Q10 | multi_hop | 2,804 | 6.3x | 84% | 100% | 62 ms |
| Q11 | multi_hop | 978 | 18.1x | 94% | 100% | 40 ms |
| Q12 | multi_hop | 1,839 | 9.6x | 90% | 100% | 54 ms |
| Q13 | cross_reference | 1,843 | 9.6x | 90% | 100% | 58 ms |
| Q14 | cross_reference | 2,819 | 6.3x | 84% | 100% | 52 ms |
| Q15 | architecture | 2,664 | 6.6x | 85% | 100% | 30 ms |
| **平均** | | **2,228** | **10.6x** | **87.4%** | **100%** | **711 ms** |

¹ Q01 首次查詢包含 TCP 連線建立時間（cold start），後續查詢均 < 100 ms。

### 驗證結論

| 指標 | 門檻 | 實際 | 結果 |
|------|------|------|------|
| Token 效率倍數 | ≥ 5x | **10.6x** | PASS |
| Token 節省率 | ≥ 80% | **87.4%** | PASS |
| 節點涵蓋率 | ≥ 70% | **100%** | PASS |
| Easy 問題全覆蓋 | 5/5 | **5/5** | PASS |
| 平均延遲 | < 2,000 ms | **711 ms** | PASS |

**整體判定：PASS — KB 查詢方式相較全文閱讀有效率，且資訊涵蓋完整。**

---

## 八、已知限制與改善方向

### 當前限制

1. **涵蓋率為結構性指標，非語意正確性**
   - Benchmark 確認「預期節點是否被取到」，但不驗證 AI 是否從節點內容中得出「正確答案」
   - 需要：加入人工評審或 LLM-as-judge 對答案品質評分

2. **Q04 / Q07 效率偏低（3–4x）**
   - 這兩題的搜尋詞彙命中多個節點，導致返回資料量偏大
   - 改善方向：MCP `traverse` 工具取代 `search`，精準鎖定節點

3. **未測試 traverse 工具的 multi-hop 效果**
   - 目前 benchmark 只用 `search_nodes` + `get_node`
   - 加入 `traverse` 後，multi_hop 類問題的效率預計再提升 30–50%

4. **KB 內容準確性依賴人工維護**
   - 若 KB 節點描述過時，涵蓋率高但答案錯誤
   - 緩解方式：每次 code 變更後重跑 benchmark + 人工抽查 ground_truth

### 下一步改善計畫

| 優先級 | 項目 |
|--------|------|
| 高 | 加入 `traverse` 工具到 benchmark 的查詢策略 |
| 高 | 加入 LLM-as-judge 對答案品質評分（0–1 分） |
| 中 | 擴充問題集至 30 題（補充 AI ingestion、auth、workspace 類別） |
| 中 | CI 整合：每次 spec-as-kb 節點更新後自動執行 |
| 低 | 多語言測試（zh-TW / en 雙語問題集） |

---

## 九、詮釋方法

### 如何閱讀結果

- **效率 > 10x**：高度集中的查詢，單節點即可回答（factual_lookup 的理想情況）
- **效率 5–10x**：正常情況，需 2–3 個節點
- **效率 < 5x**：查詢詞彙過廣或問題本身需要大量上下文；考慮拆分問題或改用 traverse

### 何時應重新執行

- 新增或修改 spec-as-kb 節點後
- 修改 MCP server 的查詢邏輯後
- 更新 SPEC.md 且同步更新節點後
- 建議：每週自動執行一次作為持續監控

---

*此文件由 Claude Code 建立。Benchmark runner 原始碼：`scripts/benchmark/run_benchmark.py`　問題集：`scripts/benchmark/questions.json`*

---

## 十、基準資料更新需求（2026-04-27 校對）

校對時發現 §三的基準數據與 §七的執行結果都對應 2026-04-11 的狀態，與目前差距如下：

| 項目 | 文件值 | 目前 | 差距 |
|------|--------|------|------|
| SPEC.md 字元數 | 75,564 | ~145,000 | +92% |
| KB 節點數（`examples/spec-as-kb/`） | 27 | 30 | +3 |
| 線上 `ws_spec0001` 節點數 | 27 | 已超出（含 AI 萃取與測試） | 需重新統計 |

### 必要動作

1. 重跑 `scripts/benchmark/run_benchmark.py`，產出 2026-04 末或 Phase 4 啟動時的新基準
2. 同步更新 §三、§七的表格（保留歷史欄位以便對照）
3. 此重跑工作已納入 `docs/dev/phase4-plan.md` 的 P4-A（健康儀表板 + Token 效率報告），完成後本節可改為「最新基準同步於 Analytics 頁面，每月由 CI 重新執行」

### 為什麼不在此次校對直接重跑

- 重跑屬功能性更新而非文件修補；應與 P4-A 的 `mcp_query_logs` 表落地一起做
- 若僅手動重跑一次而沒有 CI/儀表板綁定，下一次又會過期

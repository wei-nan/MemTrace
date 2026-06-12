# Phase 7 — Agent 開發迴圈：收斂、強化與正式化

> 承 Phase 6（見 `docs/phase6-agent-loop-plan.md`）。
> Phase 6 已把**單 agent 脊椎**跑通（Sprint A–C 完整、Sprint D 接縫到位）。
> 本階段收掉 Phase 6 刻意延後的項目，以及 Sprint D 收斂時記下的 caveat / 與計畫字面的偏離。

---

## 來源盤點

本階段項目有三個來源：

1. **Phase 6 延後 backlog**（`phase6-agent-loop-plan.md` 第 119–125 行）
2. **Sprint D 偏離計畫字面之處**（converge / 多 agent 已達成「效果」但非「字面」）
3. **實作 caveat**（B2/C3 空 diff、claim registry 記憶體、schema/migration 落差）

---

## 工作項目

```
Sprint E — 多 agent 規劃討論（補完 D3）
  ├─ E1 多 planner 編排：fan-out 數個 planner → 各自產提案
  ├─ E2 用 converge_proposals（已複用 synthesizer）裁決 consensus / escalate
  ├─ E3 escalate 路徑：divergent 時把候選提案打包送 review_queue 給人選
  └─ E4 claim registry 從行程內記憶體換 Redis（多 worker / 重啟存活）

Sprint F — 人 gate 內容品質（補完 B2/C3 caveat）
  ├─ F1 B2 失敗送審：把失敗摘要 / 嫌疑 playbook 段落寫進 node_data，讓 diff 有內容
  ├─ F2 C3 整合檢查：把「哪些子任務、用了哪些實作節點」摘要寫進 review 項目
  └─ F3 review_queue 呈現：空 diff 的「flag-only」項目改用獨立視覺樣式

Sprint G — Conductor + 事件觸發
  ├─ G1 process_node_events 掛點：pending inquiry / residue 出現時發事件
  ├─ G2 事件 → 外部 harness 觸發（webhook / 佇列），收斂 conductor 角色
  └─ G3 outcome 回流：harness 跑完一圈後回報，串回 path_reinforcement

Sprint H — 多 agent 信任與隔離（安全面）
  ├─ H1 per-agent 身分 / 認證（proposer_id 已預留，補實際憑證分發）
  ├─ H2 agent 信任分級 + 記憶污染防禦（低信任 agent 寫入一律人 gate）
  └─ H3 多人 / 多 workspace 寫入隔離

Sprint I — 基礎設施技術債
  └─ I1 釐清 schema/sql 與 packages/api/migrations 落差（見 D-debt）
```

---

## 設計決策（待拍板）

### E — 多 agent 規劃討論
- **E2 已備料**：`converge_proposals` 工具已複用 `services.consult.synthesize_responses`，回傳 `converge` / `escalate`。Phase 7 只需補「誰來產生多個提案」與「escalate 後怎麼呈現」。
- **E4 claim registry**：Phase 6 用行程內 `_TASK_CLAIMS`（TTL 30 分鐘），單行程可用但重啟即失、多 worker 不共享。沿用 A7「run-state 不進知識圖」原則，換 Redis 而非寫 DB。

### F — 空 diff 議題
Phase 6 的 B2（失敗標 playbook）與 C3（per-feature 整合檢查）都用 `change_type="update"` + `node_data={}` 送審，語意是「把節點挑出來給人看」，但 review 卡片**沒有具體變更內容可顯示**（before == after）。
- **F1/F2**：把「為何送審」的摘要寫進 `node_data`（或 `proposer_meta`），讓 reviewer 看得到脈絡。
- **F3**：或者承認這類是「flag-only」項目，在 UI 用不同樣式呈現（不顯示 diff，改顯示原因 + 跳轉節點）。
- 兩條路二選一，建議先做 F1（成本低、立即有用）。

### G — Conductor
Phase 6 明確把 MemTrace 定位為**記憶（+ 可選 conductor），不是 loop runtime**（決策 A1）。`process_node_events_job`（每 10s）是既有 event bus，G1/G2 把它接成「pending inquiry / residue 出現 → 通知外部 harness」，但**沙盒、多輪 tool-use、context 管理仍留外部**。

### H — 信任分級
延續 Phase 6 backlog。目前是單一 trusted 憑證（決策 A3）。多 agent 異質信任分級在此補上，與 E（多 planner）搭配才有意義。

---

## D-debt — schema / migration 落差（需先釐清）

排查 Phase 6 時發現：
- 執行期由 `core.database.run_migrations()` 套用 `packages/api/migrations/*.sql`，但該目錄目前只有 `054`–`056` 三個檔。
- `schema/sql/` 編號到 `111`，且 `inquiry_paths` 等基礎表的建表 SQL 在這兩個可見位置都找不到。
- 測試 `test_inquiry_paths.py` 直接 assert 表存在（不自建），代表有**另一套 base schema 機制**（疑似對 `shared-postgres` 外部一次性載入），但本 repo 內未見來源。

> 影響：Phase 6 新功能全部複用既有表（`review_queue` / `memory_nodes` / `edges` / `inquiry_paths`），**不需要新 migration**，故不影響本階段功能。但 base schema 的單一事實來源不明，是部署面的技術債，應在 I1 釐清（確認 `schema/sql` 與 `migrations` 何者為準、補齊缺漏的建表來源）。

---

## 不在本階段（仍延後）

- 完整的 agent 記憶污染攻防（H2 只做基本分級門檻，進階對抗延後）
- 跨組織 / 多租戶層級的隔離（H3 只到 workspace 級）

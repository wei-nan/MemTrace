# Agent Loop KB — 小任務開發迴圈的種子知識庫

這是一個**可由 Claude 試跑**的實驗知識庫。它把「小任務開發迴圈」本身的運作知識，
用 MemTrace 節點表達出來——也就是說，這個 KB 教一個 agent **如何在 MemTrace 上跑開發迴圈**（dogfooding）。

- 12 個節點、15 條邊，使用 canonical 建立 API 形狀（單一 `title` / `body`，非舊版雙語匯出）
- `nodes.json` ≈ `NodeCreate` payload；`edges.json` ≈ `EdgeCreate` payload
- 規劃文件：`docs/phase6-agent-loop-plan.md`

> `id` 為穩定參照鍵供 `edges.json` 連線；實際建立時由 server 指派。
> `trust` / `provenance` / `decay` 等欄位皆由 server 管理，故不在 payload 內。

---

## 它如何被用來「試驗」

一個 Claude 驅動的 agent，理想的第一圈是：

1. 讀 `mem_loop001`（目標與邊界）→ 沿 `depends_on` 到 `mem_loop002`（迴圈骨架）
2. 依 `mem_loop003`（定向）去找一個 `status=pending` 的 `inquiry` 節點 —— 種子缺口是 `mem_loop900`、`mem_loop901`
3. 取對應 playbook（`mem_loop010` 開發 → `mem_loop011` 測試 → `mem_loop012` 驗收）
4. 遵守 `mem_loop020`（兩速）、`mem_loop021`（決策分級）兩條政策
5. 完成後依 `mem_loop022` 吐出 residue（新的 pending `inquiry`）
6. 把實作節點以 `answered_by` 連回被解決的 `inquiry`

種子缺口 `mem_loop900` / `mem_loop901` 正好就是規劃文件裡要建的 MCP 工具
（`get_next_task` / `emit_residue`），所以這個 KB 也是它自己第一批任務的待辦清單。

---

## Node Index

| ID | Title | Content Type | 角色 |
|----|---------------|--------------|------|
| mem_loop001 | Agent 開發迴圈：目標與邊界 | context | 入口 / 北極星 |
| mem_loop002 | 迴圈骨架：七階段 | context | 定向地圖 |
| mem_loop003 | 定向：如何找下一個小任務 | procedural | 「要查什麼」 |
| mem_loop010 | 開發 Playbook | procedural | 「怎麼做」 |
| mem_loop011 | 測試 Playbook | procedural | 「怎麼做」 |
| mem_loop012 | 驗收 Playbook（兩段式） | procedural | 「怎麼做」 |
| mem_loop013 | 拆解 Playbook：功能切小任務 | procedural | 拆解層 |
| mem_loop020 | 兩速演化規則 | factual | 政策 |
| mem_loop021 | 決策分級政策 | preference | 政策 |
| mem_loop022 | residue 規則（飛輪） | factual | 政策 |
| mem_loop900 | 缺口：get_next_task 工具 | inquiry | seed 任務 |
| mem_loop901 | 缺口：emit_residue 機制 | inquiry | seed 任務 |

---

## Suggested Entry Points

| 你是誰 | 建議入口 | 沿著走 |
|--------|---------|--------|
| 第一次了解這個迴圈 | mem_loop001 | → loop002 → loop003 |
| 想知道「怎麼開發」 | mem_loop010 | → loop011 → loop012 |
| 想知道規則 / 政策 | mem_loop020 | → loop021 → loop022 |
| 想直接開跑第一個任務 | mem_loop900 | → loop003 → loop010 |

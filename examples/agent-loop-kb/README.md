# Agent Loop KB — 小任務開發迴圈的種子知識庫

這是一個**可由 Claude 試跑**的實驗知識庫。它把「小任務開發迴圈」本身的運作知識，
用 MemTrace 節點表達出來——也就是說，這個 KB 教一個 agent **如何在 MemTrace 上跑開發迴圈**（dogfooding）。

- **16 個節點、26 條邊**（Phase 6 同步後）
- `nodes.json` ≈ `NodeCreate` payload；`edges.json` ≈ `EdgeCreate` payload
- 規劃文件：`docs/phase6-agent-loop-plan.md`、`docs/phase7-agent-loop-plan.md`

> `id` 為穩定參照鍵供 `edges.json` 連線；實際建立時由 server 指派。
> `trust` / `provenance` / `decay` 等欄位皆由 server 管理，故不在 payload 內。

---

## 它如何被用來「試驗」

一個 Claude 驅動的 agent，理想的第一圈是：

1. 讀 `mem_loop001`（目標與邊界）→ 沿 `depends_on` 到 `mem_loop002`（迴圈骨架）
2. 依 `mem_loop003`（定向）去找一個 `status=pending` 的 `inquiry` 節點
3. 取對應 playbook（`mem_loop010` 開發 → `mem_loop011` 測試 → `mem_loop012` 驗收）
4. 遵守 `mem_loop020`（兩速）、`mem_loop021`（決策分級）兩條政策
5. 完成後依 `mem_loop022` 吐出 residue（`emit_residue` 工具）
6. 把實作節點以 `answered_by` 連回被解決的 `inquiry`

---

## Node Index

| ID | Title | Content Type | 角色 | Phase |
|----|-------|--------------|------|-------|
| mem_loop001 | Agent 開發迴圈：目標與邊界 | context | 入口 / 北極星 | seed |
| mem_loop002 | 迴圈骨架：七階段 | context | 定向地圖 | seed |
| mem_loop003 | 定向：如何找下一個小任務 | procedural | 「要查什麼」 | seed |
| mem_loop010 | 開發 Playbook | procedural | 「怎麼做」 | seed |
| mem_loop011 | 測試 Playbook | procedural | 「怎麼做」 | seed |
| mem_loop012 | 驗收 Playbook（兩段式） | procedural | 「怎麼做」 | seed |
| mem_loop013 | 拆解 Playbook：功能切小任務 | procedural | 拆解層 | seed |
| mem_loop020 | 兩速演化規則 | factual | 政策 | seed |
| mem_loop021 | 決策分級政策 | preference | 政策 | seed |
| mem_loop022 | residue 規則（飛輪） | factual | 政策 | seed |
| mem_loop900 | 缺口：get_next_task 工具 | inquiry | seed 任務（已解決） | seed |
| mem_loop901 | 缺口：emit_residue 機制 | inquiry | seed 任務（已解決） | seed |
| mem_loop910 | 實作：get_next_task MCP 工具 | factual | Sprint A 實作記錄 | Phase 6 |
| mem_loop911 | 實作：emit_residue MCP 工具 | factual | Sprint B 實作記錄 | Phase 6 |
| mem_loop912 | 實作：get_playbook / propose_decision / submit_outcome | factual | Sprint A–C 實作記錄 | Phase 6 |
| mem_loop913 | 實作：Sprint D 多 agent 協調工具 | factual | Sprint D 實作記錄 | Phase 6 |

---

## Phase 6 MCP 工具清單

| 工具 | Sprint | 實作節點 | 缺口節點 |
|------|--------|----------|----------|
| `get_next_task` | A | mem_loop910 | mem_loop900 |
| `get_playbook` | A | mem_loop912 | — |
| `propose_decision` | A | mem_loop912 | — |
| `submit_outcome` | B | mem_loop912 | — |
| `emit_residue` | B | mem_loop911 | mem_loop901 |
| `converge_check` | D | mem_loop913 | — |
| `converge_proposals` | D | mem_loop913 | — |
| `claim_task` | D | mem_loop913 | — |
| `release_task` | D | mem_loop913 | — |

---

## Phase 7 待辦（尚未在 seed 中）

見 `docs/phase7-agent-loop-plan.md`：
- E4：`claim_task` run-state 從行程內記憶體換 Redis（多 worker / 重啟存活）
- F1–F3：空 diff 送審問題修正
- G1–G3：Conductor + 事件觸發
- H1–H3：多 agent 信任分級

---

## Suggested Entry Points

| 你是誰 | 建議入口 | 沿著走 |
|--------|---------|--------|
| 第一次了解這個迴圈 | mem_loop001 | → loop002 → loop003 |
| 想知道「怎麼開發」 | mem_loop010 | → loop011 → loop012 |
| 想知道規則 / 政策 | mem_loop020 | → loop021 → loop022 |
| 想了解已實作的工具 | mem_loop910 | → loop912 → loop913 |

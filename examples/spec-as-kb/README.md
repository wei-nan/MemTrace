# MemTrace Spec — as a Knowledge Base

This directory contains the MemTrace specification represented as a MemTrace knowledge base itself.
It demonstrates the product's core philosophy in practice: one idea per node, value through connections.

- **19 Memory Nodes** across 5 clusters
- **37 Edges** with typed relationships
- All nodes and edges conform to `schema/node.v1.json` and `schema/edge.v1.json`

> Note: `provenance.signature` values are placeholders. In a live system they would be
> SHA-256 hashes computed from the node's content fields by `packages/core/src/id.ts`.

---

## Graph Overview

```
╔══════════════════════════════════════════════════════════════════════════╗
║  Cluster P — Core Philosophy                                             ║
║                                                                          ║
║   [mem_p001] 知識透過連結而非積累                                           ║
║       │ extends ──────────────────────► [mem_p002] 為知識傳承而設計         ║
║       │ extends ──────────────────────► [mem_p003] 人與AI的協作知識圖        ║
║       │ depends_on ────────────────────────────────────────────────────► D ║
╚══════════════════════════════════════════════════════════════════════════╝
         │                        │
         ▼                        ▼
╔══════════════════╗   ╔══════════════════════════════════════════════════╗
║ Cluster D        ║   ║  Cluster G — Graph Mechanics                    ║
║ Data Model       ║   ║                                                  ║
║                  ║   ║   [mem_g001] Decay 衰減機制                       ║
║  [mem_d001]      ║◄──╫──── depends_on ─── [mem_g002] Co-Access Boost   ║
║  Memory Node     ║   ║         │ depends_on                             ║
║    │ extends     ║   ║         ▼                                        ║
║    ├──► d003     ║   ║   [mem_g003] Edge 關係類型                        ║
║    ├──► d004     ║   ╚══════════════════════════════════════════════════╝
║    ├──► d005     ║
║    └──► d006     ║
║                  ║
║  [mem_d002]      ║──── extends ───► [mem_g003]
║  Edge            ║
║                  ║
║  [mem_d003] Content Type
║  [mem_d004] Trust
║  [mem_d005] Provenance
║  [mem_d006] Traversal
╚══════════════════╝
         │ depends_on (multiple)
         ▼
╔══════════════════════════════════════════════════════════════════════════╗
║  Cluster K — Knowledge Base                                              ║
║                                                                          ║
║   [mem_k001] Knowledge Base ◄─ depends_on ── [mem_k002] 共享層級          ║
║       ▲                     ◄─ depends_on ── [mem_k003] 節點跨庫複製      ║
║       │                                             │ extends            ║
║       │                                             ▼                   ║
║       │                                       [mem_d005] Provenance     ║
╚══════════════════════════════════════════════════════════════════════════╝
         ▲ depends_on
         │
╔══════════════════════════════════════════════════════════════════════════╗
║  Cluster A — AI Features                                                 ║
║                                                                          ║
║   [mem_a001] AI Provider & API Key                                       ║
║       ▲ depends_on                                                       ║
║   [mem_a002] 文件攝入與AI萃取 ──── extends ──► [mem_k001]                 ║
║       ▲ depends_on                                                       ║
║   [mem_a003] Review Queue ─────── extends ──► [mem_d001]                 ║
╚══════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════╗
║  Cluster I — Integration                                                 ║
║                                                                          ║
║   [mem_i001] Auth (Email / Google OAuth)                                 ║
║       ▲ depends_on                                                       ║
║   [mem_i002] REST API & API Key ──── depends_on ──► [mem_k001]           ║
║       ▲ depends_on                                                       ║
║   [mem_i003] MCP Server ─────────── related_to ──► [mem_g002]            ║
╚══════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════╗
║  Cluster O — Onboarding                                                  ║
║                                                                          ║
║   [mem_o001] Web UI Wizard ── depends_on ──► [mem_i001]                  ║
║                            ── depends_on ──► [mem_k001]                  ║
║                            ── extends   ──► [mem_a002]                   ║
║                                                                          ║
║   [mem_o002] CLI init      ── depends_on ──► [mem_i001]                  ║
║                            ── extends   ──► [mem_a001]                   ║
╚══════════════════════════════════════════════════════════════════════════╝
```

---

## Node Index

| ID | Title (zh-TW) | Content Type | Cluster |
|----|---------------|--------------|---------|
| mem_p001 | 知識透過連結而非積累 | context | Philosophy |
| mem_p002 | 為知識傳承而設計 | context | Philosophy |
| mem_p003 | 人與 AI 的協作知識圖 | context | Philosophy |
| mem_d001 | Memory Node：知識的最小單位 | factual | Data Model |
| mem_d002 | Edge：有向有型的關係 | factual | Data Model |
| mem_d003 | Content Type：節點的知識性質 | factual | Data Model |
| mem_d004 | Trust 系統：信任如何被計算 | factual | Data Model |
| mem_d005 | Provenance：來源與可溯性 | factual | Data Model |
| mem_d006 | Traversal Tracking：走訪計數 | factual | Data Model |
| mem_g001 | Decay：Edge 權重的自然衰減 | factual | Graph Mechanics |
| mem_g002 | Co-Access Boost：共存取加成 | factual | Graph Mechanics |
| mem_g003 | Edge 關係類型：四種語意方向 | factual | Graph Mechanics |
| mem_k001 | Knowledge Base：知識庫（Workspace）| factual | Knowledge Base |
| mem_k002 | 知識庫共享層級：三種可見性 | factual | Knowledge Base |
| mem_k003 | 節點跨庫複製：可攜性 | procedural | Knowledge Base |
| mem_a001 | AI Provider 與 API Key 自管 | procedural | AI Features |
| mem_a002 | 文件攝入與 AI 節點萃取 | procedural | AI Features |
| mem_a003 | Review Queue：人工審核 AI 萃取結果 | procedural | AI Features |
| mem_i001 | 使用者認證：Email 或 Google OAuth | procedural | Integration |
| mem_i002 | REST API 與外部 API Key | factual | Integration |
| mem_i003 | MCP Server：AI Agent 整合 | factual | Integration |
| mem_o001 | 初次使用引導：Web UI 精靈 | procedural | Onboarding |
| mem_o002 | 初次使用引導：CLI memtrace init | procedural | Onboarding |

---

## Suggested Entry Points

Depending on who you are, start here:

| 你是誰 | 建議入口 | 沿著走 |
|--------|---------|--------|
| 初次了解這個產品 | mem_p001 | → p002 → p003 → d001 → d002 |
| 要理解資料結構 | mem_d001 | → d002 → d003 → d004 → d005 |
| 要理解圖的運作邏輯 | mem_g001 | → g002 → g003 → d002 |
| 要設定 AI 萃取 | mem_a001 | → a002 → a003 → k001 |
| 要接入外部服務或 AI Agent | mem_i002 | → i003 → g002 |
| 剛開始使用這個產品 | mem_o001 or mem_o002 | → i001 → k001 → a001 |

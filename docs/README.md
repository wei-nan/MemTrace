# MemTrace 文件庫（Documentation Directory）

歡迎使用 MemTrace 文件庫。本目錄收錄 MemTrace 系統架構、規格定義、開發指南、部署方式、設計系統以及 AI Agent 作業規範等全方位文件。

---

## 核心定位與設計哲學（Public KB Core Positioning）

依據 MemTrace 公開規格知識庫（`ws_spec0001`）之規範：

1. **共享脈絡（Shared Context）**：人與多個 AI / 工具共同使用同一份知識與決策脈絡。
2. **結構化圖譜（Structured Knowledge Graph）**：以記憶節點（Memory Nodes）、具類型的邊（Typed Edges）、查詢（Inquiry）與路徑（Paths）展現資訊關聯。
3. **知識延續（Knowledge Continuity）**：新參與者或 AI 可沿既有路徑理解背景與決策，無需原作者重新交接。
4. **信任評分定位（Deferred Trust Score）**：內部 trust score、維度與驗證欄位為系統保留欄位，非當前 UI 核心呈現，亦不構成內容真實性之擔保。

---

## 文件索引 (Documentation Index)

### 核心規格與開發 (Core Specifications & Development)

- **[SPEC.md](SPEC.md)** — **系統完整規格書 (Full Specification)**
  涵蓋數據模型（Node v1 / Edge v1）、衰減引擎（Decay Engine）、存取控制、外部 REST API、MCP 服務端整合、OpenAI API 相容端點與 CLI / SDK 規範。
- **[DEVELOPMENT.md](DEVELOPMENT.md)** — **開發者指南 (Developer Setup Guide)**
  包含 Monorepo 環境建置（Node.js / Python / Docker）、資料庫初始化（PostgreSQL 17 + pgvector）、單元測試與端到端測試執行方法。

### 系統架構與營運 (Architecture & Operations)

- **[CONNECTORS.md](CONNECTORS.md)** — **外部數據連接器框架 (Connector Framework)**
  說明個人憑證與工作區綁定機制，支援 Google Drive、Asana、GitHub、GitLab 等第三方數據源安全攝入。
- **[DEPLOYMENT.md](DEPLOYMENT.md)** — **正式部署指南 (Deployment Guide)**
  提供 Docker Compose 環境變數設定、記憶體配置（建議 8GB RAM 用於 pgvector 運算）與服務維護步驟。
- **[DESIGN_SYSTEM.md](DESIGN_SYSTEM.md)** — **設計系統 (Design System v3.0)**
  定義 React UI 視覺規範、CSS Variables 標記 (Tokens)、Teal 主色調、Glassmorphism 表面樣式與 UI 元件庫指南。
- **[VALIDATION.md](VALIDATION.md)** — **驗證與品質標準 (Validation Suite)**
  收錄系統測試清單、驗收情境與資料品質檢核項目。
- **[TEMPLATE_KB.md](TEMPLATE_KB.md)** — **知識庫範本 (Knowledge Base Template)**
  提供打造優質 MemTrace 知識圖譜的範本與維護實務。

### AI Agent 作業規範 (Agent Loop & Governance)

- **[agent-loop-gates.md](agent-loop-gates.md)** — **Agent Loop 階段交接閘門 (Gates v2)**
  說明 AI Agent 在執行規劃、開發與驗證時的 Mandatory Gate 機制 (`G1`, `G2`, `G3`) 及 Agent Loop KB (`ws_6aa957c3`) 節點對照。
- **[dev/](dev/)** — **開發計畫與研究紀錄 (Dev Plans & Proposals)**
  包含專案各階段設計初稿、階段性計畫與特定模組深入研究。

### 階段計畫 (Milestone Plans)

- **[phase6-agent-loop-plan.md](phase6-agent-loop-plan.md)** — Phase 6 Agent Loop 實作計畫
- **[phase6-ai-chat-plan.md](phase6-ai-chat-plan.md)** — Phase 6 AI Chat 整合計畫
- **[phase7-agent-loop-plan.md](phase7-agent-loop-plan.md)** — Phase 7 Agent Loop 演進計畫

---

## 相關鏈結 (Related Links)

- **專案主 README**：[../README.md](../README.md)
- **Agent 入口指引**：[../agent.md](../agent.md)
- **MCP 服務端說明**：[../packages/api/README.md](../packages/api/README.md)

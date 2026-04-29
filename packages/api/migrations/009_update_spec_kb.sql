-- Migration 009: Update canonical spec KB nodes for Phase 4 completion
-- Applies to existing installations that already have ws_spec0001 from the
-- old 099_seed_spec_kb.sql.  Fresh installs get the correct data directly
-- from the updated 099, but the ON CONFLICT clauses below make this migration
-- safe to run on either.
--
-- Changes:
--   mem_w004  — Phase 4 完成狀態 (was "規劃中")
--   mem_a001  — 加入 Ollama provider (was 3-provider table)
--   mem_g004  — NEW: Trust Score 四維評分
--   mem_a005  — NEW: Analytics 儀表板與 Token 效率報告
--   5 new edges connecting the above nodes


-- ─── mem_w004: 開發進度 ─────────────────────────────────────────────────────

INSERT INTO public.memory_nodes (
  id, schema_version, workspace_id, title_zh, title_en,
  content_type, content_format, body_zh, body_en,
  tags, visibility, author, created_at, updated_at,
  signature, source_type,
  trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep,
  votes_up, votes_down, verifications, traversal_count, unique_traverser_count,
  status
) VALUES (
  'mem_w004', '1.0', 'ws_spec0001',
  '開發實作順序與現況', 'Development Progress & Status',
  'procedural', 'markdown',
  '## 完成進度（Phase 1–4）

| 層 | 狀態 |
|----|------|
| core（型別/decay/簽章/trust 計算）| ✅ |
| SQL schema（001_init + 28 migrations）| ✅ |
| api/core（database/security/AI 抽象）| ✅ |
| api/routers/auth（登入/JWT/密碼重設）| ✅ |
| api/routers/kb（workspace/node/edge/roles）| ✅ |
| api/routers/ingest（PDF/Markdown 攝入）| ✅ |
| mcp server（stdio+SSE / read+write+vote_trust tools）| ✅ |
| ui（Auth/Onboarding/Graph 2D+3D/Table/Settings/Analytics）| ✅ |

## Phase 4 完成項目

| 任務 | 目標 | 狀態 |
|------|------|------|
| P4-A | 知識庫健康儀表板 + Token 效率報告 | ✅ |
| P4-B | Spec-as-KB 升級為對外展示首頁 | ✅ |
| P4-C | MCP vote_trust 工具 + Trust 4 維投票 API | ✅ |
| P4-D | CLI ingest/copy-node/init、Core contentTypeHalfLife/SHA-256、Scheduler jobs | ✅ |
| P4-G | 自管 Ollama Provider（本機/LAN/Reverse Proxy）| ✅ |',
  '## Completed (Phase 1–4)

| Layer | Status |
|-------|--------|
| core (types/decay/signature/trust computation) | ✅ |
| SQL schema (001_init + 28 migrations) | ✅ |
| api/core (database/security/AI abstraction) | ✅ |
| api/routers/auth (login/JWT/password reset) | ✅ |
| api/routers/kb (workspace/node/edge/roles) | ✅ |
| api/routers/ingest (PDF/Markdown ingestion) | ✅ |
| mcp server (stdio+SSE / read+write+vote_trust tools) | ✅ |
| ui (Auth/Onboarding/Graph 2D+3D/Table/Settings/Analytics) | ✅ |

## Phase 4 Completed Tasks

| Task | Goal | Status |
|------|------|--------|
| P4-A | KB health dashboard + token efficiency report | ✅ |
| P4-B | Spec-as-KB upgraded to public demo homepage | ✅ |
| P4-C | MCP vote_trust tool + 4-dimension trust vote API | ✅ |
| P4-D | CLI ingest/copy-node/init, Core contentTypeHalfLife/SHA-256, Scheduler jobs | ✅ |
| P4-G | Self-hosted Ollama provider (local/LAN/reverse proxy) | ✅ |',
  '{dev,workflow,procedural}', 'public', 'system',
  '2026-04-28 00:00:00+00', '2026-04-29 00:00:00+00',
  '', 'human',
  0.950, 0.950, 1.000, 0.950, 0.900,
  0, 0, 0, 0, 0, 'active'
)
ON CONFLICT (id) DO UPDATE SET
  body_zh        = EXCLUDED.body_zh,
  body_en        = EXCLUDED.body_en,
  updated_at     = EXCLUDED.updated_at,
  trust_score    = EXCLUDED.trust_score,
  dim_utility    = EXCLUDED.dim_utility;


-- ─── mem_a001: AI Provider ──────────────────────────────────────────────────

INSERT INTO public.memory_nodes (
  id, schema_version, workspace_id, title_zh, title_en,
  content_type, content_format, body_zh, body_en,
  tags, visibility, author, created_at, updated_at,
  signature, source_type,
  trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep,
  votes_up, votes_down, verifications, traversal_count, unique_traverser_count,
  status
) VALUES (
  'mem_a001', '1.0', 'ws_spec0001',
  'AI Provider 與 API Key 自管', 'AI provider and self-managed API keys',
  'procedural', 'markdown',
  'MemTrace 不自營 AI 推論服務。所有 AI 功能由使用者選擇的供應商提供。

**官方內建 Provider**：

| Provider | 識別碼 | 預設 Chat 模型 | Embedding 模型 | 維度 |
|----------|--------|---------------|---------------|------|
| OpenAI | `openai` | `gpt-4o-mini` | `text-embedding-3-small` | 1536 |
| Anthropic | `anthropic` | `claude-haiku-4-5-20251001` | `voyage-3-lite` | 1024 |
| Google Gemini | `gemini` | `gemini-2.0-flash` | `text-embedding-004` | 768 |
| Ollama（自管）| `ollama` | `llama3`（可變）| `nomic-embed-text` | 可變 |

**Ollama 特別說明**：不需 API Key，改填 `base_url`（預設 `http://localhost:11434`）。支援 `auth_mode: none`（本機）與 `bearer`（Reverse Proxy）兩種認證模式。Embedding 維度依所選模型決定（`nomic-embed-text`=768、`mxbai-embed-large`=1024），**建立工作區後不可更改**。詳見 `docs/ollama-deployment.md`。

**Embedding 維度限制**：每個工作區的 embedding 維度在建立時固定（`workspaces.embedding_provider` + `embedding_dim`），**不可變更**。不同 provider 產生的向量維度不同，無法跨 provider 比較 cosine similarity。

**API Key 儲存**：CLI 存於 `~/.memtrace/config.json`（chmod 600），UI 存於加密寫入 `user_ai_keys`（Ollama 另存 `base_url` 與 `auth_token`）。Key **永不**傳送至 MemTrace 伺服器以外的任何地方。

**社群 Provider**：透過 `packages/api/core/ai.py` 的 `AIProvider` Protocol 可加入更多 provider（Mistral、Cohere、vLLM 等）。實作後在 `PROVIDER_REGISTRY` 註冊即可，不需修改 router 或資料庫 schema。

**未來商業模式**：可能提供 MemTrace 代管額度（免費層 + 付費方案）；架構透過 provider interface 抽象，日後切換不影響上層邏輯。',
  'MemTrace does not operate its own AI inference service. All AI features are powered by the user''s chosen provider.

**Officially built-in providers**:

| Provider | Identifier | Default chat model | Embedding model | Dim |
|----------|------------|--------------------|-----------------|-----|
| OpenAI | `openai` | `gpt-4o-mini` | `text-embedding-3-small` | 1536 |
| Anthropic | `anthropic` | `claude-haiku-4-5-20251001` | `voyage-3-lite` | 1024 |
| Google Gemini | `gemini` | `gemini-2.0-flash` | `text-embedding-004` | 768 |
| Ollama (self-hosted) | `ollama` | `llama3` (variable) | `nomic-embed-text` | Variable |

**Ollama notes**: No API key required. Configure `base_url` (default `http://localhost:11434`) and `auth_mode`: `none` (local) or `bearer` (reverse proxy). Embedding dimension depends on the chosen model (`nomic-embed-text`=768, `mxbai-embed-large`=1024) and is **immutable after workspace creation**. See `docs/ollama-deployment.md`.

**Embedding dimension constraint**: Each workspace fixes its embedding dimension at creation time (`workspaces.embedding_provider` + `embedding_dim`) and it is **immutable**. Different providers produce vectors of different dimensions; nodes embedded with different models cannot be compared via cosine similarity.

**API key storage**: CLI in `~/.memtrace/config.json` (chmod 600); UI encrypted in `user_ai_keys` (Ollama also stores `base_url` and `auth_token`). Keys are **never** transmitted outside the MemTrace server.

**Community providers**: Add more providers via the `AIProvider` Protocol in `packages/api/core/ai.py` (Mistral, Cohere, vLLM, etc.). Implement and register in `PROVIDER_REGISTRY` — no router or schema changes needed.

**Future business model**: a managed credit option (free tier + paid) may be introduced. The provider interface abstraction lets this swap in without touching extraction logic.',
  '{ai,api-key,provider,security,gemini,ollama,embedding}', 'public', 'memtrace-spec',
  '2026-04-11 00:00:00+00', '2026-04-29 00:00:00+00',
  'd6e7f8a3b4c5d6e7f8a3b4c5d6e7f8a3b4c5d6e7f8a3b4c5d6e7f8a3b4c5d6e7', 'human',
  0.950, 0.950, 1.000, 0.950, 0.900,
  0, 0, 0, 0, 0, 'active'
)
ON CONFLICT (id) DO UPDATE SET
  body_zh    = EXCLUDED.body_zh,
  body_en    = EXCLUDED.body_en,
  tags       = EXCLUDED.tags,
  updated_at = EXCLUDED.updated_at;


-- ─── mem_g004: Trust Score（新節點）────────────────────────────────────────

INSERT INTO public.memory_nodes (
  id, schema_version, workspace_id, title_zh, title_en,
  content_type, content_format, body_zh, body_en,
  tags, visibility, author, created_at, updated_at,
  signature, source_type,
  trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep,
  votes_up, votes_down, verifications, traversal_count, unique_traverser_count,
  status
) VALUES (
  'mem_g004', '1.0', 'ws_spec0001',
  'Trust Score：節點可信度四維評分', 'Trust Score: four-dimension node credibility rating',
  'factual', 'markdown',
  '每個節點有一個合成 `trust_score`（0–1），由四個維度加權計算：

| 維度 | 欄位 | 權重 | 說明 |
|------|------|------|------|
| 準確度 | `dim_accuracy` | 40% | 內容是否正確無誤 |
| 新鮮度 | `dim_freshness` | 25% | 資訊是否仍為最新 |
| 實用度 | `dim_utility` | 25% | 對讀者是否有實際幫助 |
| 作者聲譽 | `dim_author_rep` | 10% | 貢獻者的歷史可靠性 |

```
trust_score = accuracy×0.4 + freshness×0.25 + utility×0.25 + author_rep×0.1
```

## 投票機制（vote_trust）

評分以 **1–5 整數**提交（API 接受 accuracy 與 utility 兩個維度），後端取所有投票的平均值除以 5 換算為 0–1 浮點數後更新節點。

**API**：`POST /workspaces/{ws_id}/nodes/{node_id}/vote-trust`
```json
{ "accuracy": 4, "utility": 5 }
```

**MCP Tool**：`vote_trust(node_id, accuracy, utility)`
- AI agent 在讀取節點後，若認為內容正確且有用，應主動呼叫
- 每位使用者對同一節點只能有一筆投票（ON CONFLICT DO UPDATE）
- 投票記錄存於 `node_trust_votes` 表

## confirm_node_validity

`POST /workspaces/{ws_id}/nodes/{node_id}/confirm-validity` 可對節點進行一鍵確認：自動將 `dim_accuracy` 提升至 1.0 並重算 `trust_score`，同時更新 `validity_confirmed_at` 時間戳。等同於「我已人工核實此節點仍然正確」。

## TypeScript 實作

`packages/core/src/trust.ts` 提供 `computeTrustScore()` 與 `updateTrustScore()`，與 Python 端計算結果一致（誤差 < 0.01）。',
  'Each node carries a composite `trust_score` (0–1) computed from four weighted dimensions:

| Dimension | Field | Weight | Meaning |
|-----------|-------|--------|---------|
| Accuracy | `dim_accuracy` | 40% | Whether the content is correct |
| Freshness | `dim_freshness` | 25% | Whether the information is still current |
| Utility | `dim_utility` | 25% | Whether the content is practically helpful |
| Author Reputation | `dim_author_rep` | 10% | Historical reliability of the contributor |

```
trust_score = accuracy×0.4 + freshness×0.25 + utility×0.25 + author_rep×0.1
```

## Voting mechanism (vote_trust)

Scores are submitted as **integers 1–5** (API accepts accuracy and utility). The backend averages all votes, divides by 5 to get a 0–1 float, then updates the node.

**API**: `POST /workspaces/{ws_id}/nodes/{node_id}/vote-trust`
```json
{ "accuracy": 4, "utility": 5 }
```

**MCP Tool**: `vote_trust(node_id, accuracy, utility)`
- AI agents should call this proactively after reading a node they find correct and useful
- Each user has one vote per node (ON CONFLICT DO UPDATE)
- Votes stored in the `node_trust_votes` table

## confirm_node_validity

`POST /workspaces/{ws_id}/nodes/{node_id}/confirm-validity` is a one-tap validity stamp: automatically raises `dim_accuracy` to 1.0, recomputes `trust_score`, and sets `validity_confirmed_at`. Equivalent to "I have manually verified this node is still accurate."

## TypeScript implementation

`packages/core/src/trust.ts` exposes `computeTrustScore()` and `updateTrustScore()`, matching the Python-side result to within 0.01.',
  '{graph-mechanics,trust,vote,quality,mcp-tool,credibility}', 'public', 'system',
  '2026-04-29 00:00:00+00', NULL,
  '', 'human',
  0.950, 0.950, 1.000, 0.950, 0.900,
  0, 0, 0, 0, 0, 'active'
)
ON CONFLICT (id) DO NOTHING;


-- ─── mem_a005: Analytics Dashboard（新節點）────────────────────────────────

INSERT INTO public.memory_nodes (
  id, schema_version, workspace_id, title_zh, title_en,
  content_type, content_format, body_zh, body_en,
  tags, visibility, author, created_at, updated_at,
  signature, source_type,
  trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep,
  votes_up, votes_down, verifications, traversal_count, unique_traverser_count,
  status
) VALUES (
  'mem_a005', '1.0', 'ws_spec0001',
  'Analytics 儀表板與 Token 效率報告', 'Analytics dashboard and token efficiency report',
  'procedural', 'markdown',
  '## KB 健康摘要

`GET /workspaces/{ws_id}/analytics` 回傳以下欄位（30 日視窗）：

| 欄位 | 說明 |
|------|------|
| `total_nodes` | 活躍節點總數 |
| `active_edges` | weight > 0.3 的活躍邊數 |
| `orphan_node_count` | 沒有任何活躍邊的孤立節點數 |
| `avg_trust_score` | 工作區平均 trust_score |
| `faded_edge_ratio` | faded 邊佔全部邊的比例 |
| `monthly_traversal_count` | 近 30 日走訪總次數 |
| `top_nodes` | 走訪次數最高的 5 個節點 |
| `traversal_trend` | 逐日走訪折線資料（30 天） |
| `kb_type_metrics` | KB 類型感知指標（見下）|

**KB 類型感知指標**：
- `evergreen`：`isolated_subgraph_count`（孤立子圖數）、`avg_edges_per_node`
- `operational/ephemeral`：`never_traversed_ratio`、`avg_days_between_traversals`

**警示邏輯（UI）**：
- `evergreen` + `orphan_node_count > 0` → 橘色警示
- 非 evergreen + `never_traversed_ratio > 0.3` → 黃色警示

## Token 效率報告

`GET /workspaces/{ws_id}/analytics/token-efficiency` 回傳：

| 欄位 | 說明 |
|------|------|
| `avg_tokens_per_query` | 本月 MCP 呼叫平均回傳 token 數 |
| `estimated_full_doc_tokens` | 全文讀取的估算 token 數（body 字元數 / 4）|
| `savings_ratio` | `1 - avg_per_query / full_doc`（節省比例）|
| `monthly_query_count` | 本月 MCP 呼叫次數 |

資料來源：`mcp_query_logs` 表。每次 MCP read tool（search_nodes / traverse / get_node / list_by_tag / vote_trust）呼叫後非同步寫入一筆 log，記錄 `tool_name`、`result_node_count`、`estimated_tokens`、`provider`。

## UI 元件

`packages/ui/src/AnalyticsDashboard.tsx`：4 格指標卡片 + 30 日走訪折線圖 + Top Nodes 清單 + Token 效率區塊 + KB 類型指標格。透過 workspace 詳情頁的 Analytics 分頁開啟。',
  '## KB health summary

`GET /workspaces/{ws_id}/analytics` returns the following (30-day window):

| Field | Description |
|-------|-------------|
| `total_nodes` | Total active node count |
| `active_edges` | Edges with weight > 0.3 |
| `orphan_node_count` | Nodes with no active edges |
| `avg_trust_score` | Workspace-wide average trust_score |
| `faded_edge_ratio` | Ratio of faded edges to all edges |
| `monthly_traversal_count` | Total traversals in the last 30 days |
| `top_nodes` | Top-5 nodes by traversal count |
| `traversal_trend` | Per-day traversal data (30 days) |
| `kb_type_metrics` | KB-type-aware metrics (see below) |

**KB-type-aware metrics**:
- `evergreen`: `isolated_subgraph_count`, `avg_edges_per_node`
- `operational/ephemeral`: `never_traversed_ratio`, `avg_days_between_traversals`

**Alert logic (UI)**:
- `evergreen` + `orphan_node_count > 0` → orange alert
- non-evergreen + `never_traversed_ratio > 0.3` → yellow alert

## Token efficiency report

`GET /workspaces/{ws_id}/analytics/token-efficiency` returns:

| Field | Description |
|-------|-------------|
| `avg_tokens_per_query` | Average tokens returned per MCP call this month |
| `estimated_full_doc_tokens` | Estimated full-read tokens (body char count / 4) |
| `savings_ratio` | `1 - avg_per_query / full_doc` |
| `monthly_query_count` | MCP call count this month |

Data source: `mcp_query_logs` table. Each MCP read tool call (search_nodes / traverse / get_node / list_by_tag / vote_trust) writes one log entry asynchronously, recording `tool_name`, `result_node_count`, `estimated_tokens`, and `provider`.

## UI component

`packages/ui/src/AnalyticsDashboard.tsx`: 4-card metric grid + 30-day traversal sparkline + Top Nodes list + token efficiency block + KB-type metrics grid. Opened via the Analytics tab in the workspace detail view.',
  '{analytics,dashboard,token-efficiency,kb-health,mcp-logs,ui}', 'public', 'system',
  '2026-04-29 00:00:00+00', NULL,
  '', 'human',
  0.950, 0.950, 1.000, 0.950, 0.900,
  0, 0, 0, 0, 0, 'active'
)
ON CONFLICT (id) DO NOTHING;


-- ─── New edges ──────────────────────────────────────────────────────────────

INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count)
VALUES ('edge_g004_g001', 'ws_spec0001', 'mem_g004', 'mem_g001', 'extends',    1.00000, 0, '2026-04-29 00:00:00+00', 180, 0.100, 'active', false, 0, 0.00, 0)
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count)
VALUES ('edge_g004_g002', 'ws_spec0001', 'mem_g004', 'mem_g002', 'related_to', 0.90000, 0, '2026-04-29 00:00:00+00', 180, 0.100, 'active', false, 0, 0.00, 0)
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count)
VALUES ('edge_g004_a001', 'ws_spec0001', 'mem_g004', 'mem_a001', 'depends_on', 0.90000, 0, '2026-04-29 00:00:00+00', 180, 0.100, 'active', false, 0, 0.00, 0)
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count)
VALUES ('edge_a005_a001', 'ws_spec0001', 'mem_a005', 'mem_a001', 'depends_on', 0.90000, 0, '2026-04-29 00:00:00+00', 180, 0.100, 'active', false, 0, 0.00, 0)
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count)
VALUES ('edge_a005_g004', 'ws_spec0001', 'mem_a005', 'mem_g004', 'related_to', 0.85000, 0, '2026-04-29 00:00:00+00', 180, 0.100, 'active', false, 0, 0.00, 0)
ON CONFLICT (id) DO NOTHING;

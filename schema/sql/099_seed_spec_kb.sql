INSERT INTO users (id, display_name, email, email_verified, onboarding) VALUES ('system', 'System', 'system@memtrace.local', true, '{"completed": true}'::jsonb) ON CONFLICT DO NOTHING;
ALTER TYPE source_type ADD VALUE IF NOT EXISTS 'ai';
INSERT INTO public.workspaces (id, schema_version, name_zh, name_en, visibility, kb_type, owner_id, archive_window_days, min_traversals, created_at, updated_at, settings) VALUES ('ws_spec0001', '1.0', 'MemTrace 規格知識庫', 'MemTrace Spec Knowledge Base', 'public', 'evergreen', 'system', 90, 1, '2026-04-12 00:00:21.378267+00', '2026-04-26 02:08:37.266982+00', '{}');
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_5e541a9d', '1.0', 'ws_spec0001', 'Markdown 模式下的即時預覽', 'Live Preview in Markdown Mode', 'factual', 'markdown', '蝺刻摩?典`markdown`璅∪?銝???靘??祕??閬賡?踴?The editor must provide a live preview panel when in `markdown` mode.', '蝺刻摩?典`markdown`璅∪?銝???靘??祕??閬賡?踴?The editor must provide a live preview panel when in `markdown` mode.', '{editor,markdown,preview}', 'public', 'system', '2026-04-24 11:25:39.463663+00', NULL, 'cd53c9cd3540a9cc3d0e9462e2fb041b0f9775acd9c1c20a372955a4aa590bce', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_f7cbeb5e', '1.0', 'ws_spec0001', '來源文件：SPEC.md', 'Source: SPEC.md', 'source_document', 'plain', '', '', '{}', 'public', 'system', '2026-04-24 11:16:37.210116+00', NULL, 'source', 'human', NULL, NULL, NULL, NULL, 0.500, 0.500, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, 'SPEC.md');
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_44f68c0d', '1.0', 'ws_spec0001', '來源文件：SPEC.md', 'Source: SPEC.md', 'source_document', 'plain', '', '', '{}', 'public', 'system', '2026-04-24 06:12:04.328722+00', NULL, 'source', 'human', NULL, NULL, NULL, NULL, 0.500, 0.500, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, 'SPEC.md');
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_4afa80ea', '1.0', 'ws_spec0001', '來源文件：SPEC.md', 'Source: SPEC.md', 'source_document', 'plain', '', '', '{}', 'public', 'system', '2026-04-24 08:56:48.052833+00', NULL, 'source', 'human', NULL, NULL, NULL, NULL, 0.500, 0.500, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, 'SPEC.md');
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_2698efe6', '1.0', 'ws_spec0001', 'POST /edges/{edge_id}/traverse 請求體', 'POST /edges/{edge_id}/traverse Request Body', 'factual', 'markdown', '請求體包含一個 `actor_id` (例如 `usr_abc123` 或 `apikey_abc123`) 以及一個可選的 `note` 欄位。', 'The request body includes an `actor_id` (e.g., `usr_abc123` or `apikey_abc123`) and an optional `note` field.', '{api,request-body,traversal}', 'public', 'system', '2026-04-24 11:25:40.220298+00', NULL, '8da827ee692a2b067d6b98da026c3001d951a76bece032cb35ba88cef2a09dda', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_w002', '1.0', 'ws_spec0001', '本地開發環境啟動', 'Local Development Stack Setup', 'procedural', 'markdown', '## 前置需求
- Node.js 20 LTS+
- Python **3.11+**
- Docker Desktop（啟動 PostgreSQL 17 + pgvector）

## 啟動開發環境
```bash
# 1. 複製環境設定
cp .env.example .env  # 填入 POSTGRES_PASSWORD 與 SECRET_KEY

# 2. 安裝 Node 相依
npm install

# 3. 安裝 Python 相依
cd packages/api && python -m venv venv
source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt && cd ../..

# 4. 啟動資料庫（首次自動執行所有 schema/sql/*.sql）
docker compose up -d

# 5. 啟動 API
cd packages/api && uvicorn main:app --reload --port 8000

# 6. 啟動 UI（另一個終端機）
cd packages/ui && npm run dev
```

API：http://localhost:8000 / UI：http://localhost:5173', '## Prerequisites
- Node.js 20 LTS+
- Python **3.11+**
- Docker Desktop (runs PostgreSQL 17 + pgvector)

## Start the Dev Environment
```bash
# 1. Copy env config
cp .env.example .env  # fill in POSTGRES_PASSWORD and SECRET_KEY

# 2. Install Node dependencies
npm install

# 3. Install Python dependencies
cd packages/api && python -m venv venv
source venv/bin/activate
pip install -r requirements.txt && cd ../..

# 4. Start the database (auto-applies all schema/sql/*.sql on first run)
docker compose up -d

# 5. Start the API
cd packages/api && uvicorn main:app --reload --port 8000

# 6. Start the UI (separate terminal)
cd packages/ui && npm run dev
```

API: http://localhost:8000 / UI: http://localhost:5173', '{dev,setup,database,procedural}', 'public', 'system', '2026-04-28 00:00:00+00', NULL, '', 'human', NULL, NULL, NULL, NULL, 0.900, 0.950, 1.000, 0.900, 0.900, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_d003', '1.0', 'ws_spec0001', 'Content Type：節點的知識性質', 'Content Type: the nature of knowledge in a node', 'factual', 'markdown', '每個 Memory Node 必須標記一種 Content Type：

| Type | 說明 | 例子 |
|------|------|------|
| `factual` | 陳述性事實 | 「pgvector 支援 cosine similarity」 |
| `procedural` | 步驟流程 | 「如何設定 Docker Compose 開發環境」 |
| `preference` | 偏好或決策 | 「我們選擇 bcrypt 而非 argon2」 |
| `context` | 背景脈絡 | 「這個專案採用雙語設計的原因」 |
| `source_document` | 攝入時保留的原始文件（§20）| 一個會議錄音逐字稿、一份 PDF 全文 |

**`source_document` 特性**：由 `ingest` 流程自動建立，body 為文件全文或逐字稿，預設從 Graph View / 搜尋 / Q&A context 中**排除**。萃取出的節點透過 `source_doc_node_id` + `source_paragraph_ref` 反向連結到原始段落。

Content Type 影響：搜尋過濾、AI 萃取分類、預設 decay half-life（ephemeral 工作區）、Export Scope 配對（`procedural` → user-manual，`factual` → functional-spec 等）。', 'Every Memory Node must be tagged with a Content Type:

| Type | Description | Example |
|------|-------------|---------|
| `factual` | Declarative facts | "pgvector supports cosine similarity" |
| `procedural` | Step-by-step process | "How to set up a Docker Compose dev environment" |
| `preference` | Preferences or decisions | "We chose bcrypt over argon2" |
| `context` | Background context | "Why this project uses bilingual design" |
| `source_document` | Original document retained at ingestion (§20) | A meeting transcript, a full PDF |

**`source_document` characteristics**: Created automatically by the `ingest` flow; body holds the full text or transcript. **Excluded by default** from Graph View / search / Q&A context. Extracted nodes link back to the original passage via `source_doc_node_id` + `source_paragraph_ref`.

Content Type affects: search filtering, AI extraction classification, default decay half-life (ephemeral workspaces), and Export Scope matching (`procedural` → user-manual, `factual` → functional-spec, etc.).', '{data-model,schema,content-type,source-document}', 'public', 'memtrace-spec', '2026-04-11 00:00:00+00', NULL, 'f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1', 'human', NULL, NULL, NULL, NULL, 0.950, 0.950, 1.000, 0.900, 0.900, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_25ad6564', '1.0', 'ws_spec0001', '個人工作區可見性', 'Private Workspace Visibility', 'factual', 'markdown', '「私有」(private) 工作區對所有其他使用者完全隱藏。', 'A `private` workspace is completely hidden from all other users.', '{workspace-type,visibility,private}', 'public', 'system', '2026-04-24 11:25:39.649243+00', NULL, 'd9e0ea13c43e0e843f62e0fde909343ab684ea90f2dd3e4d953aaf5dbb099de5', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_i004', '1.0', 'ws_spec0001', '存取控制與權限角色：viewer / contributor / admin', 'Access control and permission roles: viewer / contributor / admin', 'factual', 'plain', 'MemTrace 採用類 git 的三層權限模型，適用於人類使用者與 AI 工具（含 MCP）。

角色定義：
- viewer：唯讀 + 問答 + 節點評分（rate）
- contributor：viewer 全部能力 + 提出修改建議（→ review queue，需管理員審核）
- admin：contributor 全部能力 + 直接寫入 + 審核提案 + 管理成員 + 邀請使用者 + 軟刪除/還原工作區

工作區擁有者（owner）永遠是 admin，不可降級。

API Key scope 對應：
- kb:read → viewer
- kb:propose → contributor
- kb:write → admin

MCP 工具遵守相同規則：kb:read key 無法呼叫 create_node；kb:propose key 可呼叫 propose_node；kb:write key 可直接寫入。

Contributor 提案流程：POST /workspaces/{ws_id}/proposals → review_queue（source_type = contributor_proposal）→ admin 審核後生效。

加入工作區的預設角色：
- 建立工作區 → admin（擁有者）
- 透過邀請連結加入 → 邀請建立時指定的角色
- 跨庫複製節點 → 不授予任何成員資格', 'MemTrace uses a git-inspired three-tier permission model that applies equally to human users and AI tools (including MCP).

Roles:
- viewer: read-only + Q&A chat + node rating (votes_up/down)
- contributor: all viewer capabilities + submit change proposals (→ review queue, requires admin approval)
- admin: all contributor capabilities + direct write + approve/reject proposals + manage members + invite users + soft-delete/restore workspace

The workspace owner is always admin and cannot be demoted.

API Key scope mapping:
- kb:read → viewer
- kb:propose → contributor
- kb:write → admin

MCP tools respect the same rules: a kb:read key cannot call create_node; a kb:propose key can call propose_node; a kb:write key can write directly.

Contributor proposal flow: POST /workspaces/{ws_id}/proposals → review_queue (source_type = contributor_proposal) → takes effect after admin approval.

Default role on join:
- Create workspace → admin (owner)
- Accept invite link → role embedded in the invite token by admin
- Cross-workspace node copy → no membership granted', '{access-control,permissions,roles,viewer,contributor,admin,mcp,api-key}', 'public', 'system', '2026-04-12 00:00:00+00', NULL, 'd1e2f3a4b5c6d1e2f3a4b5c6d1e2f3a4b5c6d1e2f3a4b5c6d1e2f3a4b5c6d1e2', 'human', NULL, NULL, NULL, NULL, 0.950, 0.950, 1.000, 0.950, 0.900, 0, 0, 0, 5, 2, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_0d6a7214', '1.0', 'ws_spec0001', '工作區存取授權', 'Workspace Access Granting', 'factual', 'markdown', '工作區的存取權限僅透過管理員的明確邀請授予。', 'Access to a workspace is granted only via explicit admin invitation.', '{access-control,admin,invitation}', 'public', 'system', '2026-04-24 11:25:39.592594+00', NULL, '7565ff5c348962f12749977db91aa8c4ec162aaa28a3d45be254023066708312', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_k003', '1.0', 'ws_spec0001', '節點跨庫複製：可攜性', 'Cross-workspace node copy: portability', 'procedural', 'plain', '任何節點可被複製到另一個知識庫，但 Edge 不隨行。複製行為：目標庫中取得新 id；created_at 重設為複製時間；provenance.copied_from 記錄 { node_id, workspace_id } 供溯源；目標庫中 visibility 預設為 private；Trust 分數以快照帶入，兩邊後續互不影響；signature 在目標庫環境重新計算。CLI 指令：memtrace copy-node <node-id> --to <workspace-id>。API：POST /workspaces/{ws_id}/nodes（帶 copied_from 參數）。', 'Any node can be copied to another Knowledge Base, but its Edges are not copied. Copy behaviour: the target KB assigns a new id; created_at is reset to the copy time; provenance.copied_from records { node_id, workspace_id } for traceability; visibility defaults to private in the target KB; Trust scores are carried as a snapshot — subsequent changes in either KB do not affect the other; signature is recomputed in the target KB context. CLI: memtrace copy-node <node-id> --to <workspace-id>. API: POST /workspaces/{ws_id}/nodes (with copied_from parameter).', '{knowledge-base,portability,copy,provenance}', 'public', 'memtrace-spec', '2026-04-11 00:00:00+00', NULL, 'c5d6e7f8a3b4c5d6e7f8a3b4c5d6e7f8a3b4c5d6e7f8a3b4c5d6e7f8a3b4c5d6', 'human', NULL, NULL, NULL, NULL, 0.950, 0.950, 1.000, 0.900, 0.900, 0, 0, 0, 1, 1, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_d3564082', '1.0', 'ws_spec0001', '處理 createNode/updateNode 的 202 回應', 'Handle 202 Response for createNode/updateNode', 'procedural', 'markdown', '當 createNode 或 updateNode API 回傳 202 狀態碼時，應從回應主體中提取 review_id 並明確回傳給 AI 代理。', 'When the createNode or updateNode API returns a 202 status code, the review_id should be extracted from the response body and explicitly returned to the AI agent.', '{api,錯誤處理,ai代理,審核流程}', 'public', 'system', '2026-04-25 02:39:59.693849+00', NULL, '23ae917c2d984d6ff3437a3c309dd34ed183a39846dbcf3156193dc0e779c845', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_e778fedf', '1.0', 'ws_spec0001', '記憶節點簽名', 'Memory Node Signature', 'factual', 'markdown', '`memory_nodes` 表中的 `signature` 欄位類型為 TEXT，存儲記憶節點內容的 SHA-256 哈希值。', 'The `signature` column in the `memory_nodes` table is of type TEXT, storing the SHA-256 content hash of the memory node.', '{database,schema,memory_nodes,column,hash}', 'public', 'system', '2026-04-24 11:25:39.08939+00', NULL, 'b3e2a69453c440c83d3d584bf7789a00fa68991922c6de7dd86d5e94dc6f159b', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_524c73f6', '1.0', 'ws_spec0001', 'D4 節點歸檔排程完整化', 'D4 Node Archiving Schedule Completion', 'procedural', 'markdown', '此功能目標是補齊缺失的排程呼叫，以完整實作節點從衰減到歸檔的生命週期。', 'The goal of this feature is to complete missing scheduled calls to fully implement the node lifecycle from decay to archiving.', '{scheduler,node-management,archiving}', 'public', 'system', '2026-04-25 02:40:00.508542+00', NULL, '4c99e0484ce778915b995e295444a4ca0df29299e9704f530886f6082898b1b1', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_861a5678', '1.0', 'ws_spec0001', '記憶節點中文標題', 'Memory Node Chinese Title', 'factual', 'markdown', '`memory_nodes` 表中的 `title_zh` 欄位類型為 TEXT，存儲記憶節點的繁體中文標題。', 'The `title_zh` column in the `memory_nodes` table is of type TEXT, storing the Traditional Chinese title of the memory node.', '{database,schema,memory_nodes,column,i18n}', 'public', 'system', '2026-04-24 11:25:38.887496+00', NULL, '12328509dc7671ad30f9527c83a236ec95851b5d63e6c5365783c6b50b757d97', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_9209a508', '1.0', 'ws_spec0001', '記憶節點標籤', 'Memory Node Tags', 'factual', 'markdown', '`memory_nodes` 表中的 `tags` 欄位類型為 TEXT[]，存儲記憶節點的標籤，並已建立 GIN 索引。', 'The `tags` column in the `memory_nodes` table is of type TEXT[], storing tags for the memory node, and is GIN-indexed.', '{database,schema,memory_nodes,column,indexing}', 'public', 'system', '2026-04-24 11:25:39.008653+00', NULL, '56e5ce2c9c37c38be23ac86af4fe6b4d09f5df89d845026f4202d553b0f40f75', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_bcc8e28c', '1.0', 'ws_spec0001', '記憶節點可見性', 'Memory Node Visibility', 'factual', 'markdown', '`memory_nodes` 表中的 `visibility` 欄位類型為 ENUM，可能的值為 `public` / `team` / `private`。', 'The `visibility` column in the `memory_nodes` table is of type ENUM, with possible values `public` / `team` / `private`.', '{database,schema,memory_nodes,column,enum}', 'public', 'system', '2026-04-24 11:25:39.029513+00', NULL, '07adf4dc6273637faa730c865f2b2953aa0ea1a717679492657b03f24f16450e', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_21638c34', '1.0', 'ws_spec0001', 'POST /edges/{edge_id}/rate 端點', 'POST /edges/{edge_id}/rate Endpoint', 'procedural', 'markdown', '此端點用於為路徑提交明確的評分（1-5）。', 'This endpoint is used to submit an explicit rating (1-5) for a path.', '{api,rest,rating,edge}', 'public', 'system', '2026-04-24 11:25:40.201027+00', NULL, 'cb4131be818878d469bd1c212bcc26506d6ca08b7a42d30d9a8991f3ffa33f05', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_f027cd84', '1.0', 'ws_spec0001', 'MemTrace AI 功能概覽', 'MemTrace AI Features Overview', 'factual', 'markdown', 'MemTrace 在三個不同的上下文中使用 AI，所有這些都共享相同的提供者抽象和 API 金鑰模型。', 'MemTrace uses AI in three distinct contexts, all sharing the same provider abstraction and API key model.', '{ai,features,architecture}', 'public', 'system', '2026-04-24 11:25:40.433573+00', NULL, '613853d08868de023cab46df86662e05317b460277273a997266163eb98cd87a', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_9d2bb35f', '1.0', 'ws_spec0001', 'API 金鑰範圍與工具行為', 'API Key Scopes and Tool Behavior', 'factual', 'markdown', '一個 API 金鑰可以持有這三種範圍中的恰好一種。MCP 工具遵循金鑰的範圍，行為與相同角色的真人使用者完全一致；例如，`kb:read` 金鑰不能調用 `create_node`，而 `kb:write` 金鑰可以直接調用 `create_node`。', 'An API key can hold exactly one of these three scopes. MCP tools respect the key''s scope identically to a human user of the same role; for example, a `kb:read` key cannot call `create_node`, while a `kb:write` key can call `create_node` directly.', '{api-key,scope,restriction,tool-integration}', 'public', 'system', '2026-04-24 11:25:40.662171+00', NULL, 'ebf39bff13bb90908583ff5cb051532e6a089703a636a2ef60cb0edc2de260b1', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_32bc6360', '1.0', 'ws_spec0001', '排程呼叫 `apply_node_archiving()`', 'Schedule Call for `apply_node_archiving()`', 'procedural', 'markdown', '排程器應補上對 `apply_node_archiving()` 函式的每日 UTC 02:00 呼叫，該函式已存在但目前未被觸發。', 'The scheduler should add a daily UTC 02:00 call to the `apply_node_archiving()` function, which exists but is currently not triggered.', '{scheduler,node-archiving}', 'public', 'system', '2026-04-25 02:38:35.076074+00', NULL, '014a6e02054ebb86a8d31ec981406f8fa1b145a2fe86d02590c5310b59f8a95d', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_7f9fadcd', '1.0', 'ws_spec0001', '記憶節點中文正文', 'Memory Node Chinese Body', 'factual', 'markdown', '`memory_nodes` 表中的 `body_zh` 欄位類型為 TEXT，存儲記憶節點的繁體中文正文。', 'The `body_zh` column in the `memory_nodes` table is of type TEXT, storing the Traditional Chinese body of the memory node.', '{database,schema,memory_nodes,column,i18n}', 'public', 'system', '2026-04-24 11:25:38.966141+00', NULL, 'd7824a074eb822f728708f7437e9754dbf474edae0ed0e7f62c5e84b47844983', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_bf7d06a5', '1.0', 'ws_spec0001', '記憶匯入功能', 'Memory Import Functionality', 'factual', 'markdown', '使用者可以將現有的存檔匯入回任何工作區。', 'Users can import an existing archive back into any workspace.', '{memory-management,import}', 'public', 'system', '2026-04-24 11:25:39.253573+00', NULL, 'ec2855a3149c8bc86122529991ed1de3b55a67fed7374831c98c416815915ad0', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_b41097bf', '1.0', 'ws_spec0001', '記憶節點複製功能', 'Memory Node Copying Functionality', 'factual', 'markdown', '任何單獨的記憶節點都可以複製到不同的知識庫。', 'Any individual Memory Node can be copied to a different Knowledge Base.', '{memory-node,knowledge-base,copy}', 'public', 'system', '2026-04-24 11:31:27.655142+00', NULL, 'cea540a33f70ed93236f0dbdc41def46a9b3201f9f8378d4a7f27aa582019b77', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_ef8ec8ec', '1.0', 'ws_spec0001', 'AI Chat 使用知識庫關聯邊界', 'AI Chat Uses KB Association Boundaries', 'factual', 'markdown', 'AI Chat 功能將依賴知識庫關聯的邊界設定。', 'The AI Chat functionality will depend on the boundary settings of knowledge base associations.', '{ai-chat,knowledge-base-association}', 'public', 'system', '2026-04-25 02:39:58.716612+00', NULL, '386ed5a376b7d7370a26182eaf9146e51d7f02dc1aec134bab2d9fb00a5f2986', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_82683707', '1.0', 'ws_spec0001', 'MCP 傳輸模式：stdio', 'MCP Transport Mode: stdio', 'factual', 'markdown', 'stdio 是本地 CLI 使用的默認 MCP 傳輸模式。', 'stdio is the default MCP transport mode for local CLI usage.', '{mcp,transport,cli}', 'public', 'system', '2026-04-24 11:25:40.307697+00', NULL, 'f880922d12b02e864797d55776d62aa807c4e9908e7c0cd744586cd744afcf2c', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_526945e4', '1.0', 'ws_spec0001', 'MCP 傳輸模式：HTTP + SSE', 'MCP Transport Mode: HTTP + SSE', 'factual', 'markdown', '當 `memtrace serve --mcp` 運行時（第二階段），可以使用 HTTP + SSE 傳輸模式。', 'The HTTP + SSE transport mode is available when `memtrace serve --mcp` is running (Phase 2).', '{mcp,transport,http,sse,phase-2}', 'public', 'system', '2026-04-24 11:25:40.327756+00', NULL, '8dfd08b535e9fe8263dcd1cf08eebf3b2f95bc51b3a1c9d7fc574a6d12ecbb5d', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_eedc4eef', '1.0', 'ws_spec0001', 'API 金鑰權限範圍：kb:read', 'API Key Scope: kb:read', 'factual', 'markdown', '`kb:read` 權限範圍的 API 金鑰授予檢視者角色能力，允許搜索、讀取、走訪和評分操作。', 'An API key with the `kb:read` scope grants viewer role capabilities, allowing search, read, traverse, and rate operations.', '{api-key,scope,viewer,read-access}', 'public', 'system', '2026-04-24 11:25:40.597989+00', NULL, '1be172568b159d3b911a49177c590a9d5b74b6ec33a344f7abd355388b2c30c5', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_cd89f403', '1.0', 'ws_spec0001', '暫時性知識庫邊緣衰減排程', 'Ephemeral KB Edge Decay Schedule', 'procedural', 'markdown', '暫時性知識庫的邊緣衰減排程應從每日觸發改為每 1 小時觸發。', 'The edge decay schedule for Ephemeral Knowledge Bases should be changed from daily to hourly triggering.', '{scheduler,ephemeral-kb,edge-decay}', 'public', 'system', '2026-04-25 02:38:39.851283+00', NULL, '0880355a86987c4a47300e767f68c6870b43bc47586c6c8c16f1825998a6e90b', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_a4bdc8a9', '1.0', 'ws_spec0001', '從歸檔還原節點 API', 'Restore Node from Archive API', 'procedural', 'markdown', '提供一個 API 端點 `POST /nodes/{id}/restore`，允許編輯者或更高權限的使用者從歸檔中還原節點。', 'Provide an API endpoint `POST /nodes/{id}/restore` allowing editors or higher-privileged users to restore nodes from archive.', '{api,node-archiving}', 'public', 'system', '2026-04-25 02:38:45.09492+00', NULL, '029e98ddd550f5a3e9de0fffe6caf0393b841248c6f5db9ba68f07f14c5c8c28', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_a002', '1.0', 'ws_spec0001', '文件攝入與 AI 節點萃取', 'Document ingestion and AI node extraction', 'procedural', 'markdown', '支援格式：`.md`、`.txt`、`.pdf`、`.docx`。萃取流程：

1. AI 依文件結構（標題、段落）切割成候選塊
2. 各塊被分類為 Content Type
3. 生成雙語標題與內文草稿
4. 提議候選 Edge（依語意相近與文件順序）

所有結果進入 **Review Queue**，不自動 commit。萃取節點的 source_type 預設為 `ai_generated`，人工無修改接受 → `ai_verified`，人工修改後接受 → `human`。每個節點記錄 source_document 與 extraction_model。', 'Supported formats: `.md`, `.txt`, `.pdf`, `.docx`. Extraction flow:

1. AI segments the document into candidate chunks by structure (headings, paragraphs)
2. Each chunk is classified into a Content Type
3. Bilingual title and body drafts are generated
4. Candidate Edges are proposed based on semantic proximity and document order

All results enter the **Review Queue** — never auto-committed. Extracted node source_type defaults to `ai_generated`; accepted without edits → `ai_verified`; accepted after edits → `human`. Each node records source_document and extraction_model.', '{ai,ingestion,extraction,document}', 'public', 'memtrace-spec', '2026-04-11 00:00:00+00', NULL, 'e7f8a3b4c5d6e7f8a3b4c5d6e7f8a3b4c5d6e7f8a3b4c5d6e7f8a3b4c5d6e7f8', 'human', NULL, NULL, NULL, NULL, 0.950, 0.950, 1.000, 0.950, 0.900, 0, 0, 0, 2, 1, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_e10a0200', '1.0', 'ws_spec0001', '顯示新金鑰的一次性複製對話框', 'Display One-Time Copy Dialog for New Key', 'procedural', 'markdown', '金鑰建立後，應顯示一個一次性複製對話框。', 'After creation, a one-time copy dialog should be displayed for the new key.', '{api-key,ui}', 'public', 'system', '2026-04-25 02:38:53.632458+00', NULL, '04c3b3db95c39e7be32de5edbd26fc9e83a18b2fc27939e5c70d2740b8e39975', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_cbe1be4b', '1.0', 'ws_spec0001', '工作區類型分配', 'Workspace Type Assignment', 'factual', 'markdown', '工作區類型是在創建過程中分配的（Web UI 第 ?? 步或 CLI 第 3 步）。', 'Workspace types are assigned during creation (Web UI step ?? CLI step 3).', '{workspace,creation,configuration}', 'public', 'system', '2026-04-24 11:31:27.627383+00', NULL, 'a0a8bffabfa012bb38c759fc8c239a205e5a471557bd7e38294d264dd464e45b', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_07334d61', '1.0', 'ws_spec0001', '記憶導出/匯入範圍', 'Memory Export/Import Scope', 'factual', 'markdown', '支持節點級別和全知識庫級別的導出/匯入。', 'Node-level and full-Knowledge Base export/import are supported.', '{export,import,scope}', 'public', 'system', '2026-04-24 11:25:39.270852+00', NULL, 'c097f8f7975d3ca47dd120efbcc14faf227f40b75fb9f2ad81971d7bc57ae2ed', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_6a46a549', '1.0', 'ws_spec0001', '知識庫導出與匯入規範', 'Knowledge Base Export & Import Specification', 'context', 'markdown', '關於導出類型、可篩選範圍和格式詳情的完整規範，請參閱 禮22。', 'For full specification including export types, filterable scopes, and format details, see 禮22.', '{specification,export,import}', 'public', 'system', '2026-04-24 11:25:39.289665+00', NULL, '1fe072bfa79a235c67cbcb708caaa9f62839ddcb301956885e5fc13d472ac11f', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_8dc3944b', '1.0', 'ws_spec0001', '撤銷工作區邀請 API', 'Revoke Workspace Invitation API', 'procedural', 'markdown', '提供 `DELETE /workspaces/{ws_id}/invites/{token}` 端點，用於撤銷已發送的工作區邀請。', 'Provides the `DELETE /workspaces/{ws_id}/invites/{token}` endpoint to revoke a sent workspace invitation.', '{api,邀請管理}', 'public', 'system', '2026-04-25 02:39:01.850026+00', NULL, '93a44d63a64aa6011cdb805134454d4bf38d2959fdfc83f09af4b64fd2048c5d', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_e5ee7b93', '1.0', 'ws_spec0001', '來源文件：SPEC.md', 'Source: SPEC.md', 'source_document', 'plain', '# MemTrace Specification

## 1. Introduction
MemTrace is an open platform for building shared knowledge through minimal, well-connected Memory Nodes. Its core design goal is to allow any human or AI agent to reach any answer by following the shortest possible path through a graph of small, typed relationships — rather than reading through large documents. This specification outlines all core components, including Memory Schema, Edge Schema, Trust mechanics, and the Decay engine.

Central to MemTrace is the belief that **knowledge itself has intrinsic value** and that the people who curate it should have full sovereignty over how it is shared — whether openly with the world, conditionally with an audience, or kept entirely private. The platform is designed so that sharing a knowledge base is a deliberate choice, not an accident.

## 1.1 Core Product Philosophy

### Knowledge through connection, not accumulation

The fundamental premise of MemTrace is that knowledge does not need to live in large, monolithic documents. Instead, it is best expressed as a network of small, focused Memory Nodes — each one capturing a single idea clearly — whose value emerges from the relationships between them.

A node on its own is lightweight. Connected to others, it becomes part of a living knowledge base that grows organically over time and survives beyond any single author or conversation.

### Designed for inheritance

MemTrace is built for the moment when someone new needs to understand what came before — whether that is a new team member, a collaborator joining mid-project, or an AI agent operating in an unfamiliar context.

Every Memory Node is designed to be self-contained enough to be read in isolation, yet connected enough that following its edges leads naturally to everything related. A reader does not need prior context from the author: they enter at any node and navigate the graph by following the associations that matter to them.

### Co-authorship between humans and AI

MemTrace is designed for knowledge work that happens collaboratively — between people, between people and AI tools, or between AI agents operating in the same workspace. All contributors, regardless of whether they are human or AI, write into the same graph. The graph''s structure — the edges, their weights, the traversal counts — reflects which knowledge has actually proven useful, not just what was recorded.

Decay ensures that the graph stays honest: connections that nobody follows fade over time. Connections that are visited frequently, rated positively, or built upon by other nodes strengthen and persist. The result is a knowledge base that self-organises around what actually matters.

Importantly, **nothing is deleted by decay alone**. A node that has not been accessed in a long time does not disappear — it fades into the background, becoming less visible in default views and traversal results. An author or workspace admin can always retrieve, restore, or archive any node explicitly. The decay mechanism shapes attention, not existence.

### Knowledge has intrinsic value

Knowledge is not a commodity that becomes more valuable only when shared freely. The effort, insight, and curation behind a well-structured Knowledge Base represent real intellectual work — work that belongs to its author.

MemTrace is built on the premise that **anyone can choose how to present the knowledge they manage**:

- **Openly** — a public Knowledge Base becomes a shared resource, discoverable by anyone, growing in value through community traversal and contribution.
- **Conditionally** — a conditionally-public Knowledge Base lets the wider world see its shape and structure, signalling that the knowledge exists, without surrendering the content itself. Interested parties can request access; the author decides who enters.
- **Restrictedly** — a restricted Knowledge Base is invisible to those not invited. Its existence is not disclosed, and access is entirely on the author''s terms.
- **Privately** — a private Knowledge Base is for the author alone, a personal thinking space with no external surface.

This is not merely a permissions model. It is a statement about the **relationship between knowledge and its curator**. MemTrace does not assume that value is created only when knowledge is free. It assumes that value is created when knowledge is structured, connected, and curated — and that the curator has the right to decide what happens next.

### Design principles that follow from this

| Principle | Implication |
|-----------|-------------|
| **Nodes are minimal** | A node contains the smallest unit of knowledge that can stand alone. If a thought can be split without losing meaning, it should be. |
| **Relationships carry the knowledge** | The value of a Knowledge Base lies in its edges, not in the volume of its nodes. Two small nodes with a typed edge express more than one large node that conflates two ideas. |
| **Shortest path is the design goal** | Every structural decision — node granularity, edge type, content type — should be evaluated by whether it shortens the path a human or AI agent needs to follow to reach an answer. |
| **Entry point independence** | Any node can serve as an entry point. Navigation follows edges, not a fixed hierarchy. |
| **Value is earned** | Trust scores, traversal counts, and edge weights reflect real usage, not just authorship intent. |
| **Knowledge sovereignty and protection** | The core value is knowledge sharing, but the author retains full control over the depth of that sharing. Roles clearly distinguish between those who can only see the graph structure (Viewers) and those who can access and edit detailed content (Editors/Admins). |
| **Decay shapes attention, not existence** | No node or edge is permanently deleted by the decay engine alone. Faded content is archived, not destroyed. |
| **Knowledge sovereignty belongs to the curator** | Every Knowledge Base owner decides how their knowledge is shared — fully public, conditionally visible, invitation-only, or entirely private. Sharing is always a deliberate act, never a default. |

## 2. Terminology
- **Memory Node**: A discrete piece of knowledge, written bilingually (zh-TW and en) or unilaterally.
- **Edge**: A typed relationship connecting two Memory Nodes.
- **Co-Access**: An event where two connected memories are accessed sequentially or simultaneously in the same context.
- **Decay**: The natural reduction of edge weight over time if not co-accessed.
- **Archive**: The state a node or edge enters when it is no longer relevant to default views. Archived content is hidden but not destroyed and can be restored at any time.
- **Faded**: The state an edge enters when its weight drops below `min_weight` due to decay. A faded edge is archived automatically but can be restored.
- **Knowledge Base Type**: A workspace-level setting (`evergreen` or `ephemeral`) that governs how the decay engine treats nodes and edges in that workspace (see §7.3).
- **Knowledge Base Visibility**: The four-tier sharing level of a Knowledge Base (`public`, `conditional_public`, `restricted`, `private`), controlling who can discover and access it. Set at creation time and immutable thereafter. Distinct from Memory Node visibility, which controls individual node access within a Knowledge Base.
- **Write Serialization**: The per-workspace write queue mechanism that ensures concurrent writes (by humans or AI) are applied in arrival order, preventing race conditions.
- **Conflict Flag**: A marker applied to a Memory Node when the system detects a logical inconsistency introduced by an AI or concurrent human edit (see §17.4).
- **KB Association**: An explicit link between two Knowledge Bases that grants AI agents permission to reason across their contents (see §18).
- **Source Document Node**: A special `source_document` node created when a file is ingested, retaining the original text with paragraph-level markers. Excluded from default graph and search views (see §20).
- **Identity Provider (IdP)**: An external service that authenticates a user and returns a verified identity claim. Google is the supported IdP for OAuth login.
- **Session Token**: A short-lived signed token issued by MemTrace after successful authentication, used to authorize subsequent API requests.

## 3. Product User Flow
1. **Knowledge Base Creation**: A user can initialize multiple Knowledge Bases (Workspaces) with a chosen **type** (`evergreen` or `ephemeral`, see §7.3) and **sharing level** — one of four tiers: `public`, `conditional_public`, `restricted`, or `private` (see §12). The sharing level is immutable after creation. The creating user is automatically added as an admin. A Knowledge Base may be started blank or bootstrapped from a document (see §11.1). A workspace may be associated with other workspaces to enable AI cross-KB reasoning (see §18).
2. **Ingestion & Upload**: Users can input raw text, Markdown, or upload rich files (PDF, Word, video, meeting recordings). The AI Extraction pipeline applies the Node Minimization Principle (§11.3) to split source material into the smallest meaningful units and proposes typed edges between them. All candidates enter a Review Queue for human approval before committing (see §11.2).
3. **Relationship Mapping**: Edges are as important as nodes. After creating or accepting a node, users are expected to define its relationships — by drawing connections in the Graph View, using the Edge panel in the Node Editor, or accepting AI-proposed edges. A node with no edges is incomplete.
4. **Node Portability**: Any individual Memory Node can be copied to another Knowledge Base without carrying its Edges (see §11.3).
5. **Organic Decay**: Once established, the system takes over with the organic decay mechanism unless manually pinned.

## 4. Schemas

### 4.1 Memory Node v1
- Validated via `schema/node.v1.json`
- Supports multi-lingual title/body (en/zh-TW).
- Tags array, visibility (public/team/private).
- Built in trust dimensions: accuracy, freshness, utility, author reputation.

### 4.2 Edge v1
- Validated via `schema/edge.v1.json`
- From -> To directed graph.
- Relationship types: `depends_on`, `extends`, `related_to`, `contradicts`.
- Weight tracked between 0 and 1.
- Decay half-life tracked individually per edge; default varies by workspace `kb_type` and node `content_type` (see §7.3).
- Edge status: `active` / `faded` / `pinned`. Faded edges are archived, not deleted.

## 5. Trust & Anti-Forgery
- Memories are digitally fingerprinted with SHA-256 hashes generated from the content.
- Community and AI votes update the trust scores continuously.

## 6. Operations
- `new`: Create a new Memory Node. Each node should capture exactly one idea — if the content spans multiple ideas, create multiple nodes and link them. Running `link` immediately after `new` is the expected workflow.
- `link`: Create a typed edge between two existing nodes. Edges are the primary carrier of knowledge in MemTrace; a node without edges is not yet a useful part of the graph.
- `ingest <file>`: Upload a document and trigger AI extraction to propose candidate Memory Nodes (see §11.2).
- `copy-node <node-id> --to <workspace-id>`: Copy a single Memory Node into another Knowledge Base; Edges are not copied (see §11.3).
- `push`: Sync local changes to a remote repository (e.g. GitHub).
- `pull`: Pull remote changes from GitHub or central index.
- `export`: Export a Knowledge Base or filtered subset to local filesystem. Accepts `--type` and `--format` flags (see §22).
- `import`: Import a previously exported Knowledge Base archive into MemTrace (see §22).

## 7. Decay Mechanics

### 7.1 Current Model (v1)

Weight formula over time:

```
weight(t) = w0_current × 0.5 ^ (days_since_last_access / half_life)
```

When `weight < min_weight`, the edge transitions to **faded** state — it is not deleted. Faded edges:
- Are hidden from default Graph View and traversal results
- Are still stored in the database with `status = ''faded''`
- Can be restored manually by the workspace owner or original author
- Remain queryable via API with the `include_faded=true` parameter

Co-access boost by relation type:

| Relation      | Boost  |
|---------------|--------|
| `depends_on`  | +0.30  |
| `extends`     | +0.20  |
| `related_to`  | +0.15  |
| `contradicts` | +0.10  |

### 7.2 Open Design Questions (Under Discussion)

The current decay model applies uniformly to all edges based on time since last access. The following questions remain open and will inform a future v2 decay model:

**Q1 — Should content type affect the default half-life?**

Some knowledge is structurally timeless (mathematical facts, definitions), while other knowledge is highly perishable (meeting context, temporary preferences). A content-type-aware default half-life may be more appropriate than a single global value:

| Content Type  | Proposed Default Half-life |
|---------------|---------------------------|
| `factual`     | 365 days (or pinned)      |
| `procedural`  | 90 days                   |
| `preference`  | 30 days                   |
| `context`     | 14 days                   |

**Q2 — Should decay apply to nodes as well as edges?**

Currently only edges decay. A node that has no incoming traversals over time does not fade — it simply becomes an island. Options:
- **Option A**: Apply a node-level `visibility_weight` (separate from trust) that fades if the node has zero traversal activity over a threshold period, causing it to drop out of default search/graph results.
- **Option B**: Keep nodes permanently visible unless explicitly archived; let edge decay naturally isolate unreachable nodes.
- **Option C**: Compute a derived "reachability score" based on the weights of its connected edges; nodes with no active edges become visually dimmed.

> Current lean: **Option C** — derive reachability from edge state rather than adding a separate node decay axis.

**Q3 — Should decay be time-based or activity-based?**

The current formula counts calendar days since last access. An alternative is to count only relative to workspace activity: if nobody has used the workspace at all, no decay should occur. This avoids penalising knowledge in low-activity workspaces.

**Q4 — What triggers the decay recalculation?**

Options: (a) a scheduled nightly job, (b) on every read request (lazy decay), (c) on write events only. Lazy decay is simpler to implement but can lead to stale weights being served briefly.

**Q5 — Pin / exemption mechanism**

High-value nodes and edges should be exemptable from decay. A `pinned: true` flag (set by the author or workspace admin) would bypass the decay formula entirely. Pinned edges still record co-access boosts but their weight does not decrease below the current value.

### 7.3 Knowledge Base Types

A workspace is assigned one of two **types** at creation time, as part of the workspace creation flow (Web UI step ④, CLI step 3). The type governs how the decay engine treats all nodes and edges within that workspace. **The type cannot be changed after the workspace is created.**

---

#### `evergreen` — 長效型知識庫

**Use cases**: Specification documents, architectural decisions, team playbooks, product philosophy, onboarding guides.

**Characteristics**:
- Knowledge in this type of workspace is assumed to be **structurally stable**. Facts do not expire simply because time passes.
- **Time-based decay is disabled.** Edge weights do not decrease based on calendar days.
- **Reference-count-based archiving** is used instead: nodes and edges that fall below a minimum traversal threshold over a configurable observation window are automatically **archived**, not faded.
- Archived nodes remain fully accessible via the Archive view and API but do not appear in default search or graph traversal results, reducing cognitive load without destroying knowledge.
- The observation window and minimum traversal threshold are configurable per workspace (defaults: 90-day window, minimum 1 traversal).
- All nodes and edges start in `active` state. Archiving is triggered by a scheduled job, not in real-time.

**Archive trigger logic (evergreen)**:
```
IF traversal_count(node, last 90 days) == 0
AND node is not pinned
THEN node.status → ''archived''

IF co_access_count(edge, last 90 days) == 0
AND edge is not pinned
THEN edge.status → ''faded''
```

---

#### `ephemeral` — 短效型知識庫

**Use cases**: Troubleshooting runbooks, incident postmortems, daily task procedures, tool-specific how-to guides that change as tools evolve.

**Characteristics**:
- Knowledge in this type of workspace is assumed to have a **natural expiry**: procedures become outdated, tools change, contexts shift.
- **Time-based decay is enabled**, using the weight formula from §7.1. The decay half-life defaults are shorter than the global defaults, reflecting the expected rate of change:

| Content Type  | Default Half-life (ephemeral) |
|---------------|-------------------------------|
| `factual`     | 90 days                       |
| `procedural`  | 30 days                       |
| `preference`  | 14 days                       |
| `context`     | 7 days                        |

- When an edge''s weight drops below `min_weight`, it transitions to `faded` (same as the base model in §7.1).
- When **all edges connected to a node** are faded, the node itself is automatically archived.
- A node with no edges is archived after the observation window (default: 60 days without traversal).
- Pinned nodes and edges are exempt from both time-decay and traversal-count archiving.

---

#### Comparison

| Behaviour | `evergreen` | `ephemeral` |
|-----------|-------------|-------------|
| Time-based edge decay | Disabled | Enabled |
| Archive trigger | Low traversal count | Edge weight < min_weight |
| Default half-life | N/A | Short (7–90 days by content type) |
| Node archiving | Traversal threshold | All connected edges faded |
| Pin support | Yes | Yes |
| Can restore archived content | Yes | Yes |
| Permanent deletion | Owner only, explicit | Owner only, explicit |

## 8. Data Storage

### 8.1 Local (Phase 1 — CLI)
The CLI stores memories and edges as JSON files under `~/.memtrace/`, validated against `schema/node.v1.json` and `schema/edge.v1.json`.

### 8.2 Server (Phase 2 — API)
The API layer uses **PostgreSQL 17 + pgvector** as the primary data store.

#### Infrastructure
- Container image: `pgvector/pgvector:pg17`
- Managed via `docker-compose.yml` at the repository root
- Schema auto-applied from `schema/sql/001_init.sql` on first `docker compose up`
- Data persisted in Docker volume `memtrace_pgdata`

#### Tables

**`workspaces`**

| Column          | Type          | Notes                                                         |
|-----------------|---------------|---------------------------------------------------------------|
| `id`            | TEXT PK       | e.g. `ws_abc123`                                              |
| `name_zh`       | TEXT          | Bilingual name (zh-TW)                                        |
| `name_en`       | TEXT          | Bilingual name (en)                                           |
| `visibility`    | ENUM          | public / restricted / private                                 |
| `kb_type`       | ENUM          | `evergreen` / `ephemeral` — governs decay behaviour (§7.3)    |
| `owner_id`      | TEXT FK       | → `users.id`                                                  |
| `archive_window_days` | INTEGER | Observation window for traversal-count archiving (default 90) |
| `min_traversals`| INTEGER       | Traversal threshold before archiving (evergreen only, default 1) |
| `created_at`    | TIMESTAMPTZ   |                                                               |
| `updated_at`    | TIMESTAMPTZ   |                                                               |

**`memory_nodes`**

| Column         | Type              | Notes                              |
|----------------|-------------------|------------------------------------|
| `id`           | TEXT PK           | e.g. `mem_abc123`                  |
| `schema_version` | TEXT            | `''1.0''`                            |
| `title_zh`     | TEXT              | Bilingual title (zh-TW)            |
| `title_en`     | TEXT              | Bilingual title (en)               |
| `content_type` | ENUM              | factual / procedural / preference / context |
| `body_zh`      | TEXT              | Bilingual body (zh-TW)             |
| `body_en`      | TEXT              | Bilingual body (en)                |
| `tags`         | TEXT[]            | GIN-indexed                        |
| `visibility`   | ENUM              | public / team / private            |
| `author`       | TEXT              |                                    |
| `created_at`   | TIMESTAMPTZ       |                                    |
| `signature`    | TEXT              | SHA-256 content hash               |
| `source_type`  | ENUM              | human / ai_generated / ai_verified |
| `trust_score`  | NUMERIC(4,3)      | Composite 0–1                      |
| `dim_accuracy` | NUMERIC(4,3)      | Trust dimension                    |
| `dim_freshness`| NUMERIC(4,3)      | Trust dimension                    |
| `dim_utility`  | NUMERIC(4,3)      | Trust dimension                    |
| `dim_author_rep` | NUMERIC(4,3)   | Trust dimension                    |
| `votes_up`     | INTEGER           |                                    |
| `votes_down`   | INTEGER           |                                    |
| `verifications`| INTEGER           |                                    |
| `traversal_count` | INTEGER        | Total times this node was traversed by any actor |
| `unique_traverser_count` | INTEGER | Distinct users or service principals that have traversed this node |
| `status`       | ENUM              | active / archived; archived nodes are hidden from default views |
| `archived_at`  | TIMESTAMPTZ       | Null unless status = ''archived''    |
| `embedding`    | vector(1536)      | ivfflat index, cosine similarity   |

**`edges`**

| Column            | Type          | Notes                          |
|-------------------|---------------|--------------------------------|
| `id`              | TEXT PK       | e.g. `edge_xyz789`             |
| `from_id`         | TEXT FK       | → `memory_nodes.id`            |
| `to_id`           | TEXT FK       | → `memory_nodes.id`            |
| `relation`        | ENUM          | depends_on / extends / related_to / contradicts |
| `weight`          | NUMERIC(6,5)  | 0–1, updated by decay          |
| `status`          | ENUM          | active / faded / pinned; faded edges are hidden from default traversal |
| `co_access_count` | INTEGER       |                                |
| `last_co_accessed`| TIMESTAMPTZ   |                                |
| `half_life_days`  | INTEGER       | Default varies by content_type (see §7.2 Q1) |
| `min_weight`      | NUMERIC(4,3)  | Default 0.1; edge transitions to `faded` when reached (not deleted) |
| `pinned`          | BOOLEAN       | Default false; pinned edges are exempt from decay |
| `traversal_count` | INTEGER       | Total traversals recorded on this edge |
| `rating_sum`      | NUMERIC(10,2) | Sum of all explicit path ratings (for average calculation) |
| `rating_count`    | INTEGER       | Number of explicit ratings submitted |

#### SQL Functions
- `apply_edge_decay()` — recalculates all edge weights; transitions edges to `faded` when weight drops below `min_weight`; never deletes rows; mirrors `packages/core/src/decay.ts`
- `record_co_access(edge_id)` — increments co-access count and applies boost
- `record_traversal(edge_id, actor_id, rating?)` — increments `traversal_count` on both the edge and its endpoint nodes; updates `rating_sum` / `rating_count` if a rating is provided; records the actor for unique traverser tracking

#### Environment Configuration
Connection settings are defined in `.env` (not committed). See `.env.example` for the template.

```
DATABASE_URL=postgresql://<user>:<password>@<host>:<port>/<db>
```

#### Developer Setup
```bash
cp .env.example .env       # fill in credentials
docker compose up -d       # start DB (schema auto-applied)
docker compose down -v     # stop and wipe data
```

## 9. Frontend (UI) Specifications

### 9.1 Multi-Language Support (i18n)
The MemTrace Web UI is fully internationalized to support a global user base and knowledge network.
- **Library**: `react-i18next` with `i18next`.
- **Supported Languages**:
  - Traditional Chinese (`zh-TW` / `zh-Hant`)
  - English (`en`)
- **Scope**: All UI elements including sidebars, headers, tooltips, form labels, and placeholders must utilize the translation engine.
- **Language Selection**: Users can toggle between languages globally, which operates independently from the bilingual content tabs used during memory creation.

### 9.2 Memory Export & Import
Users can export their current working memory to a local file (JSON, Markdown, or plain text) and import an existing archive back into any workspace. Node-level and full-KB export/import are supported. For full specification including export types, filterable scopes, and format details, see **§22 — Knowledge Base Export & Import**.

### 9.3 Manual Memory Node Creation & Editing

#### 9.3.1 Overview
Users can manually create and edit Memory Nodes through a dedicated editor panel within the UI. The editor is accessible from the Graph View (via a toolbar button or double-clicking an empty canvas area) and from the node''s context menu.

#### 9.3.2 Input Formats
Each Memory Node body (`content.body`) supports two input modes, selectable via a tab toggle within the editor:

| Mode       | Description                                                             |
|------------|-------------------------------------------------------------------------|
| `plain`    | Plain text input. Stored as-is in `content.body`. No rendering markup. |
| `markdown` | Markdown input. Rendered as HTML in read view; raw Markdown stored.     |

- The selected mode is persisted in the node as `content.format` field (see §4.1 schema extension below).
- The editor must provide a **live preview** panel when in `markdown` mode.
- Switching modes does **not** automatically convert existing content.

#### 9.3.3 Editor Fields
The creation/edit form exposes the following fields:

| Field           | Required | Notes                                                        |
|-----------------|----------|--------------------------------------------------------------|
| Title (zh-TW)   | Yes      | Maps to `title["zh-TW"]`                                    |
| Title (en)      | Yes      | Maps to `title["en"]`                                       |
| Content Type    | Yes      | Dropdown: `factual / procedural / preference / context`      |
| Body (zh-TW)    | No       | Text or Markdown; maps to `content.body["zh-TW"]`           |
| Body (en)       | No       | Text or Markdown; maps to `content.body["en"]`              |
| Tags            | No       | Comma-separated or tag-chip input; maps to `tags[]`          |
| Visibility      | Yes      | Dropdown: `public / team / private`; default `private`       |

- At least one Body language field must be non-empty to save.
- **Body length guidance**: If the body exceeds 280 characters, the editor displays a soft warning: *"This node may contain more than one idea — consider splitting it."* This is a prompt, not a hard limit. The user may dismiss it.
- The body must not restate information already expressed in the title. The title is the index; the body is the substance.
- `provenance.author` is auto-filled from the current session user.
- `provenance.created_at` is auto-set on first save; `updated_at` is added on edit (see §10.1).
- `provenance.signature` (SHA-256) is recomputed on every save.
- `trust` fields are initialized to defaults on creation and not user-editable.

#### 9.3.4 Creating an Edge (Association) from the Editor
After saving a node, the editor **immediately opens the Edge creation sub-panel** by default. A node without any edges is visually flagged in the Graph View with an indicator (e.g. a hollow ring instead of a filled node) to signal that it is not yet connected. Users can also initiate edge creation by dragging from one node''s handle to another in the Graph View.

Edges are not optional — they are what give a node its meaning in context. The editor should make edge creation the natural next step after every save, not an afterthought.

Edge creation fields:

| Field         | Required | Notes                                                           |
|---------------|----------|-----------------------------------------------------------------|
| Target Node   | Yes      | Searchable dropdown of existing node titles                     |
| Relation Type | Yes      | `depends_on / extends / related_to / contradicts`               |
| Initial Weight| No       | Slider 0.1–1.0; default `1.0`                                   |
| Half-life     | No       | Integer days; default `30`                                      |

- Direction is always **from the current node → target node**.
- Duplicate edges (same `from`, `to`, `relation`) are rejected with a validation error.
- On creation, `co_access_count` is set to `0` and `last_co_accessed` to the current timestamp.

#### 9.3.5 Editing an Existing Node
- Double-clicking a node in the Graph View opens the editor pre-filled with its current data.
- All fields except `id`, `schema_version`, and `provenance.created_at` are editable.
- Editing a node''s content triggers a SHA-256 signature recompute on save.
- Existing edges attached to the node are listed in a collapsible **"Associations"** section within the editor, where each edge''s relation type and weight are visible and editable inline.

#### 9.3.6 Archiving and Deletion

**Archive** (default action):
- A node can be **archived** from its context menu (right-click on Graph View) or from the editor toolbar.
- Archived nodes are hidden from the default Graph View and search results but are never destroyed.
- All edges connected to an archived node are automatically faded (not deleted).
- Archived nodes appear in a dedicated **"Archive"** view, accessible from the workspace sidebar.
- An archived node can be restored at any time by the workspace owner or the node''s original author.

**Permanent deletion** (destructive, requires confirmation):
- Permanent deletion is only available to workspace **owners**.
- A two-step confirmation dialog is required, listing the count of edges and any dependant nodes that reference this node.
- Permanently deleted nodes and their edges are removed from the database. This action is irreversible.
- Permanent deletion should be reserved for nodes created in error (e.g. duplicate, test data), not for nodes that have simply become irrelevant over time — archiving is preferred for the latter case.

## 11. Document-Based Knowledge Base Bootstrapping

### 11.1 Starting a Knowledge Base from a Document

A Knowledge Base may be initialized from one or more source materials instead of being built node-by-node. The AI Extraction pipeline accepts a wide range of input formats — not limited to formal documents.

| Format | Extension(s) | Preprocessing | Notes |
|--------|-------------|---------------|-------|
| Markdown | `.md` | — | Headings used as structural hints for node boundaries |
| Plain text | `.txt` | — | Paragraph breaks used as structural hints |
| PDF | `.pdf` | Text layer extraction | Scanned PDFs require OCR (Phase 2+) |
| Word | `.docx` | Heading style extraction | Heading levels used as structural hints |
| Presentation | `.pptx`, `.key` | Slide-per-slide text extraction | Each slide treated as a candidate segment |
| Meeting notes / transcripts | `.txt`, `.md`, `.vtt`, `.srt` | Speaker turn segmentation | Action items and decisions prioritised as `procedural` / `context` nodes |
| Video | `.mp4`, `.mov`, URL | Transcription via provider speech-to-text (e.g. Whisper) | Transcript is extracted first, then processed as text |
| Audio | `.mp3`, `.m4a`, `.wav` | Transcription via provider speech-to-text | Same pipeline as video |
| Web page / URL | `https://...` | HTML → Markdown conversion (readability extraction) | Requires the server to fetch and parse the URL |

**Phase 1 scope**: Markdown and plain text only.  
**Phase 2 scope**: PDF, Word, PPTX, meeting notes/VTT/SRT.  
**Phase 3 scope**: Video, audio, and URL ingestion (depends on provider support for transcription).

All ingested materials are stored as **Source Document** references on the Knowledge Base and retained for traceability. Multiple materials can be ingested into the same Knowledge Base sequentially.

### 11.2 AI Provider & API Key

MemTrace does **not** operate its own AI inference service. All AI features (node extraction, classification, title generation) are powered by third-party LLM providers configured by the user.

#### 11.2.1 API Key Management

- Users must supply their own API key for each AI provider they intend to use.
- API keys are stored **locally only** — in `~/.memtrace/config.json` (CLI) or in the browser''s `localStorage` (UI). Keys are never transmitted to or stored on any MemTrace server.
- A key must be present and valid before any AI feature can be invoked. If no key is configured, AI features are disabled and the user is prompted to add one via settings.
- Keys are associated with a provider identifier (e.g. `openai`, `anthropic`) and can be updated or deleted at any time from the settings panel.

#### 11.2.2 Supported Providers

The following providers are supported in the official release:

| Provider | Identifier | Chat model (default) | Embedding model | Embedding Dim |
|----------|------------|----------------------|-----------------|---------------|
| OpenAI | `openai` | `gpt-4o-mini` | `text-embedding-3-small` | 1536 |
| Anthropic | `anthropic` | `claude-haiku-4-5-20251001` | `voyage-3-lite` | 1024 |
| **Google Gemini** | `gemini` | `gemini-2.0-flash` | `text-embedding-004` | **768** |

> **Embedding dimension note**: Different providers produce vectors of different dimensions. A workspace''s embedding dimension is fixed at creation time based on the provider chosen (stored in `workspaces.embedding_provider` and `workspaces.embedding_dim`). Nodes embedded with different models cannot be compared by cosine similarity.

The Gemini provider is implemented as a built-in `AIProvider` calling the Google Generative Language API. Users supply a personal Gemini API key (`AIza...`) via Settings → AI Provider, stored encrypted under `provider = ''gemini''` in `user_ai_keys`.

#### 11.2.3 Community-Contributed Providers

MemTrace is open source. The AI call path is built around a provider `Protocol` (`packages/api/core/ai.py`) that any contributor can implement to add support for additional models or services — including:

- Other commercial APIs (Gemini, Mistral, Cohere, etc.)
- OpenAI-compatible self-hosted endpoints (Ollama, vLLM, LM Studio, Groq)
- Private or fine-tuned models exposed over HTTP

**To add a provider**, implement the `AIProvider` protocol:

```python
# packages/api/core/ai.py

class AIProvider(Protocol):
    name: str                          # identifier used in DB and UI
    default_chat_model: str
    default_embedding_model: str

    async def chat(
        self,
        api_key: str,
        model: str,
        messages: list[dict],
        max_tokens: int,
        temperature: float,
    ) -> tuple[str, int]: ...          # (response_text, tokens_used)

    async def embed(
        self,
        api_key: str,
        model: str,
        text: str,
    ) -> tuple[list[float], int]: ... # (vector, tokens_used)
```

Register the implementation in `PROVIDER_REGISTRY` at the bottom of `core/ai.py`. No changes to routers, models, or the database schema are needed.

> **Embedding dimension note**: Different models produce vectors of different dimensions. A workspace''s embedding dimension is fixed at creation time based on the provider chosen. Nodes embedded with different models cannot be compared by cosine similarity. Contributors adding embedding-capable providers must document the output dimension of their model.


#### 11.2.5 Config Schema (CLI)

API keys are stored in `~/.memtrace/config.json`:

```json
{
  "ai": {
    "provider": "openai",
    "api_keys": {
      "openai": "<user-supplied key>",
      "anthropic": "<user-supplied key>"
    }
  }
}
```

Keys in this file must be protected with user-only read permissions (`chmod 600`).

#### 11.2.6 Failure Handling

If an AI call fails due to an invalid key, quota exhaustion, or provider error, the ingestion step is aborted. No candidate nodes are generated. The user is shown the provider error message and prompted to check their API key in settings.

---

### 11.3 AI-Driven Node Extraction

When a material is ingested via `ingest` (CLI) or the Upload panel (UI), the system invokes an AI Extraction step using the configured provider and API key (see §11.2).

#### Node Minimization Principle

> **The AI must produce the smallest possible nodes and the richest possible set of edges.**

This is the single most important constraint governing extraction. It has two parts:

**Minimize nodes** — A candidate node should contain exactly one discrete idea, fact, procedure step, or context signal. If a segment of the source material contains two separable ideas, the AI must split them into two nodes. Nodes must not serve as containers for related content — that is what edges are for.

| Too large ❌ | Minimal ✓ |
|---|---|
| "The decay formula is `w(t) = w₀ × 0.5^(d/h)`. Co-access boosts weight by +0.10 to +0.30 depending on relation type." | Node A: "Edge Decay Formula" — the formula only. Node B: "Co-Access Weight Boost" — boost values only. Edge A→B: `related_to` |
| "To set up the project: install Node.js, then Python, then run `npm install`." | Node A: "Install Node.js". Node B: "Install Python". Node C: "Run npm install". Edges: A→B `depends_on`, B→C `depends_on` |

**Maximize edges** — After splitting, the AI must identify and propose all meaningful relationships between the resulting nodes. An extracted node with no proposed edges is a signal that the split was too aggressive or the surrounding context was not analysed thoroughly enough.

---

The extraction step:

1. **Segments** the material into candidate chunks based on structural cues (headings, paragraphs, slide boundaries, speaker turns, topic shifts).
2. **Splits** each chunk into minimal atomic units, applying the Node Minimization Principle above.
3. **Classifies** each unit into a Content Type (`factual`, `procedural`, `preference`, `context`).
4. **Generates** a bilingual title (zh-TW + en) and a concise body for each candidate node. The body must not restate what the title already expresses.
5. **Proposes** candidate Edges between all extracted nodes, selecting the most specific relation type available (`depends_on` > `extends` > `related_to` > `contradicts`). Cross-segment edges are explicitly encouraged.

#### 11.3.1 Review Step (required before commit)

All AI-extracted candidates enter a **Review Queue** and are never committed automatically. The user must:

- **Accept** — commit the node as-is.
- **Edit then Accept** — modify title, body, type, or tags before committing.
- **Reject** — discard the candidate; it is not saved.

Bulk accept/reject is allowed. At least one node must be accepted before the review step can be closed.

#### 11.3.2 Extraction Metadata

Each node committed from AI extraction carries:

```json
{
  "provenance": {
    "source_type": "ai_generated",
    "source_document": "<filename or SHA-256 of the source file>",
    "extraction_model": "<model identifier>"
  }
}
```

`source_document` and `extraction_model` are appended to the `provenance` object (see §10.2).

#### 11.3.3 Trust Defaults for AI-Extracted Nodes

| Dimension | Default |
|-----------|---------|
| `accuracy` | 0.5 (unverified; boosted when a human accepts without edits) |
| `freshness` | 1.0 |
| `utility` | 0.5 |
| `author_rep` | 0.5 |
| `source_type` | `ai_generated` → `ai_verified` after human acceptance |

When a human edits a candidate before accepting, `source_type` is set to `human`.

### 11.3.4 Extraction Prompt Design

The AI provider receives a structured prompt that includes:

1. **System role**:
   > "You are a knowledge graph extraction assistant. Your goal is to convert source material into the smallest possible set of atomic Memory Nodes connected by the richest possible set of typed edges. A node must contain exactly one idea — if you find two ideas in a segment, split them. An edge is not optional: every node you produce must have at least one proposed edge to another node in the output, unless it is the only node extracted. The design goal is that a human or AI agent can reach any answer by following the shortest possible path through the graph."

2. **Segment text**: The raw text of the chunk being processed (or transcript segment, slide text, etc.).
3. **Workspace context**: The `kb_type` (`evergreen` or `ephemeral`), existing node titles in the workspace (to avoid duplication), and the edge type vocabulary (`depends_on`, `extends`, `related_to`, `contradicts`).
4. **Quality constraints** (included in the prompt):
   - A node body must not repeat information already expressed in the title.
   - A node body should be as short as possible while remaining self-contained.
   - Prefer `depends_on` and `extends` over `related_to` when a more specific relationship can be inferred.
   - If two candidate nodes could be merged without losing specificity, merge them.
5. **Output schema**: A JSON array of candidate nodes, each with `title_zh`, `title_en`, `content_type`, `body_zh`, `body_en`, `tags`, and a `suggested_edges[]` array referencing other nodes in the same output by their array index.

The prompt is sent once per segment. The provider must return a valid JSON array. If it does not, the segment is flagged as an extraction failure and shown to the user for manual handling.

### 11.4 Copying a Node to Another Knowledge Base

Any individual Memory Node can be copied to a different Knowledge Base. Edges are **not** copied — only the node''s content, metadata, and trust snapshot are transferred.

#### 11.4.1 Behavior

- The copied node receives a **new `id`** in the target Knowledge Base.
- `provenance.created_at` is set to the time of the copy operation.
- `provenance.updated_at` is absent (the copy is treated as a fresh creation).
- A `provenance.copied_from` field records the original node''s `id` and source workspace for traceability.
- The original node and its Edges are unaffected.
- The `signature` (SHA-256) is recomputed from the copied content in the target workspace context.

#### 11.4.2 Trust on Copy

Trust scores are carried over as a snapshot. They are not linked — subsequent votes or verifications in either workspace do not affect the other copy.

#### 11.4.3 Visibility on Copy

The copied node''s `visibility` defaults to `private` in the target Knowledge Base, regardless of its visibility in the source. The user may change it after copying.

## 12. Knowledge Base Sharing Levels

### 12.1 Four-Tier Visibility System

Each Knowledge Base has a **visibility** setting that controls who can discover and access it. This is independent from the `visibility` field on individual Memory Nodes. **Visibility is set at creation time and cannot be changed thereafter.**

| Tier | Identifier | Chinese | Description |
|------|------------|---------|-------------|
| 全公開 | `public` | 公開 | Discoverable and readable by anyone, including unauthenticated users. |
| 有條件公開 | `conditional_public` | 有條件公開 | Anyone can discover the KB and submit a **join request** to admins. Admission requires explicit admin approval. |
| 限制公開 | `restricted` | 限制公開 | The KB is **invisible** to non-members through search or discovery. Access requires explicit invitation from an admin. |
| 私有 | `private` | 私有 | Completely inaccessible to all other users. Invitations cannot be issued. |

> **Design constraint**: The visibility selector must be shown clearly during workspace creation, each tier described inline, and the user must explicitly confirm their choice. The field is immutable — any `PATCH /workspaces/{ws_id}` request that includes `visibility` returns `400 Immutable field: visibility`.

### 12.2 Behavior by Tier

#### `public`
- Appears in global search and discovery feeds, accessible without login.
- Any authenticated user can read all nodes whose node-level `visibility` is `public`.
- Nodes with node-level `visibility: team` or `private` remain hidden from non-members.
- Anyone can copy `public`-visibility nodes to their own Knowledge Base.

#### `conditional_public`
- Appears in global search and discovery. KB name, description, and public-facing summary are readable by anyone.
- **Graph Preview Mode**: Non-members (unauthenticated or not-yet-approved) may view the **knowledge graph topology** (node positions, edge connections, relation type labels) but **cannot access node content**. Clicking any node displays a locked placeholder instead of the node body.
- Node titles are **obfuscated** in graph preview: only the `content_type` badge and an anonymized node ID are shown. Titles and body content are not transmitted to the client.
- The graph preview is read-only and non-interactive beyond panning and zooming.
- Any authenticated user may submit a join request (`POST /workspaces/{ws_id}/join-requests`).
- An admin must explicitly approve or reject each request.
- Approved users are added as `viewer` by default (configurable per request) and gain full node content access.
- Rejected applicants may not reapply for 7 days.

#### `restricted`
- Does **not** appear in global search or discovery. The KB''s existence is not disclosed to non-members through any API.
- Access is granted via explicit admin invitation only (`POST /workspaces/{ws_id}/invites`).
- Invited users are added with the role specified in the invite token.

#### `private`
- Completely hidden from all other users.
- **Invitations cannot be issued.** No non-owner user may be added to the workspace.
- Does not appear in any listing or search result.

### 12.3 Workspace Roles & Permissions

To firmly establish the product''s core focus on the **Knowledge Owner**, access to knowledge within a workspace (particularly `conditional_public` and `restricted` workspaces) is strictly role-based. Knowledge sharing is the primary goal, but the author has the ultimate choice regarding who can extract raw facts or modify the structure.

| Role | Permissions |
|------|-------------|
| **`viewer`** (檢視者) | Can view the knowledge graph topology and node titles, but **cannot access individual node body content or details**. This allows viewers to understand the shape of the knowledge and its connections without allowing data extraction. |
| **`editor`** (編輯者) | Can view both the topology and full node details. Can propose edits to nodes, create new nodes, and establish edges. |
| **`admin`** (管理者) | Retains full ownership features. Can view and edit everything, configure the Knowledge Base, manage join requests, and invite users while assigning roles. |

A workspace may have **multiple admins**. The original creator is automatically assigned the `admin` role and cannot demote themselves unless another admin exists. Any existing admin may promote another member to admin.

```sql
-- member_role ENUM definition:
ALTER TYPE member_role ADD VALUE IF NOT EXISTS ''admin'';
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_90397c97', '1.0', 'ws_spec0001', '來源文件：FEATURE_PLAN.md', 'Source: FEATURE_PLAN.md', 'source_document', 'plain', '# MemTrace Feature Plan — Task Breakdown

> 產出日期：2026-04-23
> 作者：Product Planning Session
> 說明：本文件為功能計畫的開發任務拆解，供開發人員執行使用。
> 依功能群組（A–H）分類，每項任務標注所屬層（DB / API / UI / MCP / CLI / Core / Scheduler）。

---

## 目錄

- [A. 知識庫健康度與有效性驗證](#a-知識庫健康度與有效性驗證)
- [B. 知識主權與存取控制](#b-知識主權與存取控制)
- [C. 知識攝入與 AI 提案流程](#c-知識攝入與-ai-提案流程)
- [D. 圖譜操作與知識流動](#d-圖譜操作與知識流動)
- [E. MCP / AI Agent 生態](#e-mcp--ai-agent-生態)
- [F. 匯出匯入與可攜性](#f-匯出匯入與可攜性)
- [G. 安全性與系統強健度](#g-安全性與系統強健度)
- [H. 規格書知識庫化](#h-規格書知識庫化)

---

## A. 知識庫健康度與有效性驗證

> 核心目標：知識的有效性可被驗證——包含 token 效率與知識可被實際使用兩個維度。
> 注意：健康指標依 kb_type 不同而異。evergreen KB 關注連結性；operational KB 關注活性。

---

### A1 — KB Analytics Dashboard

**目標**：每個知識庫提供健康概覽頁，指標依 kb_type 切換。

| 層 | 任務 |
|----|------|
| API | `GET /workspaces/{ws_id}/analytics` — 回傳健康摘要，包含：總節點數、活躍邊數、孤立節點數、平均 trust_score、faded 邊比例、最近 30 天 traversal 總次數、top 5 最常走節點 |
| API | 依 kb_type 切換指標：evergreen 回傳「連結性指標」（平均 edge per node、最大孤立子圖大小）；operational 回傳「活性指標」（未被 traverse 節點比例、平均 traversal 間隔天數） |
| UI | 知識庫 Analytics 頁面，含摘要卡片 + 30 天趨勢折線圖（traversal count） |
| UI | kb_type 感知的健康警示：evergreen 顯示「X 個孤立節點需要連結」；operational 顯示「X 個節點超過 N 天未被使用」 |

**依賴**：無（可獨立開發，API 查詢現有資料）

---

### A2 — Token Efficiency Report

**目標**：量化 KB 結構化設計對 AI agent 查詢效率的貢獻，作為產品價值的可視化依據。

| 層 | 任務 |
|----|------|
| API | `GET /workspaces/{ws_id}/analytics/token-efficiency` — 計算：(1) 本月 MCP query 平均回傳 token 數；(2) 估算等效全文讀取 token 數（以全部節點 body 加總估算）；(3) 節省比例 |
| API | 記錄每次 MCP tool call 的回傳 token 估算值至新增的 `mcp_query_logs` 資料表 |
| DB | 新增 `mcp_query_logs` 資料表：`id, workspace_id, tool_name, query_text, result_node_count, estimated_tokens, created_at` |
| UI | Analytics 頁面內嵌 Token Efficiency 區塊：顯示本月節省 token 數、節省比例、歷史趨勢 |

**依賴**：E1（MCP 寫入工具）上線後才有完整 MCP 使用資料；初期可只統計讀取工具

---

### A3 — Node Validity Heatmap（雙模式）

**目標**：在 GraphView 疊加顏色層，依 kb_type 切換不同健康維度。

| 層 | 任務 |
|----|------|
| API | `GET /workspaces/{ws_id}/nodes/health-scores` — 回傳所有節點的健康分數陣列：`{ node_id, score, mode }` |
| API | evergreen 模式：score = edge_count（連結越多越健康）；operational 模式：score = days_since_last_traversal 反轉（越近越健康） |
| UI | GraphView 新增 "Health Mode" 切換按鈕 |
| UI | 依 score 對節點上色：綠（健康）→ 黃（待關注）→ 紅（問題節點） |
| UI | 節點 hover tooltip 顯示健康分數與原因文字 |

**依賴**：A1（共用 analytics API 基礎）

---

### A4 — Faded / Orphan Node 管理頁

**目標**：集中管理需要人工介入的問題節點。

| 層 | 任務 |
|----|------|
| API | `GET /workspaces/{ws_id}/nodes?filter=orphan` — 回傳無任何 edge 的節點清單 |
| API | `GET /workspaces/{ws_id}/nodes?filter=faded` — 回傳所有相連 edge 皆為 faded 狀態的節點 |
| API | `GET /workspaces/{ws_id}/nodes?filter=never_traversed` — 回傳 traversal_count = 0 的節點（operational KB 使用） |
| API | `POST /workspaces/{ws_id}/nodes/bulk-archive` — 批次歸檔，接收 `{ node_ids: [] }` |
| UI | 獨立「節點管理」頁面，分三個 Tab：孤立節點 / Faded / 從未被使用 |
| UI | 每個 Tab 支援全選、批次歸檔、單節點跳轉至 Editor |

**依賴**：D4（節點歸檔排程）需先上線，faded 資料才有意義

---

### A5 — Trust Score 維度展示與自動更新

**目標**：在 NodeEditor 展示 trust score 四個維度，並補上缺失的自動更新邏輯。

| 層 | 任務 |
|----|------|
| API | 節點被 traverse 時（`POST /nodes/{id}/traverse`）自動計算並更新 `dim_utility`：`utility = min(1.0, traversal_count / 100)` |
| API | 節點被人工編輯時更新 `dim_freshness`：`freshness = 1.0`，之後依 `updated_at` 隨時間線性衰減 |
| API | 節點被接受自 Review Queue 且 source 為 `ai_verified` 時，`dim_accuracy` 初始值設為 0.8；人工建立的節點設為 1.0 |
| UI | NodeEditor trust_score 區塊展開為四個維度進度條：accuracy / freshness / utility / author_rep |
| UI | 每個維度加 tooltip 說明計算依據 |

**依賴**：無

---

### A6 — 節點人工有效性確認（Manual Validity Stamp）

**目標**：讓人或 AI 主動聲明節點在特定日期仍有效，不依賴 traversal 資料。

| 層 | 任務 |
|----|------|
| DB | `memory_nodes` 新增欄位：`validity_confirmed_at TIMESTAMPTZ`、`validity_confirmed_by VARCHAR`（user_id 或 `ai:{model}`） |
| API | `POST /nodes/{id}/confirm-validity` — 記錄 confirmed_at 與 confirmed_by；限 editor 以上角色 |
| API | `GET /workspaces/{ws_id}/nodes` 回傳中加入 `validity_confirmed_at` 欄位 |
| UI | NodeEditor 加入「確認有效」按鈕，點擊後顯示「最後確認：YYYY-MM-DD by {user}」 |
| UI | 超過 90 天未確認的節點（operational KB）顯示黃色警示標籤 |
| MCP | `confirm_node_validity(node_id)` 工具，供 AI agent 在使用節點後主動聲明有效 |

**依賴**：E1（MCP 工具）

---

## B. 知識主權與存取控制

> 核心目標：知識擁有者對知識的分享方式有完整主權。

---

### B1 — RBAC 修補

**目標**：修正現有 Admin 權限缺漏，實作 Viewer 內容過濾。

| 層 | 任務 |
|----|------|
| API | 修正 `_require_ws_access(write=True)` — 同時允許 `editor` 與 `admin` 角色通過，目前只允許 `editor` |
| API | `GET /workspaces/{ws_id}/nodes` 及 `GET /nodes/{id}`：若請求者角色為 `viewer`，回傳前清空 `body_zh`、`body_en`，並加入 `content_stripped: true` 旗標 |
| UI | NodeEditor：偵測 `content_stripped: true` 時，顯示鎖定狀態提示「詳細內容僅限編輯者或管理員存取」 |
| UI | Viewer 角色隱藏：編輯按鈕、AI Restructure 按鈕、刪除按鈕 |

**依賴**：無（修補現有功能）

---

### B2 — Workspace 成員管理

**目標**：完整的成員管理 API 與 UI。

| 層 | 任務 |
|----|------|
| API | `GET /workspaces/{ws_id}/members` — 列出成員清單（含 user_id、email、role、joined_at） |
| API | `PUT /workspaces/{ws_id}/members/{user_id}` — 變更角色（限 admin；不能降低自己的角色） |
| API | `DELETE /workspaces/{ws_id}/members/{user_id}` — 移除成員（限 admin；不能移除自己） |
| UI | Workspace Settings 頁新增 Members Tab |
| UI | 成員清單表格，含角色 badge、變更角色下拉、移除按鈕 |
| UI | 角色變更與移除操作需二次確認 dialog |

**依賴**：無

---

### B3 — Workspace 邀請連結

**目標**：產生帶過期時間的邀請連結，支援撤銷。

| 層 | 任務 |
|----|------|
| API | `POST /workspaces/{ws_id}/invites` — 建立邀請：`{ role, expires_in_days }` → 回傳 `{ token, invite_url, expires_at }` |
| API | `GET /workspaces/{ws_id}/invites` — 列出有效邀請清單 |
| API | `DELETE /workspaces/{ws_id}/invites/{token}` — 撤銷邀請 |
| API | `POST /invites/{token}/accept` — 用邀請連結加入（驗證未過期、workspace 仍存在）；自動以指定 role 加入成員 |
| UI | Members Tab 新增「建立邀請連結」按鈕，選擇角色與過期天數 |
| UI | 產生後顯示可複製連結，列出目前有效邀請（含過期時間、撤銷按鈕） |
| Scheduler | 定期清理已過期的 `workspace_invites` 記錄（每日執行） |

**依賴**：B2（共用 Members Tab）

---

### B4 — Conditional Public 申請加入流程

**目標**：訪客可申請加入 conditional_public KB，Admin 可核准或拒絕。

| 層 | 任務 |
|----|------|
| DB | 確認 `join_requests` 資料表存在，若無則新增：`id, workspace_id, user_id, status(pending/approved/rejected), cooldown_until, created_at, reviewed_at` |
| API | `POST /workspaces/{ws_id}/join-requests` — 送出申請（限未加入的使用者；冷卻期內不可重複申請） |
| API | `GET /workspaces/{ws_id}/join-requests` — 列出待審申請（限 admin） |
| API | `POST /workspaces/{ws_id}/join-requests/{id}/approve` — 核准，自動以 viewer 角色加入成員 |
| API | `POST /workspaces/{ws_id}/join-requests/{id}/reject` — 拒絕，記錄 `cooldown_until = now + 7 days` |
| UI | 公開 KB 目錄頁（或 Graph Preview 頁）：顯示「申請存取」按鈕 |
| UI | Admin 後台新增「加入申請」Tab，列出待審清單，操作核准/拒絕 |

**依賴**：B5（Graph Preview，申請流程的入口）

---

### B5 — Graph Preview Mode

**目標**：conditional_public KB 對未授權者展示匿名化圖譜結構。

| 層 | 任務 |
|----|------|
| API | `GET /workspaces/{ws_id}/graph?preview=true` — 僅限 conditional_public KB；回傳節點以 `node_preview_N` 替換真實 ID，移除 title、body、tags；保留 edge 類型與節點位置（若有） |
| API | 未登入或無存取權的請求，自動以 preview 模式回應 |
| UI | 訪問 conditional_public KB 且無存取權時，渲染預覽版 GraphView（2D），節點顯示為匿名形狀 |
| UI | 頁面頂部 Banner：「此知識庫為條件開放存取，圖譜結構僅供預覽」+ 申請存取按鈕 |

**依賴**：無

---

### B6 — API Key Scope 強制驗證

**目標**：落實 API Key 的 scope 邊界，防止越權呼叫。

| 層 | 任務 |
|----|------|
| API | 修改 `deps.py` 的 `verify_api_key()` — 加入 `required_scope` 參數，驗證 key 的 `scopes` 欄位包含該 scope |
| API | 各 router 標注所需 scope：`kb:read`（讀取節點/邊）、`kb:write`（建立/修改節點）、`node:traverse`（記錄 traversal）、`node:rate`（評分 edge） |
| API | scope 驗證失敗時回傳 `403 Forbidden`，說明缺少的 scope |

**依賴**：無

---

## C. 知識攝入與 AI 提案流程

> 核心目標：將大文件原子化為最小節點，透過 Review Queue 確保人工把關。

---

### C1 — File Ingestion 完整流程

**目標**：支援 .md/.txt/.pdf/.docx 上傳，觸發 AI 擷取並進入 Review Queue。

| 層 | 任務 |
|----|------|
| API | `POST /workspaces/{ws_id}/ingest` — 接收檔案上傳（multipart），支援 .md/.txt/.pdf/.docx |
| API | 後端解析管線：.md/.txt 直接讀取；.pdf 使用 pdfplumber 擷取文字；.docx 使用 python-docx |
| API | 呼叫 AI extraction（依使用者設定的 provider/model），依 Node Minimization Principle 拆解為候選節點 |
| API | 批次寫入 `review_queue`，記錄來源檔案名稱與段落位置 |
| API | `GET /workspaces/{ws_id}/ingest/logs` — 列出攝入歷史（狀態、節點數、時間） |
| UI | 拖拉上傳元件，支援多檔同時上傳 |
| UI | 上傳後顯示解析進度（Polling ingest logs） |
| UI | 解析完成後跳轉至 Review Queue 並 highlight 新增的候選節點 |

**依賴**：使用者需已設定 AI provider key

---

### C2 — URL 抓取攝入

**目標**：輸入網址，後端抓取內容後進入同一套攝入流程。

| 層 | 任務 |
|----|------|
| API | `POST /workspaces/{ws_id}/ingest/url` — 接收 `{ url }` |
| API | 後端使用 httpx + BeautifulSoup 抓取網頁內文，過濾導覽列/廣告等雜訊，擷取主要 article 內容 |
| API | 後續流程與 C1 相同（AI extraction → review_queue） |
| UI | 攝入頁面新增「從 URL 攝入」Tab，輸入欄位 + 送出按鈕 |

**依賴**：C1（共用後端 extraction 管線）

---

### C3 — AI Chat Panel

**目標**：獨立 AI 對話面板，基於當前 KB graph 上下文回答，對話中可產生節點/邊提案。

| 層 | 任務 |
|----|------|
| API | `POST /workspaces/{ws_id}/chat` — 接收對話訊息，自動 semantic search 取得相關節點作為 context，呼叫 AI 回答 |
| API | 支援 `allow_edits: true` 參數：AI 可在回答中附帶 node/edge 提案，自動寫入 review_queue |
| API | 支援 `cross_kb: [ws_id_2, ...]` 參數：允許跨關聯 KB 取得 context（依 KB Association 設定） |
| UI | 右側滑出式 Chat Panel，可在不離開 GraphView 的情況下使用 |
| UI | 對話訊息中渲染 Inline 提案卡片（顯示提案的 node title + body 預覽，操作：Accept / Edit / Reject） |
| UI | Accept 操作直接呼叫 Review Queue accept API，不需跳轉頁面 |

**依賴**：D5（Semantic Search）提供 context 取得能力；B4 KB Association 提供跨庫邊界

---

### C4 — Source Document 保留

**目標**：攝入後保留原始文件供溯源，從預設圖譜隱藏。

| 層 | 任務 |
|----|------|
| DB | 確認 `content_type` ENUM 包含 `source_document`；若不存在則 migration 新增 |
| API | 攝入成功後建立一個 `content_type: source_document` 節點，body 存放原始完整文字，加入 `source_file` 欄位記錄原始檔名 |
| API | `GET /workspaces/{ws_id}/nodes` 預設過濾掉 `source_document` 節點；加入 `?include_source=true` 參數可包含 |
| API | Graph endpoint 同樣預設排除 `source_document` 節點 |
| UI | Review Queue 每筆候選節點加入「查看原始段落」連結，可 modal 展開 source document 的對應段落 |

**依賴**：C1

---

### C5 — AI Reviewer Profile

**目標**：可設定自動化審核規則，減少人工逐筆審核的負擔。

| 層 | 任務 |
|----|------|
| DB | `review_queue` 新增 `confidence_score FLOAT` 欄位，由 AI extraction 時填入 |
| API | AI extraction prompt 要求回傳每個候選節點的 confidence score（0–1） |
| API | `GET/POST /workspaces/{ws_id}/reviewer-profiles` — 管理自動審核規則，欄位：`{ auto_accept_threshold, auto_reject_threshold, require_human_review_for_types }` |
| API | 攝入後根據 reviewer profile 自動處理：confidence > `auto_accept_threshold` → 直接 accept；confidence < `auto_reject_threshold` → 直接 reject；其餘進入人工佇列 |
| UI | Workspace Settings 新增「AI Reviewer」Tab，設定閾值滑桿與例外條件 |

**依賴**：C1

---

## D. 圖譜操作與知識流動

---

### D1 — Copy Node（跨知識庫）

**目標**：將節點複製到其他 KB，記錄來源追溯。

| 層 | 任務 |
|----|------|
| API | `POST /workspaces/{target_ws_id}/nodes` 支援 `copied_from: { node_id, workspace_id }` 欄位（DB 欄位已存在） |
| API | 複製時：複製 title_zh/en、body_zh/en、content_type、tags；不複製 edges；記錄 copied_from |
| API | 驗證：使用者對來源 KB 需有 viewer 以上權限，對目標 KB 需有 editor 以上權限 |
| CLI | `memtrace copy-node <node-id> --to <workspace-id>` 指令 |
| UI | NodeEditor 加入「複製到其他知識庫」選項（下拉選擇目標 KB） |

**依賴**：無

---

### D2 — Edge 視覺化強化

**目標**：Edge 的 weight 與狀態在圖譜中有視覺表達。

| 層 | 任務 |
|----|------|
| UI | GraphView 2D：edge 線條粗細對應 weight（weight=1.0 → 3px；weight=0.1 → 0.5px） |
| UI | GraphView 2D：faded edge（status=''faded''）使用虛線 + 低透明度呈現 |
| UI | Edge hover tooltip 顯示：relation type、weight、half_life_days、co_access_count、last_traversed_at |
| UI | Co-access boost 觸發時，相關 edge 短暫高亮動畫（0.5 秒黃色 glow） |
| UI | GraphView 3D 同步套用上述視覺規則 |

**依賴**：無

---

### D3 — KB Association 管理 UI

**目標**：完整的跨知識庫關聯設定介面（API 已存在，補 UI）。

| 層 | 任務 |
|----|------|
| UI | Workspace Settings 新增「關聯知識庫」Tab |
| UI | 列出目前已關聯的 KB（名稱、visibility、加入日期） |
| UI | 新增關聯：搜尋並選擇目標 KB（限 public 或已有存取權的 KB） |
| UI | 移除關聯按鈕（含確認 dialog） |
| UI | 關聯 KB 在 AI Chat 中可選擇是否納入 cross-KB context |

**依賴**：C3（AI Chat 使用 KB Association 邊界）

---

### D4 — 節點歸檔排程完整化

**目標**：補上缺失的排程呼叫，完整實作 decay → archive 生命週期。

| 層 | 任務 |
|----|------|
| Scheduler | 補上 `apply_node_archiving()` 排程呼叫（每日 UTC 02:00，函式已存在但未被觸發） |
| Scheduler | Ephemeral KB 的 edge decay 排程改為每 1 小時觸發（目前為每日） |
| API | `POST /nodes/{id}/archive` — 手動歸檔（限 editor 以上） |
| API | `POST /nodes/{id}/restore` — 從歸檔還原（限 editor 以上） |
| API | `GET /workspaces/{ws_id}/nodes?filter=archived` — 列出已歸檔節點 |
| UI | NodeEditor 加入「歸檔」按鈕（已歸檔節點顯示「還原」按鈕） |
| UI | GraphView 加入「顯示已歸檔節點」切換開關（預設隱藏） |

**依賴**：無

---

### D5 — Semantic Search

**目標**：節點建立/更新時自動生成 embedding，UI 支援語意搜尋。

| 層 | 任務 |
|----|------|
| API | 節點建立（`POST /nodes`）與更新（`PATCH /nodes/{id}`）後，非同步呼叫 embedding API，將向量存入 `memory_nodes.embedding` 欄位 |
| API | `POST /workspaces/{ws_id}/nodes/search` 支援 `mode` 參數：`keyword`（現有）或 `semantic`（新增，使用 pgvector cosine similarity） |
| API | Semantic search：將 query 轉為 embedding，比對所有節點向量，回傳 top-K 相似節點（含相似度分數） |
| UI | 搜尋列加入 Keyword / Semantic 模式切換 toggle |
| UI | Semantic 搜尋結果卡片顯示相似度分數（百分比） |

**依賴**：使用者需已設定 AI provider key（embedding model）

---

## E. MCP / AI Agent 生態

> 核心目標：讓 AI agent 可以用最少 token 走到答案，同時能主動寫入知識。

---

### E1 — MCP 寫入工具

**目標**：AI agent 可透過 MCP 建立和更新知識節點。

| 層 | 任務 |
|----|------|
| MCP | `create_node({ workspace_id, title_zh, title_en, body_zh, body_en, content_type, tags })` — 建立節點，自動記錄 `source_type: ai_generated` |
| MCP | `update_node({ node_id, body_zh?, body_en?, tags? })` — 更新節點內容，建立 revision 記錄 |
| MCP | `create_edge({ from_id, to_id, relation, weight? })` — 建立邊 |
| MCP | `traverse_edge({ edge_id, context? })` — 記錄邊的 traversal，觸發 co-access boost 邏輯 |
| MCP | `confirm_node_validity({ node_id })` — 對應 A6 的有效性確認 |

**依賴**：A6（confirm_node_validity 工具依賴 DB 欄位）

---

### E2 — MCP 多工作區支援

**目標**：單一 MCP server 實例支援多個知識庫查詢。

| 層 | 任務 |
|----|------|
| MCP | `search_nodes`、`get_node`、`traverse`、`list_by_tag` 四個工具加入可選參數 `workspace_id`（不傳則沿用 `MEMTRACE_WS` 預設值） |
| MCP | 新增 `list_workspaces()` 工具 — 列出當前 API token 可存取的工作區清單（id、name、kb_type、visibility） |
| MCP | 更新 README：說明多工作區設定方式與 `workspace_id` 參數用法 |

**依賴**：無

---

### E3 — MCP HTTP + SSE Transport

**目標**：支援遠端 AI agent 連線，不需本地 `.mcp.json`。

| 層 | 任務 |
|----|------|
| MCP | 新增 HTTP server 模式（啟動時依 `TRANSPORT=http` 環境變數切換） |
| MCP | 實作 SSE endpoint：`GET /sse` — 建立 SSE 連線；`POST /messages` — 接收 MCP 訊息 |
| MCP | Bearer token 驗證（取自 `Authorization` header，對應 MemTrace API key） |
| MCP | 更新 `docker-compose.yml`，加入 MCP HTTP server 服務設定（port 3100） |
| MCP | 更新 README：說明遠端連線方式與 token 設定 |

**依賴**：無

---

### E4 — MCP Resources

**目標**：實作標準 MCP Resources 協議，讓 AI agent 以 URI 直接讀取節點。

| 層 | 任務 |
|----|------|
| MCP | 實作 `resources/list` handler — 回傳工作區內所有節點的 resource 清單（`memtrace://node/{id}`） |
| MCP | 實作 `resources/read` handler — 依 URI 讀取節點完整內容（含 edges） |
| MCP | URI 格式：`memtrace://node/{node_id}`、`memtrace://workspace/{ws_id}` |

**依賴**：無

---

## F. 匯出匯入與可攜性

---

### F1 — 非同步匯出 API

**目標**：後端非同步產生 `.memtrace` 壓縮檔，支援條件過濾。

| 層 | 任務 |
|----|------|
| DB | 建立 `kb_exports` 資料表：`id, workspace_id, status(pending/processing/done/failed), filter_params JSONB, file_path, created_at, completed_at` |
| API | `POST /workspaces/{ws_id}/exports` — 建立匯出任務，支援 filter：`{ include_archived, tags, date_range }` |
| API | 後台非同步任務：產生包含 nodes.json、edges.json、revisions.json 與原始 Markdown 的 ZIP |
| API | `GET /workspaces/{ws_id}/exports/{export_id}` — 查詢進度與取得下載連結 |
| API | `GET /workspaces/{ws_id}/exports` — 列出匯出歷史 |
| UI | Workspace Settings 新增「匯出」Tab |
| UI | 匯出設定面板（條件選擇）+ 送出後顯示進度輪詢 + 完成後下載按鈕 |

**依賴**：無

---

### F2 — `.memtrace` 匯入

**目標**：從 `.memtrace` 檔案重建知識庫內容。

| 層 | 任務 |
|----|------|
| API | `POST /workspaces/{ws_id}/imports` — 接收 `.memtrace` ZIP 上傳 |
| API | 解析 ZIP：驗證格式版本；批次建立 nodes（保留原始 id 或重新生成）；批次建立 edges；還原 revision history |
| API | 衝突處理：若節點 id 已存在，以 `skip` 或 `overwrite` 模式處理（由參數決定） |
| API | 回傳匯入摘要：成功節點數、跳過數、失敗數 |
| UI | 匯入設定面板：上傳 `.memtrace` 檔案、選擇衝突處理模式、確認後執行 |

**依賴**：F1（使用相同 ZIP 格式）

---

### F3 — CLI 補強

**目標**：完整化 CLI 工具的常用操作。

| 層 | 任務 |
|----|------|
| CLI | `memtrace ingest <file> --workspace <ws_id>` — 上傳並觸發 ingestion |
| CLI | `memtrace copy-node <node-id> --to <workspace-id>` — 跨 KB 複製節點 |
| CLI | `memtrace init` 補完 AI provider 設定步驟：互動式選擇 provider（OpenAI / Anthropic）、輸入 key、呼叫 API 驗證有效性後儲存 |

**依賴**：C1（ingest API）、D1（copy-node API）

---

## G. 安全性與系統強健度

---

### G1 — 登入失敗鎖定

**目標**：防止暴力破解，5 次失敗後鎖定帳號 15 分鐘。

| 層 | 任務 |
|----|------|
| DB | `users` 資料表新增：`failed_login_count INT DEFAULT 0`、`locked_until TIMESTAMPTZ` |
| API | 登入失敗時遞增 `failed_login_count`；達 5 次時設定 `locked_until = now + 15 minutes` |
| API | 登入時先檢查 `locked_until`，若仍在鎖定期回傳 `429 Too Many Requests`，訊息含解鎖剩餘時間 |
| API | 登入成功時重置 `failed_login_count = 0`，清除 `locked_until` |

**依賴**：無

---

### G2 — HaveIBeenPwned 整合

**目標**：註冊與修改密碼時，檢查密碼是否出現在已知洩漏資料庫。

| 層 | 任務 |
|----|------|
| API | 在現有 `check_password_policy()` 函式中補上 HIBP API 呼叫（k-Anonymity 模式：只傳送 SHA-1 hash 前 5 碼） |
| API | 密碼出現在洩漏資料庫時回傳 `400 Bad Request`，說明需更換密碼 |

**依賴**：無

---

### G3 — API Key 輪換

**目標**：支援 API key 輪換，不中斷現有整合。

| 層 | 任務 |
|----|------|
| API | `POST /auth/api-keys/{id}/rotate` — 使舊 key 失效，產生新 key（相同 scopes），回傳新 key 值（僅顯示一次） |
| UI | API Keys 設定頁每個 key 加入「輪換」按鈕，操作後顯示新 key 的一次性複製 dialog |

**依賴**：無

---

### G4 — 背景排程清理

**目標**：定期清除無效資料，防止資料庫膨脹。

| 層 | 任務 |
|----|------|
| Scheduler | 每日清理過期 `workspace_invites`（`expires_at < now AND status = ''pending''`） |
| Scheduler | 每週清理超過 90 天的 `ai_usage_log` 記錄 |
| Scheduler | 每週清理已完成超過 30 天的 `kb_exports` 記錄（同時刪除檔案） |

**依賴**：B3（邀請連結）、F1（匯出任務）

---

### G5 — Core Library 補強

**目標**：補全 TypeScript core 層的缺失函式，統一前後端計算邏輯。

| 層 | 任務 |
|----|------|
| Core | `contentTypeHalfLife(content_type, kb_type): number` — 依 content_type 與 kb_type 回傳預設 half_life_days（目前只有 Python 端 hardcode） |
| Core | `composeTrustScore({ dim_accuracy, dim_freshness, dim_utility, dim_author_rep }): number` — 加權合成 trust score（weights: accuracy 0.3、freshness 0.25、utility 0.25、author_rep 0.2） |
| Core | `verifyNodeSignature(node): boolean` — SHA-256 驗證節點內容完整性，防止資料被竄改（`mem_d005.json` 規格） |

**依賴**：無

---

## H. 規格書知識庫化

> 把 MemTrace 自身的規格書（SPEC.md + 本功能計畫）轉入知識庫，作為產品 dogfooding 的第一個真實案例。
> 有效性驗證（A 組）在此 KB 上線後才有意義，待 A 組功能完成後啟動。

---

### H1 — 初始化規格知識庫

**目標**：建立一個 evergreen、restricted 的知識庫專門存放產品規格。

| 層 | 任務 |
|----|------|
| 操作 | 建立 workspace：name="MemTrace Spec"、kb_type=evergreen、visibility=restricted |
| 操作 | 透過 Onboarding 或直接 API 設定 AI provider key（用於 extraction） |

**依賴**：無

---

### H2 — SPEC.md 攝入

**目標**：將 SPEC.md 透過攝入流程拆解為節點，作為 C1 的第一個真實測試。

| 層 | 任務 |
|----|------|
| 操作 | 上傳 SPEC.md → 觸發 AI extraction → 進入 Review Queue |
| 操作 | 人工逐筆審核候選節點，確保每個節點符合「最小可獨立存在的知識單元」原則 |
| 操作 | 為核心概念節點手動建立 edge（node minimization、decay、trust score、visibility 等之間的關聯） |

**依賴**：C1（File Ingestion）

---

### H3 — 功能計畫攝入

**目標**：將本文件（FEATURE_PLAN.md）以及討論結論轉為節點，與規格節點建立關聯邊。

| 層 | 任務 |
|----|------|
| 操作 | 上傳 FEATURE_PLAN.md → 觸發 AI extraction → Review Queue |
| 操作 | 功能節點與對應規格節點建立 `depends_on` / `extends` 邊 |
| 操作 | 每個功能節點加上 A6 有效性確認（確認截至今日此功能仍在計畫中） |

**依賴**：H2、C1、A6

---

### H4 — MCP 設定指向規格知識庫

**目標**：讓 AI agent 可透過 MCP 查詢規格，日常開發中取得準確的規格上下文。

| 層 | 任務 |
|----|------|
| 操作 | 更新 `.mcp.json`：新增規格知識庫的 MCP server 實例（或待 E2 上線後改用 workspace_id 參數） |
| 操作 | 驗證：AI agent 查詢「node minimization principle 的定義」能在 2 次 tool call 內找到答案 |
| 操作 | 記錄 Token Efficiency 基準數字（對應 A2 功能上線後的第一筆量測） |

**依賴**：H2、E2（MCP 多工作區）

---

## 功能依賴關係快速參照

```
B1（RBAC 修補）          ─ 無依賴，優先修補
G1（登入鎖定）           ─ 無依賴，安全性基礎
D4（歸檔排程）           ─ 無依賴，A4 依賴此項
A5（Trust 維度）         ─ 無依賴
D2（Edge 視覺化）        ─ 無依賴
G5（Core Library）       ─ 無依賴
B2（成員管理）           ─ 無依賴
B3（邀請連結）           ─ 依賴 B2
B5（Graph Preview）      ─ 無依賴
B4（Conditional 申請）   ─ 依賴 B5
B6（API Key Scope）      ─ 無依賴
C1（File Ingestion）     ─ 依賴使用者 AI key 設定
C4（Source Document）    ─ 依賴 C1
C5（AI Reviewer）        ─ 依賴 C1
D1（Copy Node）          ─ 無依賴
D5（Semantic Search）    ─ 依賴使用者 AI key 設定
A4（Faded 管理）         ─ 依賴 D4
A1（Analytics）          ─ 無依賴
A3（Heatmap）            ─ 依賴 A1
E1（MCP 寫入）           ─ 依賴 A6（DB 欄位）
E2（MCP 多工區）         ─ 無依賴
E3（MCP HTTP+SSE）       ─ 無依賴
A6（Validity Stamp）     ─ 無依賴
C3（AI Chat）            ─ 依賴 D5、D3
A2（Token Efficiency）   ─ 依賴 E1 有完整資料
F1（匯出）               ─ 無依賴
F2（匯入）               ─ 依賴 F1（共用格式）
F3（CLI）                ─ 依賴 C1、D1
H1（初始化規格 KB）      ─ 無依賴
H2（SPEC 攝入）          ─ 依賴 C1
H3（功能計畫攝入）       ─ 依賴 H2、A6
H4（MCP 指向規格）       ─ 依賴 H2、E2
```

---

*文件版本：v1.0 — 2026-04-23*
*下一步：開發人員認領任務，按依賴關係排序執行；H 組（規格 KB）在 C1 完成後即可啟動。*
', '', '{}', 'public', 'system', '2026-04-25 01:25:00.423747+00', NULL, 'source', 'human', NULL, NULL, NULL, NULL, 0.500, 0.500, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, 'FEATURE_PLAN.md');
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_e9875476', '1.0', 'ws_spec0001', '輸入模式選擇', 'Input Mode Selection', 'procedural', 'markdown', '頛詨璅∪???蝺刻摩?典?????脰??豢???Input modes are selectable via a tab toggle within the editor.', '頛詨璅∪???蝺刻摩?典?????脰??豢???Input modes are selectable via a tab toggle within the editor.', '{editor,input-mode,ui}', 'public', 'system', '2026-04-24 11:25:39.374323+00', NULL, '585df44f3ba32837cd36c7de38c486adf0a047f38a72f9bbf983f9615d86b47b', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_1f134086', '1.0', 'ws_spec0001', '來源文件：FEATURE_BREAKDOWN.md', 'Source: FEATURE_BREAKDOWN.md', 'source_document', 'plain', '# MemTrace 功能實作展開細項 (Feature Breakdown) - Phase 2 Completed

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
    - `change_type TEXT NOT NULL DEFAULT ''create''` — `create` / `update` / `delete`
    - `target_node_id TEXT REFERENCES memory_nodes(id) ON DELETE CASCADE`（`update` / `delete` 必填）
    - `before_snapshot JSONB` — 提案產生時鎖定的當時節點狀態；`create` 為 `NULL`
    - `diff_summary JSONB` — 由後端預先計算好的欄位級 diff（見 5.2）
    - `proposer_type TEXT NOT NULL DEFAULT ''human''` — `human` / `ai`
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
  - Body 類輸出 `{type: ''text'', before, after, line_diff: [...]}`（line-level）
  - Tags 輸出 `{type: ''set'', added: [...], removed: [...]}`
  - 其他輸出 `{type: ''scalar'', before, after}`
- [x] **AI Ingest 支援編輯既有節點**
  - 檔案：`packages/api/routers/ingest.py`
  - 抽取到的 candidate 先做相似度比對（embedding cosine ≥ 門檻或 title 精確比對）：
    - 命中 → `change_type=''update''`、`target_node_id` = 命中節點
    - 未命中 → `change_type=''create''`
  - 透過 `_propose_change` 寫入，`proposer_type=''ai''`、`proposer_id=ai:<provider>:<model>`
- [x] **MCP 寫入工具整合**
  - 檔案：`packages/mcp-server/...`（Phase 3 交付）
  - 所有節點異動工具（create/update/delete）走 `_propose_change`，依呼叫端身分標註 proposer_type
- [x] **AI Reviewer CRUD 端點**
  - `GET/POST /workspaces/{ws_id}/ai-reviewers`
  - `PATCH/DELETE /workspaces/{ws_id}/ai-reviewers/{id}`
  - 僅 owner 可管理；提供預設 system_prompt 模板
- [x] **AI 預審背景任務**
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
- [x] 上傳檔案 ingest → AI 抽取到與既有節點相似的條目 → 產生 `update` 提案（含 before/after）→ AI reviewer 信心 0.95 自動 accept → `node_revisions` 新增一筆、reviewer_type=''ai''
- [x] Owner 在節點 History tab 選 3 版前的快照 → Restore → 產生新的 update 提案（非直接覆寫）
- [x] 同一 node 累積超過 10 版 → 最舊版自動裁剪
- [x] Viewer 打開 ReviewQueue 可見項目列表與 diff 摘要，但 body 內容被遮蔽，且無法 accept/reject

---

## 6. MCP 多工作區支援 (Multi-Workspace MCP)

**目標**：讓 AI agent 在單一 MCP server 實例中跨多個知識庫查詢，不需為每個知識庫啟動獨立行程，且工具呼叫上下文清楚標明操作的是哪一個庫。

**背景**：目前 `packages/mcp/src/index.ts` 啟動時從 `MEMTRACE_WS` 環境變數固定一個 `WS_ID`，所有工具只能查詢該庫。要查詢其他庫需在 `.mcp.json` 多啟一個實例，但工具名稱全部相同（`search_nodes` 等），AI agent 難以區分歸屬，且每個實例各佔一個 Node.js 行程。

**Backlog 依據**：`docs/BACKLOG.md §3.6`

### 6.1 MCP Server 開發細項

- [x] **各工具新增可選 `workspace_id` 參數**
  - 檔案：`packages/mcp/src/index.ts`
  - 影響工具：`search_nodes`、`get_node`、`traverse`、`list_by_tag`
  - 參數定義（各工具 `inputSchema.properties` 新增）：
    ```json
    "workspace_id": {
      "type": "string",
      "description": "Target workspace ID (e.g. ws_abc123). Omit to use the server default (MEMTRACE_WS)."
    }
    ```
  - 工具實作：`const wsId = args?.workspace_id ?? WS_ID;`，所有 API 路徑改用 `wsId`
  - 向下相容：不傳 `workspace_id` 時行為與現在完全相同

- [x] **新增 `list_workspaces` 工具**
  - 目的：讓 AI agent 在不知道 ws_id 時，先呼叫此工具取得可用清單再決定查哪個庫
  - inputSchema：無必填參數（可選 `limit: number`，預設 20）
  - 實作：呼叫 `GET /api/v1/workspaces`（需帶 token，見 6.2），回傳 id / name_zh / name_en / kb_type / visibility 清單
  - 輸出格式：
    ```
    **3** workspace(s) accessible:
    - [ws_spec0001] MemTrace 規格書 (evergreen / private)
    - [ws_project_abc] 專案日誌 (ephemeral / restricted)
    - [ws_personal_xyz] 個人筆記 (evergreen / private)
    ```

- [x] **新增 `MEMTRACE_TOKEN` 環境變數支援**
  - 目的：`list_workspaces` 與未來寫入工具需要帶 API token 才能存取 `/api/v1/workspaces`
  - 將 token 注入 `apiFetch` 的 `Authorization: Bearer` header
  - 不傳時維持匿名行為（只能存取 public workspace，`list_workspaces` 返回公開庫或空列表）
  - 安全提醒文字加入 server 啟動 stderr log

- [x] **工具 `description` 更新**
  - `search_nodes`、`get_node`、`traverse`、`list_by_tag` 的 description 各加一行說明：
    > Pass `workspace_id` to query a specific KB; omit to use the configured default (`MEMTRACE_WS`).

### 6.2 設定檔變更細項

- [x] **更新 `.mcp.json` 為單實例寫法**
  - 檔案：`.mcp.json`（現有）
  - 改為單實例 + token，移除對每庫一實例的依賴：
    ```json
    {
      "mcpServers": {
        "memtrace": {
          "command": "node",
          "args": ["packages/mcp/dist/index.js"],
          "env": {
            "MEMTRACE_API":   "http://localhost:8000/api/v1",
            "MEMTRACE_WS":    "ws_spec0001",
            "MEMTRACE_LANG":  "zh-TW",
            "MEMTRACE_TOKEN": "<your_api_token_here>"
          }
        }
      }
    }
    ```
  - `MEMTRACE_WS` 為預設庫（不傳 `workspace_id` 時的 fallback），可繼續使用現有值

- [x] **更新 README / 使用文件**
  - 說明三種使用情境：
    1. **單庫（最簡單）**：只設 `MEMTRACE_WS`，不傳 `workspace_id` 參數
    2. **多庫、已知 id**：設 `MEMTRACE_WS` 為最常用庫，查其他庫時每次呼叫帶 `workspace_id`
    3. **多庫、不知 id**：設 `MEMTRACE_TOKEN`，先呼叫 `list_workspaces` 取清單再決定

### 6.3 驗收情境

- [x] 不傳 `workspace_id` → 使用 `MEMTRACE_WS` 預設值，行為與現版相同
- [x] `search_nodes(query="認證", workspace_id="ws_project_abc")` → 查詢 `ws_project_abc` 的節點
- [x] `list_workspaces()` → 回傳 token 可存取的所有庫清單（需設 `MEMTRACE_TOKEN`）
- [x] 不設 `MEMTRACE_TOKEN`，呼叫 `list_workspaces()` → 回傳友善錯誤提示而非 crash
- [x] 傳入不存在或無權限的 `workspace_id` → API 回 403/404，工具回傳可讀錯誤訊息而非丟出 exception

---

## §7 持久化 API Key（Persistent API Key）(Completed)

> **目標**：讓外部工具（MCP Server、CI/CD、第三方整合）能以不過期的 token 存取 MemTrace API，同時維持細粒度的權限控制，不影響現有 JWT session 流程。

### 7.1 背景與動機

| 面向 | JWT Session Token | Persistent API Key |
|------|-------------------|--------------------|
| 主要用途 | 瀏覽器登入 session | MCP / 自動化 / CLI |
| 有效期 | 7 天，需重新登入 | 永久（可手動撤銷）|
| 儲存位置 | `localStorage` (前端) | 使用者自行保管 |
| 撤銷方式 | `session_blocklist` jti | `revoked_at` 欄位 |
| 簽發方式 | Google OAuth 登入後自動產生 | 使用者在 Settings 手動建立 |

### 7.2 Token 格式

```
mt_<40 個 hex 字元>
範例：mt_a3f8c2e1d9b047560f2a8c3e4d5b6f7a8b9c0d1e
```

- 前綴 `mt_` 方便掃描工具辨識洩漏（類似 GitHub `ghp_`）
- 完整 key 僅在建立時顯示一次，之後只儲存 SHA-256 hash
- 資料庫存 `prefix`（前 8 字元）供顯示用，不儲存明文

### 7.3 資料庫異動

現有 `api_keys` 表（`schema/sql/001_init.sql` 第 79–90 行）已有基礎欄位，需補充：

```sql
-- Migration: add revoked_at, last_used_ip to api_keys
ALTER TABLE api_keys
  ADD COLUMN IF NOT EXISTS revoked_at   TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS last_used_ip INET;
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_6709672b', '1.0', 'ws_spec0001', 'B 關聯管理 UI', 'B Association Management UI', 'procedural', 'markdown', '此功能目標是為跨知識庫關聯提供一個完整的設定介面，以補充現有的 API 功能。', 'The goal of this feature is to provide a complete UI for cross-knowledge base association settings, complementing existing API functionality.', '{ui,knowledge-base,association}', 'public', 'system', '2026-04-25 02:39:05.267545+00', NULL, '23d35304327fc4430ebc791c6c9b00a2c222a6c3516e33b32fb27dcf9990b9e9', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_f70b4273', '1.0', 'ws_spec0001', '判斷入門流程進度', 'Determining Onboarding Progress', 'factual', 'markdown', '`steps_done`?steps_skipped`甈??勗?瘙箏??嗅??蝙?刻?撠郊撽??脣漲璇??潦?The `steps_done` and `steps_skipped` fields together determine the current onboarding step and progress bar value.', '`steps_done`?steps_skipped`甈??勗?瘙箏??嗅??蝙?刻?撠郊撽??脣漲璇??潦?The `steps_done` and `steps_skipped` fields together determine the current onboarding step and progress bar value.', '{onboarding,progress,ui}', 'public', 'system', '2026-04-24 11:25:40.398911+00', NULL, '16aaf873e830ab998ec1834add380b9d5bafa80ec0b980ad6bc58c2a60e90b4a', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_0752c920', '1.0', 'ws_spec0001', '貢獻者角色能力：提議更改', 'Contributor Role Capability: Proposing Changes', 'factual', 'markdown', '貢獻者可以提議對節點或邊進行更改。這些提案進入審核隊列，需要管理員核准後才能應用。', 'Contributors can propose changes to nodes or edges. These proposals enter a review queue and require admin approval to be applied.', '{role,contributor,proposal,review-queue}', 'public', 'system', '2026-04-24 11:25:40.48633+00', NULL, 'c9e0f98fe56cae12c67d59594eb46922bacdf9e4aa36e3df1f975b9552b4828e', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_8a8214f3', '1.0', 'ws_spec0001', '記憶節點來源類型', 'Memory Node Source Type', 'factual', 'markdown', '`memory_nodes` 表中的 `source_type` 欄位類型為 ENUM，可能的值為 `human` / `ai_generated` / `ai_verified`。', 'The `source_type` column in the `memory_nodes` table is of type ENUM, with possible values `human` / `ai_generated` / `ai_verified`.', '{database,schema,memory_nodes,column,enum}', 'public', 'system', '2026-04-24 11:25:39.108336+00', NULL, '5dce0a872a0e0bec6f9fc2e51d4e0fc0593f549fbac11c16734de343d7cce113', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_013d11be', '1.0', 'ws_spec0001', 'Markdown 輸入模式', 'Markdown Input Mode', 'factual', 'markdown', '在 `markdown` 模式下，輸入內容在閱讀視圖中被渲染為 HTML，而原始 Markdown 內容被儲存。', 'In `markdown` mode, input is rendered as HTML in read view, while raw Markdown is stored.', '{input-mode,markdown}', 'public', 'system', '2026-04-24 11:25:39.414292+00', NULL, '3f5ab1967571ab79453c47895d21ed5af47489952515e7f2b69c52dd17c70c39', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_263e8dd9', '1.0', 'ws_spec0001', '邀請 API 端點', 'Invitation API Endpoint', 'factual', 'markdown', '?冽?喲極雿??隢?API蝡舫???`POST /workspaces/{ws_id}/invites`??The API endpoint for issuing workspace invitations is `POST /workspaces/{ws_id}/invites`.', '?冽?喲極雿??隢?API蝡舫???`POST /workspaces/{ws_id}/invites`??The API endpoint for issuing workspace invitations is `POST /workspaces/{ws_id}/invites`.', '{api,invitation,admin}', 'public', 'system', '2026-04-24 11:25:39.611211+00', NULL, '6fc2382e4ea2d6fb918a89b618c797778a7778327c86d6939a3571ef142d5cfc', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_25b80084', '1.0', 'ws_spec0001', '非成員存取條件式公開工作區', 'Non-Member Access to Conditional Public Workspace', 'factual', 'markdown', '?園??雿輻?赤???conditional_public`撌乩????隡箸??冽?餈?銝?移蝪∠??????瑯?When a non-member user accesses a `conditional_public` workspace, the server returns a stripped graph payload.', '?園??雿輻?赤???conditional_public`撌乩????隡箸??冽?餈?銝?移蝪∠??????瑯?When a non-member user accesses a `conditional_public` workspace, the server returns a stripped graph payload.', '{}', 'public', 'system', '2026-04-24 11:25:39.722141+00', NULL, '1ad8d1c6a71fd754a34836bb2dcb3ae02a1792f1819065808a800393d273da28', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_9b4c8d95', '1.0', 'ws_spec0001', '新增內容類型：source_document', 'New Content Type: source_document', 'factual', 'markdown', 'content_type 列舉中新增了 source_document 值，以支援來源文件的保留。', '?箔??舀??瑼???`content_type` ??銝剜憓? `source_document` ?潦?The `source_document` value has been added to the `content_type` enum to support source file retention.', '{}', 'public', 'system', '2026-04-24 11:25:40.757174+00', NULL, '82ce2be4c99239eecb2f93776b4e69fda7149935e80c8f2a181d4424f7672e7f', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_4f8e3f0b', '1.0', 'ws_spec0001', '記憶節點新鮮度維度', 'Memory Node Freshness Dimension', 'factual', 'markdown', '`memory_nodes` 表中的 `dim_freshness` 欄位類型為 NUMERIC(4,3)，表示信任分數的一個維度。', 'The `dim_freshness` column in the `memory_nodes` table is of type NUMERIC(4,3), representing a dimension of the trust score.', '{database,schema,memory_nodes,column,trust_dimension}', 'public', 'system', '2026-04-24 11:25:39.174808+00', NULL, 'c1f8cd3af9c051f8cfc0a733c22430151a7cc93d1acb0271c531b2a83dc854ec', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_9fe95573', '1.0', 'ws_spec0001', '純文本導出格式結構', 'Plain Text Export Format Structure', 'factual', 'markdown', '純文本導出格式的整體結構包含一個頁首，列出知識庫名稱、範圍標籤、導出的 ISO 時間戳以及工作區 ID。', 'The overall structure of the plain text export format includes a header with the Knowledge Base Name, Scope Label, ISO datetime of export, and Workspace ID.', '{export,format,plain-text}', 'public', 'system', '2026-04-24 11:25:40.929029+00', NULL, '8be687263181850916849d41e4c5a323a08df03632ea41235d3f0b3ceb3b7198', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_54cc2c31', '1.0', 'ws_spec0001', '非成員存取單一節點權限', '???∟赤???暺?閮勗甈?Non-Member Access to Individual Nodes', 'factual', 'markdown', '非成員嘗試執行 GET /api/v1/workspaces/{ws_id}/nodes/{id} 將會回傳 HTTP 403。', '???∩蝙?刻?閰阡?`GET /api/v1/workspaces/{ws_id}/nodes/{id}`閮芸??桀?暺?餈?`HTTP 403`?航炊??Attempting `GET /api/v1/workspaces/{ws_id}/nodes/{id}` as a non-member returns `HTTP 403`.', '{}', 'public', 'system', '2026-04-24 11:25:39.81002+00', NULL, 'b459d17d111fb8c96441d6b90de474522e0adef6a244d7932ff73fa93c624ea2', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_da5739b0', '1.0', 'ws_spec0001', '匯入預覽畫面概覽', 'Import Preview Screen Overview', 'factual', 'markdown', '匯入預覽畫面顯示匯入作業的摘要，包括節點和邊的總數，以及哪些節點是乾淨的或可能是重複的。', 'The import preview screen displays a summary of the import job, including the total number of nodes and edges, and which nodes are clean or potentially duplicates.', '{import,ui,preview}', 'public', 'system', '2026-04-24 11:25:40.950895+00', NULL, '33e0e380ea727d436286ac1bf2851417357f1fbec9cdf77e3c99a89c6c790c2a', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_1b0a6c77', '1.0', 'ws_spec0001', 'API 金鑰/對談停權閾值', 'API Key/Session Suspension Threshold', 'factual', 'markdown', '如果走訪率在 10 分鐘內超過 2000 次請求，API 金鑰或對談將被停權。', 'An API key or session is suspended if the traversal rate exceeds 2000 requests within a 10-minute period.', '{api-key,session,security,rate-limiting,threshold}', 'public', 'system', '2026-04-24 11:31:27.743224+00', NULL, 'b44ed89375ac73f6c55e71e4e97b9521aa00be67b37609a04552c515ac852362', 'ai', NULL, NULL, NULL, NULL, 0.593, 0.800, 1.000, 0.010, 0.500, 0, 0, 0, 1, 1, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_99877db7', '1.0', 'ws_spec0001', '管理員角色能力詳情', 'Admin Role Capabilities Detail', 'factual', 'markdown', '管理員擁有所有貢獻者能力，並可以直接寫入節點和邊，繞過審核隊列。他們可以批准或拒絕貢獻者的提案、更改成員角色、移除成員、創建邀請連結、啟動工作區軟刪除以及取消待處理的刪除。', 'Admins have all contributor capabilities and can directly write to nodes and edges, bypassing the review queue. They can approve or reject contributor proposals, change member roles, remove members, create invite links, initiate workspace soft-deletion, and cancel pending deletions.', '{role,admin,capabilities,direct-write,member-management,workspace-lifecycle}', 'public', 'system', '2026-04-24 11:25:40.578811+00', NULL, '9595d963ebb096bb9babefc681a5b117abc51207b0587a462f1d2f5a847fb7f3', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_fee2f20e', '1.0', 'ws_spec0001', 'AI 讀取權限：關聯的工作區', 'AI Read Permission: Associated Workspaces', 'factual', 'markdown', 'AI 可以從關聯的工作區讀取內容，但不被允許向其提議寫入操作。', 'AI may read from associated workspaces but is not permitted to propose writes to them.', '{}', 'public', 'system', '2026-04-24 11:25:40.71846+00', NULL, 'bf0b60327f5653184e709699864ee935ead4af7a24ab35a084ed82d36c9699b5', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_e3e6a8a4', '1.0', 'ws_spec0001', 'UI 入門流程進度條', 'UI Onboarding Flow Progress Bar', 'factual', 'markdown', '在每個步驟的頂部都會顯示一個持久的進度條，例如「步驟 X / Y」。必填步驟會被標記，可跳過的步驟則顯示「暫時跳過」連結。', 'A persistent progress bar, e.g., "Step X of Y", is shown at the top of each step. Required steps are marked, and skippable steps show a "Skip for now" link.', '{ui,onboarding,progress}', 'public', 'system', '2026-04-24 11:31:27.668692+00', NULL, 'b765919fa3c8d7ca9d84e73220b483af69ddf3e5317b220e195ca32f868b427d', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_54473627', '1.0', 'ws_spec0001', 'POST /nodes/{node_id}/traverse 端點', 'POST /nodes/{node_id}/traverse Endpoint', 'procedural', 'markdown', '此端點用於記錄調用者已訪問特定節點。', 'This endpoint is used to record that the caller has visited a specific node.', '{api,rest,traversal,node}', 'public', 'system', '2026-04-24 11:25:40.164919+00', NULL, 'd4a83d290c2c0d364f5d646e3c3032f7dc70ea68d28ded6eaba1f5cb0b7834e4', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_156804b8', '1.0', 'ws_spec0001', 'API 金鑰權限範圍：kb:write', 'API Key Scope: kb:write', 'factual', 'markdown', '`kb:write` 權限範圍的 API 金鑰授予管理員角色能力，提供完全寫入權限。', 'An API key with the `kb:write` scope grants admin role capabilities, providing full write access.', '{api-key,scope,admin,write-access}', 'public', 'system', '2026-04-24 11:25:40.640994+00', NULL, '956a647920f96b7a1b1d0aff71ff87d58dc65179427575b5a85f87acd1dacaa3', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_fcfc3360', '1.0', 'ws_spec0001', 'AI 呼叫日誌要求', 'AI Call Logging Requirement', 'factual', 'markdown', '所有 AI 呼叫，無論是使用工作區級別還是帳戶級別的金鑰，都必須記錄。日誌作為計費、調試和政策執行的權威記錄。', 'All AI calls, regardless of whether they use a workspace-level or account-level key, must be logged. The log serves as the authoritative record for billing, debugging, and policy enforcement.', '{ai,說明,記錄,錯誤,結構}', 'public', 'system', '2026-04-24 11:25:40.870968+00', NULL, 'd602c01a63a9d7c9de1f73258fc8a94b375dadb29578da5d267ed59f356eb6fa', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_ce00334f', '1.0', 'ws_spec0001', 'MemTrace 平台概覽', 'MemTrace Platform Overview', 'factual', 'markdown', 'MemTrace 是一個開放平台，旨在透過最小、連接良好的記憶節點（Memory Nodes）構建共享知識。其核心設計目標是讓任何人類或 AI 代理都能通過最短路徑在小型、分型關係圖中找到答案，而不是閱讀大量文檔。', 'MemTrace is an open platform designed for building shared knowledge through minimal, well-connected Memory Nodes. Its core design goal is to allow any human or AI agent to reach any answer by following the shortest possible path through a graph of small, typed relationships — rather than reading through large documents.', '{memtrace,概覽,介紹,平台}', 'public', 'system', '2026-04-24 11:26:52.690912+00', NULL, '7c0dc21b5b1a8849d7704332f76000351e9532b56aad2bbacdb5d7e28acbbb42', 'ai', NULL, NULL, NULL, NULL, 0.593, 0.800, 1.000, 0.010, 0.500, 0, 0, 0, 1, 1, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_107440f8', '1.0', 'ws_spec0001', '簡化圖譜載荷中的節點 ID', 'Node IDs in Stripped Graph Payload', 'factual', 'markdown', '簡化圖譜載荷中的真實 `memory_node.id` 值被替換為不透明的順序預覽 ID (`node_preview_N`)，這些 ID 在不同請求之間是不穩定的。', 'Real `memory_node.id` values in the stripped graph payload are replaced with opaque sequential preview IDs (`node_preview_N`) that are not stable across requests.', '{節點ID,簡化結構,資料載荷}', 'public', 'system', '2026-04-24 11:25:39.758281+00', NULL, '1deb02df329cb170fcdc2a70609066f0765abe86315b577b6bdf3c214b6cb7e7', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_e7f9e165', '1.0', 'ws_spec0001', '節點創建時的預設值', 'Default Values on Node Creation', 'factual', 'markdown', '新節點創建的預設值包括 `content.format` 為 `"plain"`, `trust.score` 為 0.5, `trust.dimensions` (accuracy 0.5, freshness 1.0, utility 0.5, author_rep 0.5), 以及 `trust.votes` (up 0, down 0, verifications 0)。', 'Default values for new node creation include `content.format` as `"plain"`, `trust.score` as 0.5, `trust.dimensions` (accuracy 0.5, freshness 1.0, utility 0.5, author_rep 0.5), and `trust.votes` (up 0, down 0, verifications 0).', '{設定,預設值}', 'public', 'system', '2026-04-24 11:25:39.907406+00', NULL, '11dce764ed34376c489501afe7fa9330e9e93e1b549033f0c531a25cf39e346c', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_9fbbb5eb', '1.0', 'ws_spec0001', 'Memory Node v1 手動編輯的新增欄位', 'Additional Fields for Manual Editing in Memory Node v1', 'factual', 'markdown', '為了支持手動創建和編輯，`content.format` 和 `provenance.updated_at` 欄位被附加到 `node.v1.json`。', 'To support manual creation and editing, `content.format` and `provenance.updated_at` fields are appended to `node.v1.json`.', '{schema,編輯,欄位}', 'public', 'system', '2026-04-24 11:25:39.850666+00', NULL, '452abb112c53437818f068b051dae5b3ed9838e84f1596251e5802d0afdf7c11', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_a9dee7ad', '1.0', 'ws_spec0001', 'AI 編輯限制：僅限當前工作區節點', 'AI蝺刻摩?嚗?極雿?蝭暺?AI Edit Restriction: Current Workspace Nodes', 'factual', 'markdown', '當 allow_edits: true 時，AI 只能對當前工作區中的節點提出編輯建議。', '??`allow_edits: true` ??AI?芾撠?極雿?銝剔?蝭暺??箇楊頛臬遣霅啜?When `allow_edits: true`, AI may only propose edits to nodes within the current workspace.', '{}', 'public', 'system', '2026-04-24 11:25:40.697058+00', NULL, 'e7bf10d2741911fda9174cec1c320fb1aa084b441af68b4ccf38eb16825802f4', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_d1d90285', '1.0', 'ws_spec0001', 'API Key 權限範圍：kb:propose', 'API Key Scope: kb:propose', 'factual', 'markdown', '具有 kb:propose 權限範圍的 API Key 授予貢獻者（contributor）角色的能力，包括所有讀取權限以及提交建議的能力。', '`kb:propose` 蝭???API ???鞎Ｙ???脰???????迂?舀???鈭斗?霅啁??賢???An API key with the `kb:propose` scope grants contributor role capabilities, including all read access and the ability to submit proposals.', '{api-key,scope,contributor,proposal}', 'public', 'system', '2026-04-24 11:25:40.620555+00', NULL, '676665976061e64f48291d081a2edea8a4ae9b7eafef376b42fd6438a6a74965', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_565d7142', '1.0', 'ws_spec0001', '記憶節點新增來源文件參考欄位', '閮擃?暺憓??辣撘??Memory Nodes Add Source Document Reference Columns', 'factual', 'markdown', '為了將萃取節點連結到其來源段落，memory_nodes 表中新增了 source_doc_node_id（引用來源文件節點 ID）和 source_paragraph_ref（段落級參考）欄位。', '?箔?撠???蝭暺??嗆?畾菔?韏瑚?嚗memory_nodes` 銵其葉?啣?鈭?`source_doc_node_id` (撘皞?隞嗥?暺D) ??`source_paragraph_ref` (畾菔蝝撘) ??To link extracted nodes to their source passages, `source_doc_node_id` (referencing the source document node ID) and `source_paragraph_ref` (paragraph-level reference) columns are added to the `memory_nodes` table.', '{來源,文件}', 'public', 'system', '2026-04-24 11:25:40.793451+00', NULL, '4e72999ffec0aa27b1841c5dbbc5838c1ee5228b0c418ba246b5513acf930071', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_w003', '1.0', 'ws_spec0001', 'Spec KB 初始化說明', 'Spec KB Initialization', 'procedural', 'markdown', '## Spec KB 是如何建立的？
規格知識庫（`ws_spec0001`）由 `schema/sql/099_seed_spec_kb.sql` 自動建立。

`docker compose up` 時，PostgreSQL init 機制依序執行 `schema/sql/` 下所有 `*.sql`，`099_seed_spec_kb.sql` 最後執行，建立工作區、寫入 30 個節點與對應邊。

## 驗證
```bash
docker exec -it memtrace-db psql -U memtrace -d memtrace \n  -c "SELECT COUNT(*) FROM memory_nodes WHERE workspace_id=''ws_spec0001'' AND status=''active'';" 
# 預期：30
```

## 重置 Spec KB
```bash
docker compose down -v && docker compose up -d
```', '## How is the Spec KB created?
The Spec Knowledge Base (`ws_spec0001`) is created automatically by `schema/sql/099_seed_spec_kb.sql`.

When you run `docker compose up`, PostgreSQL''s init mechanism executes all `*.sql` files under `schema/sql/` in order. `099_seed_spec_kb.sql` runs last, creating the workspace and inserting 30 nodes and their edges.

## Verify
```bash
docker exec -it memtrace-db psql -U memtrace -d memtrace \n  -c "SELECT COUNT(*) FROM memory_nodes WHERE workspace_id=''ws_spec0001'' AND status=''active'';" 
# Expected: 30
```

## Reset Spec KB
```bash
docker compose down -v && docker compose up -d
```', '{dev,seed,procedural}', 'public', 'system', '2026-04-28 00:00:00+00', NULL, '', 'human', NULL, NULL, NULL, NULL, 0.900, 0.950, 1.000, 0.900, 0.900, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_d692bb11', '1.0', 'ws_spec0001', 'README/使用文件更新：多庫、已知 ID 使用情境', 'README/Usage Document Update: Multiple Workspaces, Known ID Scenario', 'procedural', 'markdown', 'README 和使用文件已更新，說明多庫、已知 ID 使用情境：將 `MEMTRACE_WS` 設定為最常用工作區，並在查詢其他工作區時，每次呼叫工具都帶上 `workspace_id` 參數。', 'The README and usage documentation have been updated to describe the multiple workspaces, known ID scenario: set `MEMTRACE_WS` to the most frequently used workspace, and when querying other workspaces, include the `workspace_id` parameter with each tool call.', '{文件,使用情境,工作區}', 'public', 'system', '2026-04-26 00:29:47.118808+00', NULL, '9ac19666134fbb8959c26d7cb4f2bb7a4d735773f634d8f3c72e31d1df271051', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_d001', '1.0', 'ws_spec0001', 'Memory Node：知識的最小單位', 'Memory Node: the atomic unit of knowledge', 'factual', 'markdown', 'Memory Node 是 MemTrace 中知識的最小單位。每個節點捕捉**一個**想法，包含：

- **雙語標題與內文**（zh-TW + en），各自獨立
- **Content Type**：`factual` / `procedural` / `preference` / `context` / `source_document`
- **Format**：`plain` 或 `markdown`
- **Tags**：字串陣列，用於分類與搜尋
- **Visibility**：`public` / `team` / `private`
- **Provenance**：作者、建立時間、SHA-256 簽章、source_type
- **Trust**：四維度信任分數
- **Traversal**：走訪計數與不重複訪客數
- **Status**：`active` / `archived`（archived 從預設視圖隱藏，不刪除）

**並行寫入相關欄位**（§17）：
- `version` — 樂觀鎖整數，每次 UPDATE 自動 +1；PATCH 必須帶 `X-Node-Version` header
- `conflict_status` — `flagged` / `resolved`，由衝突檢測寫入
- `conflict_detail` — JSONB，記錄衝突類型與相關節點

**來源文件追溯欄位**（§20）：
- `source_doc_node_id` — 指向 `source_document` 類型節點，用於追溯萃取來源
- `source_paragraph_ref` — 字串，標記在原文件中的段落位置（如 `page:3, para:2` 或 `00:14:32-00:15:01`）

節點 ID 格式：`mem_<hex8>`，例如 `mem_a1b2c3d4`。', 'A Memory Node is the atomic unit of knowledge in MemTrace. Each node captures **one** idea and contains:

- **Bilingual title + body** (zh-TW + en), independently authored
- **Content Type**: `factual` / `procedural` / `preference` / `context` / `source_document`
- **Format**: `plain` or `markdown`
- **Tags**: string array for classification and search
- **Visibility**: `public` / `team` / `private`
- **Provenance**: author, creation timestamp, SHA-256 signature, source_type
- **Trust**: four-dimension trust score
- **Traversal**: visit count and unique visitor count
- **Status**: `active` / `archived` (archived nodes are hidden from default views, not deleted)

**Concurrency fields** (§17):
- `version` — optimistic-lock integer, auto-incremented on every UPDATE; PATCH must include `X-Node-Version` header
- `conflict_status` — `flagged` / `resolved`, set by the conflict detection job
- `conflict_detail` — JSONB, records conflict type and related node

**Source-document traceability fields** (§20):
- `source_doc_node_id` — references a `source_document`-type node for extraction traceability
- `source_paragraph_ref` — string marking the original location (e.g. `page:3, para:2` or `00:14:32-00:15:01`)

Node ID format: `mem_<hex8>`, e.g. `mem_a1b2c3d4`.', '{data-model,schema,core,version,conflict}', 'public', 'memtrace-spec', '2026-04-11 00:00:00+00', NULL, 'd4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5', 'human', NULL, NULL, NULL, NULL, 0.950, 0.950, 1.000, 0.950, 0.900, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_playbook_001', '1.0', 'ws_spec0001', 'MemTrace Playbook：知識圖譜原則', 'MemTrace Playbook: Principles of Knowledge Mapping', 'context', 'markdown', '### 核心原則
1. **原子性**：每個節點應精確描述一個獨立的概念。
2. **雙語對稱**：提供英文和中文內容，以確保跨語言發現。
3. **關係優先**：沒有邊的節點是孤立的記憶。始終考慮它如何與現有知識相關聯。', '### Core Principles
1. **Atomicity**: Each node should describe exactly one independent concept.
2. **Bilingual Symmetry**: Provide both English and Chinese content to ensure cross-lingual discovery.
3. **Relationship First**: A node without edges is isolated memory. Always consider how it relates to existing knowledge.', '{playbook,philosophy,core}', 'public', 'system', '2026-04-24 13:35:31.814382+00', NULL, 'manual_playbook_001', 'ai', NULL, NULL, NULL, NULL, 0.500, 0.500, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_6089d7d9', '1.0', 'ws_spec0001', '私有工作區搜尋與列表不可見性', 'Private Workspace Search/Listing Invisibility', 'factual', 'markdown', '「私有」(private) 工作區不會出現在任何列表或搜尋結果中。', 'A `private` workspace does not appear in any listing or search result.', '{workspace-type,private,visibility}', 'public', 'system', '2026-04-24 11:25:39.682293+00', NULL, 'f17d1b398b13665411a5e123be8e90e901051f72a5292d56240efdf3c25e755c', 'ai', NULL, NULL, NULL, NULL, 0.593, 0.800, 1.000, 0.010, 0.500, 0, 0, 0, 1, 1, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_e568aa35', '1.0', 'ws_spec0001', '來源文件：SPEC.md', 'Source: SPEC.md', 'source_document', 'plain', '', '', '{}', 'public', 'system', '2026-04-24 10:43:07.301122+00', NULL, 'source', 'human', NULL, NULL, NULL, NULL, 0.500, 0.500, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, 'SPEC.md');
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_9d419d24', '1.0', 'ws_spec0001', '記憶節點表', 'Memory Nodes Table', 'factual', 'markdown', '數據庫中的 `memory_nodes` 表存儲所有記憶節點的數據。', 'The `memory_nodes` table in the database stores data for all memory nodes.', '{database,schema,memory_nodes}', 'public', 'system', '2026-04-24 11:25:38.834888+00', NULL, '6d5d61fadf3d71c95c9a3003ed98545b06907cc17eaf4fb39604b234efd3aec2', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_1b50a9b1', '1.0', 'ws_spec0001', '記憶節點編輯器欄位', 'Memory Node Editor Fields', 'factual', 'markdown', '撱箇?/蝺刻摩銵典?湧鈭???雿?雿輻?‵撖怒?The creation/edit form exposes several fields for user input.', '撱箇?/蝺刻摩銵典?湧鈭???雿?雿輻?‵撖怒?The creation/edit form exposes several fields for user input.', '{editor,fields,memory-node}', 'public', 'system', '2026-04-24 11:25:39.497376+00', NULL, 'b20effdba67a36c189fcc02d6a494aa870056bd4e8a4f6b878040a55275100d1', 'ai', NULL, NULL, NULL, NULL, 0.593, 0.800, 1.000, 0.010, 0.500, 0, 0, 0, 1, 1, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_w001', '1.0', 'ws_spec0001', '專案套件結構', 'Project Package Structure', 'factual', 'markdown', 'MemTrace 採用 npm workspaces monorepo，根目錄 `package.json` 管理六個套件：

| 套件 | 路徑 | 語言 | 角色 |
|------|------|------|------|
| core | packages/core | TypeScript | 共用型別、decay 計算、ID/簽章產生器 |
| api | packages/api | Python/FastAPI | REST API、資料庫存取、AI 抽象層 |
| ui | packages/ui | React/Vite | 網頁前端 |
| cli | packages/cli | TypeScript | 本地 CLI 工具 |
| mcp | packages/mcp | TypeScript | MCP server（stdio + SSE 傳輸） |
| ingest | packages/ingest | TypeScript | 文件攝入 pipeline |

`core` 由 `cli` 引用；`api` 獨立於 TS 套件之外。', 'MemTrace uses an npm workspaces monorepo. The root `package.json` manages six packages:

| Package | Path | Language | Role |
|---------|------|----------|------|
| core | packages/core | TypeScript | Shared types, decay logic, ID/signature generator |
| api | packages/api | Python/FastAPI | REST API, database access, AI abstraction layer |
| ui | packages/ui | React/Vite | Web frontend |
| cli | packages/cli | TypeScript | Local CLI tool |
| mcp | packages/mcp | TypeScript | MCP server (stdio + SSE transports) |
| ingest | packages/ingest | TypeScript | Document ingestion pipeline |

`core` is consumed by `cli`. `api` is independent of the TS workspace.', '{dev,architecture,monorepo}', 'public', 'system', '2026-04-28 00:00:00+00', NULL, '', 'human', NULL, NULL, NULL, NULL, 0.900, 0.950, 1.000, 0.900, 0.900, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_40a90101', '1.0', 'ws_spec0001', '', 'T1 Only EN', 'factual', 'plain', '', 'T1 body.', '{mcp}', 'public', 'system', '2026-04-19 23:49:25.009858+00', NULL, 'e823782ce4597e9a20a7d79a73aa27f8b5f3c3c94f6780c293b81f992172f3cc', 'human', NULL, NULL, NULL, NULL, 0.503, 0.500, 1.000, 0.010, 0.500, 0, 0, 0, 1, 1, 'archived', '2026-04-24 13:08:11.382839+00', NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_w004', '1.0', 'ws_spec0001', '開發實作順序與現況', 'Development Progress & Status', 'procedural', 'markdown', '## 完成進度（Phase 1–3）

| 層 | 狀態 |
|----|------|
| core（型別/decay/簽章）| ✅ |
| SQL schema（001_init + 24 migrations）| ✅ |
| api/core（database/security/AI 抽象）| ✅ |
| api/routers/auth（登入/JWT/密碼重設）| ✅ |
| api/routers/kb（workspace/node/edge/roles）| ✅ |
| api/routers/ingest（PDF/Markdown 攝入）| ✅ |
| mcp server（stdio+SSE/read+write tools）| ✅ |
| ui（Auth/Onboarding/Graph 2D+3D/Table/Settings）| ✅ |

## Phase 4 規劃中

| 任務 | 目標 |
|------|------|
| P4-A | 知識庫健康儀表板 + Token 效率報告 |
| P4-B | Spec-as-KB 升級為對外展示首頁 |
| P4-C | MCP vote_trust 工具 |
| P4-D | CLI/Core 殘留補完 |
| P4-G | 自管 Ollama Provider |', '## Completed (Phase 1–3)

| Layer | Status |
|-------|--------|
| core (types/decay/signature) | ✅ |
| SQL schema (001_init + 24 migrations) | ✅ |
| api/core (database/security/AI abstraction) | ✅ |
| api/routers/auth (login/JWT/password reset) | ✅ |
| api/routers/kb (workspace/node/edge/roles) | ✅ |
| api/routers/ingest (PDF/Markdown ingestion) | ✅ |
| mcp server (stdio+SSE / read+write tools) | ✅ |
| ui (Auth/Onboarding/Graph 2D+3D/Table/Settings) | ✅ |

## Phase 4 (in planning)

| Task | Goal |
|------|------|
| P4-A | KB health dashboard + token efficiency |
| P4-B | Spec-as-KB as public demo homepage |
| P4-C | MCP vote_trust tool |
| P4-D | CLI/Core residuals |
| P4-G | Self-hosted Ollama provider |', '{dev,workflow,procedural}', 'public', 'system', '2026-04-28 00:00:00+00', NULL, '', 'human', NULL, NULL, NULL, NULL, 0.900, 0.950, 1.000, 0.900, 0.900, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_d002', '1.0', 'ws_spec0001', 'Edge：有向有型的關係', 'Edge: a typed, directed relationship', 'factual', 'markdown', 'Edge 連接兩個 Memory Node，方向為 `from → to`。每條 Edge 包含：

- **Relation type**：depends_on / extends / related_to / contradicts
- **Weight**：0–1，反映關係強度；由 decay 與 co-access boost 動態更新
- **Co-access count**：被共同存取的次數
- **Decay 參數**：half_life_days（預設 30）、min_weight（預設 0.1）
- **Traversal**：走訪次數、平均評分（1–5）、評分人數

Edge ID 格式：`edge_<hex8>`。同一對節點間相同 relation type 的 Edge 不重複。', 'An Edge connects two Memory Nodes with direction `from → to`. Each edge contains:

- **Relation type**: depends_on / extends / related_to / contradicts
- **Weight**: 0–1, reflecting relationship strength; dynamically updated by decay and co-access boost
- **Co-access count**: how many times accessed together
- **Decay parameters**: half_life_days (default 30), min_weight (default 0.1)
- **Traversal**: visit count, average rating (1–5), rating count

Edge ID format: `edge_<hex8>`. Duplicate edges (same from, to, relation) are rejected.', '{data-model,schema,graph,core}', 'public', 'memtrace-spec', '2026-04-11 00:00:00+00', NULL, 'e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6', 'human', NULL, NULL, NULL, NULL, 0.950, 0.950, 1.000, 0.950, 0.900, 0, 0, 0, 1, 1, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_1fc8782f', '1.0', 'ws_spec0001', '記憶節點英文內文', 'Memory Node English Body', 'factual', 'markdown', '`memory_nodes` 表中的 `body_en` 欄位類型為 TEXT，存儲記憶節點的英文正文。', 'The `body_en` column in the `memory_nodes` table is of type TEXT, storing the English body of the memory node.', '{database,schema,memory_nodes,column,i18n}', 'public', 'system', '2026-04-24 11:25:38.987893+00', NULL, '38def61e607255d825e41054e1ef73f9bbe01b69d8df3be4d7d18a59eb8e41ac', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_d004', '1.0', 'ws_spec0001', 'Trust 系統：信任如何被計算', 'Trust system: how trust is calculated', 'factual', 'markdown', '每個 Memory Node 帶有一個 0–1 的綜合信任分數，由四個維度合成：

| 維度 | 說明 | 建立時預設 |
|------|------|----------|
| `accuracy` | 事實正確性 | 0.5 |
| `freshness` | 時效性 | 1.0 |
| `utility` | 實用程度 | 0.5 |
| `author_rep` | 作者信譽 | 0.5 |

信任分數隨社群投票（up/down）與驗證次數持續更新。內容以 SHA-256 簽章防偽，每次儲存重新計算。Trust score < 0.3 的節點標記警告；< 0.1 的節點從公開索引移除。', 'Every Memory Node carries a composite trust score (0–1) derived from four dimensions:

| Dimension | Description | Default at creation |
|-----------|-------------|--------------------|
| `accuracy` | Factual correctness | 0.5 |
| `freshness` | Timeliness | 1.0 |
| `utility` | Practical usefulness | 0.5 |
| `author_rep` | Author reputation | 0.5 |

Trust scores are updated continuously by community votes (up/down) and verification counts. Content is SHA-256 signed on every save. Nodes with score < 0.3 are flagged; nodes < 0.1 are removed from the public index.', '{data-model,trust,anti-forgery}', 'public', 'memtrace-spec', '2026-04-11 00:00:00+00', NULL, 'a2b3c4d5e6f7a2b3c4d5e6f7a2b3c4d5e6f7a2b3c4d5e6f7a2b3c4d5e6f7a2b3', 'human', NULL, NULL, NULL, NULL, 0.950, 0.950, 1.000, 0.900, 0.900, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_4c589d76', '1.0', 'ws_spec0001', '記憶節點創建時間戳', 'Memory Node Creation Timestamp', 'factual', 'markdown', '`memory_nodes` 表中的 `created_at` 欄位類型為 TIMESTAMPTZ，記錄記憶節點的創建時間。', 'The `created_at` column in the `memory_nodes` table is of type TIMESTAMPTZ, recording the creation time of the memory node.', '{database,schema,memory_nodes,column,timestamp}', 'public', 'system', '2026-04-24 11:25:39.069241+00', NULL, '6469215e9e84619bfd84e3c3039b487afc9a7f9de83a8e3c6098ba15e5a4ad33', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_d005', '1.0', 'ws_spec0001', 'Provenance：來源與可溯性', 'Provenance: origin and traceability', 'factual', 'plain', '每個節點的 provenance 物件記錄知識的來源資訊：author（作者）、created_at（建立時間）、signature（SHA-256 內容雜湊）、source_type（human / ai_generated / ai_verified）。編輯後新增 updated_at。AI 萃取的節點額外記錄 source_document（來源文件）與 extraction_model（使用的 AI 模型）。複製到其他知識庫的節點記錄 copied_from.node_id 與 copied_from.workspace_id。Provenance 永遠記錄，但不構成存取限制。', 'The provenance object on each node records the knowledge''s origin: author, created_at, signature (SHA-256 content hash), source_type (human / ai_generated / ai_verified). updated_at is added on any edit. AI-extracted nodes additionally record source_document (the source file) and extraction_model (the AI model used). Nodes copied across Knowledge Bases record copied_from.node_id and copied_from.workspace_id. Provenance is always recorded but does not restrict access.', '{data-model,provenance,traceability}', 'public', 'memtrace-spec', '2026-04-11 00:00:00+00', NULL, 'b3c4d5e6f7a2b3c4d5e6f7a2b3c4d5e6f7a2b3c4d5e6f7a2b3c4d5e6f7a2b3c4', 'human', NULL, NULL, NULL, NULL, 0.950, 0.950, 1.000, 0.900, 0.900, 0, 0, 0, 2, 2, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_d006', '1.0', 'ws_spec0001', 'Traversal Tracking：走訪計數', 'Traversal Tracking: measuring real usage', 'factual', 'plain', '節點與 Edge 各自記錄走訪數據。節點記錄：traversal_count（總走訪次數）、unique_traverser_count（不重複訪客數）。Edge 記錄：traversal_count、rating_avg（1–5 平均評分，無評分時為 null）、rating_count。走訪透過 API 的 POST /nodes/{id}/traverse 或 POST /edges/{id}/traverse 記錄。MCP tool traverse_edge 也會觸發計數。這些數字反映知識的實際使用頻率，不只是被記錄的事實。', 'Nodes and edges each track traversal data. Nodes record: traversal_count (total visits) and unique_traverser_count (distinct actors). Edges record: traversal_count, rating_avg (1–5 average, null if no ratings), and rating_count. Traversals are recorded via POST /nodes/{id}/traverse or POST /edges/{id}/traverse in the REST API, or via the MCP tool traverse_edge. These numbers reflect actual knowledge usage frequency, not just what was recorded.', '{data-model,traversal,usage-tracking}', 'public', 'memtrace-spec', '2026-04-11 00:00:00+00', NULL, 'c4d5e6f7a2b3c4d5e6f7a2b3c4d5e6f7a2b3c4d5e6f7a2b3c4d5e6f7a2b3c4d5', 'human', NULL, NULL, NULL, NULL, 0.950, 0.950, 1.000, 0.900, 0.900, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_d4ea05e2', '1.0', 'ws_spec0001', '記憶節點信任分數', 'Memory Node Trust Score', 'factual', 'markdown', '`memory_nodes` 表中的 `trust_score` 欄位類型為 NUMERIC(4,3)，表示 0 到 1 之間的綜合信任分數。', 'The `trust_score` column in the `memory_nodes` table is of type NUMERIC(4,3), representing a composite trust score between 0 and 1.', '{database,schema,memory_nodes,column,score}', 'public', 'system', '2026-04-24 11:25:39.130605+00', NULL, '7c28f4b6744720099944e0b00fe9f6eacea46d6715cdde3f103aa4ba4cab8d00', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_playbook_003', '1.0', 'ws_spec0001', '最佳實踐：區分節點類型', 'Best Practice: Distinguishing Node Types', 'factual', 'markdown', '### 內容類型指南
- **事實性 (Factual)**：客觀事實、技術規格、定義。
- **程序性 (Procedural)**：行動步驟、SOP、操作指南。
- **偏好性 (Preference)**：團隊決策、設計偏好、選擇理由。
- **背景性 (Context)**：專案背景、高層次哲學、設計意圖。', '### Content Type Guide
- **Factual**: Objective facts, technical specs, definitions.
- **Procedural**: Action steps, SOPs, how-to guides.
- **Preference**: Team decisions, design preferences, rationale for choices.
- **Context**: Project background, high-level philosophy, design intent.', '{best-practice,content-type,guide}', 'public', 'system', '2026-04-24 13:35:31.814382+00', NULL, 'manual_playbook_003', 'ai', NULL, NULL, NULL, NULL, 0.500, 0.500, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_5b9dd113', '1.0', 'ws_spec0001', '記憶導出功能', 'Memory Export Functionality', 'factual', 'markdown', '雿輻?隞亙??嗅?撌乩?閮?臬?唳?唳?獢?Users can export their current working memory to a local file.', '雿輻?隞亙??嗅?撌乩?閮?臬?唳?唳?獢?Users can export their current working memory to a local file.', '{memory-management,export}', 'public', 'system', '2026-04-24 11:25:39.214139+00', NULL, 'e642c5361a573c1ec70f8f5f549a951819bcedae6c4c0110291c72e3bde360d4', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_g001', '1.0', 'ws_spec0001', 'Decay：Edge 權重的自然衰減', 'Decay: natural weight reduction on edges', 'factual', 'markdown', 'Edge 權重隨時間依以下公式衰減（v1）：

```
weight(t) = w₀ × 0.5 ^ (days_since_last_access / half_life)
```

**核心原則**：**Decay 塑造注意力，不塑造存在**。沒有東西因 decay 而被刪除。

**Edge 狀態轉換**：當 `weight < min_weight`（預設 0.1），Edge 進入 `faded` 狀態：
- 從預設 Graph View 與 traversal 結果隱藏
- 仍存於資料庫（`status = ''faded''`），可由原作者或 admin 還原
- API 加 `include_faded=true` 仍可查詢

**節點層級**：
- `evergreen` 工作區：節點本身依「觀察期內走訪計數」歸檔（§7.3），不受時間衰減
- `ephemeral` 工作區：當所有相連 Edge 皆 faded，節點自動 archived

**Pinned 例外**：`pinned: true` 的節點與 Edge 完全豁免於衰減與計數歸檔。

衰減觸發：每日由 `apply_edge_decay()` SQL 函式執行（鏡射 `packages/core/src/decay.ts`）。', 'Edge weight decays over time according to (v1):

```
weight(t) = w₀ × 0.5 ^ (days_since_last_access / half_life)
```

**Core principle**: **Decay shapes attention, not existence.** Nothing is deleted by decay alone.

**Edge state transition**: When `weight < min_weight` (default 0.1), the edge transitions to `faded`:
- Hidden from default Graph View and traversal results
- Still stored in the database (`status = ''faded''`); restorable by the original author or admin
- Queryable via API with `include_faded=true`

**Node level**:
- `evergreen` workspace: nodes are archived based on traversal count within an observation window (§7.3), not time-based
- `ephemeral` workspace: when all connected edges are faded, the node is auto-archived

**Pinned exemption**: Nodes and edges with `pinned: true` are fully exempt from both time-decay and traversal-count archiving.

Trigger: daily by the `apply_edge_decay()` SQL function (mirrors `packages/core/src/decay.ts`).', '{graph-mechanics,decay,weight,faded,archive}', 'public', 'memtrace-spec', '2026-04-11 00:00:00+00', NULL, 'd5e6f7a2b3c4d5e6f7a2b3c4d5e6f7a2b3c4d5e6f7a2b3c4d5e6f7a2b3c4d5e6', 'human', NULL, NULL, NULL, NULL, 0.950, 0.950, 1.000, 0.950, 0.900, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_g002', '1.0', 'ws_spec0001', 'Co-Access Boost：共存取加成', 'Co-Access Boost: strengthening edges through use', 'factual', 'markdown', '當兩個相連節點在同一情境下被循序或同時存取（Co-Access），對應 Edge 的 weight 會得到加成，加成量依 relation type 而異：

| Relation | Boost |
|----------|-------|
| `depends_on` | +0.30 |
| `extends` | +0.20 |
| `related_to` | +0.15 |
| `contradicts` | +0.10 |

同時觸發：co_access_count +1、last_co_accessed 更新、weight 上限 1.0。API 路徑 POST /edges/{id}/traverse 或 MCP tool traverse_edge 皆會觸發 co-access boost。', 'When two connected nodes are accessed sequentially or simultaneously in the same context (Co-Access), the corresponding edge''s weight receives a boost based on relation type:

| Relation | Boost |
|----------|-------|
| `depends_on` | +0.30 |
| `extends` | +0.20 |
| `related_to` | +0.15 |
| `contradicts` | +0.10 |

Also increments co_access_count, updates last_co_accessed, and caps weight at 1.0. Triggered by POST /edges/{id}/traverse or MCP tool traverse_edge.', '{graph-mechanics,co-access,boost,weight}', 'public', 'memtrace-spec', '2026-04-11 00:00:00+00', NULL, 'e6f7a2b3c4d5e6f7a2b3c4d5e6f7a2b3c4d5e6f7a2b3c4d5e6f7a2b3c4d5e6f7', 'human', NULL, NULL, NULL, NULL, 0.950, 0.950, 1.000, 0.950, 0.900, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_8145c1ad', '1.0', 'ws_spec0001', '個人工作區邀請限制', 'Private Workspace Invitation Restriction', 'factual', 'markdown', '無法為「私有」工作區發出邀請，且不能添加非所有者使用者。', 'Invitations cannot be issued for `private` workspaces, and no non-owner user may be added.', '{workspace-type,private,invitation,restriction}', 'public', 'system', '2026-04-24 11:25:39.666242+00', NULL, '435ab2d509c4abf3d81388b7bcca68ec976f2116156fc76bc3ee0e5a9a6baf63', 'ai', NULL, NULL, NULL, NULL, 0.593, 0.800, 1.000, 0.010, 0.500, 0, 0, 0, 1, 1, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_76037494', '1.0', 'ws_spec0001', '手動創建與編輯記憶節點', 'Manual Memory Node Creation & Editing', 'procedural', 'markdown', '使用者可以透過 UI 中專用的編輯面板手動創建和編輯記憶節點。', 'Users can manually create and edit Memory Nodes through a dedicated editor panel within the UI.', '{memory-node,creation,editing,ui}', 'public', 'system', '2026-04-24 11:25:39.311534+00', NULL, 'e1d24b6e7c1be1933fca1f5c438ed6deae3ddb38f9887c720feb6bd537e5e981', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_bd6996dd', '1.0', 'ws_spec0001', '記憶節點內容輸入模式', 'Memory Node Content Input Modes', 'factual', 'markdown', '每個記憶節點的正文 (`content.body`) 支持兩種輸入模式。', 'Each Memory Node body (`content.body`) supports two input modes.', '{memory-node,content,input}', 'public', 'system', '2026-04-24 11:25:39.354196+00', NULL, '0d9fdbf1ccbc62f8451c6a16bd834ea4e2ef14bebea32091c6e3fb59657e02f4', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_g003', '1.0', 'ws_spec0001', 'Edge 關係類型：四種語意方向', 'Edge relation types: four semantic directions', 'factual', 'markdown', '| Relation | 語意 | 使用時機 |
|----------|------|----------|
| `depends_on` | 來源節點的成立依賴目標節點 | A 的流程前提是 B 的概念 |
| `extends` | 來源節點延伸或補充目標節點 | A 是 B 的進階版本 |
| `related_to` | 有相關性但無明確依賴方向 | A 和 B 都屬於同一主題 |
| `contradicts` | 來源節點的內容與目標節點矛盾 | A 的結論與 B 相衝突 |

選擇正確的 relation type 很重要，因為它決定了 co-access boost 的強度，以及 AI agent 在遍歷圖時如何解讀關係。', '| Relation | Semantics | When to use |
|----------|-----------|-------------|
| `depends_on` | Source requires target to be valid | A''s process presupposes B''s concept |
| `extends` | Source extends or supplements target | A is an advanced version of B |
| `related_to` | Related without clear dependency direction | A and B belong to the same topic |
| `contradicts` | Source conflicts with target | A''s conclusion conflicts with B |

Choosing the correct relation type matters: it determines co-access boost strength and how AI agents interpret the relationship when traversing the graph.', '{graph-mechanics,relation-type,edge,schema}', 'public', 'memtrace-spec', '2026-04-11 00:00:00+00', NULL, 'f7a2b3c4d5e6f7a2b3c4d5e6f7a2b3c4d5e6f7a2b3c4d5e6f7a2b3c4d5e6f7a2', 'human', NULL, NULL, NULL, NULL, 0.950, 0.950, 1.000, 0.950, 0.900, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_i001', '1.0', 'ws_spec0001', '使用者認證：Email 與密碼', 'User authentication: email and password', 'procedural', 'plain', 'MemTrace 採用 Email + Password 認證路徑。安全措施包括：bcrypt 雜湊（cost ≥ 12）、密碼政策（8–128 字元、大小寫+數字、HaveIBeenPwned 洩漏檢查）、email 驗證信（24 小時效期）、失敗 5 次鎖定 15 分鐘。登入後核發 JWT Session（7 天），透過 Authorization: Bearer 標頭傳遞，登出以 blocklist 立即失效。目前不支援第三方 OAuth 登入，以簡化認證表面並減少外部依賴。', 'MemTrace uses Email + Password authentication. Security measures include: bcrypt hash (cost ≥ 12), password policy (8–128 chars, upper+lower+digit, HaveIBeenPwned check), verification email (24h expiry), and 5-failure lockout for 15 minutes. Upon login, a JWT session (7 days) is issued and passed via the Authorization: Bearer header. Logout is handled via an immediate blocklist. Third-party OAuth is currently not supported to simplify the authentication surface and reduce external dependencies.', '{auth,security,jwt,password-policy}', 'public', 'memtrace-spec', '2026-04-11 00:00:00+00', NULL, 'a4b5c6d7e8f9a4b5c6d7e8f9a4b5c6d7e8f9a4b5c6d7e8f9a4b5c6d7e8f9a4b5', 'human', NULL, NULL, NULL, NULL, 0.950, 0.950, 1.000, 0.900, 0.900, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_a6a2a683', '1.0', 'ws_spec0001', '記憶節點 ID', 'Memory Node ID', 'factual', 'markdown', '`memory_nodes` 表中的 `id` 欄位是主鍵，類型為 TEXT，例如 `mem_abc123`。', 'The `id` column in the `memory_nodes` table is the primary key, of type TEXT, e.g., `mem_abc123`.', '{database,schema,memory_nodes,column}', 'public', 'system', '2026-04-24 11:25:38.856937+00', NULL, 'b9327bb4b77a1cdb973a11d5f37e2eea745b8d5da337fc61dc0c6f2f5bcc77b7', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_d07c29a1', '1.0', 'ws_spec0001', '更新時間欄位 (provenance.updated_at)', 'Updated At Field (`provenance.updated_at`)', 'factual', 'markdown', '`provenance.updated_at`甈???箏?銝莎??交????澆?嚗?銝敹????典?憪遣蝡?瘥活蝺刻摩??身摰?The `provenance.updated_at` field is an optional string (date-time format) that is set on every edit after initial creation.', '`provenance.updated_at`甈???箏?銝莎??交????澆?嚗?銝敹????典?憪遣蝡?瘥活蝺刻摩??身摰?The `provenance.updated_at` field is an optional string (date-time format) that is set on every edit after initial creation.', '{}', 'public', 'system', '2026-04-24 11:25:39.88639+00', NULL, 'fde73fc348c926db7350610cbd46f6cc5b253b7227e3720fad21e1ac55261d00', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_i002', '1.0', 'ws_spec0001', 'REST API 與外部 API Key', 'REST API and external API keys', 'factual', 'markdown', '外部服務與腳本以 **API Key** 認證（格式：`mt_live_<hex>`），而非 session JWT。Key 可綁定至特定 workspace 或跨 workspace，建立後完整金鑰只顯示一次。四種 scope：

| Scope | 權限 |
|-------|------|
| `kb:read` | 讀取 KB、節點、Edge |
| `kb:write` | 建立與編輯節點、Edge |
| `node:traverse` | 記錄走訪事件 |
| `node:rate` | 提交路徑評分（1–5）|

所有 API 端點前綴 `/api/v1`，使用 `Authorization: Bearer` 傳遞 key 或 token（伺服器依前綴區分）。', 'External services and scripts authenticate with **API Keys** (format: `mt_live_<hex>`), not session JWTs. Keys may be scoped to a specific workspace or valid across all. Full key value shown only once at creation. Four scopes:

| Scope | Grants |
|-------|--------|
| `kb:read` | Read KBs, nodes, edges |
| `kb:write` | Create and edit nodes, edges |
| `node:traverse` | Record traversal events |
| `node:rate` | Submit path ratings (1–5) |

All API endpoints prefixed with `/api/v1`, using `Authorization: Bearer` for both keys and session tokens (server distinguishes by prefix).', '{api,api-key,access-control,integration}', 'public', 'memtrace-spec', '2026-04-11 00:00:00+00', NULL, 'b5c6d7e8f9a4b5c6d7e8f9a4b5c6d7e8f9a4b5c6d7e8f9a4b5c6d7e8f9a4b5c6', 'human', NULL, NULL, NULL, NULL, 0.950, 0.950, 1.000, 0.950, 0.900, 0, 0, 0, 2, 1, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_k001', '1.0', 'ws_spec0001', 'Knowledge Base：知識庫（Workspace）', 'Knowledge Base: the container workspace', 'factual', 'plain', 'Knowledge Base（又稱 Workspace）是 Memory Node 與 Edge 的容器，對應一個獨立的知識領域或專案。每個使用者可建立多個知識庫。知識庫本身有共享層級（public / restricted / private），與節點的 visibility 各自獨立——有效存取權取兩者較嚴格的一方。知識庫可以從空白開始，也可以從一份文件啟動並由 AI 萃取節點。ID 格式：ws_<hex8>。', 'A Knowledge Base (Workspace) is the container for Memory Nodes and Edges, corresponding to an independent knowledge domain or project. Users can create multiple Knowledge Bases. A Knowledge Base has its own sharing level (public / restricted / private), independent from node-level visibility — effective access is the more restrictive of the two. A Knowledge Base may be started blank or bootstrapped from a document with AI extraction. ID format: ws_<hex8>.', '{knowledge-base,workspace,container}', 'public', 'memtrace-spec', '2026-04-11 00:00:00+00', NULL, 'a3b4c5d6e7f8a3b4c5d6e7f8a3b4c5d6e7f8a3b4c5d6e7f8a3b4c5d6e7f8a3b4', 'human', NULL, NULL, NULL, NULL, 0.950, 0.950, 1.000, 0.900, 0.900, 0, 0, 0, 3, 1, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_k002', '1.0', 'ws_spec0001', '知識庫共享層級：四種可見性', 'Knowledge Base sharing levels: four visibility tiers', 'factual', 'markdown', '| 層級 | 識別碼 | 說明 |
|------|--------|------|
| 全公開 | `public` | 任何人（含未登入）皆可探索與閱讀 `public` 節點 |
| 有條件公開 | `conditional_public` | 任何人皆可看到圖譜結構（拓撲），但節點內容隱藏；可向管理員提交加入申請 |
| 限制公開 | `restricted` | 知識庫對非成員不可見，必須由 admin 明確邀請才能加入 |
| 私有 | `private` | 僅擁有者可見，無法發出邀請 |

**重要**：visibility 在建立時設定後**不可變更**（immutable）。任何 `PATCH /workspaces/{ws_id}` 含 `visibility` 欄位的請求一律回 `400 Immutable field: visibility`。建立時 UI 必須清楚顯示四個層級，使用者必須明確確認。

節點層級的 visibility（public / team / private）獨立於知識庫層級，最終存取權取兩者較嚴格的一方。', '| Tier | Identifier | Description |
|------|------------|-------------|
| Public | `public` | Anyone (incl. unauthenticated) can discover and read `public` nodes |
| Conditional Public | `conditional_public` | Anyone can see graph topology, but node content is hidden; users may submit a join request to admins |
| Restricted | `restricted` | KB is invisible to non-members; entry requires explicit admin invitation |
| Private | `private` | Owner-only; invitations cannot be issued |

**Important**: visibility is **immutable** after creation. Any `PATCH /workspaces/{ws_id}` containing `visibility` is rejected with `400 Immutable field: visibility`. The creation UI must show all four tiers clearly with inline descriptions and require explicit user confirmation.

Node-level visibility (`public` / `team` / `private`) is independent of KB-level visibility — effective access is the more restrictive of the two.', '{knowledge-base,sharing,visibility,access-control,four-tier}', 'public', 'memtrace-spec', '2026-04-11 00:00:00+00', NULL, 'b4c5d6e7f8a3b4c5d6e7f8a3b4c5d6e7f8a3b4c5d6e7f8a3b4c5d6e7f8a3b4c5', 'human', NULL, NULL, NULL, NULL, 0.950, 0.950, 1.000, 0.950, 0.900, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_10a89b1f', '1.0', 'ws_spec0001', '受邀使用者角色分配', 'Invited User Role Assignment', 'factual', 'markdown', '受邀使用者將以邀請令牌中指定的角色添加到工作區中。', 'Invited users are added to the workspace with the role specified in the invite token.', '{roles,invitation,access-control}', 'public', 'system', '2026-04-24 11:25:39.631905+00', NULL, '7cf62b3b242f03e9b7889e041598b464fd164b5d7d1f01cba4a9eda874bbb8ed', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_79dce6e3', '1.0', 'ws_spec0001', '記憶節點 Schema 版本', 'Memory Node Schema Version', 'factual', 'markdown', '`memory_nodes` 表中的 `schema_version` 欄位類型為 TEXT，固定為 ''1.0''。', 'The `schema_version` column in the `memory_nodes` table is of type TEXT, fixed to ''1.0''.', '{database,schema,memory_nodes,column}', 'public', 'system', '2026-04-24 11:25:38.872833+00', NULL, 'ba4fdaf3d15b468f342627140d094e4d7edd8e03d683ca2e527e33dca2be84ed', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_o001', '1.0', 'ws_spec0001', '初次使用引導：Web UI 精靈', 'First-run onboarding: web UI wizard', 'procedural', 'plain', '首次登入後自動顯示，完成後永久不再彈出（可從 Settings → Getting Started 重新開啟）。八步流程：

① 建立帳號（Email + Password）
② 驗證 Email
③ 命名第一個知識庫（雙語名稱 + 可見性，預設 private）
④ 選擇知識庫類型：Evergreen（長效型，預設）或 Ephemeral（短效型）— **建立後不可變更**
⑤ 選擇起點：空白 或 上傳文件（.md/.txt/.pdf/.docx）
⑥ AI Provider 設定（僅文件路徑顯示，可跳過）
⑦ Review 萃取候選節點（至少接受一個才能繼續）
⑧ 完成（顯示三個捷徑：手動新增節點、邀請成員、連接 AI 工具）

進度以伺服器端的 `onboarding` 物件追蹤（`steps_done[]` + `steps_skipped[]`），中斷後可從上次未完成步驟恢復。`completed: true` 後永遠不再自動顯示。', 'Shown automatically on first login; permanently dismissed after completion (re-accessible from Settings → Getting Started). Eight-step flow:

① Create account (Email + Password)
② Verify email
③ Name first Knowledge Base (bilingual name + visibility, default private)
④ Choose Knowledge Base Type: Evergreen (default) or Ephemeral — **immutable after creation**
⑤ Choose starting point: blank or upload document (.md/.txt/.pdf/.docx)
⑥ AI provider setup (shown only on document path, skippable)
⑦ Review extracted candidate nodes (at least one must be accepted to advance)
⑧ Done (three shortcuts: add first node, invite someone, connect AI tool)

Progress tracked server-side via the `onboarding` object (`steps_done[]` + `steps_skipped[]`); resumes from the last incomplete step after interruption. Once `completed: true`, the wizard is never shown automatically again.', '{onboarding,ui,wizard,ux,kb-type}', 'public', 'memtrace-spec', '2026-04-11 00:00:00+00', NULL, 'd7e8f9a4b5c6d7e8f9a4b5c6d7e8f9a4b5c6d7e8f9a4b5c6d7e8f9a4b5c6d7e8', 'human', NULL, NULL, NULL, NULL, 0.950, 0.950, 1.000, 0.900, 0.900, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_45b2269d', '1.0', 'ws_spec0001', '記憶節點作者', 'Memory Node Author', 'factual', 'markdown', '`memory_nodes` 表中的 `author` 欄位類型為 TEXT，存儲記憶節點的作者。', 'The `author` column in the `memory_nodes` table is of type TEXT, storing the author of the memory node.', '{database,schema,memory_nodes,column}', 'public', 'system', '2026-04-24 11:25:39.051144+00', NULL, 'a6702d11b7568adb799d43ae69e7fccd6ac9372871cf1d585ea67034809ab809', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_o002', '1.0', 'ws_spec0001', '初次使用引導：CLI memtrace init', 'First-run onboarding: CLI memtrace init', 'procedural', 'plain', '執行 `memtrace init` 啟動終端機互動式精靈，五步：

① 認證：登入既有帳號 / 建立新帳號
② 建立第一個知識庫：英文名稱 + 可見性（private / restricted / public，預設 private）
③ 選擇 KB 類型：evergreen（長效型，預設）或 ephemeral（短效型）— **建立後不可變更**
④ AI Provider 設定（可 Enter 跳過）：選擇 openai / anthropic 並輸入 API Key（自動測試連線）
⑤ 匯入文件（可 Enter 跳過）：輸入檔案路徑或 URL

設定寫入 `~/.memtrace/config.json`，立即 `chmod 600`。

重複執行：詢問要更新 AI provider / 切換預設工作區 / 重新認證 / 退出，不自動覆寫現有設定。', 'Running `memtrace init` launches an interactive terminal wizard with five steps:

① Authentication: log in to existing account / create new account
② Create first Knowledge Base: English name + visibility (private / restricted / public, default private)
③ Choose KB type: evergreen (default) or ephemeral — **immutable after creation**
④ AI provider setup (press Enter to skip): choose openai / anthropic and enter API key (auto-tests connection)
⑤ Import document (press Enter to skip): provide file path or URL

Config written to `~/.memtrace/config.json` with `chmod 600` immediately.

Re-running: prompts which setting to update — AI provider / switch default workspace / re-authenticate / exit. Existing values are not overwritten unless explicitly selected.', '{onboarding,cli,init,setup,kb-type}', 'public', 'memtrace-spec', '2026-04-11 00:00:00+00', NULL, 'e8f9a4b5c6d7e8f9a4b5c6d7e8f9a4b5c6d7e8f9a4b5c6d7e8f9a4b5c6d7e8f9', 'human', NULL, NULL, NULL, NULL, 0.950, 0.950, 1.000, 0.900, 0.900, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_p003', '1.0', 'ws_spec0001', '人與 AI 的協作知識圖', 'Co-authorship between humans and AI', 'context', 'plain', 'MemTrace 中，人與 AI 寫入同一張圖。圖的結構——Edge 的權重、走訪計數、評分——反映哪些知識實際上被證明有用，而非只是被記錄。Decay 確保圖的誠實性：沒人走的連結自然消退，頻繁被使用的連結強化並持續存在。最終形成一個圍繞「真正重要的知識」自我組織的知識庫。', 'In MemTrace, humans and AI write into the same graph. The graph''s structure — edge weights, traversal counts, path ratings — reflects which knowledge has actually proven useful, not just what was recorded. Decay keeps the graph honest: connections nobody follows fade; connections visited frequently, rated positively, or extended by other nodes strengthen and persist. The result is a knowledge base that self-organises around what actually matters.', '{philosophy,core,ai,co-authorship}', 'public', 'memtrace-spec', '2026-04-11 00:00:00+00', NULL, 'c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4', 'human', NULL, NULL, NULL, NULL, 0.950, 0.950, 1.000, 0.900, 0.900, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_2c1bd9d5', '1.0', 'ws_spec0001', '對話 API：發送消息 (POST /chat)', 'Chat API: Send Message (POST /chat)', 'procedural', 'markdown', '透過 POST 請求向指定的工作區發送消息。可以傳遞可選的 `session_id` 以繼續現有對話。', 'Sends a message to a specified workspace via a POST request. An optional `session_id` can be passed to continue an existing conversation.', '{api,chat,message,conversation,post}', 'public', 'system', '2026-04-24 11:31:27.693915+00', NULL, '6b15654db2b55b29e7943d96ebfe8bd110b52e5febab150f4e704a1b2117ab6b', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_6d8524a7', '1.0', 'ws_spec0001', '新數據模型欄位', 'New Data Model Fields', 'factual', 'markdown', '數據模型中新增了 `version`, `conflict_status`, `conflict_detail`, `source_doc_node_id`, 和 `source_paragraph_ref` 等欄位。', 'New fields `version`, `conflict_status`, `conflict_detail`, `source_doc_node_id`, and `source_paragraph_ref` have been added to the data model.', '{data-model,schema,update}', 'public', 'system', '2026-04-24 11:31:27.718604+00', NULL, 'ce86c3a5dbe8e825cb9600f783656939236cc44481125fd58c074491c61e572c', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_1fc9c6b4', '1.0', 'ws_spec0001', 'AI 代理工作流程：搜尋現有節點', 'AI Agent Workflow: Search Existing Nodes', 'procedural', 'markdown', 'AI 代理在建立新節點前，應先呼叫 `search_nodes("認證機制")` 等功能，確認知識庫中是否已存在相關節點，避免重複。', 'Before creating a new node, an AI agent should first call `search_nodes("authentication mechanism")` or similar functions to check if related nodes already exist in the knowledge base, preventing duplication.', '{ai代理,工作流程,節點建立,搜尋}', 'public', 'system', '2026-04-25 02:40:02.057085+00', NULL, 'ce76ce6a71d629231411b6006cde3379e98c2074b2cf40c3fc050542c9a16cfb', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_dc852972', '1.0', 'ws_spec0001', 'MEMTRACE_TOKEN 安全提醒', 'MEMTRACE_TOKEN Security Reminder', 'factual', 'markdown', '關於 `MEMTRACE_TOKEN` 的安全提醒文字已加入伺服器啟動時的標準錯誤日誌 (stderr log) 中。', 'A security reminder text regarding `MEMTRACE_TOKEN` has been added to the server startup''s standard error log (stderr log).', '{環境變數,安全性,日誌}', 'public', 'system', '2026-04-25 02:39:36.926692+00', NULL, '656f7b6e924f07b2bef8f84a0a2a011de8f9270d6618c86707eb069cb8973af7', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_5e486c31', '1.0', 'ws_spec0001', '記憶節點內容類型', 'Memory Node Content Type', 'factual', 'markdown', '`memory_nodes` 表中的 `content_type` 欄位類型為 ENUM，可能的值為 `factual` / `procedural` / `preference` / `context`。', 'The `content_type` column in the `memory_nodes` table is of type ENUM, with possible values `factual` / `procedural` / `preference` / `context`.', '{database,schema,memory_nodes,column,enum}', 'public', 'system', '2026-04-24 11:25:38.931076+00', NULL, '179fb1239331cc5bbd9a469a659b3dfaa27968ce2e431f888b057fc4aff9e393', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_42669ba9', '1.0', 'ws_spec0001', 'POST /edges/{edge_id}/rate 請求體', 'POST /edges/{edge_id}/rate Request Body', 'factual', 'markdown', '請求體包含一個 `rating` 欄位（1 到 5 之間的整數）和一個可選的 `note` 欄位。每個執行者對每條邊只能提交一次評分，後續提交將覆蓋先前的評分。', 'The request body includes a `rating` field (an integer between 1 and 5) and an optional `note` field. Only one rating per actor per edge is enforced, with subsequent submissions overwriting previous ratings.', '{api,request-body,rating,constraints}', 'public', 'system', '2026-04-24 11:25:40.239378+00', NULL, 'a5a308930ff1aefa0598e53a5f2529fd427006c614b29d6f873d4ac68e4b6ed4', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_45350e40', '1.0', 'ws_spec0001', 'AI 呼叫執行位置', 'AI Call Execution Location', 'factual', 'markdown', 'AI 呼叫由客戶端或伺服器使用使用者提供的金鑰發出。', 'AI calls are made from the client or server using the user''s supplied key.', '{ai,client-side,server-side,api}', 'public', 'system', '2026-04-24 11:25:40.470219+00', NULL, 'a3a3895d6cb9185703b032de058c6dd65efd9cc05ede25cb259018cb9089e18c', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_d2b5ef2f', '1.0', 'ws_spec0001', 'MCP 伺服器中的資源 URI 處理', 'Resource URI Handling in MCP Server', 'factual', 'markdown', 'MCP 伺服器根據請求參數中的 URI，處理對 `memtrace://guide/node` 和 `memtrace://guide/edge` 的請求，並回傳對應的 Markdown 內容。對於未知資源 URI，伺服器會拋出錯誤。', 'The MCP server handles requests for `memtrace://guide/node` and `memtrace://guide/edge` URIs based on the request parameters, returning corresponding Markdown content. For unknown resource URIs, the server throws an error.', '{mcp,server,resource,uri,api}', 'public', 'system', '2026-04-25 02:39:28.168325+00', NULL, '2a481a49932b3fe3aaa57af8df71c64f827b6103478398eaaae36179a315ab44', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_e0ebc6e5', '1.0', 'ws_spec0001', 'README/使用文件更新：單庫使用情境', 'README/Usage Document Update: Single Workspace Scenario', 'procedural', 'markdown', 'README 和使用文件已更新，說明單庫（最簡單）使用情境：只需設定 `MEMTRACE_WS` 環境變數，並在呼叫工具時不傳遞 `workspace_id` 參數。', 'The README and usage documentation have been updated to describe the single workspace (simplest) scenario: only set the `MEMTRACE_WS` environment variable and omit the `workspace_id` parameter when calling tools.', '{文件,使用情境,工作區}', 'public', 'system', '2026-04-25 02:39:36.230691+00', NULL, 'e59e02c6a9011e9b691d3806389ed96d8988532eecc222d1c30c7876176156ef', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_1b09b6ed', '1.0', 'ws_spec0001', '記憶節點準確性維度', 'Memory Node Accuracy Dimension', 'factual', 'markdown', '`memory_nodes` 表中的 `dim_accuracy` 欄位類型為 NUMERIC(4,3)，表示信任分數的一個維度。', 'The `dim_accuracy` column in the `memory_nodes` table is of type NUMERIC(4,3), representing a dimension of the trust score.', '{database,schema,memory_nodes,column,trust_dimension}', 'public', 'system', '2026-04-24 11:25:39.152271+00', NULL, '15656e7278fb5473c5f316278cbe9a4ad0be33234c87f6b7dd9d4e505fcd217b', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_fb026368', '1.0', 'ws_spec0001', '記憶節點英文標題', 'Memory Node English Title', 'factual', 'markdown', '`memory_nodes` 表中的 `title_en` 欄位類型為 TEXT，存儲記憶節點的英文標題。', 'The `title_en` column in the `memory_nodes` table is of type TEXT, storing the English title of the memory node.', '{database,schema,memory_nodes,column,i18n}', 'public', 'system', '2026-04-24 11:25:38.909891+00', NULL, '3a62af0adbac099be083237631539bac551d692c9362add2123ac306fa432351', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_033baf41', '1.0', 'ws_spec0001', 'NODE_GUIDE 內容定義', 'NODE_GUIDE Content Definition', 'factual', 'markdown', '`NODE_GUIDE` 常數定義了節點欄位規格、`content_type` 說明、`visibility` 說明、建立最佳實踐以及常見錯誤。', 'The `NODE_GUIDE` constant defines node field specifications, `content_type` explanation, `visibility` explanation, best practices for creation, and common errors.', '{node_guide,node,specification,documentation}', 'public', 'system', '2026-04-25 02:39:28.703205+00', NULL, 'e455fd7e83ae5aa06dfc303f056131a6fba3450abac4370621b5128c99d786f6', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_f2edb572', '1.0', 'ws_spec0001', '邊走訪統計數據結構', 'Edge Traversal Statistics Data Structure', 'factual', 'markdown', '邊響應中的 `traversal` 物件包含 `count`（走訪次數）、`rating_avg`（平均評分）和 `rating_count`（評分次數）欄位。', 'The `traversal` object in an edge response includes `count` (number of traversals), `rating_avg` (average rating), and `rating_count` (number of ratings) fields.', '{data-structure,traversal-stats,edge,rating}', 'public', 'system', '2026-04-24 11:25:40.274389+00', NULL, '44138550101d58d53cf07a6ec12d41ed6fae6e149da9cf27f11fffac79788237', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_c8db759e', '1.0', 'ws_spec0001', '連向封存節點的邊會自動衰減', '甇豢?蝭暺???鋡急楚??Edges Connected to Archived Nodes Are Faded', 'factual', 'markdown', '所有連向已封存節點的邊，其外觀會自動變為「衰減」狀態，但不會從資料庫中刪除。', '?????唳飛瑼?暺????楚?＊蝷綽?雿??◤?芷??All edges linked to an archived node are automatically faded in appearance but are not deleted from the database.', '{}', 'public', 'system', '2026-04-24 11:25:39.557633+00', NULL, 'e2889812266b17efc364454a6ee3ea5a6881e8250b720564bfa2dc84bbaddf20', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_fb0354ee', '1.0', 'ws_spec0001', '新增 MEMTRACE_TOKEN 環境變數', 'Add MEMTRACE_TOKEN Environment Variable', 'factual', 'markdown', '為支援 `list_workspaces` 及未來寫入工具存取 `/api/v1/workspaces`，新增 `MEMTRACE_TOKEN` 環境變數。此變數將 API token 注入 `apiFetch` 的 `Authorization: Bearer` 標頭中。', 'The `MEMTRACE_TOKEN` environment variable is added to support `list_workspaces` and future writing tools in accessing `/api/v1/workspaces`. This variable injects the API token into the `Authorization: Bearer` header of `apiFetch`.', '{環境變數,api,認證,安全性}', 'public', 'system', '2026-04-25 02:39:33.890766+00', NULL, '5a92752ad8e42bd741785135c860e72414dc35b7ea7f68525e8f904ee3b40f5f', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_f8057a39', '1.0', 'ws_spec0001', '工具 description 更新', 'Tool Description Update', 'procedural', 'markdown', '`search_nodes`、`get_node`、`traverse`、`list_by_tag` 等工具的描述已更新，新增一行說明如何使用 `workspace_id` 參數查詢特定知識庫，或省略以使用預設值 `MEMTRACE_WS`。', 'The descriptions for tools like `search_nodes`, `get_node`, `traverse`, and `list_by_tag` have been updated to include a line explaining how to pass `workspace_id` to query a specific KB, or omit it to use the configured default (`MEMTRACE_WS`).', '{工具,文件,工作區}', 'public', 'system', '2026-04-25 02:39:37.786358+00', NULL, '619066f74e4abdca14e319bcd9cbfe613562619b098582a5070872003bddedae', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_f83d6e1b', '1.0', 'ws_spec0001', 'AI 代理工作流程：建立新節點', 'AI Agent Workflow: Create New Node', 'procedural', 'markdown', 'AI 代理應呼叫 `create_node` 函數來建立新節點，並提供 `title_zh`、`title_en`、`content_type`、`content_format`、`body_zh` 等欄位。特別是，AI 代理必須設定 `source_type: "ai"`。', 'AI agents should call the `create_node` function to create new nodes, providing fields such as `title_zh`, `title_en`, `content_type`, `content_format`, and `body_zh`. Specifically, AI agents must set `source_type: "ai"`.', '{ai代理,工作流程,節點建立,api}', 'public', 'system', '2026-04-25 02:39:25.137437+00', NULL, '04fe85dcca072d61a5b4587e35961b2be16ec3bc52a01b288b2e17f13a480e33', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_71aebf92', '1.0', 'ws_spec0001', '驗收情境：查詢指定工作區節點', 'Acceptance Scenario: Query Specific Workspace Nodes', 'procedural', 'markdown', '驗收情境之一：呼叫 `search_nodes(query="認證", workspace_id="ws_project_abc")` 應能成功查詢 `ws_project_abc` 工作區中的節點。', 'One acceptance scenario: calling `search_nodes(query="認證", workspace_id="ws_project_abc")` should successfully query nodes within the `ws_project_abc` workspace.', '{驗收測試,工作區,查詢}', 'public', 'system', '2026-04-25 02:39:48.355492+00', NULL, '8afa92eb018c4301321a6ed7b199a7ec28ba488e9f2e899f75ef028ff4ea9e09', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_ff4e804e', '1.0', 'ws_spec0001', '入門精靈自動顯示條件', '雿輻??撠?撠?＊蝷箸?隞?Onboarding Wizard Auto-Display Condition', 'factual', 'markdown', '銝?圳completed: true`嚗蝙?刻?撠?撠?銝??芸?憿舐內??Once `completed: true`, the onboarding wizard is never shown automatically again.', '銝?圳completed: true`嚗蝙?刻?撠?撠?銝??芸?憿舐內??Once `completed: true`, the onboarding wizard is never shown automatically again.', '{onboarding,ui,completion}', 'public', 'system', '2026-04-24 11:25:40.415959+00', NULL, '0c8adbf4e2f1b9f5bc07fac93f031d00d9a0cf53f41896d28bb69c72e0415ce9', 'ai', NULL, NULL, NULL, NULL, 0.593, 0.800, 1.000, 0.010, 0.500, 0, 0, 0, 1, 1, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_62d07b1d', '1.0', 'ws_spec0001', 'AI 代理工作流程：確認節點建立狀態', 'AI Agent Workflow: Confirm Node Creation Status', 'procedural', 'markdown', '在 AI 代理呼叫 `create_node` 後，若 API 回傳 201 狀態碼，應呼叫 `traverse(node.id)` 確認邊已建立；若回傳 202 狀態碼並帶有 `review_id`，則應呼叫 `list_review_queue()` 確認審核佇列狀態。', 'After an AI agent calls `create_node`, if the API returns a 201 status code, it should call `traverse(node.id)` to confirm edge creation. If a 202 status code with a `review_id` is returned, it should call `list_review_queue()` to check the review queue status.', '{ai代理,工作流程,節點建立,api,審核流程}', 'public', 'system', '2026-04-25 02:39:26.18783+00', NULL, '900865976521e0a50bd83f5ae1e63ce3cad6a2db9ff6e46516532a3dde144e24', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_1185cce5', '1.0', 'ws_spec0001', '建立 API 金鑰', 'Create API Key', 'procedural', 'markdown', '使用 `curl` 命令向 `/api/v1/users/me/api-keys` 端點發送 POST 請求，以建立一個新的 API 金鑰。請求需包含授權 Bearer Token、Content-Type 為 `application/json`，以及包含金鑰名稱和範圍（例如 `kb:read`, `kb:write`）的 JSON 資料。', 'Use a `curl` command to send a POST request to the `/api/v1/users/me/api-keys` endpoint to create a new API key. The request must include an Authorization Bearer Token, Content-Type as `application/json`, and JSON data containing the key name and scopes (e.g., `kb:read`, `kb:write`).', '{}', 'public', 'system', '2026-04-25 02:39:30.610529+00', NULL, '64f3676e69b048faf93b180a7bd9c33f59d965f34af7acd616c3933fa4b44cd7', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_76d6491f', '1.0', 'ws_spec0001', '.mcp.json 設定檔更新為單實例寫法', '.mcp.json Configuration Update to Single Instance', 'procedural', 'markdown', '`.mcp.json` 設定檔已更新為單實例寫法，移除了對每個知識庫一個實例的依賴，並整合了 token 設定。這簡化了配置，使其更易於管理。', 'The `.mcp.json` configuration file has been updated to a single-instance approach, removing the dependency on one instance per knowledge base and integrating token settings. This simplifies configuration and makes it easier to manage.', '{設定檔,mcp,架構,配置}', 'public', 'system', '2026-04-25 02:39:38.497095+00', NULL, '61e28dfaf329b22ab626103c29e89e1dc61b98f08be7a0c17c2ca073c04ef97c', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_3b303d15', '1.0', 'ws_spec0001', '處理 createNode/updateNode 的 422 驗證錯誤', 'Handle 422 Validation Errors for createNode/updateNode', 'procedural', 'markdown', '當 createNode 或 updateNode API 回傳 422 驗證錯誤時，應將回應中的 detail 陣列萃取為可讀的提示訊息。', 'When the createNode or updateNode API returns a 422 validation error, the ''detail'' array from the response should be extracted into readable prompt messages.', '{api,錯誤處理,驗證}', 'public', 'system', '2026-04-25 02:40:01.366196+00', NULL, '409f48944a83ee3860534aa1c918f07f3d9c337c4c946bf715b933bd5360ea67', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_e73ea399', '1.0', 'ws_spec0001', 'EDGE_GUIDE 內容定義', 'EDGE_GUIDE Content Definition', 'factual', 'markdown', '`EDGE_GUIDE` 常數定義了關聯類型語意、權重範圍、`half_life_days` 說明以及 409 衝突處理方式。', 'The `EDGE_GUIDE` constant defines relation type semantics, weight range, `half_life_days` explanation, and 409 conflict handling.', '{edge_guide,edge,specification,documentation}', 'public', 'system', '2026-04-25 02:39:29.242927+00', NULL, '5fef9aae465627bf86285619c53a86bb7deaa85f2734000b16bad20efcd47632', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_c3e5a685', '1.0', 'ws_spec0001', '貢獻者角色能力詳情', 'Contributor Role Capabilities Detail', 'factual', 'markdown', '貢獻者擁有所有檢視者能力，並可以提交新節點、編輯現有節點或新/刪除邊的提案。這些提案進入審核隊列，狀態為 `pending_admin_review`，直到管理員批准。貢獻者不得批准自己的提案。', 'Contributors have all viewer capabilities and can submit proposals for new nodes, edits to existing nodes, or new/deleted edges. These proposals enter a review queue with `status = pending_admin_review` until an admin approves. A contributor may not approve their own proposals.', '{role,contributor,capabilities,proposal,review-queue}', 'public', 'system', '2026-04-24 11:25:40.561589+00', NULL, 'e9503d1f90e13846bc35650c0f983527ccabd9b7209e4b6faab958cab6bd02f8', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_dbaef1ba', '1.0', 'ws_spec0001', '工作區所有者角色', 'Workspace Owner Role', 'factual', 'markdown', '工作區所有者始終是管理員，且不能從該角色降級。', 'The workspace owner is always an admin and cannot be demoted from this role.', '{role,owner,admin,restriction}', 'public', 'system', '2026-04-24 11:25:40.522712+00', NULL, '5adde963a195e4b5f2c42f464fcdc25d634412c734ad62d4e46760cb4799b819', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_097ff069', '1.0', 'ws_spec0001', 'AI 提供者抽象與 API 金鑰模型', 'AI Provider Abstraction and API Key Model', 'factual', 'markdown', 'MemTrace 的 AI 功能共享通用的提供者抽象和 API 金鑰模型，使用者需自行提供金鑰。', 'MemTrace''s AI features share a common provider abstraction and API key model, where users supply their own keys.', '{ai,api,security,configuration}', 'public', 'system', '2026-04-24 11:25:40.454141+00', NULL, '3670462d56d5294b06b1cdd0f98f5e5570062473d91f2c8839b81a34659a4a11', 'ai', NULL, NULL, NULL, NULL, 0.593, 0.800, 1.000, 0.010, 0.500, 0, 0, 0, 1, 1, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_a71dcf58', '1.0', 'ws_spec0001', '手動歸檔節點 API', 'Manual Node Archiving API', 'procedural', 'markdown', '提供一個 API 端點 `POST /nodes/{id}/archive`，允許編輯者或更高權限的使用者手動歸檔節點。', 'Provide an API endpoint `POST /nodes/{id}/archive` allowing editors or higher-privileged users to manually archive nodes.', '{api,node-archiving}', 'public', 'system', '2026-04-25 02:38:43.473681+00', NULL, '26e451b46c407090a14f1a4895054227a8666715f81b890e1197f195286486f6', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_a590bb10', '1.0', 'ws_spec0001', '工作區創建者的默認角色', 'Default Role for Workspace Creator', 'factual', 'markdown', '當使用者創建工作區時，他們會自動被分配管理員（所有者）角色。', 'When a user creates a workspace, they are automatically assigned the admin (owner) role.', '{role,default,workspace-creation,admin,owner}', 'public', 'system', '2026-04-24 11:25:40.680957+00', NULL, '39f9a4ffb3fb89db47b80bab32db52d8c4accf6828180b79d56d1eef56cff254', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_7f8829ed', '1.0', 'ws_spec0001', '記憶節點實用性維度', 'Memory Node Utility Dimension', 'factual', 'markdown', '`memory_nodes` 表中的 `dim_utility` 欄位類型為 NUMERIC(4,3)，表示信任分數的一個維度。', 'The `dim_utility` column in the `memory_nodes` table is of type NUMERIC(4,3), representing a dimension of the trust score.', '{database,schema,memory_nodes,column,trust_dimension}', 'public', 'system', '2026-04-24 11:25:39.190339+00', NULL, '020d80e8d3685d96e7721f3ea118c1bd2cb4ea2707e2725207fdfa2f04ecdd0f', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_727c2cb2', '1.0', 'ws_spec0001', '入門流程完成狀態追蹤', 'Onboarding Completion State Tracking', 'factual', 'markdown', 'MemTrace 在服務端追蹤每個使用者的入門 (onboarding) 流程完成進度。', 'MemTrace tracks onboarding completion status per user on the server-side.', '{onboarding,user-state,server-side}', 'public', 'system', '2026-04-24 11:25:40.365178+00', NULL, '7afcc2ae675a0fe89085bcc1e691fed58e025a908cae57ce7cfdb000934644f6', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_a28ca156', '1.0', 'ws_spec0001', '支持的記憶導出格式', 'Supported Memory Export Formats', 'factual', 'markdown', '記憶可以以 JSON、Markdown 或純文本格式導出。', 'Memory can be exported in JSON, Markdown, or plain text formats.', '{export,file-format}', 'public', 'system', '2026-04-24 11:25:39.232184+00', NULL, '75a768bb0777511311b5dd2bd3fc4b6ac90d651224dd1d6cee54e45d817fe664', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_ac50a001', '1.0', 'ws_spec0001', '對談管理：JWTs', 'Session Management: JWTs', 'factual', 'markdown', '對談由使用 HS256 算法簽署的 JWT (JSON Web Tokens) 表示，密鑰存儲在環境中。', 'Sessions are represented as signed JWTs (JSON Web Tokens) using the HS256 algorithm, with the secret stored in the environment.', '{對談管理,jwt,hs256,安全}', 'public', 'system', '2026-04-24 11:25:40.107288+00', NULL, 'cd442ccb55c20dab87ed4f4c0ff1e966f5a7ba54018623f6ec3172ab3c6d9d5e', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_184116bb', '1.0', 'ws_spec0001', '入門流程物件結構', 'Onboarding Object Structure', 'factual', 'markdown', '入門流程狀態由一個 `onboarding` 物件表示，包括 `completed`、`steps_done`、`steps_skipped` 和 `first_kb_id` 等欄位。', 'The onboarding state is represented by an `onboarding` object, including `completed`, `steps_done`, `steps_skipped`, and `first_kb_id` fields.', '{onboarding,data-model,json}', 'public', 'system', '2026-04-24 11:25:40.381562+00', NULL, '5651cf39b30ea36b6a4a87ddb2eef33aa78408a213d5570ebbd306c438554bb1', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_df5063bd', '1.0', 'ws_spec0001', '列出已歸檔節點 API', 'List Archived Nodes API', 'procedural', 'markdown', '提供一個 API 端點 `GET /workspaces/{ws_id}/nodes?filter=archived`，用於列出指定工作區中所有已歸檔的節點。', 'Provide an API endpoint `GET /workspaces/{ws_id}/nodes?filter=archived` to list all archived nodes within a specified workspace.', '{api,node-archiving}', 'public', 'system', '2026-04-25 02:38:49.910036+00', NULL, '50c10babc72825ea1a4c613a30ae476d998c5a3f0fbe90f05d8277b528f729c9', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_31b38aa1', '1.0', 'ws_spec0001', '指南內容來源共用', 'Guide Content Source Sharing', 'factual', 'markdown', '`NODE_GUIDE` 和 `EDGE_GUIDE` 的內容與 `get_schema` 工具共用同一份來源，該來源是從 `SCHEMA_GUIDE` 常數拆分而來。', 'The content for `NODE_GUIDE` and `EDGE_GUIDE` shares the same source as the `get_schema` tool, derived from a split `SCHEMA_GUIDE` constant.', '{schema_guide,node_guide,edge_guide,get_schema,source}', 'public', 'system', '2026-04-25 02:39:31.349734+00', NULL, '6dd2202e0239d34dcbc455ca48e987489b046a8e53676f2c290064bc4f23d649', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_d679d993', '1.0', 'ws_spec0001', 'MemTrace 核心哲學：知識與策展人關係', 'MemTrace Core Philosophy: Knowledge and Curator Relationship', 'factual', 'markdown', 'MemTrace 的設計理念超越了單純的權限模型，闡述了知識與其策展人之間的關係。', 'MemTrace''s design philosophy goes beyond a mere permissions model, articulating the relationship between knowledge and its curator.', '{memtrace,philosophy,knowledge-management}', 'public', 'system', '2026-04-24 11:27:02.088865+00', NULL, 'f8f87913529c03f880e7c1e82cea98b7b4b167dcf7d43215cacf3e98218bd995', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_bb9aff63', '1.0', 'ws_spec0001', '管理員角色概覽', 'Admin Role Overview', 'factual', 'markdown', '管理員是知識庫的所有者或維護者。他們擁有所有貢獻者能力、直接寫入權限、批准或拒絕提案的能力、管理成員以及軟刪除和恢復工作區的能力。', 'Admins are repository owners or maintainers. They possess all contributor capabilities, direct write access, the ability to approve or reject proposals, manage members, and soft-delete and restore workspaces.', '{role,admin,capabilities}', 'public', 'system', '2026-04-24 11:25:40.503845+00', NULL, 'e887ffec2fead0932c9e9c9281169b35a204c219a609098713d149f87b622012', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_af74b0f0', '1.0', 'ws_spec0001', '模型上下文協議 (MCP)', 'Model Context Protocol (MCP)', 'factual', 'markdown', 'MemTrace 實現了模型上下文協議 (MCP)，使 AI 代理和 LLM 能夠在無需手動 REST 集成的情況下消耗和貢獻知識圖譜。', 'MemTrace implements the Model Context Protocol (MCP) to enable AI agents and LLMs to consume and contribute to the Knowledge Graph without manual REST integration.', '{protocol,ai-integration,llm,knowledge-graph}', 'public', 'system', '2026-04-24 11:25:40.290234+00', NULL, '7deee1e16d2dc125019dd48422261a6a6f2a507e63a5af83183cb0baaa6465f0', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_35f0002a', '1.0', 'ws_spec0001', '檢視者角色能力', 'Viewer Role Capabilities', 'factual', 'markdown', '檢視者可以搜索、列出和獲取節點、追蹤走訪、對節點進行評分（votes_up / votes_down），以及使用對話式問答。他們不能創建、修改或刪除任何節點、邊或工作區設置，也不能提出更改建議。', 'Viewers can search, list, and get nodes, track traversals, rate nodes (votes_up / votes_down), and use conversational Q&A. They cannot create, modify, or delete any nodes, edges, or workspace settings, nor can they propose changes.', '{role,viewer,capabilities,restrictions}', 'public', 'system', '2026-04-24 11:25:40.544502+00', NULL, '05de91add0c34978b1ec1aceb37bff828648288caadf274fa3b0143c5f95a75a', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_4621ebb5', '1.0', 'ws_spec0001', 'MemTrace 功能實作展開細項 - 第二階段完成', 'MemTrace Feature Breakdown - Phase 2 Completed', 'context', 'markdown', '本文件將待辦事項中的高階規格，展開為提供給前端 (UI)、後端 (API)、資料庫 (DB) 開發人員具體可執行的工作細項。', 'This document details high-level specifications from the backlog into concrete subtasks for UI, API, and DB developers.', '{memtrace,feature-breakdown,project-management,phase-2}', 'public', 'system', '2026-04-25 02:39:32.330603+00', NULL, '3fefc7da371b9f5f6f0dd7fcadad0fc77650f3b51d4496bafe2bace9ab83ce41', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_993fc9e6', '1.0', 'ws_spec0001', '節點走訪統計數據結構', 'Node Traversal Statistics Data Structure', 'factual', 'markdown', '節點響應中的 `traversal` 物件包含 `count`（走訪次數）和 `unique_traversers`（唯一走訪者數量）欄位。', 'The `traversal` object in a node response includes `count` (number of traversals) and `unique_traversers` (number of unique traversers) fields.', '{data-structure,traversal-stats,node}', 'public', 'system', '2026-04-24 11:25:40.257768+00', NULL, '66359e4b04b32eb74bda754d4a7ce4bb86ffb941c45a7f46889bfa738edbffd8', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_ce794c4c', '1.0', 'ws_spec0001', 'MemTrace 功能計畫 - 任務拆解文件', 'MemTrace Feature Plan - Task Breakdown Document', 'factual', 'markdown', '本文件概述了 MemTrace 功能計畫的開發任務，依功能群組（A-H）分類，並標註各任務所屬的層級（DB、API、UI、MCP、CLI、Core、Scheduler）。', 'This document outlines the development tasks for the MemTrace feature plan, categorized by functional groups (A-H) and marked with their respective layers (DB, API, UI, MCP, CLI, Core, Scheduler).', '{}', 'public', 'system', '2026-04-25 02:38:58.002264+00', NULL, 'ceb8023eca96714907c41e68f043ba347de980648324aa76cae44df509ed922a', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_cce15a1a', '1.0', 'ws_spec0001', '節點修訂表唯一約束', 'Node Revisions Table Unique Constraint', 'factual', 'markdown', '在 `node_revisions` 資料表中，`node_id` 和 `revision_no` 的組合必須是唯一的，確保每個節點的每個修訂版本都有獨特的識別。', 'The combination of `node_id` and `revision_no` must be unique in the `node_revisions` table, ensuring each revision of a node has a distinct identifier.', '{資料庫,資料表,節點修訂,唯一約束}', 'public', 'system', '2026-04-25 02:39:32.871852+00', NULL, '1c84d32a9837c44a5f42f009e966b613ed097d1fb83d089d9741a87ae2b34222', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_52ac8940', '1.0', 'ws_spec0001', '純文本輸入模式', 'Plain Text Input Mode', 'factual', 'markdown', '在 `plain` 模式下，輸入內容會按原樣存儲在 `content.body` 中，不進行任何渲染標記。', 'In `plain` mode, input is stored as-is in `content.body` with no rendering markup.', '{input-mode,plain-text}', 'public', 'system', '2026-04-24 11:25:39.391767+00', NULL, '0d46112da947dead20360dc05d449e40425556481707045ac95fe29254d918b3', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_5a3bd1b0', '1.0', 'ws_spec0001', '輸入模式切換與內容轉換', 'Input Mode Switching and Content Conversion', 'factual', 'markdown', '切換輸入模式不會自動轉換現有內容。', 'Switching input modes does not automatically convert existing content.', '{editor,input-mode,content-conversion}', 'public', 'system', '2026-04-24 11:25:39.480432+00', NULL, 'd021d2e82b6639637bd114078242f8e2b2c15fd730461f24e271137b0b3c8e9a', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_7dfe253a', '1.0', 'ws_spec0001', 'MCP 身份驗證', 'MCP Authentication', 'factual', 'markdown', '驗證是透過傳遞 API 金鑰完成的，該金鑰作為 `MEMTRACE_API_KEY` 環境變量（stdio 模式）或 `Authorization` 標頭（HTTP 模式）傳遞。', 'Authentication is via an API key passed as the `MEMTRACE_API_KEY` environment variable (stdio mode) or `Authorization` header (HTTP mode).', '{mcp,authentication,api-key,environment-variable,http-header}', 'public', 'system', '2026-04-24 11:25:40.347126+00', NULL, '40ba3456cf0cbbf4aa1cf85bbac939f6d6e95a7488dd0d987161188f20053de6', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_a003', '1.0', 'ws_spec0001', 'Review Queue：人工審核 AI 萃取結果', 'Review Queue: human review of AI-extracted candidates', 'procedural', 'plain', 'AI 萃取的候選節點不自動進入知識庫，必須通過人工審核。三種操作：Accept（接受原樣）、Edit then Accept（修改後接受）、Reject（捨棄）。支援批次操作（Accept all / Reject all）。至少需接受一個節點才能關閉審核步驟。審核完成後，被接受的節點以正確的 source_type 寫入知識庫，被拒絕的候選永久丟棄。這是 MemTrace 確保 AI 生成內容不污染知識庫的核心機制。', 'AI-extracted candidate nodes do not enter the Knowledge Base automatically — they must pass human review. Three actions: Accept (as-is), Edit then Accept (modify before committing), Reject (discard). Bulk operations (Accept all / Reject all) are supported. At least one node must be accepted before the review step can be closed. After review, accepted nodes are written with the correct source_type; rejected candidates are permanently discarded. This is MemTrace''s core mechanism for preventing AI-generated content from polluting the Knowledge Base.', '{ai,review-queue,quality-control,ingestion}', 'public', 'memtrace-spec', '2026-04-11 00:00:00+00', NULL, 'f8a3b4c5d6e7f8a3b4c5d6e7f8a3b4c5d6e7f8a3b4c5d6e7f8a3b4c5d6e7f8a3', 'human', NULL, NULL, NULL, NULL, 0.950, 0.950, 1.000, 0.950, 0.900, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_i003', '1.0', 'ws_spec0001', 'MCP Server：AI Agent 整合', 'MCP Server: AI agent integration', 'factual', 'markdown', 'MemTrace 實作 **Model Context Protocol (MCP)**，讓 AI agent（如 Claude Code）可以將 MemTrace 知識庫作為 context provider，無需直接讀取規格文件。

**Transport**：目前僅支援 stdio（`node packages/mcp/dist/index.js`）。

**當前實作工具（Tools）**：

| 工具 | 說明 |
|------|------|
| `search_nodes` | 關鍵字搜尋節點（中英文皆可），回傳完整內容 |
| `get_node` | 依 ID 取得特定節點完整內容與 metadata |
| `traverse` | 取得節點及其上下游關聯（depth=1 或 2）|
| `list_by_tag` | 依 tag 列出所有節點 |

**環境變數**：
- `MEMTRACE_API`：API base URL（預設 `http://localhost:8000/api/v1`）
- `MEMTRACE_WS`：Workspace ID（預設 `ws_spec0001`）
- `MEMTRACE_LANG`：顯示語言（預設 `zh-TW`）

**現有限制**：
每個 MCP server 實例只能查詢單一工作區（由 `MEMTRACE_WS` 固定）。若需查詢多個知識庫，目前 workaround 是在 `.mcp.json` 中為每個工作區啟動獨立實例，但工具名稱相同會造成 AI agent 混淆。

**已規劃但尚未實作**：
- 多工作區支援：工具加入可選 `workspace_id` 參數 + `list_workspaces` 工具
- Resources（`memtrace://node/{id}` 等 URI 讀取）
- 寫入工具（`create_node`、`update_node`、`create_edge`）
- HTTP + SSE transport
- `traverse_edge` 觸發 co-access boost

Agent 每次沿 Edge 移動時應呼叫 traverse 工具，讓常用路徑保持活躍，抵抗 decay。', 'MemTrace implements the **Model Context Protocol (MCP)**, allowing AI agents (e.g. Claude Code) to use MemTrace as a context provider without reading raw spec documents.

**Transport**: stdio only for now (`node packages/mcp/dist/index.js`).

**Currently implemented tools**:

| Tool | Description |
|------|-------------|
| `search_nodes` | Keyword search across nodes (Chinese and English), returns full content |
| `get_node` | Retrieve a specific node by ID with full content and metadata |
| `traverse` | Get a node plus its upstream/downstream associations (depth=1 or 2) |
| `list_by_tag` | List all nodes with a specific tag |

**Environment variables**:
- `MEMTRACE_API`: API base URL (default `http://localhost:8000/api/v1`)
- `MEMTRACE_WS`: Workspace ID (default `ws_spec0001`)
- `MEMTRACE_LANG`: Display language (default `zh-TW`)

**Current limitation**: Each MCP server instance is locked to a single workspace (set by `MEMTRACE_WS`). To query multiple knowledge bases, the current workaround is to start a separate instance per workspace in `.mcp.json`, but identical tool names cause confusion for AI agents.

**Planned but not yet implemented**:
- Multi-workspace support: optional `workspace_id` parameter on all tools + `list_workspaces` tool
- Resources (`memtrace://node/{id}` URI reads)
- Write tools (`create_node`, `update_node`, `create_edge`)
- HTTP + SSE transport
- `traverse_edge` to trigger co-access boost

Agents should call traverse when following an edge, keeping frequently used paths alive against decay.', '{mcp,ai-agent,integration,api}', 'public', 'system', '2026-04-11 00:00:00+00', NULL, 'c6d7e8f9a4b5c6d7e8f9a4b5c6d7e8f9a4b5c6d7e8f9a4b5c6d7e8f9a4b5c6d7', 'human', NULL, NULL, NULL, NULL, 0.950, 0.950, 1.000, 0.950, 0.900, 0, 0, 0, 3, 2, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_k004', '1.0', 'ws_spec0001', '工作區生命週期與軟刪除（30 天寬限期）', 'Workspace lifecycle and soft-delete (30-day grace period)', 'procedural', 'plain', '工作區有三個狀態：active（正常）、pending_deletion（軟刪除中）、deleted（已清除）。

軟刪除觸發：admin 呼叫 DELETE /workspaces/{ws_id}
- 設定 status = pending_deletion、deleted_at = NOW()
- 非 admin 成員立即失去存取
- Admin/owner 保留唯讀存取（可匯出資料）
- 通知郵件：第 0 天（刪除啟動）、第 25 天（5 天警告）、第 30 天（最終清除）

還原：在寬限期內 admin 呼叫 POST /workspaces/{ws_id}/restore
- status 回到 active，deleted_at 清空，所有成員存取恢復

自動清除：每日背景排程，清除 status = pending_deletion AND deleted_at < NOW() - INTERVAL ''30 days'' 的工作區（CASCADE DELETE：節點、邊、成員、邀請、對話紀錄全部刪除，不可還原）。

KB 類型寬限期差異：
- evergreen：30 天
- ephemeral：7 天

Schema 新增：
ALTER TABLE workspaces ADD COLUMN status TEXT NOT NULL DEFAULT ''active'' CHECK (status IN (''active'',''pending_deletion'',''deleted'')), ADD COLUMN deleted_at TIMESTAMPTZ;', 'Workspaces move through three states: active (normal), pending_deletion (soft-deleted, grace period active), deleted (purged from DB).

Soft-delete trigger: admin calls DELETE /workspaces/{ws_id}
- Sets status = pending_deletion, deleted_at = NOW()
- Non-admin members immediately lose access
- Admin/owner retains read-only access (for data export)
- Email notifications: day 0 (deletion initiated), day 25 (5-day warning), day 30 (final purge)

Restoration: any admin calls POST /workspaces/{ws_id}/restore within the grace period
- status returns to active, deleted_at is cleared, all member access is restored

Automatic purge: daily background job deletes workspaces where status = ''pending_deletion'' AND deleted_at < NOW() - INTERVAL ''30 days''. This is a hard CASCADE DELETE — all nodes, edges, members, invites, and chat sessions are deleted. Cannot be undone.

Grace period by KB type:
- evergreen: 30 days
- ephemeral: 7 days

Schema change:
ALTER TABLE workspaces ADD COLUMN status TEXT NOT NULL DEFAULT ''active'' CHECK (status IN (''active'',''pending_deletion'',''deleted'')), ADD COLUMN deleted_at TIMESTAMPTZ;', '{workspace,lifecycle,soft-delete,grace-period,deletion,restore}', 'public', 'system', '2026-04-12 00:00:00+00', NULL, 'e2f3a4b5c6d7e2f3a4b5c6d7e2f3a4b5c6d7e2f3a4b5c6d7e2f3a4b5c6d7e2f3', 'human', NULL, NULL, NULL, NULL, 0.950, 0.950, 1.000, 0.900, 0.900, 0, 0, 0, 4, 2, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_p002', '1.0', 'ws_spec0001', '為知識傳承而設計', 'Designed for knowledge inheritance', 'context', 'plain', 'MemTrace 為「非作者」設計。無論是剛加入的團隊成員、中途加入的協作者，還是在陌生情境中運作的 AI agent，都能從任何節點進入知識庫，沿著 Edge 找到所有相關內容，不需要原作者引導。每個節點設計上要自給自足到可以獨立閱讀，同時又透過 Edge 連結讓讀者可以自然深入探索。', 'MemTrace is designed for the reader who was not there when the knowledge was created. A new team member, a late collaborator, or an AI agent in an unfamiliar context — all can enter at any node and navigate by following edges, without needing the original author to guide them. Each node is self-contained enough to read in isolation, yet connected enough that following its edges leads naturally to everything related.', '{philosophy,core,design-principle,inheritance}', 'public', 'memtrace-spec', '2026-04-11 00:00:00+00', NULL, 'b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3', 'human', NULL, NULL, NULL, NULL, 0.950, 0.950, 1.000, 0.950, 0.900, 0, 0, 0, 1, 1, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_a001', '1.0', 'ws_spec0001', 'AI Provider 與 API Key 自管', 'AI provider and self-managed API keys', 'procedural', 'markdown', 'MemTrace 不自營 AI 推論服務。所有 AI 功能由使用者選擇的第三方供應商提供。

**官方支援的 Provider**：

| Provider | 識別碼 | 預設 Chat 模型 | Embedding 模型 | 維度 |
|----------|--------|---------------|---------------|------|
| OpenAI | `openai` | `gpt-4o-mini` | `text-embedding-3-small` | 1536 |
| Anthropic | `anthropic` | `claude-haiku-4-5-20251001` | `voyage-3-lite` | 1024 |
| Google Gemini | `gemini` | `gemini-2.0-flash` | `text-embedding-004` | 768 |

**Embedding 維度限制**：每個工作區的 embedding 維度在建立時固定（`workspaces.embedding_provider` + `embedding_dim`），**不可變更**。不同 provider 產生的向量維度不同，無法跨 provider 比較 cosine similarity。

**API Key 儲存**：CLI 存於 `~/.memtrace/config.json`（chmod 600），UI 存於 localStorage 或加密寫入 `user_ai_keys`。Key **永不**傳送至 MemTrace 伺服器以外的任何地方。

**社群 Provider**：透過 `packages/api/core/ai.py` 的 `AIProvider` Protocol 可加入新 provider（Mistral、Cohere、Ollama、vLLM 等）。實作後在 `PROVIDER_REGISTRY` 註冊即可，不需修改 router 或資料庫 schema。

**未來商業模式**：可能提供 MemTrace 代管額度（免費層 + 付費方案）；架構透過 provider interface 抽象，日後切換不影響上層邏輯。', 'MemTrace does not operate its own AI inference service. All AI features are powered by the user''s chosen third-party provider.

**Officially supported providers**:

| Provider | Identifier | Default chat model | Embedding model | Dim |
|----------|------------|--------------------|-----------------|-----|
| OpenAI | `openai` | `gpt-4o-mini` | `text-embedding-3-small` | 1536 |
| Anthropic | `anthropic` | `claude-haiku-4-5-20251001` | `voyage-3-lite` | 1024 |
| Google Gemini | `gemini` | `gemini-2.0-flash` | `text-embedding-004` | 768 |

**Embedding dimension constraint**: Each workspace fixes its embedding dimension at creation time (`workspaces.embedding_provider` + `embedding_dim`) and it is **immutable**. Different providers produce vectors of different dimensions; nodes embedded with different models cannot be compared via cosine similarity.

**API key storage**: CLI in `~/.memtrace/config.json` (chmod 600); UI in localStorage or encrypted in `user_ai_keys`. Keys are **never** transmitted to any MemTrace server.

**Community providers**: Add new providers via the `AIProvider` Protocol in `packages/api/core/ai.py` (Mistral, Cohere, Ollama, vLLM, etc.). Implement and register in `PROVIDER_REGISTRY` — no router or schema changes needed.

**Future business model**: a managed credit option (free tier + paid) may be introduced. The provider interface abstraction lets this swap in without touching extraction logic.', '{ai,api-key,provider,security,gemini,embedding}', 'public', 'memtrace-spec', '2026-04-11 00:00:00+00', NULL, 'd6e7f8a3b4c5d6e7f8a3b4c5d6e7f8a3b4c5d6e7f8a3b4c5d6e7f8a3b4c5d6e7', 'human', NULL, NULL, NULL, NULL, 0.950, 0.950, 1.000, 0.950, 0.900, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_p001', '1.0', 'ws_spec0001', '知識透過連結而非積累', 'Knowledge through connection, not accumulation', 'context', 'plain', 'MemTrace 的核心前提：知識不需要存在於龐大的文件中。每個節點只捕捉一個想法，價值來自節點之間的連結網絡。節點本身輕量，但透過關聯性形成龐大的知識庫。知識庫的規模不是由單一節點的大小決定，而是由節點之間關係的密度與品質決定。', 'The core premise of MemTrace: knowledge does not need to live in large, monolithic documents. Each node captures one idea. Value emerges from the network of relationships between nodes. A node alone is lightweight; connected to others, it becomes part of a knowledge base whose scale is determined by the density and quality of its relationships, not the size of any single entry.', '{philosophy,core,design-principle}', 'public', 'memtrace-spec', '2026-04-11 00:00:00+00', NULL, 'a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2', 'human', NULL, NULL, NULL, NULL, 0.950, 0.950, 1.000, 0.950, 0.900, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_a004', '1.0', 'ws_spec0001', '對話式問答（Conversational Q&A）', 'Conversational Q&A against the knowledge base', 'procedural', 'plain', 'viewer 以上角色可對知識庫進行自然語言問答。Q&A 為唯讀操作，不修改知識庫內容。

執行流程：
1. 使用者傳送訊息
2. search_nodes(query) → 取得最相關的 5 個節點
3. traverse(最高分節點, depth=1) → 補充鄰近上下文（可選）
4. 組合 prompt：system 說明（只使用提供的節點作答，並引用節點 ID）+ 節點內容 + 使用者問題
5. 呼叫 AI（使用工作區 AI provider 設定，§16.5）
6. 回傳：answer + cited_nodes[] + tokens_used + session_id

API：
- POST /workspaces/{ws_id}/chat — 發送訊息（傳入 session_id 可延續對話，不傳則建立新 session）
- GET /workspaces/{ws_id}/chat/sessions — 列出使用者的 session 清單
- GET /workspaces/{ws_id}/chat/sessions/{session_id} — 取得完整對話紀錄

多輪對話：session 中最近 10 則訊息會一起送入 context window 以支援連續問答。

Schema：chat_sessions（id, workspace_id, user_id, created_at, updated_at）和 chat_messages（id, session_id, role user/assistant, content, cited_nodes[], tokens_used, created_at）。

注意：即使是 public 工作區，Q&A 也需要登入。未認證使用者無法使用此功能。', 'Any member with viewer role or above can ask natural-language questions against a workspace''s KB. Q&A is read-only — it never writes to the KB.

Execution flow:
1. User sends a message
2. search_nodes(query) → retrieves top-5 relevant nodes
3. traverse(top node, depth=1) → adds neighbour context (optional, improves multi-hop answers)
4. Build prompt: system instruction (answer only from provided nodes, cite node IDs) + node content blocks + user question
5. Call AI (uses workspace AI provider config, §16.5)
6. Return: answer + cited_nodes[] + tokens_used + session_id

API:
- POST /workspaces/{ws_id}/chat — send message (pass session_id to continue a conversation; omit to start a new session)
- GET /workspaces/{ws_id}/chat/sessions — list the caller''s sessions
- GET /workspaces/{ws_id}/chat/sessions/{session_id} — get full message history

Multi-turn: the last 10 messages in the session are included in the context window for conversational continuity.

Schema: chat_sessions (id, workspace_id, user_id, created_at, updated_at) and chat_messages (id, session_id, role user/assistant, content, cited_nodes[], tokens_used, created_at).

Note: Q&A requires authentication even on public workspaces. Unauthenticated users cannot use this feature.', '{ai,chat,q&a,conversational,session,read-only}', 'public', 'system', '2026-04-12 00:00:00+00', NULL, 'f3a4b5c6d7e8f3a4b5c6d7e8f3a4b5c6d7e8f3a4b5c6d7e8f3a4b5c6d7e8f3a4', 'human', NULL, NULL, NULL, NULL, 0.950, 0.950, 1.000, 0.950, 0.900, 0, 0, 0, 3, 1, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_d0961cfa', '1.0', 'ws_spec0001', '記憶節點編輯器存取方法', 'Memory Node Editor Access Methods', 'procedural', 'markdown', '編輯器可從圖譜視圖（透過工具列按鈕或雙擊空白畫布區域）以及節點的上下文菜單存取。', 'The editor is accessible from the Graph View (via a toolbar button or double-clicking an empty canvas area) and from the node''s context menu.', '{editor,access,ui}', 'public', 'system', '2026-04-24 11:25:39.331044+00', NULL, '8a3d4055ab327d3e4acebfb2c8f2e9c165b22d5051ede17ec4d37ec45d66869a', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_05ce17d1', '1.0', 'ws_spec0001', 'AI 使用日誌表索引', 'AI Usage Log Table Indexes', 'factual', 'markdown', '在 `ai_usage_log` 表上建立三個索引：`idx_ai_usage_user` (基於 `user_id`, `called_at` 降序), `idx_ai_usage_feature` (基於 `feature`, `called_at` 降序), 以及 `idx_ai_usage_provider` (基於 `provider`, `called_at` 降序)。', 'Three indexes are created on the `ai_usage_log` table: `idx_ai_usage_user` (on `user_id`, `called_at` DESC), `idx_ai_usage_feature` (on `feature`, `called_at` DESC), and `idx_ai_usage_provider` (on `provider`, `called_at` DESC).', '{ai,說明}', 'public', 'system', '2026-04-24 11:25:40.908853+00', NULL, '7a1280b6e7a2bff93fc5743846592250a33fd7b5f18dc420af70ec1fee8983b6', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_7e74197c', '1.0', 'ws_spec0001', 'AI Provider `embed` 方法簽名', 'AI Provider `embed` Method Signature', 'factual', 'markdown', '`embed` 方法接受 API 金鑰、模型名稱和文本字串，並返回包含浮點數列表（嵌入向量）和所用 token 數量的元組。', 'The `embed` method takes an API key, model name, and text string, returning a tuple containing a list of floats (the embedding vector) and the number of tokens used.', '{ai,embedding,api,method-signature}', 'public', 'system', '2026-04-24 11:31:27.640059+00', NULL, '8ca7e05bc01d9b03cc82dfdd508527e481f07deb3644e4b1dbdbb685d9ebe61e', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_c9bd6c49', '1.0', 'ws_spec0001', 'memory_nodes 表中的 `conflict_status` 欄位', '`conflict_status` Column in `memory_nodes` Table', 'factual', 'markdown', '`memory_nodes` 表包含一個名為 `conflict_status` 的文本欄位，其值可以為 `NULL`, `''flagged''`, 或 `''resolved''`。', 'The `memory_nodes` table includes a text column named `conflict_status`, which can have values of `NULL`, `''flagged''`, or `''resolved''`.', '{database_schema,conflict_management}', 'public', 'system', '2026-04-24 11:31:27.706468+00', NULL, '155f94b0cc3c745f38e13c0f4213965a92517eca84f2b2f56cb27d1c3765b21d', 'ai', NULL, NULL, NULL, NULL, 0.593, 0.800, 1.000, 0.010, 0.500, 0, 0, 0, 1, 1, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_27e2935e', '1.0', 'ws_spec0001', '工作區角色與權限', 'Workspace Roles & Permissions', 'factual', 'markdown', '工作區內的知識存取嚴格基於角色，特別是對於「有條件公開」(conditional_public) 和「受限」(restricted) 的工作區。', 'Access to knowledge within a workspace is strictly role-based, especially for `conditional_public` and `restricted` workspaces.', '{access-control,roles,permissions}', 'public', 'system', '2026-04-24 11:25:39.701124+00', NULL, 'd1a47e7c44150c33817a30ae6a42bfaf25f2225950b5aff7824c979513ec19be', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_playbook_002', '1.0', 'ws_spec0001', '工作流程：人機協作審核週期', 'Workflow: Human-in-the-Loop Review Cycle', 'procedural', 'markdown', '### 協作流程
1. **AI 提案**：AI 在對話或攝入過程中生成建議節點，並進入 review_queue。
2. **人工審核**：使用者定期檢查隊列以完善、合併或拒絕提案。
3. **提交**：批准的知識成為永久 Evergreen 圖譜的一部分。', '### Collaboration Workflow
1. **AI Proposal**: AI generates suggested nodes during chat or ingestion, which enter the review_queue.
2. **Human Review**: Users periodically check the queue to refine, merge, or reject proposals.
3. **Commit**: Approved knowledge becomes part of the permanent Evergreen graph.', '{workflow,review,collaboration}', 'public', 'system', '2026-04-24 13:35:31.814382+00', NULL, 'manual_playbook_002', 'ai', NULL, NULL, NULL, NULL, 0.503, 0.500, 1.000, 0.010, 0.500, 0, 0, 0, 1, 1, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_2a909fec', '1.0', 'ws_spec0001', 'create_node 驗收情境：僅填寫 title_en', 'create_node Acceptance Scenario: title_en Only', 'factual', 'markdown', '驗收情境之一是測試 `create_node` 函數在只填寫 `title_en` 而不填寫 `title_zh` 的情況下，是否能正常建立節點，且 `title_zh` 預設為空字串。', 'One acceptance scenario is to test if the `create_node` function can successfully create a node when only `title_en` is provided and `title_zh` is left empty, with `title_zh` defaulting to an empty string.', '{驗收情境,節點建立,api,測試}', 'public', 'system', '2026-04-25 02:39:27.638354+00', NULL, 'ad2e98d78ac8c1440456beee48b50a220b21705bd120a7fbdb0c32c8d6ca88fa', 'ai', NULL, NULL, NULL, NULL, 0.593, 0.800, 1.000, 0.010, 0.500, 0, 0, 0, 1, 1, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_c24bbdad', '1.0', 'ws_spec0001', 'AI 代理建立節點時必須指定 source_type 為 "ai"', 'AI Agents Must Specify source_type as "ai" When Creating Nodes', 'factual', 'markdown', '當 AI 代理建立知識節點時，`source_type` 欄位必須明確設定為 `"ai"`。這會導致資料庫中的 `source_type` 欄位為 ''ai''，且審核佇列中的 `proposer_type` 欄位也為 ''ai''。', 'When an AI agent creates a knowledge node, the `source_type` field must be explicitly set to `"ai"`. This results in the `source_type` field in the database being ''ai'' and the `proposer_type` field in the review queue also being ''ai''.', '{ai代理,節點建立,api,規範}', 'public', 'system', '2026-04-25 02:39:26.969779+00', NULL, '59ac0bfa279bf73aaa1a12d438248fbd2ddec10e108d722f3e09e55b42d105dd', 'ai', NULL, NULL, NULL, NULL, 0.593, 0.800, 1.000, 0.010, 0.500, 0, 0, 0, 1, 1, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_4b0125e0', '1.0', 'ws_spec0001', '攝入節點的來源文件保留策略', '??蝭暺?靽???瑼?Source File Retention on Ingested Nodes', 'factual', 'markdown', '當文件被攝入時，其原始來源文件會被保留為一個特殊節點，以確保萃取的可溯性，並提供從任何萃取節點回到其來源段落的直接連結，而不污染主知識圖譜。', '?嗆?隞嗉◤????????瑼?雿銝?畾?暺◤靽?嚗誑蝣箔????餈賣滲?改?銝行?靘?隞颱???蝭暺?嗆?畾菔??仿??嚗????蜓?亥?????When a document is ingested, its original source file is retained as a special node to ensure extraction traceability and provide a direct link from any extracted node back to its source passage without polluting the main knowledge graph.', '{存取,來源,文件}', 'public', 'system', '2026-04-24 11:25:40.736854+00', NULL, '944b98fa9abb8ad8331129296039305a02c7b9291c5257066ca17a2918a88b3a', 'ai', NULL, NULL, NULL, NULL, 0.593, 0.800, 1.000, 0.010, 0.500, 0, 0, 0, 1, 1, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_82b732f5', '1.0', 'ws_spec0001', '內容格式欄位 (`content.format`)', 'Content Format Field (`content.format`)', 'factual', 'markdown', '`content.format` 欄位是一個必填字串，接受值 `"plain"` 或 `"markdown"`，預設為 `"plain"`。', 'The `content.format` field is a required string, accepting values `"plain"` or `"markdown"`, and defaults to `"plain"`.', '{schema,格式,內容}', 'public', 'system', '2026-04-24 11:25:39.870431+00', NULL, 'c804559e5fa18383474f35358a7146e7a9493a0cbf66038ca86a8e45800a35c4', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_ee62ef2c', '1.0', 'ws_spec0001', '簡化圖譜載荷的 API 端點', 'API Endpoint for Stripped Graph Payload', 'factual', 'markdown', '端點 `GET /api/v1/workspaces/{ws_id}/graph?preview=true` 用於提供簡化圖譜載荷。', 'The endpoint `GET /api/v1/workspaces/{ws_id}/graph?preview=true` serves the stripped graph payload.', '{api,端點,簡化結構}', 'public', 'system', '2026-04-24 11:25:39.793666+00', NULL, '692f0b08e25bd54aa1bb741d90fa13d17d3c521fb8eae5d5eea3f70315d0124c', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_2e101ff1', '1.0', 'ws_spec0001', 'AI 使用日誌表結構', 'AI Usage Log Table Schema', 'factual', 'markdown', '建立新的 `ai_usage_log` 表，包含 `id`, `user_id`, `key_source`, `provider`, `model`, `feature`, `workspace_id`, `node_id`, `tokens_input`, `tokens_output`, `tokens_total`, `latency_ms`, `success`, `error_code`, `called_at` 等欄位。', 'A new `ai_usage_log` table is created with fields such as `id`, `user_id`, `key_source`, `provider`, `model`, `feature`, `workspace_id`, `node_id`, `tokens_input`, `tokens_output`, `tokens_total`, `latency_ms`, `success`, `error_code`, and `called_at`.', '{ai,說明}', 'public', 'system', '2026-04-24 11:25:40.887123+00', NULL, 'aca74ab39cb65f069516c41944edd02ff6232f8dea53e0413c1c026bad64746c', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_73ea8135', '1.0', 'ws_spec0001', '簡化圖譜載荷結構', 'Stripped Graph Payload Structure', 'factual', 'markdown', '簡化圖譜載荷包含 `preview_mode: true` 以及簡化後的 `nodes` 和 `edges` 數組。節點僅包含 `id` 和 `position`，而邊包含 `from`, `to`, 和 `relation`。', 'The stripped graph payload includes `preview_mode: true` and stripped `nodes` and `edges` arrays. Nodes only contain `id` and `position`, while edges contain `from`, `to`, and `relation`.', '{API優化,簡化結構,api優化,結構,載荷}', 'public', 'system', '2026-04-24 11:25:39.742298+00', NULL, 'cda26ec974454fdbdab284c8fb6a214080176621f450398f2a91a6605e980ddf', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_8575b4a1', '1.0', 'ws_spec0001', '封存節點在預設視圖與搜尋中隱藏', 'Archived Nodes Hidden in Default View and Search', 'factual', 'markdown', '封存節點不會顯示在預設的圖譜視圖中，且會從搜尋結果中排除。', '甇豢?蝭暺???曉?身??瑼Ｚ???撠??葉??Archived nodes are not displayed in the default Graph View and are excluded from search results.', '{視圖,隱藏,封存}', 'public', 'system', '2026-04-24 11:25:39.518038+00', NULL, '0d0565328c95ff76b4d7bddc886b99868a2cef6b224c8263f7cfb5763f7e465f', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_c4ce77e1', '1.0', 'ws_spec0001', '封存節點在專屬的「封存」視圖中可見', 'Archived Nodes Visible in Dedicated "Archive" View', 'factual', 'markdown', '封存節點可以在專用的「封存」視圖中訪問和顯示，該視圖可從工作區側邊欄進入。', 'Archived nodes are accessible and displayed within a dedicated "Archive" view, which can be reached from the workspace sidebar.', '{視圖,封存,隱藏}', 'public', 'system', '2026-04-24 11:25:39.57505+00', NULL, 'bf861774dffed73c434ea5c3c5a0d846a0ac249c2558d9ad2e8b12173dcaa5e2', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_aab6d931', '1.0', 'ws_spec0001', '簡化圖譜載荷的快取政策', 'Caching Policy for Stripped Graph Payload', 'factual', 'markdown', '預覽載荷不可由客戶端快取，這由響應標頭 `Cache-Control: no-store` 指示。', 'The preview payload is not cacheable by the client, indicated by the response header `Cache-Control: no-store`.', '{快取,API優化,性能}', 'public', 'system', '2026-04-24 11:25:39.829461+00', NULL, '6e6398e27fe86238ff08625e26c0b131b6cabffda49bd17964086ec5d8f0d341', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_80054468', '1.0', 'ws_spec0001', '簡化圖譜載荷中省略的欄位', 'Omitted Fields in Stripped Graph Payload', 'factual', 'markdown', '簡化圖譜載荷響應中完全省略的欄位包括 `title_zh`, `title_en`, `body_zh`, `body_en`, `tags`, `author`, `signature`, `trust_score` 以及所有來源 (provenance) 欄位。', 'Fields entirely omitted from the stripped graph payload response include `title_zh`, `title_en`, `body_zh`, `body_en`, `tags`, `author`, `signature`, `trust_score`, and all provenance fields.', '{資料載荷,API優化,簡化結構}', 'public', 'system', '2026-04-24 11:25:39.775592+00', NULL, 'b6201a17eb809238e3e05fdce0623986c75613178b63db97cecd1176547cd3ec', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_53258df1', '1.0', 'ws_spec0001', 'JWT Token 生命週期', 'JWT Token Lifetime', 'factual', 'markdown', 'JWT Token???賡望???憭押恥?嗥垢?Token???蝙?灼/auth/refresh`蝡舫??脰???渡???The JWT Token lifetime is 7 days. Clients should refresh the token before expiry using the `/auth/refresh` endpoint.', 'JWT Token???賡望???憭押恥?嗥垢?Token???蝙?灼/auth/refresh`蝡舫??脰???渡???The JWT Token lifetime is 7 days. Clients should refresh the token before expiry using the `/auth/refresh` endpoint.', '{jwt,token,生命週期,重新整理}', 'public', 'system', '2026-04-24 11:25:40.146846+00', NULL, '8399bf427db47ef13542102eafca9d11e86950d69a8ad492ce82ba7fd62fe25e', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_ef3bebe9', '1.0', 'ws_spec0001', 'JWT Token 載荷結構', 'JWT Token Payload Structure', 'factual', 'markdown', 'JWT Token 載荷包括 `sub` (使用者 ID)、`email`、`display_name`、`iat` (簽發時間) 和 `exp` (過期時間) 等欄位。', 'The JWT Token payload includes `sub` (user ID), `email`, `display_name`, `iat` (issued-at time), and `exp` (expiry time) fields.', '{jwt,token,載荷,對談管理}', 'public', 'system', '2026-04-24 11:25:40.127115+00', NULL, '28b7156405594bd26902d892ca1e916dbbde4c482b49dbb04839f3fec346da9a', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_f9a2bb47', '1.0', 'ws_spec0001', '來源文件節點欄位定義', 'Source Document Node Field Definition', 'factual', 'markdown', '來源文件節點包含以下欄位：`content_type` 為 `source_document`，`title_zh`/`title_en` 為原始檔名 + 匯入時間戳，`body_zh`/`body_en` 為完整的提取文本或轉錄稿，`visibility` 預設為 `private`，且 `source_type` 為 `human`。', 'A source document node has the following fields: `content_type` as `source_document`, `title_zh`/`title_en` as original filename + ingestion timestamp, `body_zh`/`body_en` as full extracted text or transcript, `visibility` defaulting to `private`, and `source_type` as `human`.', '{後端資料,來源,文件}', 'public', 'system', '2026-04-24 11:25:40.77386+00', NULL, '7d2711cfebac275319bf5ebc62579cd1b3de62a9d03f2952bdd65e03bb984b84', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_c9dd39d4', '1.0', 'ws_spec0001', '知識庫保護機制概覽', 'Overview of Knowledge Base Protection Mechanisms', 'factual', 'markdown', '本節定義了旨在防止知識盜竊的保護機制，同時保留對授權成員和核准預覽的合法可用性。', 'This section defines protection mechanisms designed to prevent knowledge theft while preserving legitimate usability for authorized members and approved previews.', '{安全,概覽,介紹,權限,保護}', 'public', 'system', '2026-04-24 11:31:27.730201+00', NULL, 'a78ac73dff4068fc8b90f4c1d73ea5fd9589364d6f39cd0d31951ca205b53a5a', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_00d32c49', '1.0', 'ws_spec0001', '節點極小化原則', 'Node Minimization Principle', 'factual', 'markdown', '知識圖譜設計的核心原則，主張使用更小的節點、更多的邊以及更短的走訪路徑，以提高資訊檢索效率並降低認知負荷。', '?亥???閮剛??敹???銝餃撐?游???暺憭????渡??甇瑁楝敺?隞交?擃?閮炎蝝Ｘ???A core principle for knowledge graph design, advocating for smaller nodes, more edges, and shorter traversal paths to improve information retrieval efficiency.', '{knowledge-graph,design-principle,ai-restructuring}', 'public', 'system', '2026-04-24 11:31:27.681728+00', NULL, '9371b1b41df3cfd13fc796a731df2f30c24170405d5e9772324e1620188ba65f', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_cdea5189', '1.0', 'ws_spec0001', '封存節點永不銷毀原則', 'Archived Nodes Are Never Destroyed', 'factual', 'markdown', '封存的節點將無限期保留，永遠不會被永久刪除。', '?喃蝙蝭暺◤甇豢?嚗???瘞賊?銝?鋡怠?斗??瑞??Archived nodes are preserved indefinitely and are never permanently deleted.', '{}', 'public', 'system', '2026-04-24 11:25:39.539979+00', NULL, '50b0515bc00d8ed2ec480923fd0e3b1837b27543d57436eb4770e741c478f558', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_4379cf51', '1.0', 'ws_spec0001', '內容格式欄位', 'Content Format Field', 'factual', 'markdown', '所選的輸入模式會作為 content.format 欄位持久化在節點中（參見 §4.1 schema 擴充）。', '?詨??撓?交芋撘??槁content.format`甈????蝭暺葉嚗?閬?.1璅∪??游?憟辣嚗?The selected input mode is persisted in the node as the `content.format` field (see 禮4.1 schema extension).', '{memory-node,schema,content-format}', 'public', 'system', '2026-04-24 11:25:39.438284+00', NULL, 'c8318b292f3ffcbd257b802a6890d12035f468d5483c527af32c73489ff3955d', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_08f1c514', '1.0', 'ws_spec0001', '來源文件節點預設排除項', 'Source Document Node Default Exclusions', 'factual', 'markdown', '來源文件節點預設會從圖譜視圖（除非啟動「顯示來源文件」）、關鍵字與語義搜尋結果、問答與 AI 對話上下文檢索以及 MCP search_nodes 結果中排除。', '皞?隞嗥?暺?閮剖??炎閬??日???＊蝷箏?憪??????菔???蝢拇?撠???蝑?AI撠店銝??炎蝝Ｖ誑?CP `search_nodes` 蝯?銝剜??扎?Source document nodes are excluded by default from Graph View (unless ''Show source files'' is enabled), keyword and semantic search results, Q&A and AI Conversation context retrieval, and MCP `search_nodes` results.', '{}', 'public', 'system', '2026-04-24 11:25:40.831618+00', NULL, '8c1c5ae6bf2674b4f5bd74831f3b1e8b63148c33abfec5059782b406519f5e93', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_5e292da7', '1.0', 'ws_spec0001', '來源格式參考範本', '皞撘??冽撘?Source Format Reference Formats', 'factual', 'markdown', '不同的來源格式使用特定的參考格式：Markdown/純文字使用 §<heading> 或 ¶<paragraph_index>；PDF/DOCX 使用 page:<n>, para:<m>；PPTX 使用 slide:<n>；影片/音訊使用 <HH:MM:SS>-<HH:MM:SS>；網頁使用 <section heading or XPath fragment>。', '銝????澆??摰?撘?澆?嚗arkdown/蝝?摮蝙??`禮<heading>` ??`繞<paragraph_index>`嚗DF/DOCX 雿輻 `page:<n>, para:<m>`嚗PTX 雿輻 `slide:<n>`嚗蔣???唾?雿輻 `<HH:MM:SS>-<HH:MM:SS>`嚗雯?蝙??`<section heading or XPath fragment>`??Different source formats use specific reference formats: Markdown/plain text uses `禮<heading>` or `繞<paragraph_index>`; PDF/DOCX uses `page:<n>, para:<m>`; PPTX uses `slide:<n>`; Video/audio uses `<HH:MM:SS>-<HH:MM:SS>`; and Web pages use `<section heading or XPath fragment>`.', '{}', 'public', 'system', '2026-04-24 11:25:40.812338+00', NULL, '588186fe569c2ea8746c1b3951552737e78c888f03e512bb9c31ce683af3aa0f', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_97757fb8', '1.0', 'ws_spec0001', '來源文件節點存取方法', '皞?隞嗥?暺赤?撘?Source Document Node Access Methods', 'factual', 'markdown', '來源文件節點可透過直接 GET /workspaces/{ws_id}/nodes/{node_id}、專用的 GET /workspaces/{ws_id}/source-documents 端點，以及節點編輯器側邊欄中的「查看來源段落」連結進行存取。', '皞?隞嗥?暺隞仿??湔 `GET /workspaces/{ws_id}/nodes/{node_id}`?GET /workspaces/{ws_id}/source-documents` 撠蝡舫?隞亙?蝭暺楊頛臬?湧?甈葉?炎閬?畾菔????脰?閮芸???Source document nodes are accessible via direct `GET /workspaces/{ws_id}/nodes/{node_id}`, the dedicated `GET /workspaces/{ws_id}/source-documents` endpoint, and the ''View source passage'' link in the node editor sidebar.', '{}', 'public', 'system', '2026-04-24 11:25:40.853431+00', NULL, '20054bbc0e4ca5efb9dc19d5efcf7549ce87b43972a0aa5f0489f4250824e2a4', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_5b28def8', '1.0', 'ws_spec0001', '移除知識庫關聯按鈕', 'Remove Knowledge Base Association Button', 'procedural', 'markdown', '使用者介面應包含一個按鈕，用於移除知識庫關聯，並附帶確認對話框。', 'The UI should include a button to remove knowledge base associations, accompanied by a confirmation dialog.', '{UI,"Knowledge Base Association"}', 'public', 'system', '2026-04-26 00:29:47.019233+00', NULL, '63987de6f6b609d100025c5009e0017cc37a1357adbb70f5fa4d00659a74843d', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_22c9d8d6', '1.0', 'ws_spec0001', '自然衰減機制', 'Organic Decay Mechanism', 'factual', 'markdown', '系統會自動管理知識的衰減，除非節點或邊被手動釘選（pinned）。', '蝟餌絞??恣?霅?銵唳?嚗??暺??◤???箏???The system automatically manages the decay of knowledge unless a node or edge is manually pinned.', '{衰減,權重,decay}', 'public', 'system', '2026-04-24 11:31:27.612477+00', NULL, '81794826c7a783c9fbfa0d8eaa2e8526a26dc20b3f852f4a42811973c0866b02', 'ai', NULL, NULL, NULL, NULL, 0.593, 0.800, 1.000, 0.010, 0.500, 0, 0, 0, 1, 1, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_7f0a2526', '1.0', 'ws_spec0001', '工作區設定中的「關聯知識庫」分頁', '"Associated Knowledge Bases" Tab in Workspace Settings', 'procedural', 'markdown', '在使用者介面的工作區設定中新增一個分頁，用於管理關聯的知識庫。', 'Add a new tab in the Workspace Settings UI for managing associated knowledge bases.', '{UI,"Workspace Settings","Knowledge Base Association"}', 'public', 'system', '2026-04-26 00:13:59.077027+00', NULL, 'b07954d0440f7a87d0c57d8eb15595501425aa56ef273f4c8fbf4159e9bb2f4f', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_8c9d6883', '1.0', 'ws_spec0001', '列出已關聯知識庫', 'List Associated Knowledge Bases', 'procedural', 'markdown', '使用者介面應顯示目前已關聯的知識庫清單，包含其名稱、可見性及加入日期。', 'The UI should display a list of currently associated knowledge bases, including their name, visibility, and join date.', '{UI,"Knowledge Base Association"}', 'public', 'system', '2026-04-26 00:29:46.907519+00', NULL, '19f346e6b9ce368196351ab310fcc0fe214b2868b43cce79cd4c9920e8be0aa8', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_7e3f40a4', '1.0', 'ws_spec0001', '新增知識庫關聯', 'Add Knowledge Base Association', 'procedural', 'markdown', '使用者介面應提供功能，讓使用者可以搜尋並選擇目標知識庫進行關聯，僅限公共或已有存取權的知識庫。', 'The UI should provide functionality to search and select target knowledge bases for association, limited to public KBs or those with existing access.', '{UI,"Knowledge Base Association"}', 'public', 'system', '2026-04-26 00:29:47.001045+00', NULL, 'f2473369340496fcb6392f6e752729905ea8a7cb37a37cebb1ce91ffeb268882', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_4abf6ce6', '1.0', 'ws_spec0001', 'AI Chat 整合跨知識庫上下文', 'AI Chat Integration for Cross-KB Context', 'procedural', 'markdown', '在 AI Chat 中，使用者應能選擇是否將關聯的知識庫納入跨知識庫上下文。', 'In AI Chat, users should be able to select whether to include associated knowledge bases in the cross-knowledge base context.', '{UI,"AI Chat","Knowledge Base Association"}', 'public', 'system', '2026-04-26 00:29:47.040241+00', NULL, 'd15cbc156c54c6415189a7eab841f4cc072a4aacda160f0d1d45b3eaa8685d13', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_964c73a3', '1.0', 'ws_spec0001', 'MEMTRACE_TOKEN 匿名行為', 'MEMTRACE_TOKEN Anonymous Behavior', 'factual', 'markdown', '若未傳遞 `MEMTRACE_TOKEN`，系統將維持匿名行為，僅能存取公開工作區，`list_workspaces` 將返回公開庫或空列表。', 'If `MEMTRACE_TOKEN` is not provided, the system will maintain anonymous behavior, allowing access only to public workspaces. `list_workspaces` will return public repositories or an empty list.', '{環境變數,API,認證,匿名存取}', 'public', 'system', '2026-04-26 00:29:47.061108+00', NULL, '12b69126a9d518c5b28e719a150430576fa04e99ea78b9b1c86d9a7769fee9eb', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_960858c8', '1.0', 'ws_spec0001', '.mcp.json 設定範例', '.mcp.json Configuration Example', 'factual', 'markdown', '更新後的 `.mcp.json` 範例結構包含 `mcpServers` 物件，其中 `memtrace` 服務定義了 `command`、`args` 和 `env` 變數，如 `MEMTRACE_API`、`MEMTRACE_WS`、`MEMTRACE_LANG` 和 `MEMTRACE_TOKEN`。', 'The updated `.mcp.json` example structure includes an `mcpServers` object, where the `memtrace` service defines `command`, `args`, and `env` variables such as `MEMTRACE_API`, `MEMTRACE_WS`, `MEMTRACE_LANG`, and `MEMTRACE_TOKEN`.', '{設定檔,MCP,範例,環境變數}', 'public', 'system', '2026-04-26 00:29:47.081337+00', NULL, 'cb8a163dc1c365306103f3ad0ff2315f25bf59e91ccf68703c3ca99fda285996', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_b3ee2495', '1.0', 'ws_spec0001', 'MEMTRACE_WS 作為預設工作區', 'MEMTRACE_WS as Default Workspace', 'factual', 'markdown', '`MEMTRACE_WS` 環境變數被設定為預設工作區。當工具呼叫未傳遞 `workspace_id` 參數時，將會使用此預設值。', 'The `MEMTRACE_WS` environment variable is configured as the default workspace. This default value will be used when tool calls do not provide a `workspace_id` parameter.', '{環境變數,工作區,預設值}', 'public', 'system', '2026-04-26 00:29:47.097515+00', NULL, 'fc08a173c8a31db9d4fbf0232313d32789b8d3c9b4b025c8947b7c51a658ee1b', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_41c6465d', '1.0', 'ws_spec0001', 'POST /edges/{edge_id}/traverse 端點實作', 'POST /edges/{edge_id}/traverse Endpoint', 'procedural', 'markdown', '此端點用於記錄邊的走訪，這會觸發共同存取加成（co-access boost）並增加端點兩側節點的走訪計數。', '甇斤垢暺?潸?????甇瘀?閫貊?梯赤????銝血???垢暺?暺??風閮??This endpoint is used to record the traversal of an edge, which triggers a co-access boost and increments traversal counts on both endpoint nodes.', '{api,rest,traversal,edge,co-access-boost}', 'public', 'system', '2026-04-24 11:25:40.181154+00', NULL, '92857f221640729e4aed86a22587b9cceb30a11eb100a6498d8ffcc15cb2ba88', 'ai', NULL, NULL, NULL, NULL, 0.595, 0.800, 1.000, 0.020, 0.500, 0, 0, 0, 2, 2, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_7484cfc2', '1.0', 'ws_spec0001', 'README/使用文件更新：多庫、不知 ID 使用情境', 'README/Usage Document Update: Multiple Workspaces, Unknown ID Scenario', 'procedural', 'markdown', 'README 和使用文件已更新，說明多庫、不知 ID 使用情境：設定 `MEMTRACE_TOKEN`，然後先呼叫 `list_workspaces` 取得工作區清單，再決定要操作哪個工作區。', 'The README and usage documentation have been updated to describe the multiple workspaces, unknown ID scenario: set `MEMTRACE_TOKEN`, then first call `list_workspaces` to retrieve the list of workspaces before deciding which one to operate on.', '{文件,使用情境,工作區,API}', 'public', 'system', '2026-04-26 00:29:47.140277+00', NULL, '6983266fb92ae46b22414142a0280713c5effeace03270342f52ae2abd1ed078', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_2c0de61a', '1.0', 'ws_spec0001', '驗收情境：不傳 workspace_id', 'Acceptance Scenario: No workspace_id Provided', 'procedural', 'markdown', '驗收情境之一：當呼叫工具不傳遞 `workspace_id` 時，系統應使用 `MEMTRACE_WS` 的預設值，且行為應與現有版本相同。', 'One acceptance scenario: when calling a tool without providing `workspace_id`, the system should use the default value from `MEMTRACE_WS`, and its behavior should be identical to the current version.', '{驗收測試,工作區,預設值}', 'public', 'system', '2026-04-26 00:29:47.16015+00', NULL, '89d20e0e7af63433f78a354afc2310c674a8000d91be7a2f7763c8b069a72691', 'ai', NULL, NULL, NULL, NULL, 0.715, 0.800, 1.000, 0.500, 0.500, 0, 0, 0, 0, 0, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.memory_nodes (id, schema_version, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en, tags, visibility, author, created_at, updated_at, signature, source_type, source_document, extraction_model, copied_from_node, copied_from_ws, trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep, votes_up, votes_down, verifications, traversal_count, unique_traverser_count, status, archived_at, embedding, validity_confirmed_at, validity_confirmed_by, source_file) VALUES ('mem_87639252', '1.0', 'ws_spec0001', '驗收情境：列出所有可存取工作區', 'Acceptance Scenario: List All Accessible Workspaces', 'procedural', 'markdown', '驗收情境之一：當設定 `MEMTRACE_TOKEN` 後，呼叫 `list_workspaces()` 應回傳該 token 可存取的所有工作區清單。', 'One acceptance scenario: after setting `MEMTRACE_TOKEN`, calling `list_workspaces()` should return a list of all workspaces accessible by that token.', '{驗收測試,工作區,API,認證}', 'public', 'system', '2026-04-26 00:29:47.179895+00', NULL, 'f9748eb16dab611945667df0411f7ebb856c3ecaaf7a2ee54cbf2d213a113962', 'ai', NULL, NULL, NULL, NULL, 0.593, 0.800, 1.000, 0.010, 0.500, 0, 0, 0, 1, 1, 'active', NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_p001_d001', 'ws_spec0001', 'mem_p001', 'mem_d001', 'depends_on', 1.00000, 0, '2026-04-12 00:00:21.378267+00', 90, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_p001_d002', 'ws_spec0001', 'mem_p001', 'mem_d002', 'depends_on', 1.00000, 0, '2026-04-12 00:00:21.378267+00', 90, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_p002_d006', 'ws_spec0001', 'mem_p002', 'mem_d006', 'depends_on', 1.00000, 0, '2026-04-12 00:00:21.378267+00', 90, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_p002_d005', 'ws_spec0001', 'mem_p002', 'mem_d005', 'related_to', 1.00000, 0, '2026-04-12 00:00:21.378267+00', 90, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_p003_i003', 'ws_spec0001', 'mem_p003', 'mem_i003', 'depends_on', 1.00000, 0, '2026-04-12 00:00:21.378267+00', 90, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_p003_g001', 'ws_spec0001', 'mem_p003', 'mem_g001', 'depends_on', 1.00000, 0, '2026-04-12 00:00:21.378267+00', 90, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_p001_p002', 'ws_spec0001', 'mem_p001', 'mem_p002', 'extends', 1.00000, 0, '2026-04-12 00:00:21.378267+00', 90, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_p001_p003', 'ws_spec0001', 'mem_p001', 'mem_p003', 'extends', 1.00000, 0, '2026-04-12 00:00:21.378267+00', 90, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_d001_d004', 'ws_spec0001', 'mem_d001', 'mem_d004', 'extends', 1.00000, 0, '2026-04-12 00:00:21.378267+00', 90, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_d001_d005', 'ws_spec0001', 'mem_d001', 'mem_d005', 'extends', 1.00000, 0, '2026-04-12 00:00:21.378267+00', 90, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_d001_d006', 'ws_spec0001', 'mem_d001', 'mem_d006', 'extends', 1.00000, 0, '2026-04-12 00:00:21.378267+00', 90, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_d002_g003', 'ws_spec0001', 'mem_d002', 'mem_g003', 'extends', 1.00000, 0, '2026-04-12 00:00:21.378267+00', 90, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_d002_g001', 'ws_spec0001', 'mem_d002', 'mem_g001', 'related_to', 1.00000, 0, '2026-04-12 00:00:21.378267+00', 90, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_d006_g002', 'ws_spec0001', 'mem_d006', 'mem_g002', 'related_to', 1.00000, 0, '2026-04-12 00:00:21.378267+00', 90, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_g001_d002', 'ws_spec0001', 'mem_g001', 'mem_d002', 'depends_on', 1.00000, 0, '2026-04-12 00:00:21.378267+00', 90, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_g002_g001', 'ws_spec0001', 'mem_g002', 'mem_g001', 'extends', 1.00000, 0, '2026-04-12 00:00:21.378267+00', 90, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_g002_g003', 'ws_spec0001', 'mem_g002', 'mem_g003', 'depends_on', 1.00000, 0, '2026-04-12 00:00:21.378267+00', 90, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_d004_d001', 'ws_spec0001', 'mem_d004', 'mem_d001', 'depends_on', 1.00000, 0, '2026-04-12 00:00:21.378267+00', 90, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_k001_d001', 'ws_spec0001', 'mem_k001', 'mem_d001', 'depends_on', 1.00000, 0, '2026-04-12 00:00:21.378267+00', 90, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_k001_d002', 'ws_spec0001', 'mem_k001', 'mem_d002', 'depends_on', 1.00000, 0, '2026-04-12 00:00:21.378267+00', 90, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_k002_k001', 'ws_spec0001', 'mem_k002', 'mem_k001', 'depends_on', 1.00000, 0, '2026-04-12 00:00:21.378267+00', 90, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_k003_k001', 'ws_spec0001', 'mem_k003', 'mem_k001', 'depends_on', 1.00000, 0, '2026-04-12 00:00:21.378267+00', 90, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_k003_d005', 'ws_spec0001', 'mem_k003', 'mem_d005', 'extends', 1.00000, 0, '2026-04-12 00:00:21.378267+00', 90, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_a002_k001', 'ws_spec0001', 'mem_a002', 'mem_k001', 'depends_on', 1.00000, 0, '2026-04-12 00:00:21.378267+00', 90, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_a003_a002', 'ws_spec0001', 'mem_a003', 'mem_a002', 'depends_on', 1.00000, 0, '2026-04-12 00:00:21.378267+00', 90, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_a003_d001', 'ws_spec0001', 'mem_a003', 'mem_d001', 'extends', 1.00000, 0, '2026-04-12 00:00:21.378267+00', 90, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_i002_k001', 'ws_spec0001', 'mem_i002', 'mem_k001', 'depends_on', 1.00000, 0, '2026-04-12 00:00:21.378267+00', 90, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_i003_i002', 'ws_spec0001', 'mem_i003', 'mem_i002', 'depends_on', 1.00000, 0, '2026-04-12 00:00:21.378267+00', 90, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_i003_g002', 'ws_spec0001', 'mem_i003', 'mem_g002', 'related_to', 1.00000, 0, '2026-04-12 00:00:21.378267+00', 90, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_i004_i002', 'ws_spec0001', 'mem_i004', 'mem_i002', 'extends', 1.00000, 0, '2026-04-12 00:00:00+00', 180, 0.050, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_i004_i003', 'ws_spec0001', 'mem_i004', 'mem_i003', 'related_to', 0.90000, 0, '2026-04-12 00:00:00+00', 180, 0.050, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_i004_a003', 'ws_spec0001', 'mem_i004', 'mem_a003', 'related_to', 0.85000, 0, '2026-04-12 00:00:00+00', 180, 0.050, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_k004_k001', 'ws_spec0001', 'mem_k004', 'mem_k001', 'extends', 1.00000, 0, '2026-04-12 00:00:00+00', 180, 0.050, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_k004_i004', 'ws_spec0001', 'mem_k004', 'mem_i004', 'depends_on', 1.00000, 0, '2026-04-12 00:00:00+00', 180, 0.050, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_k004_g003', 'ws_spec0001', 'mem_k004', 'mem_g003', 'related_to', 0.80000, 0, '2026-04-12 00:00:00+00', 180, 0.050, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_a004_i004', 'ws_spec0001', 'mem_a004', 'mem_i004', 'depends_on', 1.00000, 0, '2026-04-12 00:00:00+00', 180, 0.050, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_a004_i003', 'ws_spec0001', 'mem_a004', 'mem_i003', 'related_to', 0.85000, 0, '2026-04-12 00:00:00+00', 180, 0.050, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_656a0e22', 'ws_spec0001', 'mem_5f13436f', 'mem_a004', 'related_to', 0.80000, 0, '2026-04-19 23:45:20.070316+00', 365, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_b5c5dab3', 'ws_spec0001', 'mem_f9211ac0', 'mem_40a90101', 'extends', 0.90000, 0, '2026-04-19 23:49:26.383244+00', 90, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_2e1a4055', 'ws_spec0001', 'mem_9d419d24', 'mem_d001', 'related_to', 1.00000, 0, '2026-04-24 12:36:26.778339+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_fe6f055f', 'ws_spec0001', 'mem_10a89b1f', 'mem_ce00334f', 'depends_on', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_b2d8bb45', 'ws_spec0001', 'mem_8145c1ad', 'mem_25b80084', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_a68f7b40', 'ws_spec0001', 'mem_25b80084', 'mem_10a89b1f', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_d41a0854', 'ws_spec0001', 'mem_af74b0f0', 'mem_9fbbb5eb', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_64a35936', 'ws_spec0001', 'mem_af74b0f0', 'mem_d679d993', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_0a34c5a0', 'ws_spec0001', 'mem_af74b0f0', 'mem_82b732f5', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_062161ab', 'ws_spec0001', 'mem_af74b0f0', 'mem_d07c29a1', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_81b4725d', 'ws_spec0001', 'mem_af74b0f0', 'mem_22c9d8d6', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_a547ba97', 'ws_spec0001', 'mem_27e2935e', 'mem_54cc2c31', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_e68b0d5f', 'ws_spec0001', 'mem_ee62ef2c', 'mem_10a89b1f', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_5575cee7', 'ws_spec0001', 'mem_54cc2c31', 'mem_ce00334f', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_93db2df5', 'ws_spec0001', 'mem_aab6d931', 'mem_10a89b1f', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_38600758', 'ws_spec0001', 'mem_9fbbb5eb', 'mem_aab6d931', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_1c570d11', 'ws_spec0001', 'mem_82b732f5', 'mem_54cc2c31', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_8e3f199e', 'ws_spec0001', 'mem_d07c29a1', 'mem_54cc2c31', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_6c47922d', 'ws_spec0001', 'mem_22c9d8d6', 'mem_861a5678', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_047d551a', 'ws_spec0001', 'mem_cbe1be4b', 'mem_10a89b1f', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_47fe6bc3', 'ws_spec0001', 'mem_cbe1be4b', 'mem_8145c1ad', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_8274ce8b', 'ws_spec0001', 'mem_80054468', 'mem_10a89b1f', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_08f77c5f', 'ws_spec0001', 'mem_e7f9e165', 'mem_54cc2c31', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_0bc26c86', 'ws_spec0001', 'mem_861a5678', 'mem_ce00334f', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_37a338f1', 'ws_spec0001', 'mem_97757fb8', 'mem_54cc2c31', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_5ff3d7e2', 'ws_spec0001', 'mem_5e486c31', 'mem_ce00334f', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_eccd7b3c', 'ws_spec0001', 'mem_1fc8782f', 'mem_ce00334f', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_1d5ed7fe', 'ws_spec0001', 'mem_ef3bebe9', 'mem_9fbbb5eb', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_d860dd06', 'ws_spec0001', 'mem_2698efe6', 'mem_10a89b1f', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_89a4fa58', 'ws_spec0001', 'mem_993fc9e6', 'mem_ee62ef2c', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_3c022e1a', 'ws_spec0001', 'mem_993fc9e6', 'mem_cbe1be4b', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_7aadf0e2', 'ws_spec0001', 'mem_526945e4', 'mem_54cc2c31', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_72e52180', 'ws_spec0001', 'mem_7dfe253a', 'mem_54cc2c31', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_750979fa', 'ws_spec0001', 'mem_7dfe253a', 'mem_9fbbb5eb', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_468e1757', 'ws_spec0001', 'mem_7dfe253a', 'mem_d679d993', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_f7559b5d', 'ws_spec0001', 'mem_da5739b0', 'mem_10a89b1f', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_08493ecd', 'ws_spec0001', 'mem_da5739b0', 'mem_8145c1ad', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_a5cbb4aa', 'ws_spec0001', 'mem_f70b4273', 'mem_10a89b1f', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_22d5b4c2', 'ws_spec0001', 'mem_ff4e804e', 'mem_10a89b1f', 'depends_on', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_d7151fbc', 'ws_spec0001', 'mem_097ff069', 'mem_af74b0f0', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_95419a3b', 'ws_spec0001', 'mem_8a8214f3', 'mem_ce00334f', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_511b633e', 'ws_spec0001', 'mem_dbaef1ba', 'mem_10a89b1f', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_d6099c0d', 'ws_spec0001', 'mem_c3e5a685', 'mem_25b80084', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_4da7ccdb', 'ws_spec0001', 'mem_c3e5a685', 'mem_ce00334f', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_e827033b', 'ws_spec0001', 'mem_99877db7', 'mem_af74b0f0', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_44e9771f', 'ws_spec0001', 'mem_99877db7', 'mem_10a89b1f', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_f6a4447f', 'ws_spec0001', 'mem_99877db7', 'mem_d679d993', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_5a2cb28d', 'ws_spec0001', 'mem_99877db7', 'mem_82b732f5', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_66f502ea', 'ws_spec0001', 'mem_99877db7', 'mem_d07c29a1', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_e7fe22ad', 'ws_spec0001', 'mem_99877db7', 'mem_22c9d8d6', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_2ab05f4b', 'ws_spec0001', 'mem_99877db7', 'mem_cbe1be4b', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_87f16be7', 'ws_spec0001', 'mem_eedc4eef', 'mem_25b80084', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_4fb17d4f', 'ws_spec0001', 'mem_184116bb', 'mem_ce00334f', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_2a781ce1', 'ws_spec0001', 'mem_bb9aff63', 'mem_ce00334f', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_39299c86', 'ws_spec0001', 'mem_156804b8', 'mem_27e2935e', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_d98782a6', 'ws_spec0001', 'mem_a590bb10', 'mem_8145c1ad', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_c646d386', 'ws_spec0001', 'mem_9b4c8d95', 'mem_8145c1ad', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_ed1c80e0', 'ws_spec0001', 'mem_2e101ff1', 'mem_9fbbb5eb', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_e7a1f166', 'ws_spec0001', 'mem_9fe95573', 'mem_10a89b1f', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_bb746187', 'ws_spec0001', 'mem_45350e40', 'mem_27e2935e', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_ff1efcb2', 'ws_spec0001', 'mem_d1d90285', 'mem_af74b0f0', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_8f9c0f9d', 'ws_spec0001', 'mem_5b9dd113', 'mem_10a89b1f', 'extends', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_f491e209', 'ws_spec0001', 'mem_9d2bb35f', 'mem_ee62ef2c', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_214992ad', 'ws_spec0001', 'mem_9d2bb35f', 'mem_54cc2c31', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_7e889a3b', 'ws_spec0001', 'mem_9d2bb35f', 'mem_aab6d931', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_9487cec0', 'ws_spec0001', 'mem_bf7d06a5', 'mem_ce00334f', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_d0b9e9ab', 'ws_spec0001', 'mem_fee2f20e', 'mem_ce00334f', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_68f438b9', 'ws_spec0001', 'mem_f9a2bb47', 'mem_25b80084', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_533750d3', 'ws_spec0001', 'mem_565d7142', 'mem_8145c1ad', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_0c6397ff', 'ws_spec0001', 'mem_5e292da7', 'mem_27e2935e', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_24dfdebd', 'ws_spec0001', 'mem_08f1c514', 'mem_8145c1ad', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_8d7fa7f8', 'ws_spec0001', 'mem_76037494', 'mem_ee62ef2c', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_89df9f23', 'ws_spec0001', 'mem_05ce17d1', 'mem_d679d993', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_61231935', 'ws_spec0001', 'mem_a6a2a683', 'mem_ce00334f', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_5e1f7e80', 'ws_spec0001', 'mem_79dce6e3', 'mem_ce00334f', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_bd3c13c5', 'ws_spec0001', 'mem_1b0a6c77', 'mem_10a89b1f', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_671a42f3', 'ws_spec0001', 'mem_fb026368', 'mem_ce00334f', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_b710644c', 'ws_spec0001', 'mem_7f9fadcd', 'mem_ce00334f', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_35e4ebe5', 'ws_spec0001', 'mem_e9875476', 'mem_54cc2c31', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_fab2900b', 'ws_spec0001', 'mem_9209a508', 'mem_ce00334f', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_3a6cc35d', 'ws_spec0001', 'mem_bcc8e28c', 'mem_ce00334f', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_2b47e6ca', 'ws_spec0001', 'mem_013d11be', 'mem_54cc2c31', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_b38505cf', 'ws_spec0001', 'mem_45b2269d', 'mem_ce00334f', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_5a03f41d', 'ws_spec0001', 'mem_4c589d76', 'mem_ce00334f', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_61f8ef6d', 'ws_spec0001', 'mem_73ea8135', 'mem_ce00334f', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_fb7b42c2', 'ws_spec0001', 'mem_73ea8135', 'mem_8145c1ad', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_8ab83897', 'ws_spec0001', 'mem_5e541a9d', 'mem_d679d993', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_1162caa6', 'ws_spec0001', 'mem_e778fedf', 'mem_ce00334f', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_b970b4d2', 'ws_spec0001', 'mem_d4ea05e2', 'mem_ce00334f', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_622e463e', 'ws_spec0001', 'mem_1b09b6ed', 'mem_ce00334f', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_4ad63282', 'ws_spec0001', 'mem_1b09b6ed', 'mem_cbe1be4b', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_d198d0b9', 'ws_spec0001', 'mem_1b50a9b1', 'mem_80054468', 'extends', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_749a44a8', 'ws_spec0001', 'mem_1b50a9b1', 'mem_861a5678', 'extends', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_b7a3d074', 'ws_spec0001', 'mem_53258df1', 'mem_9fbbb5eb', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_8037ec69', 'ws_spec0001', 'mem_4f8e3f0b', 'mem_ce00334f', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_a32863a7', 'ws_spec0001', 'mem_4f8e3f0b', 'mem_cbe1be4b', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_933a99dc', 'ws_spec0001', 'mem_cdea5189', 'mem_ce00334f', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_12940901', 'ws_spec0001', 'mem_cdea5189', 'mem_27e2935e', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_dcb45264', 'ws_spec0001', 'mem_7f8829ed', 'mem_ce00334f', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_a1efea86', 'ws_spec0001', 'mem_7f8829ed', 'mem_cbe1be4b', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_858a86b0', 'ws_spec0001', 'mem_107440f8', 'mem_10a89b1f', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_9f6dcb71', 'ws_spec0001', 'mem_41c6465d', 'mem_ce00334f', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_731702b1', 'ws_spec0001', 'mem_c4ce77e1', 'mem_ce00334f', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_d7dbcf5c', 'ws_spec0001', 'mem_a28ca156', 'mem_ce00334f', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_60245b1b', 'ws_spec0001', 'mem_07334d61', 'mem_ce00334f', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_be22cde3', 'ws_spec0001', 'mem_07334d61', 'mem_8145c1ad', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_23a219bd', 'ws_spec0001', 'mem_21638c34', 'mem_10a89b1f', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_86da6c78', 'ws_spec0001', 'mem_21638c34', 'mem_af74b0f0', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_c8b9b311', 'ws_spec0001', 'mem_42669ba9', 'mem_8145c1ad', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_97177962', 'ws_spec0001', 'mem_6a46a549', 'mem_ce00334f', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_d6a0f5b4', 'ws_spec0001', 'mem_6a46a549', 'mem_8145c1ad', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_1f53113a', 'ws_spec0001', 'mem_d0961cfa', 'mem_27e2935e', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_3a443b0f', 'ws_spec0001', 'mem_bd6996dd', 'mem_9fbbb5eb', 'extends', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_1b6041e3', 'ws_spec0001', 'mem_f2edb572', 'mem_27e2935e', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_cb05b4ac', 'ws_spec0001', 'mem_f2edb572', 'mem_cbe1be4b', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_2d8d94c2', 'ws_spec0001', 'mem_52ac8940', 'mem_54cc2c31', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_e1db7da9', 'ws_spec0001', 'mem_4379cf51', 'mem_54cc2c31', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_6fc99ea1', 'ws_spec0001', 'mem_5a3bd1b0', 'mem_54cc2c31', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_28b93b3b', 'ws_spec0001', 'mem_82683707', 'mem_54cc2c31', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_e05e3086', 'ws_spec0001', 'mem_8575b4a1', 'mem_10a89b1f', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_cce43c8c', 'ws_spec0001', 'mem_8575b4a1', 'mem_25b80084', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_9f704b56', 'ws_spec0001', 'mem_8575b4a1', 'mem_d679d993', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_46179afc', 'ws_spec0001', 'mem_c8db759e', 'mem_ce00334f', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_91f62cc7', 'ws_spec0001', 'mem_c8db759e', 'mem_aab6d931', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_67ee8a17', 'ws_spec0001', 'mem_6089d7d9', 'mem_25b80084', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_d065f96d', 'ws_spec0001', 'mem_0d6a7214', 'mem_10a89b1f', 'related_to', 1.00000, 0, '2026-04-24 11:55:46.810734+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_787e7752', 'ws_spec0001', 'mem_263e8dd9', 'mem_10a89b1f', 'extends', 1.00000, 0, '2026-04-24 13:02:39.045024+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_cd7181cd', 'ws_spec0001', 'mem_a9dee7ad', 'mem_k001', 'related_to', 1.00000, 0, '2026-04-24 13:02:51.052196+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_7948703c', 'ws_spec0001', 'mem_c9dd39d4', 'mem_k001', 'related_to', 1.00000, 0, '2026-04-24 13:03:32.554194+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_f04d972c', 'ws_spec0001', 'mem_f027cd84', 'mem_i003', 'related_to', 1.00000, 0, '2026-04-24 13:09:26.211513+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_c1df6653', 'ws_spec0001', 'mem_00d32c49', 'mem_d001', 'related_to', 1.00000, 0, '2026-04-24 13:17:32.244924+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_pb_001', 'ws_spec0001', 'mem_p003', 'mem_playbook_001', 'extends', 1.00000, 0, '2026-04-24 13:35:36.75659+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_pb_002', 'ws_spec0001', 'mem_playbook_001', 'mem_playbook_002', 'related_to', 1.00000, 0, '2026-04-24 13:35:36.75659+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_pb_003', 'ws_spec0001', 'mem_playbook_001', 'mem_playbook_003', 'related_to', 1.00000, 0, '2026-04-24 13:35:36.75659+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_f307927c', 'ws_spec0001', 'mem_dc852972', 'mem_4621ebb5', 'related_to', 1.00000, 0, '2026-04-25 02:39:36.926692+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_9cab64b6', 'ws_spec0001', 'mem_d3564082', 'mem_cce15a1a', 'related_to', 1.00000, 0, '2026-04-25 02:39:59.693849+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_65d1eb1a', 'ws_spec0001', 'mem_3b303d15', 'mem_4621ebb5', 'related_to', 1.00000, 0, '2026-04-25 02:40:01.366196+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_d001_d003', 'ws_spec0001', 'mem_d001', 'mem_d003', 'extends', 1.00000, 0, '2026-04-11 00:00:00+00', 90, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_d005_i001', 'ws_spec0001', 'mem_d005', 'mem_i001', 'related_to', 0.90000, 0, '2026-04-11 00:00:00+00', 90, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_a002_a001', 'ws_spec0001', 'mem_a002', 'mem_a001', 'depends_on', 1.00000, 0, '2026-04-11 00:00:00+00', 90, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_i002_i001', 'ws_spec0001', 'mem_i002', 'mem_i001', 'depends_on', 1.00000, 0, '2026-04-11 00:00:00+00', 90, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_o001_i001', 'ws_spec0001', 'mem_o001', 'mem_i001', 'depends_on', 1.00000, 0, '2026-04-11 00:00:00+00', 90, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_o001_k001', 'ws_spec0001', 'mem_o001', 'mem_k001', 'depends_on', 1.00000, 0, '2026-04-11 00:00:00+00', 90, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_o001_a002', 'ws_spec0001', 'mem_o001', 'mem_a002', 'extends', 0.90000, 0, '2026-04-11 00:00:00+00', 90, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_o002_i001', 'ws_spec0001', 'mem_o002', 'mem_i001', 'depends_on', 1.00000, 0, '2026-04-11 00:00:00+00', 90, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_o002_a001', 'ws_spec0001', 'mem_o002', 'mem_a001', 'extends', 1.00000, 0, '2026-04-11 00:00:00+00', 90, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_w001_w002', 'ws_spec0001', 'mem_w001', 'mem_w002', 'depends_on', 1.00000, 0, '2026-04-11 00:00:00+00', 180, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_w002_w003', 'ws_spec0001', 'mem_w002', 'mem_w003', 'depends_on', 1.00000, 0, '2026-04-11 00:00:00+00', 180, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_w004_w001', 'ws_spec0001', 'mem_w004', 'mem_w001', 'depends_on', 1.00000, 0, '2026-04-11 00:00:00+00', 180, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_w004_d001', 'ws_spec0001', 'mem_w004', 'mem_d001', 'related_to', 0.90000, 0, '2026-04-11 00:00:00+00', 180, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_w004_i001', 'ws_spec0001', 'mem_w004', 'mem_i001', 'related_to', 0.90000, 0, '2026-04-11 00:00:00+00', 180, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_w002_d006', 'ws_spec0001', 'mem_w002', 'mem_d006', 'related_to', 0.90000, 0, '2026-04-11 00:00:00+00', 180, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_i004_i001', 'ws_spec0001', 'mem_i004', 'mem_i001', 'extends', 1.00000, 0, '2026-04-12 00:00:00+00', 180, 0.050, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_a004_a001', 'ws_spec0001', 'mem_a004', 'mem_a001', 'depends_on', 1.00000, 0, '2026-04-12 00:00:00+00', 180, 0.050, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_4fcf4b8d', 'ws_spec0001', 'mem_25ad6564', 'mem_8145c1ad', 'related_to', 1.00000, 0, '2026-04-25 14:05:07.111239+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_a304fe3e', 'ws_spec0001', 'mem_25ad6564', 'mem_27e2935e', 'depends_on', 1.00000, 0, '2026-04-25 14:05:07.111239+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_dfeb5cdb', 'ws_spec0001', 'mem_25ad6564', 'mem_k001', 'related_to', 1.00000, 0, '2026-04-25 14:05:07.111239+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_e55e384e', 'ws_spec0001', 'mem_ac50a001', 'mem_i001', 'depends_on', 1.00000, 0, '2026-04-25 14:05:07.111239+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_482615a6', 'ws_spec0001', 'mem_ac50a001', 'mem_i002', 'related_to', 1.00000, 0, '2026-04-25 14:05:07.111239+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_61a9ef7b', 'ws_spec0001', 'mem_54473627', 'mem_i002', 'extends', 1.00000, 0, '2026-04-25 14:05:07.111239+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_65ba494e', 'ws_spec0001', 'mem_54473627', 'mem_d001', 'related_to', 1.00000, 0, '2026-04-25 14:05:07.111239+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_5ad55737', 'ws_spec0001', 'mem_54473627', 'mem_p001', 'related_to', 1.00000, 0, '2026-04-25 14:05:07.111239+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_29245c4a', 'ws_spec0001', 'mem_727c2cb2', 'mem_ce00334f', 'related_to', 1.00000, 0, '2026-04-25 14:05:14.43785+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_9e3c42dc', 'ws_spec0001', 'mem_727c2cb2', 'mem_i001', 'related_to', 1.00000, 0, '2026-04-25 14:05:14.43785+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_17223f15', 'ws_spec0001', 'mem_0752c920', 'mem_27e2935e', 'extends', 1.00000, 0, '2026-04-25 14:05:14.43785+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_574a6cfe', 'ws_spec0001', 'mem_35f0002a', 'mem_27e2935e', 'extends', 1.00000, 0, '2026-04-25 14:05:14.43785+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_ed174e43', 'ws_spec0001', 'mem_fcfc3360', 'mem_i003', 'related_to', 1.00000, 0, '2026-04-25 14:05:24.442796+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_fc0dfc20', 'ws_spec0001', 'mem_b41097bf', 'mem_d001', 'extends', 1.00000, 0, '2026-04-25 14:05:31.324937+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_f704e21e', 'ws_spec0001', 'mem_b41097bf', 'mem_k001', 'related_to', 1.00000, 0, '2026-04-25 14:05:31.324937+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_373469c5', 'ws_spec0001', 'mem_e3e6a8a4', 'mem_ce00334f', 'related_to', 1.00000, 0, '2026-04-25 14:05:31.324937+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_22af54fd', 'ws_spec0001', 'mem_e3e6a8a4', 'mem_i001', 'related_to', 1.00000, 0, '2026-04-25 14:05:31.324937+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_f29eda08', 'ws_spec0001', 'mem_2c1bd9d5', 'mem_i002', 'extends', 1.00000, 0, '2026-04-25 14:05:31.324937+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_f6893d85', 'ws_spec0001', 'mem_2c1bd9d5', 'mem_k001', 'related_to', 1.00000, 0, '2026-04-25 14:05:31.324937+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_d6958040', 'ws_spec0001', 'mem_2c1bd9d5', 'mem_i003', 'related_to', 1.00000, 0, '2026-04-25 14:05:31.324937+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_eef11bfb', 'ws_spec0001', 'mem_c9bd6c49', 'mem_6d8524a7', 'extends', 1.00000, 0, '2026-04-25 14:05:43.044476+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_0d44e22e', 'ws_spec0001', 'mem_c9bd6c49', 'mem_d001', 'related_to', 1.00000, 0, '2026-04-25 14:05:43.044476+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_5235ed7e', 'ws_spec0001', 'mem_cd89f403', 'mem_d002', 'related_to', 1.00000, 0, '2026-04-25 14:05:50.641632+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_87cc947e', 'ws_spec0001', 'mem_cd89f403', 'mem_k001', 'related_to', 1.00000, 0, '2026-04-25 14:05:50.641632+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_0d8beb9d', 'ws_spec0001', 'mem_a71dcf58', 'mem_i002', 'extends', 1.00000, 0, '2026-04-25 14:05:50.641632+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_f2a2e7fa', 'ws_spec0001', 'mem_a71dcf58', 'mem_d001', 'depends_on', 1.00000, 0, '2026-04-25 14:05:50.641632+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_6f7f45f0', 'ws_spec0001', 'mem_a4bdc8a9', 'mem_i002', 'extends', 1.00000, 0, '2026-04-25 14:05:50.641632+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_1dc850d8', 'ws_spec0001', 'mem_a4bdc8a9', 'mem_d001', 'depends_on', 1.00000, 0, '2026-04-25 14:05:50.641632+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_b6970d25', 'ws_spec0001', 'mem_a4bdc8a9', 'mem_a71dcf58', 'related_to', 1.00000, 0, '2026-04-25 14:05:50.641632+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_e5c88695', 'ws_spec0001', 'mem_df5063bd', 'mem_i002', 'extends', 1.00000, 0, '2026-04-25 14:05:55.350143+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_a813d78d', 'ws_spec0001', 'mem_e10a0200', 'mem_i002', 'related_to', 1.00000, 0, '2026-04-25 14:05:55.350143+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_01635c01', 'ws_spec0001', 'mem_ce794c4c', 'mem_ce00334f', 'related_to', 1.00000, 0, '2026-04-25 14:05:55.350143+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_c2fd007f', 'ws_spec0001', 'mem_8dc3944b', 'mem_i002', 'extends', 1.00000, 0, '2026-04-25 14:06:03.811682+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_94c7575c', 'ws_spec0001', 'mem_8dc3944b', 'mem_10a89b1f', 'related_to', 1.00000, 0, '2026-04-25 14:06:03.811682+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_90fd9453', 'ws_spec0001', 'mem_8dc3944b', 'mem_8145c1ad', 'related_to', 1.00000, 0, '2026-04-25 14:06:03.811682+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_e5b99d56', 'ws_spec0001', 'mem_6709672b', 'mem_d002', 'related_to', 1.00000, 0, '2026-04-25 14:06:03.811682+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_e8ce8394', 'ws_spec0001', 'mem_6709672b', 'mem_p001', 'related_to', 1.00000, 0, '2026-04-25 14:06:03.811682+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_5e456c05', 'ws_spec0001', 'mem_f83d6e1b', 'mem_i003', 'extends', 1.00000, 0, '2026-04-25 14:06:03.811682+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_6d8ff04b', 'ws_spec0001', 'mem_f83d6e1b', 'mem_d001', 'related_to', 1.00000, 0, '2026-04-25 14:06:03.811682+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_d1d91ed3', 'ws_spec0001', 'mem_f83d6e1b', 'mem_af74b0f0', 'related_to', 1.00000, 0, '2026-04-25 14:06:03.811682+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_3614a007', 'ws_spec0001', 'mem_62d07b1d', 'mem_i003', 'extends', 1.00000, 0, '2026-04-25 14:06:13.213558+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_01b4d281', 'ws_spec0001', 'mem_62d07b1d', 'mem_i002', 'related_to', 1.00000, 0, '2026-04-25 14:06:13.213558+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_84b93650', 'ws_spec0001', 'mem_d2b5ef2f', 'mem_i003', 'extends', 1.00000, 0, '2026-04-25 14:06:20.606618+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_0550c870', 'ws_spec0001', 'mem_d2b5ef2f', 'mem_033baf41', 'related_to', 1.00000, 0, '2026-04-25 14:06:20.606618+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_7f0fd875', 'ws_spec0001', 'mem_033baf41', 'mem_d001', 'depends_on', 1.00000, 0, '2026-04-25 14:06:20.606618+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_f7a00752', 'ws_spec0001', 'mem_033baf41', 'mem_e73ea399', 'related_to', 1.00000, 0, '2026-04-25 14:06:20.606618+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_18f6785a', 'ws_spec0001', 'mem_e73ea399', 'mem_d002', 'depends_on', 1.00000, 0, '2026-04-25 14:06:20.606618+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_cf2c8559', 'ws_spec0001', 'mem_1185cce5', 'mem_i002', 'related_to', 1.00000, 0, '2026-04-25 14:06:32.013292+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_9be1e60d', 'ws_spec0001', 'mem_e0ebc6e5', 'mem_k001', 'related_to', 1.00000, 0, '2026-04-25 14:06:42.035809+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_2627ad77', 'ws_spec0001', 'mem_e0ebc6e5', 'mem_ce00334f', 'related_to', 1.00000, 0, '2026-04-25 14:06:42.035809+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_d12f2a8d', 'ws_spec0001', 'mem_71aebf92', 'mem_d001', 'related_to', 1.00000, 0, '2026-04-25 14:06:49.051845+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_a5e95faf', 'ws_spec0001', 'mem_71aebf92', 'mem_k001', 'related_to', 1.00000, 0, '2026-04-25 14:06:49.051845+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_4f84ad70', 'ws_spec0001', 'mem_71aebf92', 'mem_i002', 'depends_on', 1.00000, 0, '2026-04-25 14:06:49.051845+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_95eecfe9', 'ws_spec0001', 'mem_ef8ec8ec', 'mem_k001', 'depends_on', 1.00000, 0, '2026-04-25 14:06:49.051845+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_781b97ce', 'ws_spec0001', 'mem_ef8ec8ec', 'mem_i003', 'depends_on', 1.00000, 0, '2026-04-25 14:06:49.051845+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_3b88e540', 'ws_spec0001', 'mem_ef8ec8ec', 'mem_af74b0f0', 'related_to', 1.00000, 0, '2026-04-25 14:06:49.051845+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_23820d66', 'ws_spec0001', 'mem_524c73f6', 'mem_d001', 'related_to', 1.00000, 0, '2026-04-25 14:06:49.051845+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_e628ae9a', 'ws_spec0001', 'mem_524c73f6', 'mem_ce00334f', 'related_to', 1.00000, 0, '2026-04-25 14:06:49.051845+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_0241e599', 'ws_spec0001', 'mem_1fc9c6b4', 'mem_i003', 'related_to', 1.00000, 0, '2026-04-25 14:06:54.410669+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_dcf08ece', 'ws_spec0001', 'mem_1fc9c6b4', 'mem_af74b0f0', 'depends_on', 1.00000, 0, '2026-04-25 14:06:54.410669+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_4bec9830', 'ws_spec0001', 'mem_1fc9c6b4', 'mem_d001', 'related_to', 1.00000, 0, '2026-04-25 14:06:54.410669+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_8b2c30ba', 'ws_spec0001', 'mem_7e74197c', 'mem_i002', 'related_to', 1.00000, 0, '2026-04-25 14:42:40.023988+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_6a3c5b7f', 'ws_spec0001', 'mem_7e74197c', 'mem_i003', 'related_to', 1.00000, 0, '2026-04-25 14:42:40.023988+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_7a8dc9e0', 'ws_spec0001', 'mem_32bc6360', 'mem_d001', 'related_to', 1.00000, 0, '2026-04-25 14:42:40.023988+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_43d683a5', 'ws_spec0001', 'mem_32bc6360', 'mem_ce00334f', 'related_to', 1.00000, 0, '2026-04-25 14:42:40.023988+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_1c00c1f4', 'ws_spec0001', 'mem_fb0354ee', 'mem_i002', 'related_to', 1.00000, 0, '2026-04-25 14:42:59.149067+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_764f46eb', 'ws_spec0001', 'mem_f8057a39', 'mem_d001', 'related_to', 1.00000, 0, '2026-04-25 14:42:59.149067+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_284bd9ec', 'ws_spec0001', 'mem_76d6491f', 'mem_af74b0f0', 'related_to', 1.00000, 0, '2026-04-25 14:42:59.149067+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_71f92565', 'ws_spec0001', 'mem_31b38aa1', 'mem_d001', 'related_to', 1.00000, 0, '2026-04-25 16:02:02.51457+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_6f7058a1', 'ws_spec0001', 'mem_31b38aa1', 'mem_d002', 'related_to', 1.00000, 0, '2026-04-25 16:02:02.51457+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_ec4e067a', 'ws_spec0001', 'mem_31b38aa1', 'mem_ce00334f', 'related_to', 1.00000, 0, '2026-04-25 16:02:02.51457+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_8f89fb7c', 'ws_spec0001', 'mem_7f0a2526', 'mem_ce794c4c', 'related_to', 1.00000, 0, '2026-04-26 00:13:59.077027+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_c709aff9', 'ws_spec0001', 'mem_8c9d6883', 'mem_ce794c4c', 'related_to', 1.00000, 0, '2026-04-26 00:29:46.907519+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_e835def7', 'ws_spec0001', 'mem_7e3f40a4', 'mem_ce794c4c', 'related_to', 1.00000, 0, '2026-04-26 00:29:47.001045+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_80cfe3bf', 'ws_spec0001', 'mem_5b28def8', 'mem_ce794c4c', 'related_to', 1.00000, 0, '2026-04-26 00:29:47.019233+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_5e513c38', 'ws_spec0001', 'mem_4abf6ce6', 'mem_ce794c4c', 'related_to', 1.00000, 0, '2026-04-26 00:29:47.040241+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_fd3a3eec', 'ws_spec0001', 'mem_4abf6ce6', 'mem_5b28def8', 'depends_on', 1.00000, 0, '2026-04-26 00:29:47.040241+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_ae9ad765', 'ws_spec0001', 'mem_964c73a3', 'mem_4621ebb5', 'related_to', 1.00000, 0, '2026-04-26 00:29:47.061108+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_537826c7', 'ws_spec0001', 'mem_960858c8', 'mem_dc852972', 'related_to', 1.00000, 0, '2026-04-26 00:29:47.081337+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_772d5cd7', 'ws_spec0001', 'mem_b3ee2495', 'mem_f8057a39', 'related_to', 1.00000, 0, '2026-04-26 00:29:47.097515+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_0e02004e', 'ws_spec0001', 'mem_b3ee2495', 'mem_964c73a3', 'related_to', 1.00000, 0, '2026-04-26 00:29:47.097515+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_c50e617f', 'ws_spec0001', 'mem_d692bb11', 'mem_76d6491f', 'related_to', 1.00000, 0, '2026-04-26 00:29:47.118808+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_269859df', 'ws_spec0001', 'mem_7484cfc2', 'mem_4621ebb5', 'related_to', 1.00000, 0, '2026-04-26 00:29:47.140277+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_86ae45b8', 'ws_spec0001', 'mem_2c0de61a', 'mem_76d6491f', 'related_to', 1.00000, 0, '2026-04-26 00:29:47.16015+00', 30, 0.100, 'active', false, 0, 0.00, 0);
INSERT INTO public.edges (id, workspace_id, from_id, to_id, relation, weight, co_access_count, last_co_accessed, half_life_days, min_weight, status, pinned, traversal_count, rating_sum, rating_count) VALUES ('edge_73f801b3', 'ws_spec0001', 'mem_87639252', 'mem_4621ebb5', 'related_to', 1.00000, 0, '2026-04-26 00:29:47.179895+00', 30, 0.100, 'active', false, 0, 0.00, 0);

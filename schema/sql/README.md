# Migration Management — `schema/sql/`

本目錄存放所有 MemTrace 資料庫 schema migrations。

---

## 編號規則

- 使用 **3 位數遞增**編號，零填補（`001`, `002`, …, `042`, …）。
- 格式：`NNN_<簡短描述>.sql`，例如 `042_source_doc_backlink.sql`。
- 每個 PR 在動到 schema 前，先確認編號不衝突。

## Phase 4.8 預留編號

| 編號 | 保留給 | 任務 |
|------|-------|------|
| `042_*` | S5-6 | `source_doc_node_id` + `source_paragraph_ref` 欄位 |
| `043_*` | S8-1 | `workspaces.embedding_provider` 欄位 |
| `044_*` | S9-3 | `review_queue.split_suggestion` JSONB 欄位 |
| `045_*` | S9-5 | `workspaces.settings.node_complexity` / `dedup_threshold` |

---

## Idempotency 規範（S7-5b）

**所有 migration 必須可重複執行**，使用以下寫法：

```sql
-- 新增欄位
ALTER TABLE foo ADD COLUMN IF NOT EXISTS bar text;

-- 新增資料表
CREATE TABLE IF NOT EXISTS my_table (
  id text PRIMARY KEY,
  ...
);

-- 新增 index
CREATE INDEX IF NOT EXISTS idx_foo_bar ON foo(bar);

-- 修改 enum（需特別處理，PostgreSQL 不支援 IF NOT EXISTS）
DO $$ BEGIN
  ALTER TYPE my_enum ADD VALUE 'new_value';
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
```

---

## Rollback 政策（S7-5c）

本 phase **不寫 down migration**。但每個新增 migration 的 PR 必須在描述中說明：
- 該 migration 做了什麼
- 若 migration 執行失敗，需要的手動修復步驟（例如 `ALTER TABLE foo DROP COLUMN IF EXISTS bar;`）

---

## 執行情境（S7-5d）

### 情境 A：清空 volume 首次啟動（Docker）

```bash
docker compose down -v
docker compose up -d
```

Docker Postgres 啟動時，`docker-entrypoint-initdb.d/` 內的 init script 會按檔名順序執行所有 migration，從 `001_init.sql` 到最新。

### 情境 B：既有 DB 增量更新（開發環境）

```bash
# 手動執行新增的 migration（建議使用 psql）
psql $DATABASE_URL -f schema/sql/042_source_doc_backlink.sql

# 或使用 migrations runner（若已設定）
# python packages/api/migrations/run.py
```

---

## 驗收清單

- [ ] 清空 volume 重啟 Docker，所有 migration 通過，服務正常啟動
- [ ] 對 dev 既有 DB 執行新增的 migration，全部 idempotent 通過（執行兩次無 error）

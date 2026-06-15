import hashlib, os, textwrap

def sig(nid, title):
    return hashlib.sha256(f"{nid}{title}".encode()).hexdigest()

rows = [
    # (ws_id, node_id, title, body, tags, author)
    (
        "ws_spec0001",
        "mem_exp001",
        "知識庫探索頁（Hub）規格",
        (
            "## 目標\n\n提供統一的知識庫瀏覽與搜尋入口，解決工作區數量增長後難以找到目標 KB 的問題。\n\n"
            "## 導航邏輯（方案 B）\n\n"
            "- selectedWs === null 時，中央主內容區顯示探索頁為預設首頁\n"
            "- MemTrace logo 點擊 → 清除 selectedWs，回到探索頁\n"
            "- localStorage 記住上次工作區 ID，登入後自動跳回\n"
            "- 探索頁同時作為匿名訪客落地頁（allow_anonymous 開啟時）\n\n"
            "## 存取權限\n\n"
            "未登入：僅顯示 public / conditional_public KB。"
            "已登入：我的 KB + 公開 KB 分區塊顯示。\n\n"
            "## 後端端點：GET /workspaces/explore\n\n"
            "無需 auth。Query params：q（名稱搜尋）、lang（zh-TW/en）、sort（newest/nodes）。\n"
            "已登入時附加 Authorization header，後端額外合併返回該使用者的 private KB。\n\n"
            "## DB 異動\n\n"
            "workspaces 表新增 description text（nullable）。WorkspaceSettings 補充編輯欄位。\n\n"
            "## 前端 ExplorePage.tsx\n\n"
            "KB 卡片：名稱、描述（2 行截斷）、語言標籤、節點數 badge、visibility badge、建立者暱稱。\n"
            "篩選列：即時名稱搜尋、語言 toggle、排序（最新/節點數）。\n"
            "分區：① 我的知識庫（已登入）② 公開知識庫。\n\n"
            "狀態：pending（待實作）"
        ),
        "{feature,explore,hub,workspace,discovery,ux}",
        "usr_6bc7b4c7",
    ),
    (
        "ws_agent_loop",
        "inq_exp001",
        "功能：知識庫探索頁（Hub）",
        (
            "功能（待開發）：工作區下拉選單在知識庫數量增加後搜尋體驗差，需要統一的探索頁。\n\n"
            "設計決策（已確認）：\n"
            "- 方案 B：selectedWs === null 時預設顯示探索頁，同時作為匿名訪客落地頁\n"
            "- 登入後顯示「我的 KB + 公開 KB」統一入口\n"
            "- workspaces 表新增 description 欄位\n"
            "- 篩選：名稱搜尋、語言 toggle、排序（最新/節點數）\n"
            "- 後端：GET /workspaces/explore（public endpoint）\n\n"
            "規格節點：mem_exp001（ws_spec0001）。\n"
            "狀態：pending。期望：實作後以 answered_by 連入對應實作節點。"
        ),
        "{agent-loop,inquiry,feature,explore,hub}",
        "usr_6bc7b4c7",
    ),
]

out = []
for ws_id, nid, title, body, tags, author in rows:
    s = sig(nid, title)
    body_escaped = body.replace("'", "''")
    title_escaped = title.replace("'", "''")
    out.append(f"""
INSERT INTO memory_nodes (
    id, schema_version, workspace_id, title, body,
    content_type, content_format, tags, visibility,
    author, source_type, trust_score, signature, created_at
) VALUES (
    '{nid}', '1.0', '{ws_id}', '{title_escaped}', '{body_escaped}',
    'factual', 'markdown', '{tags}', 'public',
    '{author}', 'human', 0.85, '{s}', now()
) ON CONFLICT (id) DO UPDATE SET
    body = EXCLUDED.body,
    updated_at = now();
""".strip())

sql = "\n\n".join(out)
tmp = os.environ.get("TEMP", os.environ.get("TMP", "."))
path = os.path.join(tmp, "insert_exp001.sql")
with open(path, "w", encoding="utf-8") as f:
    f.write(sql)
print(f"Written to {path}")
print(sql[:300])

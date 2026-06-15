#!/usr/bin/env python3
"""Generate SQL INSERT statements for the 16 Phase 5 spec-as-kb nodes."""
import hashlib, json, textwrap

NODES = [
    ("mem_ta001", "factual",    ["analytics","token","retrieval","telemetry","schema","phase5"],
     "§S1 Token 遙測：retrieval_logs 表",
     "每次 retrieval / chat 呼叫都寫入 retrieval_logs 表，作為一切 token 量測的地基。\n\n表欄位：id, workspace_id, user_id, mode (search|chat|traverse), query, top_k, hit_node_ids, similarities, tokens_query, tokens_context, tokens_answer, answer_useful, trace_id, created_at。\n\n索引：(workspace_id, created_at DESC)、(workspace_id, mode, created_at DESC)。\n\n寫入點：search_nodes_in_db → mode=search；hybrid_retrieval_for_chat → mode=chat。\n\n分析端點：GET /workspaces/{ws_id}/analytics/tokens?period=7d。\n\n驗收：log 覆蓋率 ≥ 99%，token 數誤差 < 2%。",
     0.95, 0.95, 1.0, 0.9),
    ("mem_ta002", "factual",    ["analytics","health","dashboard","token","recall","schema","phase5"],
     "§S1 KB 健康度快照：kb_health_daily 表",
     "kb_health_daily 每日快照記錄知識庫核心指標，是 North Star 量測（M1-M4）的持久化來源。\n\n欄位：id, date, workspace_id, token_savings_ratio, retrieval_recall_at_5, retrieval_mrr, decay_runs_last_14d, duplicate_pairs_unlinked, avg_trust_active, active_users_7d, review_queue_depth, ai_nodes_unverified_ratio。UNIQUE (date, workspace_id)。\n\n每日 03:30 cron 快照寫入所有工作區。\n\n北極星指標（2026-05-16 實測）：M1 Token 節省率 82.1%（目標 ≥70%）、M2 Recall@5 0.9471（目標 ≥0.80）、M3 Decay 14天無中斷、M4 未連結重複對=0。",
     0.95, 0.95, 1.0, 0.92),
    ("mem_ta003", "procedural", ["dedup","similar_to","automation","cron","embedding","phase5"],
     "§S1 similar_to 自動化掃描與去重",
     "消除重複節點：embedding cosine ≥ 0.85 的節點對都應有 similar_to edge，避免把高度相似內容重複塞給 AI。\n\nbg_suggest_edges（services/bg_jobs.py）觸發時機：文件攝入後自動觸發；每週日 02:00 cron 全工作區重跑。\n\n相似度閾值：[0.85, 0.92) 自動建 similar_to edge（weight=cosine值）；≥0.92 進 review_queue 標 duplicate_candidate。\n\n驗收 SQL：找未連結高相似對，預期回傳 0。",
     0.93, 0.93, 1.0, 0.9),
    ("mem_ta004", "factual",    ["mcp-tool","merge","granularity","token","review-queue","phase5"],
     "§S1 propose_merge MCP 工具：節點粒度優化",
     "過度原子化節點（各 <50 字）比單一適當粒度節點（200 字）消耗更多 token，因為 top-k 每個都塞進 context。\n\npropose_merge 工具：參數為 node_ids 陣列和 reason。觸發條件：分析 retrieval_logs.hit_node_ids 共現矩陣，找出 ≥5 個不同 query 中同時被命中且各 body <50 字的節點群。\n\n合併流程：提案進 review_queue（change_type=merge）→ 人工確認 → 建新節點 → 舊節點 archive → 建 extends edge。\n\n驗收：合併後同題 avg context tokens 降低 ≥15%，正確率不降。",
     0.93, 0.93, 1.0, 0.9),
    ("mem_tr001", "factual",    ["trust","ai","governance","source-type","phase5"],
     "§S2 AI 節點預設 Trust 降級",
     "source_type=ai 節點若沿用預設高 trust，等同 AI 寫的就是對的，違反 trust 機制初衷。\n\n規格：source_type=ai 且 validity_confirmed_at IS NULL 者使用降級預設值：dim_accuracy=0.50（原0.95）、dim_utility=0.50（原0.90）、trust_score ≤ 0.65（原~0.924）。\n\n升級條件：累積 ≥1 次 vote_trust(accuracy≥0.8) 或 validity_confirmed_at IS NOT NULL。\n\n驗收 SQL：SELECT avg(trust_score) FROM memory_nodes WHERE source_type=ai AND validity_confirmed_at IS NULL AND status=active；應 ≤ 0.65。\n\n注意：目前 live DB 未驗證 AI 節點平均 trust ≈ 0.76，此規格尚待完整套用。",
     0.95, 0.95, 1.0, 0.92),
    ("mem_rq001", "procedural", ["review-queue","sla","steward","governance","cron","phase5"],
     "§S2 Review Queue SLA 與 Steward 輪值",
     "設計了 review queue 但沒人實際用：所有節點 validity_confirmed_at=null、vote_count=0。\n\nSLA 欄位：review_queue.assigned_to（被指派的審核者 user_id）、due_at（審核截止時間，預設指派後7天）。\n\nSteward 輪值 Cron：每週一 09:00 自動執行；找出 assigned_to IS NULL 的待審項目；round-robin 分配給 ws owner + team members；設 due_at=now()+7days；發送通知（email/webhook）。\n\nSLA 懲罰：7天未處理則節點 dim_freshness×0.8，項目進入下一輪分配。\n\n驗收：未指派率=0%，週活躍 reviewer ≥2。",
     0.95, 0.95, 1.0, 0.92),
    ("mem_ag001", "factual",    ["mcp","agent","identity","governance","inquiry-paths","phase5"],
     "§S2 MCP Agent 身份綁定",
     "匿名 MCP 呼叫會產生 ghost 節點（source_type=mcp, author=system）——無身份則無問責。\n\n現行實作：每個工作區建立時自動創建 agent node（workspaces.agent_node_id），作為 MCP 操作身份節點。inquiry_paths 表透過 agent_id 欄位記錄每次操作執行者。\n\n注意：原訂新增獨立 mcp_agents 表，目前以 agent_node_id 替代，mcp_agents 表尚未建立。\n\ninquiry_paths 表欄位：id, workspace_id, agent_id, query_text, query_emb(vector 1536), node_sequence, outcome(success|partial|failed|gap), started_at, ended_at, token_used, rating。\n\n驗收：SELECT count(*) FROM memory_nodes WHERE source_type=mcp AND author=system；應=0。",
     0.93, 0.93, 1.0, 0.9),
    ("mem_vt001", "factual",    ["trust","vote","anti-manipulation","governance","schema","phase5"],
     "§S3 投票防操縱：UNIQUE 約束與時間衰減",
     "沒有「同 user 對同 node 僅能算一票」的約束，單一使用者可刷高或刷低 trust。\n\n資料庫約束：node_trust_votes 表設有 UNIQUE(node_id, user_id)，後票覆蓋前票（ON CONFLICT UPDATE）。\n\n最低投票人數規則：同工作區節點需 ≥3 個不同 voter 才採計 trust 計算。\n\n時間衰減：超過30天的票 weight×0.5，避免早期投票永久鎖定 trust。\n\n驗收：操縱測試（單一 user 投100次）→ trust_score 變化 ≤0.05；正常測試（3個不同 user 各投1票）→ trust 完整生效。",
     0.95, 0.95, 1.0, 0.92),
    ("mem_ws003", "procedural", ["cross-workspace","sync","mcp-tool","copied-node","governance","phase5"],
     "§S3 跨工作區版本同步：sync_from_source",
     "copied_from_node 只記錄來源，來源節點更新後 copies 不會同步，導致多個工作區出現分歧內容。\n\n同步機制：原始節點更新時，透過 PostgreSQL LISTEN/NOTIFY 將所有複製節點推入 review_queue，標記 change_type=source_updated，延遲 ≤5秒。\n\nMCP 工具 sync_from_source：參數為 node_id（要同步的複製節點 id），允許手動拉取最新版本。\n\n相關欄位：memory_nodes.copied_from_node（來源節點 id）、copied_from_ws（來源工作區 id）。\n\n驗收：建節點A → 複製為節點B → 更新A → 確認B進 review_queue（change_type=source_updated），延遲 ≤5秒，所有 copies 都收到通知。",
     0.93, 0.93, 1.0, 0.9),
    ("mem_at001", "factual",    ["author","tombstone","governance","mcp-tool","schema","phase5"],
     "§S3 Author 離職與著作權轉移：author_tombstones",
     "使用者離開工作區後，其節點仍綁定該 user_id；dim_author_rep 計算對死帳號失效。\n\nauthor_tombstones 表欄位：id(serial), user_id(FK users ON DELETE CASCADE), workspace_id(FK workspaces ON DELETE CASCADE), left_at(timestamptz DEFAULT now()), transferred_to(FK users ON DELETE SET NULL), UNIQUE(user_id, workspace_id)。\n\nAuthor Rep 修正：dim_author_rep 改為「過去90天內節點品質」，避開歷史包袱。\n\ntransfer_authorship MCP 工具：參數為 node_ids 陣列和 new_author（user_id）。\n\n驗收：離職後節點 0% lock，其他 user 可正常編輯，dim_author_rep 不受死帳號干擾。",
     0.95, 0.95, 1.0, 0.92),
    ("mem_cf001", "procedural", ["conflict","contradicts","arbitration","review-queue","governance","phase5"],
     "§S3 Contradicts 衝突仲裁流程",
     "contradicts edge 只是標記，沒有強制走仲裁流程，衝突可能長期懸而未決。\n\n自動進審：建立 contradicts edge 時，系統自動將相關節點推入 review_queue（change_type=conflict）。\n\n邏輯衝突偵測（AI層）memory_nodes.conflict_status 值：contradicts_existing（與現有節點語意矛盾）、duplicate_content（內容重複）、circular_dependency（形成循環依賴）、orphaned_reference（引用不存在的節點）。\n\n仲裁結果四選一：keep_a（保留A，archive B）、keep_b（保留B，archive A）、merge（合併）、both_valid（兩者均有效，移除 contradicts edge）。\n\n仲裁結果回寫 dim_accuracy 與 status，並留下 resolution log。",
     0.95, 0.95, 1.0, 0.92),
    ("mem_ah001", "factual",    ["audit","hash-chain","integrity","mcp-tool","security","phase5"],
     "§S3 Audit Trail Hash Chain 與 verify_audit_chain",
     "audit_trail 表為 append-only，透過 hash chain 確保可驗證未被篡改。\n\naudit_trail 表 hash chain 欄位：prev_hash（前一筆的 curr_hash）、curr_hash（本筆 SHA-256 雜湊）。每筆 curr_hash = SHA-256(prev_hash || action || target_id || actor_id || created_at)。\n\nDB 層保護：trigger 拒絕 UPDATE/DELETE（append-only）。\n\nverify_audit_chain MCP 工具：參數 workspace_id，回傳 {status: ok|broken, broken_at_revision_id}。在 services/audit.py 實作，mcp_tools.py 暴露。\n\n驗收：篡改測試（手動改一筆）→ verify_audit_chain 回 broken 並指出斷點，偵測率 100%。",
     0.95, 0.95, 1.0, 0.92),
    ("mem_syn001", "factual",   ["mcp-tool","synthesis","cluster","summarize","ai","phase5"],
     "§S4 summarize_cluster MCP 工具：叢集 AI 摘要",
     "summarize_cluster 讓 AI agent 為指定叢集生成摘要節點，使查詢者能以單一節點掌握整個叢集要旨，減少逐節點遍歷的 token 消耗。\n\nMCP 工具：參數為 cluster_id 和 workspace_id。\n\n實作位置：services/synthesis.py::generate_cluster_summary、routers/kb.py::maintenance_summarize_cluster（POST /workspaces/{ws_id}/maintenance/summarize-cluster）、services/mcp_tools.py（MCP暴露）。\n\n流程：取得叢集所有 active 節點 → AI 生成摘要 → 以 source_type=ai、content_type=context 建立新節點 → 送 review_queue → 確認後與成員節點建 extends edges。\n\n使用場景：叢集成員 >10 個節點時，摘要節點作為入口，token 節省顯著。",
     0.93, 0.93, 1.0, 0.92),
    ("mem_syn002", "factual",   ["mcp-tool","synthesis","bilingual","language","complement","phase5"],
     "§S4 complement_node_languages MCP 工具：補全雙語缺口",
     "complement_node_languages 偵測工作區中語言缺口（只有 zh 沒有 en，或相反），由 AI 自動翻譯補全。\n\nMCP 工具：參數為 workspace_id 和 target_language（zh-TW|en）。\n\n雙語工作區架構：ws_spec0001（zh-TW）和 ws_spec0001_en（en）透過 workspaces.linked_workspace_id 互相連結。英文節點 id 格式：{zh_id}_en（如 mem_d001_en）。\n\n翻譯流程：找出 zh 有但 en 沒有的節點 → AI 生成英文版 body → 建 {id}_en 節點（source_type=ai）→ 送 review_queue → 審核通過後加入 en workspace。\n\nPhase 5 後 en 節點缺口（約30個）可用此工具批量生成。",
     0.93, 0.93, 1.0, 0.92),
    ("mem_syn003", "factual",   ["mcp-tool","synthesis","edges","suggest","embedding","phase5"],
     "§S4 suggest_edges MCP 工具：AI 建議缺失邊",
     "suggest_edges 分析節點語意關係，找出應連但尚未連結的 edges，提案送審，避免孤立節點造成 traversal 斷路。\n\nMCP 工具：參數為 workspace_id 和 threshold（預設0.75）。\n\n實作位置：services/synthesis.py::suggest_missing_edges、services/nodes.py::suggest_edges_for_node_in_db（單節點版）、routers/kb.py::maintenance_suggest_edges、services/bg_jobs.py::bg_suggest_edges（背景任務）、services/mcp_tools.py（MCP暴露）。\n\n觸發時機：文件攝入後自動觸發 bg_suggest_edges(ws_id, new_node_id, user_id)；或手動觸發。\n\n邊提案流程：cosine ≥ threshold 且無現有邊 → 生成邊提案 → review_queue（change_type=edge_suggestion）→ 人工確認後建立正式邊。",
     0.95, 0.95, 1.0, 0.92),
    ("mem_tg001", "factual",    ["security","rate-limit","traversal","guard","hardening","phase5"],
     "§S5 TraversalGuard：圖遍歷速率限制",
     "防止惡意或失控的 AI agent 無限遍歷知識圖，導致 DoS 或 embedding 濫用。\n\n實作位置：core/ratelimit.py::TraversalGuard。\n\n使用點：routers/kb.py 節點讀取路由（TraversalGuard.check(viewer_id)）、services/nodes.py::get_node_in_db、services/edges.py 邊相關操作。\n\n限制規則：TraversalGuard.check(user_id) 超過限制回傳 429 Too Many Requests。限制針對 viewer_id（user_id 或 agent_id），非 IP。不影響 cron/維護工作的正常遍歷。速率計數使用記憶體快取（可換 Redis，參見 mem_inq002）。",
     0.95, 0.95, 1.0, 0.9),
]

lines = ["BEGIN;"]
for nid, ctype, tags, title, body, ts, acc, fresh, util in NODES:
    sig = hashlib.sha256(f"{nid}{title}".encode()).hexdigest()
    tag_str = "{" + ",".join(tags) + "}"
    body_e = body.replace("'", "''")
    title_e = title.replace("'", "''")
    lines.append(
        f"INSERT INTO memory_nodes "
        f"(id,schema_version,workspace_id,content_type,content_format,tags,visibility,author,source_type,"
        f"title,body,trust_score,dim_accuracy,dim_freshness,dim_utility,dim_author_rep,"
        f"votes_up,votes_down,verifications,traversal_count,unique_traverser_count,status,version,signature) "
        f"VALUES "
        f"('{nid}','1.0','ws_spec0001','{ctype}','markdown','{tag_str}','public','memtrace-spec','human',"
        f"'{title_e}','{body_e}',{ts},{acc},{fresh},{util},0.9,"
        f"0,0,0,0,0,'active',1,'{sig}') "
        f"ON CONFLICT (id) DO NOTHING;"
    )

lines.append("COMMIT;")
sql = "\n".join(lines)

import os, sys
out = os.path.join(os.environ.get("TEMP", os.environ.get("TMP", ".")), "phase5_nodes.sql")
with open(out, "w", encoding="utf-8") as f:
    f.write(sql)

print(f"Generated {len(NODES)} INSERT statements → {out}")

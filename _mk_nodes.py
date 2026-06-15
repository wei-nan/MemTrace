"""Create two inquiry nodes in ws_spec_plan via MCP HTTP API."""
import json, urllib.request, urllib.error, sys

TOKEN = "mt_5ef478151429e2d28fea0559cb6ac487f84b21a3"
BASE = "http://localhost:8001/mcp"

def mcp_call(method, params, req_id=1):
    payload = json.dumps({
        "jsonrpc": "2.0", "id": req_id,
        "method": method, "params": params
    }).encode()
    req = urllib.request.Request(
        BASE,
        data=payload,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        return {"error": f"HTTP {e.code}: {body[:500]}"}

    # strip SSE prefixes
    lines = []
    for line in raw.splitlines():
        if line.startswith("data:"):
            lines.append(line[5:].strip())
        elif line.startswith("event:") or line == "":
            continue
        else:
            lines.append(line)
    text = "\n".join(lines)
    try:
        outer = json.loads(text)
    except Exception:
        return {"raw": text[:1000]}
    result = outer.get("result", {})
    content = result.get("content", [])
    if content and isinstance(content[0], dict):
        inner_text = content[0].get("text", "")
        try:
            return json.loads(inner_text)
        except Exception:
            return {"text": inner_text}
    return result

# ---- Step 1: list workspaces to get ws_spec_plan id ----
print("=== list_workspaces ===")
ws_list = mcp_call("tools/call", {"name": "list_workspaces", "arguments": {}})
print(json.dumps(ws_list, ensure_ascii=False, indent=2)[:2000])

# find ws_spec_plan
ws_id = None
workspaces = ws_list if isinstance(ws_list, list) else ws_list.get("workspaces", ws_list.get("items", []))
for ws in workspaces:
    if isinstance(ws, dict) and (ws.get("id") == "ws_spec_plan" or ws.get("slug") == "ws_spec_plan"):
        ws_id = ws.get("id") or ws.get("workspace_id")
        print(f"\n✓ ws_spec_plan id = {ws_id}")
        break

if not ws_id:
    print("Could not find ws_spec_plan, aborting")
    sys.exit(1)

# ---- Step 2: create node 1 — inquiry 自我審議迴圈 ----
print("\n=== create node 1 (self-deliberation loop) ===")

body1 = """【缺口】inquiry 自我審議迴圈（多模型 + scale 開關）

## 背景
MemTrace 規格規劃庫（ws_spec_plan）中的 inquiry 節點，目前只能由人工或 agent 觸發人工審議，缺乏依議題規模自動升級至多模型審議的機制。

## 設計結論（2026-06-15 討論）

### scale 欄位
- 每個 inquiry 節點新增 `scale` 欄位：`minor`（預設）或 `major`
- `minor`：無需大模型介入，純人工 / 規則流程
- `major`：觸發多模型自我審議迴圈（必須有 human gate）
- 升級方式：由人或人透過 agent 將 scale 從 minor 改為 major

### 自我審議迴圈流程（scale=major 時）
1. inquiry 節點標記 scale=major → MemTrace emit webhook（conductor 訂閱）
2. 外部 harness 收到 webhook，fan-out 至多個 LLM（如 Claude/Codex/Gemini）
3. 各模型寫回 proposal 節點（透過 MCP converge_proposals）
4. MemTrace layered write-back 整合多方意見
5. human gate 審核後才能 archive / 轉為 answered
6. 原始模型意見在決策後可 archive（需要時調出）

### A1 邊界
- MemTrace 本體不主動呼叫任何 LLM，只發 webhook 並收集寫回
- LLM fan-out 由外部 harness 負責（Conductor opt-in 掛 webhook 即可）

## 待決事項
- [ ] inquiry schema 新增 scale 欄位（預設 minor）
- [ ] webhook payload 格式定義（含 scale、inquiry_id、ws_id）
- [ ] converge_proposals 對 scale=major 的特殊處理（不自動 merge，等 human gate）
- [ ] archive 格式：archived_proposals 集合 vs 獨立節點？
- [ ] UI：scale 升級入口（inquiry 詳情頁按鈕 or status dropdown）

## 相關節點
- mem_75c61710（Conductor 設計）
- mem_aaad94e3（agent loop playbook）
"""

r1 = mcp_call("tools/call", {
    "name": "create_node",
    "arguments": {
        "workspace_id": ws_id,
        "title": "缺口：inquiry 自我審議迴圈（多模型 + scale 開關）",
        "body": body1,
        "node_type": "inquiry",
        "status": "open",
        "tags": ["inquiry", "agent-loop", "multi-model", "conductor", "scale"],
        "language": "zh"
    }
}, req_id=2)
print(json.dumps(r1, ensure_ascii=False, indent=2)[:1000])
node1_id = r1.get("id") or r1.get("node_id")
print(f"node1_id = {node1_id}")

# ---- Step 3: create node 2 — 背景作業可觀測性 ----
print("\n=== create node 2 (background job observability) ===")

body2 = """【缺口】背景作業可觀測性（job_runs / 心跳；審查員跑了沒紀錄）

## 現況問題
`packages/api/core/scheduler.py` 登記了 11 個背景迴圈，其中包含 7 個 AI 審查員（每日執行）：
- deduper, tag_normalizer, edge_auditor, embedding_consistency,
  trust_calibrator, coverage_gap_detector, source_decay_monitor

**問題**：這些 job 執行後沒有任何持久化紀錄。錯誤被 `results[name]=-1` 吞掉，`audit_writer_loop` 只記錄 HTTP 請求（ws_access_log），不記錄背景 job。

## 需要什麼
兩層可觀測性機制：

### Layer 1：job_heartbeat（高頻，upsert）
- 每個迴圈 tick 前後 upsert 一筆心跳記錄
- 欄位：job_name, last_seen_at, status（running/idle/error）
- 輕量，不爆炸式增長

### Layer 2：job_runs（低頻，append，有意義的 job）
- 只記錄「有意義的執行」（如 AI 審查員完成一輪）
- 欄位：job_name, started_at, finished_at, result_summary, error_msg
- 可供 UI 顯示「上次跑了什麼、有沒有錯誤」

## 阻擋點
schema / migrations 技術債（mem_bfec3997）——目前缺乏一致的 migration 流程，新增資料表風險高。需先解決 migrations 基礎設施再建 job_runs 表。

## 短期緩解（不動 schema）
- 現有審查員 job 改為把 summary 寫進 ws_access_log（type=job_run）
- 或寫進一個指定的 MemTrace 節點（每日覆寫摘要）

## 待決事項
- [ ] 確認 migrations 策略（depends on mem_bfec3997）
- [ ] 決定 job_heartbeat 存放位置（DB table vs Redis）
- [ ] job_runs 表 schema 設計
- [ ] AI 審查員錯誤改為浮出 / alert，不再吞掉
- [ ] UI 入口：Workspace Settings > 背景作業健康度 tab
"""

r2 = mcp_call("tools/call", {
    "name": "create_node",
    "arguments": {
        "workspace_id": ws_id,
        "title": "缺口：背景作業可觀測性（job_runs / 心跳；審查員跑了沒紀錄）",
        "body": body2,
        "node_type": "inquiry",
        "status": "open",
        "tags": ["inquiry", "observability", "background-jobs", "scheduler", "audit-reviewer"],
        "language": "zh"
    }
}, req_id=3)
print(json.dumps(r2, ensure_ascii=False, indent=2)[:1000])
node2_id = r2.get("id") or r2.get("node_id")
print(f"node2_id = {node2_id}")

# ---- Step 4: create edges ----
print("\n=== creating edges ===")

edges_to_create = []
if node1_id:
    edges_to_create += [
        (node1_id, "mem_75c61710", "related_to"),
        (node1_id, "mem_aaad94e3", "related_to"),
    ]
if node2_id:
    edges_to_create += [
        (node2_id, "mem_bfec3997", "depends_on"),
    ]
if node1_id and node2_id:
    edges_to_create.append((node1_id, node2_id, "related_to"))

for eid, (src, tgt, rel) in enumerate(edges_to_create, start=10):
    print(f"  edge {src} --[{rel}]--> {tgt}")
    er = mcp_call("tools/call", {
        "name": "create_edge",
        "arguments": {
            "workspace_id": ws_id,
            "source_id": src,
            "target_id": tgt,
            "relation": rel
        }
    }, req_id=eid)
    status = er.get("id") or er.get("edge_id") or er.get("error") or er
    print(f"    => {status}")

print("\n=== DONE ===")
print(f"node1: {node1_id}")
print(f"node2: {node2_id}")

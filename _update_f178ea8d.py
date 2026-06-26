"""Write the multi-model-collaboration discussion body into mem_f178ea8d (ws_spec_plan).

Mirrors _mk_nodes.py: talks to the local MCP HTTP endpoint, finds ws_spec_plan,
then update_node + create_edge. Edge targets default to the spec-as-kb snapshot ids
(mem_inq001/004/005); override EDGE_TARGETS with the live ids if they differ.
"""
import json, os, urllib.request, urllib.error, sys

# Secrets/config come from the environment — do NOT hardcode tokens in the repo.
#   MEMTRACE_TOKEN  : workspace API key (required)
#   MEMTRACE_MCP    : MCP endpoint (default http://localhost:8001/mcp)
#   EDGE_TARGETS    : optional "id:relation,id:relation,..." override for the live ws ids
TOKEN = os.environ.get("MEMTRACE_TOKEN", "")
BASE = os.environ.get("MEMTRACE_MCP", "http://localhost:8001/mcp")

NODE_ID = "mem_f178ea8d"

# (target_node_id, relation) — defaults to the spec-as-kb snapshot ids.
# Override with the *live* ws_spec_plan ids via the EDGE_TARGETS env var.
EDGE_TARGETS = [
    ("mem_inq001", "related_to"),  # 多 planner 規劃討論（fan-out + 共識裁決）
    ("mem_inq004", "related_to"),  # Conductor — MemTrace 主動觸發外部 harness
    ("mem_inq005", "depends_on"),  # 多 agent 信任分級（per-model competence 的前置）
]
if os.environ.get("EDGE_TARGETS"):
    EDGE_TARGETS = [
        (pair.split(":", 1)[0], pair.split(":", 1)[1])
        for pair in os.environ["EDGE_TARGETS"].split(",") if ":" in pair
    ]


def mcp_call(method, params, req_id=1):
    payload = json.dumps({
        "jsonrpc": "2.0", "id": req_id, "method": method, "params": params
    }).encode()
    req = urllib.request.Request(
        BASE, data=payload,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read().decode('utf-8')[:500]}"}
    lines = []
    for line in raw.splitlines():
        if line.startswith("data:"):
            lines.append(line[5:].strip())
        elif line.startswith("event:") or line == "":
            continue
        else:
            lines.append(line)
    try:
        outer = json.loads("\n".join(lines))
    except Exception:
        return {"raw": "\n".join(lines)[:1000]}
    result = outer.get("result", {})
    content = result.get("content", [])
    if content and isinstance(content[0], dict):
        inner = content[0].get("text", "")
        try:
            return json.loads(inner)
        except Exception:
            return {"text": inner}
    return result


BODY = """# 待討論：多模型協作 harness 的產品化邊界與精進迴圈

**議題規模：** major（建議；牽動 A1 邊界與精進迴圈設計）

## 背景
要把「多核心模型（Claude / Codex / Gemini）協作」做成產品，必須先釘死兩件事：
(1) **產品化邊界** — MemTrace 到哪裡為止，harness 從哪裡開始；
(2) **精進迴圈** — 多模型如何不只一次性辯論，而是隨時間彼此精進。
本節點基於外部研究 + 既有公理（A1 / A3 / A7）整理結論與待決事項。

## 立場與結論

### 1. 產品化邊界：守住 A1，把 orchestrator 當可替換的客戶
外部經驗（多 agent orchestrator 的實戰教訓）指向同一個痛點：協作真正缺的不是更強的
orchestrator（已是紅海），而是**可繼承、可審計的共享記憶**——context 必須顯式注入、
agent 之間沒有隱式共享、同一個 bug 會重複出現。MemTrace 的稀缺價值就在這一層。
→ **不要做 conductor/runtime**；邊界守在「記憶 + 仲裁存儲」，任何 harness 都能接。

### 2. Conductor 不算越界，但要畫更細的線（回應 mem_inq004）
- **MemTrace 負責：** 發事件（webhook，等同 DB trigger / CDC）＋ 收 proposal 寫回 ＋ 仲裁/存儲。
- **Harness 負責：** fan-out 到多核心、跑 tool-use 沙盒、管 context。
- **紀律（A1）：** MemTrace 本體永不主動呼叫任何 LLM。
  ⚠️ `converge_proposals` 複用 consult synthesizer — 須確認 synthesizer 不會在仲裁時偷打 LLM，否則 A1 被暗中破壞。

### 3. 精進迴圈：避免「越辯越糟」
研究顯示多輪互評不必然變好（回合越多噪音越多），故 scale=major 迴圈不能無腦多輪：
- **外部錨點優先：** 對程式類 inquiry，用可執行驗證（測試 / lint / type-check）當 tie-breaker，
  而非讓模型互相說服（solver–verifier gap：驗證比解題容易）。
- **異質 fan-out 是設計約束：** 價值來自 diverse reasoning chains；刻意用不同核心，
  別退化成同一模型跑 N 次的同質投票。
- **human gate 不擋路：** 高共識 + 通過驗證 → 自動收斂；分歧大或低信任 → 才升級 human。

### 4. 「彼此精進」的載體：已有三件，缺第四件
| 研究機制 | MemTrace 既有對應 |
|---|---|
| cross-model verification | trust votes / verifications |
| 對抗自我精進退化的遺忘 | edge decay（沒人走的提案淡出） |
| 少數正確意見不被多數淹沒 | archived_proposals（可調出） |

**缺口（本節點主張新增）：** per-model **competence profile** — 累積「哪個核心在哪類 inquiry
歷史更準」，用來加權 converge_proposals 並 route 未來 fan-out。沒有它，每次辯論從零開始；
有了它，協作從一次性辯論升級為長期學習。這是「彼此精進」名副其實的關鍵，
且與 mem_inq005（per-agent 信任）互補：inq005 偏 security/污染防禦，本缺口偏能力畫像。

## 待決事項
- [ ] 確認 `converge_proposals` / consult synthesizer 在仲裁路徑上是否呼叫 LLM（守 A1）
- [ ] scale=major 迴圈加入「可執行驗證 tie-breaker」掛點（測試 / lint 結果如何回流？）
- [ ] fan-out 異質性如何在 webhook payload / harness 契約中表達（指定核心集合？）
- [ ] human gate 自動收斂門檻：用哪些 trust 維度 + 共識度公式
- [ ] per-model competence profile：存放位置（A7：run-state 不進知識圖 → 另闢計分表？）、
      更新時機（submit_outcome 回流時）、與 trust 維度的關係
- [ ] 與 mem_inq001 多 planner 共識裁決、mem_inq005 信任分級的介面對齊

## 相關節點
- mem_inq001（多 planner 規劃討論 — fan-out + 共識裁決）
- mem_inq004（Conductor — MemTrace 主動觸發外部 harness）
- mem_inq005（多 agent 信任分級 — per-model competence 的前置）
"""


def main():
    if not TOKEN:
        print("MEMTRACE_TOKEN env var is required (export your workspace API key).")
        sys.exit(1)
    ws = mcp_call("tools/call", {"name": "list_workspaces", "arguments": {}})
    workspaces = ws if isinstance(ws, list) else ws.get("workspaces", ws.get("items", []))
    ws_id = next(
        (w.get("id") or w.get("workspace_id") for w in workspaces
         if isinstance(w, dict) and (w.get("id") == "ws_spec_plan" or w.get("slug") == "ws_spec_plan")),
        None,
    )
    if not ws_id:
        print("Could not find ws_spec_plan, aborting")
        sys.exit(1)
    print(f"✓ ws_spec_plan id = {ws_id}")

    print(f"\n=== update_node {NODE_ID} ===")
    r = mcp_call("tools/call", {
        "name": "update_node",
        "arguments": {
            "workspace_id": ws_id,
            "node_id": NODE_ID,
            "title": "待討論：多模型協作 harness 的產品化邊界與精進迴圈",
            "body": BODY,
            "content_format": "markdown",
            "tags": ["inquiry", "gap", "multi-model", "harness", "conductor",
                     "self-improvement", "agent-loop"],
            "resolution_status": "open",
        },
    }, req_id=2)
    print(json.dumps(r, ensure_ascii=False, indent=2)[:1200])

    print("\n=== edges ===")
    for i, (tgt, rel) in enumerate(EDGE_TARGETS, start=10):
        er = mcp_call("tools/call", {
            "name": "create_edge",
            "arguments": {"workspace_id": ws_id, "from_id": NODE_ID,
                          "to_id": tgt, "relation": rel},
        }, req_id=i)
        print(f"  {NODE_ID} --[{rel}]--> {tgt}  => "
              f"{er.get('id') or er.get('edge_id') or er.get('error') or er}")

    print("\n=== DONE ===")


if __name__ == "__main__":
    main()

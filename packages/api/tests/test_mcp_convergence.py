import sys
import os
import pytest
import datetime
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import HTTPException

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.node_projection import calculate_top_edges, project_node
from services.mcp_tools import execute_tool, dispatch, USER_CAPABILITIES

# ─── 1. Top Edges 計算邏輯測試 ──────────────────────────────────────────────────

def test_calculate_top_edges():
    # 建立多個模擬 edges
    now = datetime.datetime.now(datetime.timezone.utc)
    
    # 模擬 5 條邊
    edges = [
        # out 邊
        {"relation": "depends_on", "weight": 0.8, "traversal_count": 5, "last_co_accessed": now, "direction": "out", "target_id": "mem_out_1", "target_title": "Out 1"},
        {"relation": "extends", "weight": 0.5, "traversal_count": 2, "last_co_accessed": now - datetime.timedelta(days=1), "direction": "out", "target_id": "mem_out_2", "target_title": "Out 2"},
        # in 邊
        {"relation": "contradicts", "weight": 0.9, "traversal_count": 1, "last_co_accessed": now, "direction": "in", "target_id": "mem_in_1", "target_title": "In 1"},
        {"relation": "answered_by", "weight": 0.7, "traversal_count": 10, "last_co_accessed": now - datetime.timedelta(days=5), "direction": "in", "target_id": "mem_in_2", "target_title": "In 2"},
        {"relation": "similar_to", "weight": 0.3, "traversal_count": 0, "last_co_accessed": now - datetime.timedelta(days=10), "direction": "in", "target_id": "mem_in_3", "target_title": "In 3"},
    ]
    
    # 進行計算
    top_edges = calculate_top_edges(edges)
    
    # 預期：總數最多 3 條，且 in/out 混合取
    assert len(top_edges) <= 3
    
    # 檢查是否各取 1.5 條 (即第一輪 in/out 各先拿一條高分的)
    # score 計算: 
    # Out 1: (0.8 * 2) + (5 * 0.1) + 1.0 = 1.6 + 0.5 + 1.0 = 3.1
    # Out 2: (0.5 * 2) + (2 * 0.1) + 0.5 = 1.0 + 0.2 + 0.5 = 1.7
    # In 1: (0.9 * 2) + (1 * 0.1) + 1.0 = 1.8 + 0.1 + 1.0 = 2.9
    # In 2: (0.7 * 2) + (10 * 0.1) + (1/(1+5)) = 1.4 + 1.0 + 0.166 = 2.566
    # In 3: (0.3 * 2) + (0 * 0.1) + (1/(1+10)) = 0.6 + 0 + 0.09 = 0.69
    #
    # 第一輪：
    # in 中最高：In 1 (2.9)
    # out 中最高：Out 1 (3.1)
    # 第二輪：
    # 剩餘中最高：In 2 (2.566)
    # 最終選取：Out 1, In 1, In 2
    
    selected_targets = [e["target_id"] for e in top_edges]
    assert "mem_out_1" in selected_targets
    assert "mem_in_1" in selected_targets
    assert "mem_in_2" in selected_targets
    assert "mem_out_2" not in selected_targets

def test_calculate_top_edges_empty():
    assert calculate_top_edges([]) == []


# ─── 2. Node Projection 測試 ────────────────────────────────────────────────────

def test_project_node():
    node = {
        "id": "mem_1",
        "title": "Node 1",
        "content_type": "factual",
        "body": "This is a factual body text " * 10,  # 約 280 chars
        "tags": ["tag1", "tag2"],
        "trust_score": 0.85
    }
    
    top_edges = [{"relation": "depends_on", "target_id": "mem_2", "target_title": "Target", "weight": 0.8}]
    
    # 測試 probe level
    probe = project_node(node, "probe", top_edges)
    assert set(probe.keys()) == {"id", "title", "content_type", "tags", "trust_score", "summary_1line", "top_edges"}
    assert probe["summary_1line"] == node["body"][:80]
    assert len(probe["top_edges"]) == 1
    
    # 測試 brief level
    brief = project_node(node, "brief", top_edges)
    assert set(brief.keys()) == {"id", "title", "content_type", "tags", "trust_score", "summary_1line", "top_edges", "body_excerpt_200", "why_matched"}
    assert brief["body_excerpt_200"] == node["body"][:200]
    
    # 測試 full level
    full = project_node(node, "full", top_edges)
    assert "body" in full
    assert full["top_edges"] == top_edges
    assert "summary_1line" in full
    
    # 驗證 probe 模式的 token 數量比例 (DoD 條款：probe 模式 token 用量 <= 60% * full 模式)
    import json
    probe_tokens = len(json.dumps(probe))
    full_tokens = len(json.dumps(full))
    assert probe_tokens <= 0.6 * full_tokens


def test_project_node_full_whitelists_internal_bookkeeping_fields():
    """full 等級預設應濾除 signature/dim_*/ask_count 等內部簿記欄位（2026-07-07 瘦身）。"""
    node = {
        "id": "mem_1",
        "title": "Node 1",
        "content_type": "factual",
        "body": "some body",
        "tags": ["tag1"],
        "trust_score": 0.85,
        "signature": "deadbeef" * 8,
        "dim_accuracy": 0.5,
        "dim_freshness": 1.0,
        "dim_utility": 0.5,
        "dim_author_rep": 0.5,
        "ask_count": 3,
        "miss_count": 1,
        "cluster_id": None,
        "votes_up": 2,
        "votes_down": 0,
        "metadata": {"foo": "bar"},
    }

    full = project_node(node, "full")
    assert "body" in full
    assert "signature" not in full
    assert "dim_accuracy" not in full
    assert "ask_count" not in full
    assert "miss_count" not in full
    assert "votes_up" not in full
    assert "metadata" not in full


def test_project_node_full_debug_returns_raw_row():
    """debug=True 時 full 等級應回退為完整原始欄位，供維運排查用。"""
    node = {
        "id": "mem_1",
        "title": "Node 1",
        "body": "some body",
        "signature": "deadbeef" * 8,
        "dim_accuracy": 0.5,
    }

    full_debug = project_node(node, "full", debug=True)
    assert full_debug["signature"] == "deadbeef" * 8
    assert full_debug["dim_accuracy"] == 0.5


# ─── 3. Capability Handshake 測試 ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_capability_handshake():
    user = {"sub": "user_cap_test"}
    
    # 1. 測試 small
    payload_small = {
        "jsonrpc": "2.0",
        "id": "init_1",
        "method": "initialize",
        "params": {
            "capabilities": {
                "model_size": "small",
                "context_limit": 4096
            }
        }
    }
    USER_CAPABILITIES.pop("user_cap_test", None)
    res = await dispatch(payload_small, user, MagicMock())
    assert res["id"] == "init_1"
    assert "user_cap_test" in USER_CAPABILITIES
    assert USER_CAPABILITIES["user_cap_test"]["model_size"] == "small"
    
    # 模擬 get_node 工具調用時，因 model_size == 'small' 而 default detail_level 為 'probe'
    args = {"workspace_id": "ws_1", "node_id": "mem_1"}
    cur = MagicMock()
    cur.fetchone.return_value = {
        "id": "mem_1",
        "title": "Node 1",
        "content_type": "factual",
        "body": "Body content",
        "tags": [],
        "trust_score": 0.9
    }
    mock_db_cursor = MagicMock()
    mock_db_cursor.__enter__.return_value = cur
    
    with patch("services.mcp_tools.db_cursor", return_value=mock_db_cursor):
        with patch("services.mcp_tools.get_node_in_db", return_value=cur.fetchone.return_value):
            with patch("services.node_projection.get_node_top_edges", return_value=[]):
                resp = await execute_tool("get_node", args, user, MagicMock())
                assert "body" not in resp
                assert "summary_1line" in resp

    # 2. 測試 medium
    payload_med = {
        "jsonrpc": "2.0",
        "id": "init_2",
        "method": "initialize",
        "params": {
            "capabilities": {
                "model_size": "medium"
            }
        }
    }
    await dispatch(payload_med, user, MagicMock())
    assert USER_CAPABILITIES["user_cap_test"]["model_size"] == "medium"

    # 3. 測試 large
    payload_lg = {
        "jsonrpc": "2.0",
        "id": "init_3",
        "method": "initialize",
        "params": {
            "capabilities": {
                "model_size": "large"
            }
        }
    }
    await dispatch(payload_lg, user, MagicMock())
    assert USER_CAPABILITIES["user_cap_test"]["model_size"] == "large"
    
    # 模擬 get_node 在 large 時自動 fallback 到 full
    with patch("services.mcp_tools.db_cursor", return_value=mock_db_cursor):
        with patch("services.mcp_tools.get_node_in_db", return_value=cur.fetchone.return_value):
            with patch("services.node_projection.get_node_top_edges", return_value=[]):
                resp = await execute_tool("get_node", args, user, MagicMock())
                assert "body" in resp
                assert resp["body"] == "Body content"


# ─── 4. Token Budget 限制降級與裁切測試 ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_token_budget_node_truncation():
    user = {"sub": "user_1"}
    # 故意設定很小的 max_response_tokens = 50，以觸發降級與裁切
    args = {"workspace_id": "ws_1", "node_id": "mem_1", "detail_level": "full", "max_response_tokens": 30}
    
    node = {
        "id": "mem_1",
        "title": "A very long node title " * 5,
        "content_type": "procedural",
        "body": "Very long content indeed! " * 50, # 長 body
        "tags": ["tag_a", "tag_b", "tag_c"],
        "trust_score": 0.95
    }
    
    mock_db_cursor = MagicMock()
    mock_db_cursor.__enter__.return_value = MagicMock()
    
    with patch("services.mcp_tools.db_cursor", return_value=mock_db_cursor):
        with patch("services.mcp_tools.get_node_in_db", return_value=node):
            with patch("services.node_projection.get_node_top_edges", return_value=[{"relation": "depends_on", "target_id": "mem_2", "target_title": "Target", "weight": 0.8}]):
                resp = await execute_tool("get_node", args, user, MagicMock())
                
                # 應該被裁切 (truncated)
                assert resp.get("truncated") is True
                # 最低限度要保留 id 與 title
                assert resp["id"] == "mem_1"
                assert "title" in resp
                # body 等大型欄位在 probe/brief 以下應該已經被拔掉或是極限裁切了
                assert "body" not in resp

@pytest.mark.asyncio
async def test_token_budget_1024_limits():
    user = {"sub": "user_1"}
    # 設定 1024 預算，對於短內容應該不裁切
    args_no_trunc = {"workspace_id": "ws_1", "node_id": "mem_1", "detail_level": "full", "max_response_tokens": 1024}
    
    node = {
        "id": "mem_1",
        "title": "Short title",
        "content_type": "procedural",
        "body": "This is a short body text.",
        "tags": ["tag_a"],
        "trust_score": 0.95
    }
    
    mock_db_cursor = MagicMock()
    mock_db_cursor.__enter__.return_value = MagicMock()
    
    with patch("services.mcp_tools.db_cursor", return_value=mock_db_cursor):
        with patch("services.mcp_tools.get_node_in_db", return_value=node):
            with patch("services.node_projection.get_node_top_edges", return_value=[]):
                resp = await execute_tool("get_node", args_no_trunc, user, MagicMock())
                
                # 不應該被裁切
                assert resp.get("truncated") is not True
                assert resp["body"] == "This is a short body text."
                
                # 若內容非常大，設定 100 預算，實測結果之 token 數量必須小於或等於 100
                args_trunc = {"workspace_id": "ws_1", "node_id": "mem_1", "detail_level": "full", "max_response_tokens": 100}
                node_large = dict(node)
                node_large["body"] = "Very long content text " * 100
                
                resp_trunc = await execute_tool("get_node", args_trunc, user, MagicMock())
                
                # 實測所得回應的 token 數
                import json
                from services.mcp_tools import estimate_tokens
                serialized_str = json.dumps(resp_trunc, ensure_ascii=False)
                token_count = estimate_tokens(serialized_str)
                assert token_count <= 100


@pytest.mark.asyncio
async def test_token_budget_list_truncation():
    user = {"sub": "user_1"}
    # 限制 50 token，這非常容易超限
    args = {"workspace_id": "ws_1", "query": "test", "detail_level": "brief", "max_response_tokens": 50}
    
    results = [
        {"id": "mem_1", "title": "Node 1", "body": "Short content 1", "tags": [], "content_type": "factual"},
        {"id": "mem_2", "title": "Node 2", "body": "Short content 2", "tags": [], "content_type": "factual"},
        {"id": "mem_3", "title": "Node 3", "body": "Short content 3", "tags": [], "content_type": "factual"}
    ]
    
    mock_db_cursor = MagicMock()
    mock_db_cursor.__enter__.return_value = MagicMock()
    
    with patch("services.mcp_tools.db_cursor", return_value=mock_db_cursor):
        with patch("services.mcp_tools.search_nodes_in_db", new_callable=AsyncMock, return_value=results):
            with patch("services.node_projection.get_node_top_edges", return_value=[]):
                resp = await execute_tool("search_nodes", args, user, MagicMock())
                
                # 超過預算限制時，回傳格式會變成包含 results 的 dict，且有 truncated
                assert isinstance(resp, dict)
                assert resp.get("truncated") is True
                assert "results" in resp
                # 列表長度應比原來的 3 個少 (即發生了裁切)
                assert len(resp["results"]) < 3


# ─── 5. Markdown Resource 測試 ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_markdown_resources():
    user = {"sub": "user_1"}
    
    # 測試 templates list
    list_payload = {
        "jsonrpc": "2.0",
        "id": "list_res",
        "method": "resources/templates/list"
    }
    list_resp = await dispatch(list_payload, user, MagicMock())
    assert "resourceTemplates" in list_resp["result"]
    templates = list_resp["result"]["resourceTemplates"]
    assert len(templates) == 2
    assert templates[0]["uriTemplate"] == "memtrace://node/{id}"
    
    # 測試 read template - node
    node_payload = {
        "jsonrpc": "2.0",
        "id": "read_node",
        "method": "resources/read",
        "params": {
            "uri": "memtrace://node/mem_target"
        }
    }
    
    node_row = {
        "id": "mem_target",
        "workspace_id": "ws_1",
        "title": "Target Node Title",
        "content_type": "factual",
        "body": "This is a detailed node body for resource rendering.",
        "tags": ["resource", "test"],
        "trust_score": 0.99
    }
    
    edges_rows = [
        {"relation": "depends_on", "from_id": "mem_target", "to_id": "mem_dep", "target_title": "Dependency Node", "target_id": "mem_dep"},
        {"relation": "extends", "from_id": "mem_ext", "to_id": "mem_target", "target_title": "Extending Node", "target_id": "mem_ext"},
    ]
    
    mock_db_cursor = MagicMock()
    cur = MagicMock()
    mock_db_cursor.__enter__.return_value = cur
    
    with patch("services.mcp_tools.db_cursor", return_value=mock_db_cursor):
        with patch("services.workspaces.list_workspaces_in_db", return_value=[{"id": "ws_1"}]):
            cur.fetchone.return_value = node_row
            cur.fetchall.return_value = edges_rows
            
            resp = await dispatch(node_payload, user, MagicMock())
            assert "error" not in resp
            contents = resp["result"]["contents"]
            assert len(contents) == 1
            assert contents[0]["mimeType"] == "text/markdown"
            text = contents[0]["text"]
            assert "# Target Node Title" in text
            assert "類型**：factual" in text
            assert "信任**：0.99" in text
            assert "依賴**：[Dependency Node](memtrace://node/mem_dep)" in text

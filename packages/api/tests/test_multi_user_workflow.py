import pytest
import uuid
import json
from core.database import db_cursor, is_postgres
from services.nodes import create_node_full_with_dedup, update_node_full_in_db, sync_node_from_source_in_db, resolve_conflict_in_db
from services.workspaces import create_workspace_in_db
from services.audit import verify_audit_chain

@pytest.mark.asyncio
async def test_multi_user_governance_flow():
    """
    S3-T06: Multi-user smoke test for Phase 5 governance features.
    """
    if not is_postgres():
        pytest.skip("Integration test requires PostgreSQL")
    # 1. Setup two users and two workspaces
    user_a = {"sub": "usr_A", "email": "a@test.com"}
    user_b = {"sub": "usr_B", "email": "b@test.com"}
    
    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO users (id, display_name, email) VALUES (%s, %s, %s) ON CONFLICT (id) DO NOTHING",
            (user_a["sub"], "User A", user_a["email"])
        )
        cur.execute(
            "INSERT INTO users (id, display_name, email) VALUES (%s, %s, %s) ON CONFLICT (id) DO NOTHING",
            (user_b["sub"], "User B", user_b["email"])
        )
    
    with db_cursor(commit=True) as cur:
        ws_a = create_workspace_in_db(cur, user_a["sub"], {
            "name": "WS A",
            "language": "zh-TW",
            "visibility": "private",
            "kb_type": "evergreen",
        })
        ws_b = create_workspace_in_db(cur, user_b["sub"], {
            "name": "WS B",
            "language": "zh-TW",
            "visibility": "private",
            "kb_type": "evergreen",
        })
        
    with db_cursor(commit=True) as cur:
        # 2. User A creates a node
        node_a_data = {
            "title": "Source Node",
            "body": "Original content",
            "content_type": "factual",
            "content_format": "plain",
            "visibility": "public" # Must be public for B to copy/sync if no access
        }
        node_a, _, _ = await create_node_full_with_dedup(cur, ws_a["id"], node_a_data, user_a)
        
        # 3. User B copies node A to WS B
        node_b_data = node_a_data.copy()
        node_b_data["copied_from_node"] = node_a["id"]
        node_b_data["copied_from_ws"] = ws_a["id"]
        node_b, _, _ = await create_node_full_with_dedup(cur, ws_b["id"], node_b_data, user_b)
        
        # 4. User A updates Node A
        update_data = {"body": "Updated content"}
        update_node_full_in_db(cur, ws_a["id"], node_a["id"], update_data, user_a)
        
        # 5. Verify User B has a notification in review_queue
        cur.execute(
            "SELECT id FROM review_queue WHERE workspace_id = %s AND target_node_id = %s AND change_type = 'source_updated'",
            (ws_b["id"], node_b["id"])
        )
        review_item = cur.fetchone()
        assert review_item is not None, "User B should have a source_updated notification"
        
        # 6. User B syncs from source manually (S3-T02)
        updated_node_b, _ = sync_node_from_source_in_db(cur, ws_b["id"], node_b["id"], user_b)
        assert updated_node_b["body"] == "Updated content"
        
        # 7. Create a conflict (S3-T04)
        # Manually insert a contradicts edge to trigger arbitration
        from services.edges import create_edge_in_db
        node_c_data = {"title": "Conflicting Node", "body": "Opposite info", "content_type": "factual"}
        node_c, _, _ = await create_node_full_with_dedup(cur, ws_b["id"], node_c_data, user_b)
        
        create_edge_in_db(cur, ws_b["id"], {
            "from_id": node_b["id"],
            "to_id": node_c["id"],
            "relation": "contradicts",
            "weight": 1.0
        })
        
        # Verify conflict review entry
        cur.execute(
            "SELECT id FROM review_queue WHERE workspace_id = %s AND target_node_id = %s AND change_type = 'conflict'",
            (ws_b["id"], node_b["id"])
        )
        conflict_item = cur.fetchone()
        assert conflict_item is not None, "Contradiction should trigger conflict review"
        
        # 8. Resolve conflict
        resolve_conflict_in_db(cur, ws_b["id"], conflict_item["id"], "keep_a", user_b["sub"])
        
        # Verify Node C is archived
        cur.execute("SELECT status FROM memory_nodes WHERE id = %s", (node_c["id"],))
        assert cur.fetchone()["status"] == "archived"
        
        # 9. Verify Audit Trail (S3-T05)
        audit_res = verify_audit_chain(cur, ws_b["id"])
        assert audit_res["is_intact"] is True
        assert audit_res["verified_count"] >= 4 # create node, copy node, sync, resolve
        
    print("Multi-user governance flow test PASSED")

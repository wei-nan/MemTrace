import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from services.review_policy import (
    get_review_policy,
    update_review_policy,
    create_workspace_model_binding,
    update_workspace_model_binding,
    revoke_workspace_model_binding,
)
from core.ai_review import run_ai_review_for_item

def setup_test_user_workspace_and_node(cur, user_id, email, ws_id, ws_name, node_id="node_test"):
    cur.execute("SELECT 1 FROM users WHERE id = %s", (user_id,))
    if not cur.fetchone():
        unique_email = f"{user_id}@example.com"
        cur.execute(
            "INSERT INTO users (id, display_name, email) VALUES (%s, %s, %s)",
            (user_id, user_id, unique_email)
        )
    cur.execute("SELECT 1 FROM workspaces WHERE id = %s", (ws_id,))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO workspaces (id, name, owner_id, language) VALUES (%s, %s, %s, 'zh-TW')",
            (ws_id, ws_name, user_id)
        )
    cur.execute("SELECT 1 FROM memory_nodes WHERE id = %s", (node_id,))
    if not cur.fetchone():
        cur.execute(
            """
            INSERT INTO memory_nodes (id, workspace_id, title, content_type, author, signature)
            VALUES (%s, %s, 'Test Node', 'factual', %s, 'sig')
            """,
            (node_id, ws_id, user_id)
        )

@pytest.mark.integration
class TestReviewerPolicy:
    def test_get_and_update_policy(self, db_transaction):
        ws_id = "ws_test_policy"
        user_id = "usr_test_policy_owner"
        with db_transaction.cursor() as cur:
            setup_test_user_workspace_and_node(cur, user_id, "owner@example.com", ws_id, "Test Workspace")
            
            # 1. Retrieve review policy (auto-insert default)
            policy = get_review_policy(cur, ws_id)
            assert policy["workspace_id"] == ws_id
            assert policy["mode"] == "manual_only"
            assert policy["inherit_system_default"] is True

            # 2. Update policy
            updated = update_review_policy(
                cur,
                ws_id,
                mode="fallback_advisory",
                inherit_system_default=False,
                minimum_success=2,
                accept_rule={"prompt": "custom accept"},
                updated_by=user_id,
            )
            assert updated["mode"] == "fallback_advisory"
            assert updated["inherit_system_default"] is False
            assert updated["minimum_success"] == 2
            assert updated["accept_rule"] == {"prompt": "custom accept"}
            assert updated["policy_version"] == 2

    def test_model_binding_consent_and_approval(self, db_transaction):
        ws_id = "ws_test_binding"
        user_id = "usr_test_binding_owner"
        with db_transaction.cursor() as cur:
            setup_test_user_workspace_and_node(cur, user_id, "owner@example.com", ws_id, "Test Workspace")
            
            # Insert a dummy user AI key first
            key_id = "key_dummy_001"
            cur.execute(
                """
                INSERT INTO user_ai_keys (id, user_id, provider, default_chat_model, key_enc, key_hint)
                VALUES (%s, %s, 'openai', 'gpt-4o', 'enc', 'hint')
                """,
                (key_id, user_id),
            )

            # Create binding offered by owner (should be auto-approved and auto-consent)
            binding = create_workspace_model_binding(
                cur,
                workspace_id=ws_id,
                model_account_id=key_id,
                offered_by=user_id,
                allowed_usages=["review"],
                priority=10,
            )
            assert binding["status"] == "active"
            assert binding["consent_status"] == "approved"
            assert binding["approval_status"] == "approved"

            # Create binding offered by someone else
            other_user = "usr_other_binding_member"
            cur.execute(
                """
                INSERT INTO users (id, display_name, email)
                VALUES (%s, 'Other User', 'other@example.com')
                """,
                (other_user,),
            )
            key_id2 = "key_dummy_002"
            cur.execute(
                """
                INSERT INTO user_ai_keys (id, user_id, provider, default_chat_model, key_enc, key_hint)
                VALUES (%s, %s, 'openai', 'gpt-4o', 'enc', 'hint')
                """,
                (key_id2, other_user),
            )
            binding2 = create_workspace_model_binding(
                cur,
                workspace_id=ws_id,
                model_account_id=key_id2,
                offered_by=user_id, # offered by owner, but billing owner is other_user
                allowed_usages=["review"],
                priority=5,
            )
            # consent should be pending since offered_by != billing_owner
            assert binding2["consent_status"] == "pending"
            assert binding2["status"] == "offered"

            # Approve the binding consent
            updated_binding2 = update_workspace_model_binding(
                cur,
                workspace_id=ws_id,
                binding_id=binding2["id"],
                approval_user_id=other_user,
            )
            assert updated_binding2["consent_status"] == "approved"
            assert updated_binding2["status"] == "active"

    @pytest.mark.asyncio
    @patch("core.ai_review.resolve_provider")
    @patch("core.ai_review.chat_completion")
    @patch("core.ai_review.send_degradation_notification")
    async def test_run_ai_review_fallback_mode(self, mock_notify, mock_chat, mock_resolve, db_transaction):
        ws_id = "ws_test_fallback"
        user_id = "usr_fallback_owner"
        other_user = "usr_fallback_member"
        
        # Setup mock provider and response
        mock_res = MagicMock()
        mock_res.user_id = user_id
        mock_res.provider.name = "openai"
        mock_res.model = "gpt-4o"
        mock_resolve.return_value = mock_res
        mock_chat.return_value = ('{"decision": "accept", "confidence": 0.95, "reasoning": "Looks good"}', 150)

        with db_transaction.cursor() as cur:
            setup_test_user_workspace_and_node(cur, user_id, "owner@example.com", ws_id, "Test Workspace", "node_test")
            cur.execute(
                "INSERT INTO users (id, display_name, email) VALUES (%s, %s, %s)",
                (other_user, other_user, "member@example.com")
            )
            
            # 1. Update policy to fallback_advisory
            update_review_policy(cur, ws_id, mode="fallback_advisory")

            # 2. Insert user key and workspace bindings (owned by owner)
            key_id = "key_dummy_001"
            cur.execute(
                """
                INSERT INTO user_ai_keys (id, user_id, provider, default_chat_model, key_enc, key_hint)
                VALUES (%s, %s, 'openai', 'gpt-4o', 'enc', 'hint')
                """,
                (key_id, user_id),
            )
            binding = create_workspace_model_binding(
                cur,
                workspace_id=ws_id,
                model_account_id=key_id,
                offered_by=user_id,
                allowed_usages=["review"],
                priority=10,
            )
            
            # Create a second binding owned by other_user (to satisfy UNIQUE (user_id, provider))
            key_id2 = "key_dummy_002"
            cur.execute(
                """
                INSERT INTO user_ai_keys (id, user_id, provider, default_chat_model, key_enc, key_hint)
                VALUES (%s, %s, 'openai', 'gpt-4o-mini', 'enc', 'hint')
                """,
                (key_id2, other_user),
            )
            # Consent and approve binding2
            binding2 = create_workspace_model_binding(
                cur,
                workspace_id=ws_id,
                model_account_id=key_id2,
                offered_by=user_id,
                allowed_usages=["review"],
                priority=5,
            )
            update_workspace_model_binding(
                cur,
                workspace_id=ws_id,
                binding_id=binding2["id"],
                approval_user_id=other_user,
            )

            # Add bindings as policy members
            cur.execute(
                """
                INSERT INTO review_policy_members (policy_id, binding_id, priority)
                VALUES (%s, %s, 10), (%s, %s, 5)
                """,
                (ws_id, binding["id"], ws_id, binding2["id"]),
            )

            # 3. Create a pending review item in review_queue
            review_id = "rev_test_001"
            cur.execute(
                """
                INSERT INTO review_queue (
                    id, workspace_id, target_node_id, change_type, status,
                    node_data, before_snapshot, diff_summary, source_info,
                    proposer_type, proposer_meta
                ) VALUES (%s, %s, 'node_test', 'create', 'pending', '{}', '{}', '{}', '{}', 'user', '{}')
                """,
                (review_id, ws_id),
            )

        # Execute review
        db_transaction.commit()

        res = await run_ai_review_for_item(review_id)
        assert res is not None
        assert res["ai_review"]["decision"] == "accept"
        assert res["ai_review"]["mode"] == "fallback_advisory"
        
        # Verify attempt skip: first succeeded, second skipped_after_success
        with db_transaction.cursor() as cur:
            cur.execute("SELECT * FROM review_attempts WHERE run_id = %s ORDER BY started_at ASC", (res["ai_review"]["run_id"],))
            attempts = cur.fetchall()
            assert len(attempts) == 2
            assert attempts[0]["binding_id"] == binding["id"]
            assert attempts[0]["status"] == "succeeded"
            assert attempts[1]["binding_id"] == binding2["id"]
            assert attempts[1]["status"] == "skipped_after_success"

    @pytest.mark.asyncio
    @patch("core.ai_review.send_degradation_notification")
    async def test_degradation_to_manual_only(self, mock_notify, db_transaction):
        ws_id = "ws_test_degradation"
        user_id = "usr_degradation_owner"
        
        with db_transaction.cursor() as cur:
            setup_test_user_workspace_and_node(cur, user_id, "owner@example.com", ws_id, "Test Workspace", "node_test")
            
            # Update policy to fallback_advisory
            update_review_policy(cur, ws_id, mode="fallback_advisory")

            # Insert a pending review item
            review_id = "rev_test_002"
            cur.execute(
                """
                INSERT INTO review_queue (
                    id, workspace_id, target_node_id, change_type, status,
                    node_data, before_snapshot, diff_summary, source_info,
                    proposer_type, proposer_meta
                ) VALUES (%s, %s, 'node_test', 'create', 'pending', '{}', '{}', '{}', '{}', 'user', '{}')
                """,
                (review_id, ws_id),
            )

        db_transaction.commit()

        # Run AI review with no bindings
        res = await run_ai_review_for_item(review_id)
        assert res is None # degraded, should return None

        # Verify degradation notification and manual_only run record
        mock_notify.assert_called_once_with(ws_id, "No active AI reviewer model bindings found for this policy.")

        with db_transaction.cursor() as cur:
            cur.execute("SELECT * FROM review_runs WHERE review_item_id = %s", (review_id,))
            run = cur.fetchone()
            assert run is not None
            assert run["execution_mode"] == "manual_only"
            assert run["final_action"] == "escalate_manual"

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from services.review_policy import (
    create_workspace_model_binding,
    revoke_user_model_bindings,
    get_review_policy,
    update_review_policy,
)
from core.ai_review import run_ai_review_for_item
from core.database import db_cursor

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
class TestReviewerRevocation:
    def test_key_revocation_cascade(self, db_transaction):
        ws_id = "ws_test_rev_cascade"
        user_id = "usr_rev_cascade_owner"
        with db_transaction.cursor() as cur:
            setup_test_user_workspace_and_node(cur, user_id, "owner@example.com", ws_id, "Test Workspace")
            
            # 1. Insert user key
            key_id = "key_to_delete"
            cur.execute(
                """
                INSERT INTO user_ai_keys (id, user_id, provider, default_chat_model, key_enc, key_hint)
                VALUES (%s, %s, 'openai', 'gpt-4o', 'enc', 'hint')
                """,
                (key_id, user_id),
            )

            # 2. Bind to workspace
            binding = create_workspace_model_binding(
                cur,
                workspace_id=ws_id,
                model_account_id=key_id,
                offered_by=user_id,
                allowed_usages=["review"],
            )
            assert binding["status"] == "active"

            # 3. Simulate calling revocation hook (representing key deletion)
            revoke_user_model_bindings(cur, user_id, "openai")

            # 4. Check binding is revoked
            cur.execute("SELECT status FROM workspace_model_bindings WHERE id = %s", (binding["id"],))
            row = cur.fetchone()
            assert row["status"] == "revoked"

    @pytest.mark.asyncio
    @patch("core.ai_review.resolve_provider")
    @patch("core.ai_review.chat_completion")
    async def test_revocation_during_llm_call(self, mock_chat, mock_resolve, db_transaction):
        ws_id = "ws_test_rev_midflight"
        user_id = "usr_rev_midflight_owner"
        review_id = "rev_test_revocation"

        # Mock chat_completion to side-effect: revoke the binding in the database
        # during the async call!
        binding_id_holder = []
        async def mock_chat_side_effect(*args, **kwargs):
            assert len(binding_id_holder) == 1
            b_id = binding_id_holder[0]
            with db_cursor(commit=True) as cur:
                cur.execute("UPDATE workspace_model_bindings SET status = 'revoked', revoked_at = now() WHERE id = %s", (b_id,))
            return '{"decision": "accept", "confidence": 0.95, "reasoning": "Looks good"}', 100

        mock_res = MagicMock()
        mock_res.user_id = user_id
        mock_res.provider.name = "openai"
        mock_res.model = "gpt-4o"
        mock_resolve.return_value = mock_res
        mock_chat.side_effect = mock_chat_side_effect

        with db_transaction.cursor() as cur:
            setup_test_user_workspace_and_node(cur, user_id, "owner@example.com", ws_id, "Test Workspace", "node_test")
            
            # Update policy to fallback_advisory
            update_review_policy(cur, ws_id, mode="fallback_advisory")

            # Insert user key and workspace binding
            key_id = "key_dummy_rev"
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
            binding_id_holder.append(binding["id"])

            # Add binding as policy member
            cur.execute(
                """
                INSERT INTO review_policy_members (policy_id, binding_id, priority)
                VALUES (%s, %s, 10)
                """,
                (ws_id, binding["id"]),
            )

            # Create a pending review item in review_queue
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

        # Run AI review
        res = await run_ai_review_for_item(review_id)
        assert res is None

        # Verify review attempt is discarded_after_revocation
        with db_transaction.cursor() as cur:
            cur.execute("SELECT status FROM review_attempts WHERE binding_id = %s", (binding["id"],))
            attempt = cur.fetchone()
            assert attempt["status"] == "discarded_after_revocation"

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from services.connectors import (
    create_connector_account,
    create_connector_binding,
    list_connector_accounts,
    record_connector_event,
    revoke_connector_account,
)


def test_create_connector_account_encrypts_credential_and_does_not_return_it():
    cur = MagicMock()
    cur.fetchone.return_value = {
        "id": "connacct_1",
        "owner_user_id": "user_1",
        "provider": "github",
        "provider_account_id": "octocat",
        "status": "active",
    }

    with patch("services.connectors.encrypt_secret", return_value="encrypted") as encrypt:
        result = create_connector_account(
            cur,
            owner_user_id="user_1",
            provider="github",
            provider_account_id="octocat",
            credential="raw-token",
            scopes=["repo:read"],
        )

    encrypt.assert_called_once_with("raw-token")
    params = cur.execute.call_args.args[1]
    assert "encrypted" in params
    assert "raw-token" not in params
    assert "credentials_enc" not in result


def test_list_connector_accounts_is_scoped_to_owner():
    cur = MagicMock()
    cur.fetchall.return_value = [{"id": "connacct_1", "provider": "asana"}]

    result = list_connector_accounts(cur, "user_1")

    assert result[0]["provider"] == "asana"
    assert cur.execute.call_args.args[1] == ("user_1",)


def test_create_binding_requires_owned_active_account():
    cur = MagicMock()
    cur.fetchone.return_value = None

    with pytest.raises(HTTPException, match="Connector account not found"):
        create_connector_binding(
            cur,
            owner_user_id="user_1",
            workspace_id="ws_1",
            connector_account_id="connacct_other",
            external_container_type="repository",
            external_container_id="repo_1",
        )


def test_record_connector_event_is_idempotent():
    cur = MagicMock()
    cur.fetchone.side_effect = [
        None,
        {
            "id": "connevt_existing",
            "connector_account_id": "connacct_1",
            "provider_event_id": "delivery-1",
        },
    ]

    event, created = record_connector_event(
        cur,
        connector_account_id="connacct_1",
        provider_event_id="delivery-1",
        event_type="code.merged",
        payload={"repository": "memtrace"},
    )

    assert created is False
    assert event["id"] == "connevt_existing"
    assert "ON CONFLICT" in cur.execute.call_args_list[0].args[0]


def test_revoke_connector_account_clears_stored_credential():
    cur = MagicMock()
    cur.fetchone.side_effect = [
        {"id": "connacct_1", "owner_user_id": "user_1"},
        {"id": "connacct_1", "status": "revoked"},
    ]

    result = revoke_connector_account(cur, "connacct_1", "user_1")

    assert result["status"] == "revoked"
    update_sql = cur.execute.call_args_list[1].args[0]
    assert "credentials_enc = NULL" in update_sql


def test_connector_migration_is_in_runtime_manifest():
    from core.database import load_migration_files
    from pathlib import Path

    migrations = Path(__file__).parents[1] / "migrations"
    names = [path.name for path in load_migration_files(migrations)]

    assert "113_connector_framework.sql" in names

from unittest.mock import patch

import pytest

from core.credentials import decrypt_secret, encrypt_secret


def test_secret_round_trip_preserves_existing_fernet_format():
    encrypted = encrypt_secret("provider-token")

    assert encrypted != "provider-token"
    assert decrypt_secret(encrypted) == "provider-token"


def test_decrypt_secret_reports_server_key_change():
    encrypted = encrypt_secret("provider-token")

    with patch(
        "core.credentials.settings.secret_key",
        "different-test-secret-key-at-least-32-characters",
    ):
        with pytest.raises(ValueError, match="server secret key may have changed"):
            decrypt_secret(encrypted)


def test_core_ai_keeps_legacy_api_key_helpers():
    from core.ai import decrypt_api_key, encrypt_api_key

    encrypted = encrypt_api_key("legacy-ai-key")

    assert decrypt_api_key(encrypted) == "legacy-ai-key"

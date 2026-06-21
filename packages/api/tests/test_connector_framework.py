import pytest
from fastapi import HTTPException

from services.connector_framework import ConnectorProvider, ConnectorRegistry, registry


def test_builtin_connector_registry_exposes_supported_providers():
    providers = {provider.id for provider in registry.list()}
    assert providers == {"google_drive", "asana", "github", "gitlab"}


def test_connector_registry_validates_provider_capabilities():
    assert registry.validate(
        "github",
        auth_type="app",
        container_type="repository",
        sync_direction="bidirectional",
    ).id == "github"

    with pytest.raises(HTTPException, match="Unsupported auth type"):
        registry.validate("github", auth_type="basic")


def test_connector_registry_rejects_duplicate_registration():
    local = ConnectorRegistry()
    provider = ConnectorProvider(
        id="example",
        display_name="Example",
        auth_types=("token",),
        container_types=("project",),
        sync_directions=("inbound",),
        supports_webhooks=False,
        supports_incremental_sync=False,
    )
    local.register(provider)
    with pytest.raises(ValueError, match="already registered"):
        local.register(provider)

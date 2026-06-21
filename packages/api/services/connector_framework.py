"""Provider registry and capability contracts for external connectors."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

from fastapi import HTTPException


@dataclass(frozen=True)
class ConnectorProvider:
    id: str
    display_name: str
    auth_types: tuple[str, ...]
    container_types: tuple[str, ...]
    sync_directions: tuple[str, ...]
    supports_webhooks: bool
    supports_incremental_sync: bool
    instance_url_required: bool = False

    def to_dict(self) -> dict:
        result = asdict(self)
        for key in ("auth_types", "container_types", "sync_directions"):
            result[key] = list(result[key])
        return result


class ConnectorRegistry:
    """Small explicit registry used by API, workers, and future adapters."""

    def __init__(self) -> None:
        self._providers: dict[str, ConnectorProvider] = {}

    def register(self, provider: ConnectorProvider) -> None:
        if provider.id in self._providers:
            raise ValueError(f"Connector provider already registered: {provider.id}")
        self._providers[provider.id] = provider

    def get(self, provider_id: str) -> ConnectorProvider:
        provider = self._providers.get(provider_id)
        if not provider:
            raise HTTPException(status_code=422, detail=f"Unsupported connector provider: {provider_id}")
        return provider

    def list(self) -> list[ConnectorProvider]:
        return sorted(self._providers.values(), key=lambda item: item.display_name)

    def validate(
        self,
        provider_id: str,
        *,
        auth_type: Optional[str] = None,
        container_type: Optional[str] = None,
        sync_direction: Optional[str] = None,
    ) -> ConnectorProvider:
        provider = self.get(provider_id)
        checks = (
            ("auth type", auth_type, provider.auth_types),
            ("container type", container_type, provider.container_types),
            ("sync direction", sync_direction, provider.sync_directions),
        )
        for label, value, allowed in checks:
            if value is not None and value not in allowed:
                raise HTTPException(
                    status_code=422,
                    detail=f"Unsupported {label} for {provider_id}: {value}",
                )
        return provider


registry = ConnectorRegistry()

for definition in (
    ConnectorProvider(
        id="google_drive",
        display_name="Google Drive",
        auth_types=("oauth", "token"),
        container_types=("folder", "drive"),
        sync_directions=("inbound", "outbound", "bidirectional"),
        supports_webhooks=True,
        supports_incremental_sync=True,
    ),
    ConnectorProvider(
        id="asana",
        display_name="Asana",
        auth_types=("oauth", "token"),
        container_types=("project", "workspace"),
        sync_directions=("inbound", "outbound", "bidirectional"),
        supports_webhooks=True,
        supports_incremental_sync=True,
    ),
    ConnectorProvider(
        id="github",
        display_name="GitHub",
        auth_types=("oauth", "token", "app"),
        container_types=("repository", "organization"),
        sync_directions=("inbound", "outbound", "bidirectional"),
        supports_webhooks=True,
        supports_incremental_sync=True,
    ),
    ConnectorProvider(
        id="gitlab",
        display_name="GitLab",
        auth_types=("oauth", "token"),
        container_types=("project", "group"),
        sync_directions=("inbound", "outbound", "bidirectional"),
        supports_webhooks=True,
        supports_incremental_sync=True,
        instance_url_required=False,
    ),
):
    registry.register(definition)

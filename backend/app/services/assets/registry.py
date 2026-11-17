"""Registry of the asset pricing providers, discovered from ``services/asset_source_providers/``."""

from __future__ import annotations

from backend.app.config.plugins import asset_providers_enabled
from backend.app.services.platform.provider_registry import AbstractProviderRegistry


class AssetProviderRegistry(AbstractProviderRegistry):
    @classmethod
    def _get_provider_folder(cls) -> str:
        return "asset_source_providers"

    @classmethod
    def settings_family(cls) -> str:
        return "asset"

    @classmethod
    def _enabled_codes(cls) -> tuple[str, ...] | None:
        return asset_providers_enabled()

    @classmethod
    def _enabled_variable(cls) -> str | None:
        return "LIBREFOLIO_ASSET_PROVIDERS_ENABLED"

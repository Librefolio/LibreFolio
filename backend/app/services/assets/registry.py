"""Registry of the asset pricing providers, discovered from ``services/asset_source_providers/``."""

from __future__ import annotations

from backend.app.services.provider_registry import AbstractProviderRegistry


class AssetProviderRegistry(AbstractProviderRegistry):
    @classmethod
    def _get_provider_folder(cls) -> str:
        return "asset_source_providers"

    @classmethod
    def settings_family(cls) -> str:
        return "asset"

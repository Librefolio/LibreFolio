"""Registry of the FX rate providers, discovered from ``services/fx_providers/``."""

from __future__ import annotations

from backend.app.services.provider_registry import AbstractProviderRegistry


class FXProviderRegistry(AbstractProviderRegistry):
    @classmethod
    def _get_provider_folder(cls) -> str:
        return "fx_providers"

    @classmethod
    def settings_family(cls) -> str:
        return "fx"

"""Registry of the FX rate providers, discovered from ``services/fx_providers/``."""

from __future__ import annotations

from backend.app.config.plugins import fx_providers_enabled
from backend.app.services.platform.provider_registry import AbstractProviderRegistry


class FXProviderRegistry(AbstractProviderRegistry):
    @classmethod
    def _get_provider_folder(cls) -> str:
        return "fx_providers"

    @classmethod
    def settings_family(cls) -> str:
        return "fx"

    @classmethod
    def _enabled_codes(cls) -> tuple[str, ...] | None:
        return fx_providers_enabled()

    @classmethod
    def _enabled_variable(cls) -> str | None:
        return "LIBREFOLIO_FX_PROVIDERS_ENABLED"

    @classmethod
    def _always_enabled(cls) -> frozenset[str]:
        # MANUAL is the sentinel of hand-entered rates, not a source: an allow-list never switches it off
        return frozenset({"manual"})

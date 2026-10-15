"""Registry of the risk analytics, discovered from ``services/risk_plugins/``."""

from __future__ import annotations

from typing import Type

from backend.app.services.provider_registry import AbstractPluginRegistry
from backend.app.services.risk.base import RiskAnalytic


class RiskAnalyticRegistry(AbstractPluginRegistry):
    """Strict registry for multi-asset risk analytics."""

    @classmethod
    def _get_plugin_folder(cls) -> str:
        return "risk_plugins"

    @classmethod
    def _get_plugin_code_attr(cls) -> str:
        return "analytic_code"

    @classmethod
    def _normalize_lookup_code(cls, code: str) -> str:
        return code.strip().lower()

    @classmethod
    def _reject_duplicate_codes(cls) -> bool:
        return True

    @classmethod
    def _fail_on_discovery_errors(cls) -> bool:
        return True

    @classmethod
    def _ignored_module_stems(cls) -> frozenset[str]:
        return frozenset({"base"})

    @classmethod
    def _validate_plugin_class(cls, plugin_class: Type) -> None:
        super()._validate_plugin_class(plugin_class)
        if not issubclass(plugin_class, RiskAnalytic):
            raise TypeError("RiskAnalyticRegistry entries must extend RiskAnalytic")
        plugin_class.validate_definition()

    @classmethod
    def list_definitions(cls):
        """Return stable static catalog definitions sorted by analytic code."""
        cls.auto_discover()
        return [plugin_class.catalog_definition() for _code, plugin_class in sorted(cls._plugins.items())]

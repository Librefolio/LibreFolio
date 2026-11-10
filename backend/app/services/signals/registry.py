"""Registry of the technical signal plugins, discovered from ``services/signal_plugins/``."""

from __future__ import annotations

from typing import Type

from backend.app.services.provider_registry import AbstractPluginRegistry
from backend.app.services.signals.base import SignalPlugin


class SignalPluginRegistry(AbstractPluginRegistry):
    """Strict registry for autonomous technical signal plugins."""

    @classmethod
    def _get_plugin_folder(cls) -> str:
        return "signal_plugins"

    @classmethod
    def _get_plugin_code_attr(cls) -> str:
        return "signal_code"

    @classmethod
    def _normalize_lookup_code(cls, code: str) -> str:
        return code.strip().upper()

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
        if not issubclass(plugin_class, SignalPlugin):
            raise TypeError("SignalPluginRegistry entries must extend SignalPlugin")
        plugin_class.validate_definition()

    @classmethod
    def list_definitions(cls):
        """Return stable static catalog definitions sorted by signal code."""
        cls.auto_discover()
        return [plugin_class.catalog_definition() for _code, plugin_class in sorted(cls._plugins.items()) if plugin_class.catalog_visible]

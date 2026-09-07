"""Registry isolated to test-only signal plugin fixtures."""

from pathlib import Path

from backend.app.config import PROJECT_ROOT
from backend.app.services.provider_registry import SignalPluginRegistry


class FixtureSignalPluginRegistry(SignalPluginRegistry):
    @classmethod
    def _get_plugin_directory(cls) -> Path:
        return PROJECT_ROOT / "backend" / "test_scripts" / "fixtures" / "signal_plugins"

    @classmethod
    def _get_module_namespace(cls) -> str:
        return "backend.test_scripts.fixtures.signal_plugins"

    @classmethod
    def _ignored_module_stems(cls) -> frozenset[str]:
        return super()._ignored_module_stems() | frozenset({"registry"})


__all__ = ["FixtureSignalPluginRegistry"]

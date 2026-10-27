"""Registry of the Broker Report Import Manager (BRIM) plugins, discovered from ``services/brim_providers/``."""

from __future__ import annotations

from backend.app.logging_config import get_logger
from backend.app.services.provider_registry import AbstractProviderRegistry

logger = get_logger(__name__)


class BRIMProviderRegistry(AbstractProviderRegistry):
    """
    Registry for Broker Report Import Manager (BRIM) plugins.

    Auto-discovers plugins from `backend/app/services/brim_providers/`.
    """

    @classmethod
    def _get_provider_folder(cls) -> str:
        return "brim_providers"

    @classmethod
    def settings_family(cls) -> str | None:
        """The plugin settings family of the import plugins (W-BS): the generic CSV declares ``date_order`` (W5-8)."""
        return "brim"

    @classmethod
    def auto_detect_plugin(cls, file_path) -> str | None:
        """
        Auto-detect the best plugin for a file based on content analysis.

        Iterates through all registered plugins sorted by detection_priority
        (highest first) and returns the first plugin that can parse the file.

        Args:
            file_path: Path to the file to analyze

        Returns:
            Plugin code of the best matching plugin, or None if no match
        """
        cls.auto_discover()

        # Get all plugins with their instances and priorities
        plugins_with_priority = []
        for code, plugin_cls in list(cls._providers.items()):
            try:
                instance = plugin_cls()
                priority = getattr(instance, "detection_priority", 100)
                plugins_with_priority.append((code, instance, priority))
            except Exception:
                continue

        # Sort by priority descending (highest first)
        plugins_with_priority.sort(key=lambda x: x[2], reverse=True)

        # Try each plugin in order
        for code, instance, priority in plugins_with_priority:
            try:
                if instance.can_parse(file_path):
                    logger.debug(
                        "Auto-detected plugin for file",
                        plugin_code=code,
                        priority=priority,
                        file_path=str(file_path),
                    )
                    return code
            except Exception as e:
                logger.warning("Error checking plugin can_parse", plugin_code=code, error=str(e))
                continue

        return None

    @classmethod
    def get_compatible_plugins(cls, file_path) -> list:
        """
        Get list of plugin codes that can parse the given file.

        Iterates through all registered plugins and calls can_parse().
        Results are sorted by detection_priority descending (best match first).

        Args:
            file_path: Path to the file to check

        Returns:
            List of plugin codes that can parse this file, sorted by priority
        """
        cls.auto_discover()
        compatible: list[tuple[str, int]] = []
        for code, plugin_cls in list(cls._providers.items()):
            try:
                instance = plugin_cls()
                if instance.can_parse(file_path):
                    compatible.append((code, instance.detection_priority))
            except Exception:
                continue
        compatible.sort(key=lambda x: x[1], reverse=True)
        return [code for code, _ in compatible]

    @classmethod
    def list_plugin_info(cls) -> list:
        """
        Get detailed info for all registered plugins.

        Returns:
            List of BRIMPluginInfo objects (via plugin.to_plugin_info())
        """
        cls.auto_discover()
        result = []
        for _code, plugin_cls in list(cls._providers.items()):
            try:
                instance = plugin_cls()
                result.append(instance.to_plugin_info())
            except Exception:
                logger.exception("Failed to build plugin info", plugin_class=f"{plugin_cls.__module__}.{plugin_cls.__qualname__}")
        return result

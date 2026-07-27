from __future__ import annotations

import importlib
import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Type

from backend.app.config import PROJECT_ROOT
from backend.app.logging_config import get_logger
from backend.app.services.risk.base import RiskAnalytic
from backend.app.services.signal_plugins.base import SignalPlugin

logger = get_logger(__name__)


class PluginRegistryError(RuntimeError):
    """Base error for plugin registry failures."""


class DuplicatePluginCodeError(PluginRegistryError):
    """Raised when two distinct plugins claim the same registry code."""


@dataclass(frozen=True)
class PluginDiscoveryFailure:
    module_name: str
    error_type: str
    message: str


class PluginDiscoveryError(PluginRegistryError):
    """Aggregate error raised when strict plugin discovery imports fail."""

    def __init__(self, failures: tuple[PluginDiscoveryFailure, ...]):
        self.failures = failures
        details = "; ".join(f"{failure.module_name}: {failure.error_type}: {failure.message}" for failure in failures)
        super().__init__(f"Plugin discovery failed: {details}")


class AbstractPluginRegistry:
    """Filesystem-discovered class registry with per-subclass isolated state."""

    def __init_subclass__(cls, **kwargs):
        """Give each concrete registry isolated entries and discovery state."""
        super().__init_subclass__(**kwargs)
        setattr(cls, cls._get_storage_attribute(), {})
        cls._discovery_done = False
        cls._discovery_errors = ()

    @classmethod
    def register(cls, plugin_class: Type) -> None:
        """Validate and register one plugin class."""
        cls._validate_plugin_class(plugin_class)
        code = cls._get_registration_code(plugin_class)
        if not isinstance(code, str) or not code.strip():
            raise ValueError(f"Plugin class must define a non-empty {cls._get_plugin_code_attr()} attribute")
        code = code.strip()
        storage = cls._get_storage()
        existing = storage.get(code)
        if existing is not None and existing is not plugin_class:
            same_definition = existing.__module__ == plugin_class.__module__ and existing.__qualname__ == plugin_class.__qualname__
            if same_definition:
                storage[code] = plugin_class
                return
            if cls._reject_duplicate_codes():
                raise DuplicatePluginCodeError(f"Duplicate plugin code '{code}' in {existing.__module__}.{existing.__qualname__} and {plugin_class.__module__}.{plugin_class.__qualname__}")
        storage[code] = plugin_class

    @classmethod
    def get_plugin(cls, code: str):
        """Return a registered class by code after auto-discovery."""
        cls.auto_discover()
        return cls._get_storage().get(cls._normalize_lookup_code(code))

    @classmethod
    def get_plugin_instance(cls, code: str, **kwargs):
        """Instantiate a registered plugin, retrying no-arg construction."""
        plugin_class = cls.get_plugin(code)
        if not plugin_class:
            return None
        try:
            return plugin_class(**kwargs)
        except TypeError:
            return plugin_class()

    @classmethod
    def list_plugin_classes(cls) -> list[Type]:
        """Return all registered classes in registration order."""
        cls.auto_discover()
        return list(cls._get_storage().values())

    @classmethod
    def list_plugin_codes(cls) -> list[str]:
        """Return all registered codes in registration order."""
        cls.auto_discover()
        return list(cls._get_storage())

    @classmethod
    def auto_discover(cls) -> None:
        """Import plugin modules from the registry folder exactly once."""
        if cls._discovery_done:
            cls._raise_discovery_errors_if_needed()
            return
        target_dir = cls._get_plugin_directory()

        if not target_dir.exists():
            cls._discovery_done = True
            return

        failures: list[PluginDiscoveryFailure] = []
        for py in sorted(target_dir.glob("*.py")):
            if py.name == "__init__.py" or py.name.startswith("_") or py.stem in cls._ignored_module_stems() or not py.is_file():
                continue
            module_name = f"{cls._get_module_namespace()}.{py.stem}"
            try:
                if module_name in sys.modules:
                    continue
                spec = importlib.util.spec_from_file_location(module_name, str(py))
                if spec is None or spec.loader is None:
                    raise ImportError(f"Unable to create module spec for {py}")
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                try:
                    spec.loader.exec_module(module)
                except Exception:
                    sys.modules.pop(module_name, None)
                    raise
            except Exception as e:
                failure = PluginDiscoveryFailure(
                    module_name=module_name,
                    error_type=type(e).__name__,
                    message=str(e),
                )
                failures.append(failure)
                logger.error("Error importing plugin module", module_name=module_name, error_type=failure.error_type, error=failure.message)
        cls._discovery_done = True
        cls._discovery_errors = tuple(failures)
        cls._raise_discovery_errors_if_needed()

    @classmethod
    def get_discovery_errors(cls) -> tuple[PluginDiscoveryFailure, ...]:
        """Return explicit module import failures from the last discovery."""
        try:
            cls.auto_discover()
        except PluginDiscoveryError:
            pass
        return cls._discovery_errors

    @classmethod
    def _get_storage(cls) -> Dict[str, Type]:
        return getattr(cls, cls._get_storage_attribute())

    @classmethod
    def _raise_discovery_errors_if_needed(cls) -> None:
        if cls._discovery_errors and cls._fail_on_discovery_errors():
            raise PluginDiscoveryError(cls._discovery_errors)

    @classmethod
    def _get_registration_code(cls, plugin_class: Type) -> object:
        return getattr(plugin_class, cls._get_plugin_code_attr(), None)

    @classmethod
    def _normalize_lookup_code(cls, code: str) -> str:
        return code

    @classmethod
    def _validate_plugin_class(cls, plugin_class: Type) -> None:
        if not isinstance(plugin_class, type):
            raise TypeError("Registry entries must be classes")

    @classmethod
    def _get_storage_attribute(cls) -> str:
        return "_plugins"

    @classmethod
    def _get_plugin_directory(cls) -> Path:
        return PROJECT_ROOT / "backend" / "app" / "services" / cls._get_plugin_folder()

    @classmethod
    def _get_module_namespace(cls) -> str:
        return f"backend.app.services.{cls._get_plugin_folder()}"

    @classmethod
    def _get_plugin_folder(cls) -> str:
        raise NotImplementedError

    @classmethod
    def _get_plugin_code_attr(cls) -> str:
        return "plugin_code"

    @classmethod
    def _reject_duplicate_codes(cls) -> bool:
        return False

    @classmethod
    def _fail_on_discovery_errors(cls) -> bool:
        return False

    @classmethod
    def _ignored_module_stems(cls) -> frozenset[str]:
        return frozenset()


class AbstractProviderRegistry(AbstractPluginRegistry):
    """Compatibility specialization for existing provider registries."""

    @classmethod
    def _get_storage_attribute(cls) -> str:
        return "_providers"

    @classmethod
    def _get_plugin_folder(cls) -> str:
        return cls._get_provider_folder()

    @classmethod
    def _get_provider_folder(cls) -> str:
        raise NotImplementedError

    @classmethod
    def _get_plugin_code_attr(cls) -> str:
        return "provider_code"

    @classmethod
    def _get_registration_code(cls, provider_class: Type) -> object:
        try:
            return getattr(provider_class(), cls._get_plugin_code_attr(), None)
        except Exception:
            return getattr(provider_class, cls._get_plugin_code_attr(), None)

    @classmethod
    def get_provider(cls, code: str):
        return cls.get_plugin(code)

    @classmethod
    def get_provider_instance(cls, code: str, **kwargs):
        return cls.get_plugin_instance(code, **kwargs)

    @classmethod
    def list_providers(cls) -> List[Dict[str, str]]:
        providers = []
        cls.auto_discover()
        for code, provider_class in cls._providers.items():
            try:
                instance = provider_class()
                name = getattr(instance, "provider_name", None) or getattr(instance, "name", code)
                providers.append({"code": code, "name": name})
            except Exception:
                providers.append({"code": code, "name": code})
        return providers

    @classmethod
    def shutdown_all_providers(cls) -> None:  # pragma: no cover
        cls.auto_discover()
        for code, provider_class in cls._providers.items():
            try:
                provider_class().shutdown()
            except Exception as e:
                logger.warning(
                    "Error during provider shutdown",
                    provider_code=code,
                    registry=cls.__name__,
                    error=str(e),
                )


# Specializations
class FXProviderRegistry(AbstractProviderRegistry):
    @classmethod
    def _get_provider_folder(cls) -> str:
        return "fx_providers"


class AssetProviderRegistry(AbstractProviderRegistry):
    @classmethod
    def _get_provider_folder(cls) -> str:
        return "asset_source_providers"


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
        return [plugin_class.catalog_definition() for _code, plugin_class in sorted(cls._plugins.items())]


class RiskAnalyticRegistry(AbstractPluginRegistry):
    """Strict registry for deterministic multi-asset risk analytics."""

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


class BRIMProviderRegistry(AbstractProviderRegistry):
    """
    Registry for Broker Report Import Manager (BRIM) plugins.

    Auto-discovers plugins from `backend/app/services/brim_providers/`.
    """

    @classmethod
    def _get_provider_folder(cls) -> str:
        return "brim_providers"

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
        for code, plugin_cls in cls._providers.items():
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
        for code, plugin_cls in cls._providers.items():
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
        for _code, plugin_cls in cls._providers.items():
            try:
                instance = plugin_cls()
                result.append(instance.to_plugin_info())
            except Exception:
                pass
        return result


# Decorator factory
def register_provider(registry_class: Type[AbstractProviderRegistry]):
    """
    Decorator to register a provider class with the given registry.
    :param registry_class: The registry class to register the provider with. (e.g., AssetProviderRegistry or FXProviderRegistry)
    :return:

    Example usage:
    @register_provider(AssetProviderRegistry)
    class MyAssetProvider(AssetSourceProvider):
        ...
    """

    def decorator(provider_class: Type):
        registry_class.register(provider_class)
        return provider_class

    return decorator


def register_plugin(registry_class: Type[AbstractPluginRegistry]):
    """Decorator factory for non-provider plugin registries."""

    def decorator(plugin_class: Type):
        registry_class.register(plugin_class)
        return plugin_class

    return decorator


__all__ = [
    "AbstractPluginRegistry",
    "AbstractProviderRegistry",
    "AssetProviderRegistry",
    "BRIMProviderRegistry",
    "DuplicatePluginCodeError",
    "FXProviderRegistry",
    "PluginDiscoveryError",
    "PluginDiscoveryFailure",
    "PluginRegistryError",
    "SignalPluginRegistry",
    "register_plugin",
    "register_provider",
]

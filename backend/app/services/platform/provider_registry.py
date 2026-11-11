"""Bases and decorators of the plugin registries.

Each plugin family keeps its registry in its own runtime package (developer decision D-P1): ``services/assets/registry.py``,
``services/fx/registry.py``, ``services/brim/registry.py``, ``services/signals/registry.py``,
``services/risk/registry.py`` and ``services/tools/registry.py``. This module holds what they share: the folder-per-plugin
discovery, the registration rules and the ``register_provider`` / ``register_plugin`` decorators.

A registry whose plugins may declare settings names its family in ``settings_family()`` (``asset``, ``fx``); a plugin
whose ``settings_fields`` do not pass ``validate_declaration``, or whose environment variable is already another
plugin's (``claim_env_variables``), is refused at registration, like one that fails to import.
"""

from __future__ import annotations

import importlib.util
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Type

from backend.app.config import PROJECT_ROOT, is_test_mode
from backend.app.logging_config import get_logger
from backend.app.services.plugin_settings.fields import SettingsDeclarationError, claim_env_variables, validate_declaration

logger = get_logger(__name__)

PLUGIN_MODULE_NAME = "plugin"
"""A plugin is a folder ``<family>/<name>/``: ``__init__.py`` holds only its docstring and the code is in ``plugin.py``,
loaded as ``<namespace>.<name>.plugin``."""


class PluginRegistryError(RuntimeError):
    """Base error for plugin registry failures."""


class DuplicatePluginCodeError(PluginRegistryError):
    """Raised when two distinct plugins claim the same registry code."""


@dataclass(frozen=True)
class PluginDiscoveryFailure:
    module_name: str
    error_type: str
    message: str


def _plugin_entry_name(entry: Path) -> str:
    """A plugin's name: its folder name, or the stem of a single-file module."""
    return entry.stem if entry.suffix == ".py" else entry.name


def _load_module_from_file(module_name: str, path: Path):
    """Execute ``path`` as ``module_name``; on failure nothing is left in ``sys.modules``."""
    spec = importlib.util.spec_from_file_location(module_name, str(path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to create module spec for {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module


def _load_plugin_folder(folder: Path, module_name: str) -> None:
    """Load ``folder/plugin.py`` as ``module_name``, its package first so that relative imports resolve."""
    init_file = folder / "__init__.py"
    plugin_file = folder / f"{PLUGIN_MODULE_NAME}.py"
    if not init_file.is_file():
        raise ImportError(f"Plugin folder {folder.name}/ has no __init__.py")
    if not plugin_file.is_file():
        raise ImportError(f"Plugin folder {folder.name}/ has no {PLUGIN_MODULE_NAME}.py")
    package_name = module_name.rsplit(".", 1)[0]
    package = sys.modules.get(package_name)
    package_added = package is None
    if package_added:
        spec = importlib.util.spec_from_file_location(package_name, str(init_file), submodule_search_locations=[str(folder)])
        if spec is None or spec.loader is None:
            raise ImportError(f"Unable to create package spec for {folder}")
        package = importlib.util.module_from_spec(spec)
        sys.modules[package_name] = package
        try:
            spec.loader.exec_module(package)
        except Exception:
            sys.modules.pop(package_name, None)
            raise
    try:
        module = _load_module_from_file(module_name, plugin_file)
    except Exception:
        if package_added:
            sys.modules.pop(package_name, None)
        raise
    setattr(package, PLUGIN_MODULE_NAME, module)


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
        # Serialises the first discovery: callers run on worker threads (asyncio.to_thread), and a
        # caller arriving mid-discovery must wait for the full catalogue. Re-entrant, so a plugin
        # module that calls back into its own registry while it is being imported does not block.
        cls._discovery_lock = threading.RLock()

    @classmethod
    def register(cls, plugin_class: Type) -> None:
        """Validate and register one plugin class."""
        cls._validate_plugin_class(plugin_class)
        cls._validate_settings_declaration(plugin_class)
        code = cls._get_registration_code(plugin_class)
        if not isinstance(code, str) or not code.strip():
            raise ValueError(f"Plugin class must define a non-empty {cls._get_plugin_code_attr()} attribute")
        code = code.strip()
        storage = cls._get_storage()
        existing = storage.get(code)
        if existing is not None and existing is not plugin_class:
            same_definition = existing.__module__ == plugin_class.__module__ and existing.__qualname__ == plugin_class.__qualname__
            if same_definition:
                cls._claim_settings_variables(plugin_class, code)
                storage[code] = plugin_class
                return
            if cls._reject_duplicate_codes():
                raise DuplicatePluginCodeError(f"Duplicate plugin code '{code}' in {existing.__module__}.{existing.__qualname__} and {plugin_class.__module__}.{plugin_class.__qualname__}")
        cls._claim_settings_variables(plugin_class, code)
        storage[code] = plugin_class

    @classmethod
    def _withheld(cls, plugin_class: Type | None) -> bool:
        """X-R44: a plugin that exists for the tests (``test_only``) is not served outside test mode.

        No lookup finds it and no list names it, so no request reaches it on a production instance: not a search that
        names it, an assignment, a probe, a refresh, a setting. ``is_test_mode()`` is read at each call.
        """
        return plugin_class is not None and bool(getattr(plugin_class, "test_only", False)) and not is_test_mode()

    @classmethod
    def get_plugin(cls, code: str):
        """Return a registered class by code after auto-discovery; ``None`` for a test-only one outside test mode."""
        cls.auto_discover()
        plugin_class = cls._get_storage().get(cls._normalize_lookup_code(code))
        return None if cls._withheld(plugin_class) else plugin_class

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
    def list_plugin_codes(cls) -> list[str]:
        """Return all registered codes in registration order, without the test-only ones outside test mode."""
        cls.auto_discover()
        return [code for code, plugin_class in cls._get_storage().items() if not cls._withheld(plugin_class)]

    @classmethod
    def auto_discover(cls) -> None:
        """Import plugin modules from the registry folder exactly once, safely across threads.

        ``_discovery_done`` turns true only after every module has been executed, and the whole
        discovery runs under the registry's lock: a concurrent caller waits for it instead of
        skipping the modules another thread has put in ``sys.modules`` but not executed yet, and
        walking a half-filled catalogue.
        """
        if cls._discovery_done:
            cls._raise_discovery_errors_if_needed()
            return
        with cls._discovery_lock:
            if cls._discovery_done:
                cls._raise_discovery_errors_if_needed()
                return
            cls._discover_modules()
        cls._raise_discovery_errors_if_needed()

    @classmethod
    def _discover_modules(cls) -> None:
        """Import every plugin of the folder; called once, under the discovery lock.

        A plugin is a folder holding ``__init__.py`` and ``plugin.py`` (see ``PLUGIN_MODULE_NAME``). A single
        ``<name>.py`` module is still loaded, for test fixtures and test registries; the first-party families keep
        every plugin in a folder (``utils gate-plugin-layout``). A folder with neither file is data (``static/``,
        ``sample_reports/``) and is skipped. Names starting with ``_`` and the ignored stems are skipped in both
        forms, and the order is the names' order, whichever the form.
        """
        target_dir = cls._get_plugin_directory()

        if not target_dir.exists():
            cls._discovery_done = True
            return

        failures: list[PluginDiscoveryFailure] = []
        seen: set[str] = set()
        # By name; for a name that is both ``x.py`` and ``x/``, the module first, so the failure is the same everywhere.
        for entry in sorted(target_dir.iterdir(), key=lambda path: (_plugin_entry_name(path), path.is_dir())):
            module_name = cls._plugin_module_name(entry)
            if module_name is None:
                continue
            name = _plugin_entry_name(entry)
            try:
                if name in seen:
                    raise ImportError(f"Plugin '{name}' exists both as {name}.py and as {name}/")
                seen.add(name)
                if module_name in sys.modules:
                    continue
                if entry.is_dir():
                    _load_plugin_folder(entry, module_name)
                else:
                    _load_module_from_file(module_name, entry)
            except Exception as e:
                failure = PluginDiscoveryFailure(
                    module_name=module_name,
                    error_type=type(e).__name__,
                    message=str(e),
                )
                failures.append(failure)
                logger.exception("Error importing plugin module", module_name=module_name, error_type=failure.error_type, error=failure.message)
        # Errors first: a caller that sees the discovery done without the lock also sees its errors.
        cls._discovery_errors = tuple(failures)
        cls._discovery_done = True

    @classmethod
    def _plugin_module_name(cls, entry: Path) -> str | None:
        """The module ``entry`` is loaded as, or None when it is not a plugin of this registry."""
        name = _plugin_entry_name(entry)
        if name.startswith("_") or name in cls._ignored_module_stems():
            return None
        if entry.is_dir():
            if not (entry / "__init__.py").exists() and not (entry / f"{PLUGIN_MODULE_NAME}.py").exists():
                return None
            return f"{cls._get_module_namespace()}.{name}.{PLUGIN_MODULE_NAME}"
        if entry.suffix == ".py" and entry.is_file():
            return f"{cls._get_module_namespace()}.{name}"
        return None

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
    def settings_family(cls) -> str | None:
        """The family name of the plugin settings (``asset``, ``fx``), or ``None`` when its plugins declare none yet."""
        return None

    @classmethod
    def _validate_settings_declaration(cls, plugin_class: Type) -> None:
        """Refuse a plugin whose ``settings_fields`` are invalid for this family (``plugin_settings/fields.py``)."""
        fields = getattr(plugin_class, "settings_fields", ())
        if not fields:
            return
        family = cls.settings_family()
        if family is None:
            raise SettingsDeclarationError(f"{plugin_class.__qualname__}: the plugins of {cls.__name__} cannot declare settings")
        try:
            validate_declaration(fields, family=family)
        except SettingsDeclarationError as error:
            raise SettingsDeclarationError(f"{plugin_class.__qualname__}: {error}") from None

    @classmethod
    def _claim_settings_variables(cls, plugin_class: Type, code: str) -> None:
        """Reserve the environment variables of the plugin's fields; refuse it when one is another plugin's.

        Called last, right before the plugin is stored: a refused claim leaves it unregistered. A plugin without fields
        drops the claims a previous class of the same code made.
        """
        family = cls.settings_family()
        if family is None:
            return
        try:
            claim_env_variables(family, code, getattr(plugin_class, "settings_fields", ()))
        except SettingsDeclarationError as error:
            raise SettingsDeclarationError(f"{plugin_class.__qualname__}: {error}") from None

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
    def get_provider_instance(cls, code: str, **kwargs):
        return cls.get_plugin_instance(code, **kwargs)

    @classmethod
    def list_providers(cls) -> List[Dict[str, str]]:
        providers = []
        cls.auto_discover()
        for code, provider_class in list(cls._providers.items()):
            if cls._withheld(provider_class):
                continue
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
        for code, provider_class in list(cls._providers.items()):
            try:
                provider_class().shutdown()
            except Exception as e:
                logger.warning(
                    "Error during provider shutdown",
                    provider_code=code,
                    registry=cls.__name__,
                    error=str(e),
                )


# Decorator factory
def register_provider(registry_class: Type[AbstractProviderRegistry]):
    """
    Decorator to register a provider class with the given registry.
    :param registry_class: The registry class to register the provider with. (e.g., AssetProviderRegistry or FXProviderRegistry)
    :return:

    Example usage, with the registry imported from its family package (``services/assets/registry.py``):
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
    "PLUGIN_MODULE_NAME",
    "AbstractPluginRegistry",
    "AbstractProviderRegistry",
    "DuplicatePluginCodeError",
    "PluginDiscoveryError",
    "PluginDiscoveryFailure",
    "PluginRegistryError",
    "register_plugin",
    "register_provider",
]

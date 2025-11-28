from __future__ import annotations

import importlib
import importlib.util
from pathlib import Path
from typing import Type, Dict, List
from backend.app.logging_config import get_logger

logger = get_logger(__name__)


class AbstractProviderRegistry:
    """Abstract base class for provider registries.

    Each subclass automatically gets its own _providers dictionary.
    """

    def __init_subclass__(cls, **kwargs):
        """Ensure each subclass has its own _providers dict and discovery tracking."""
        super().__init_subclass__(**kwargs)
        cls._providers = {}
        cls._discovery_done = False

    @classmethod
    def register(cls, provider_class: Type) -> None:
        """Register a provider class.

        The provider_class must expose a `provider_code` attribute.
        We instantiate the class to read the provider_code (handles properties).
        """
        try:
            # Instantiate to read properties correctly
            instance = provider_class()
            code = getattr(instance, cls._get_provider_code_attr(), None)
        except Exception:
            # Fallback: try reading as class attribute
            code = getattr(provider_class, cls._get_provider_code_attr(), None)

        if not code:
            raise ValueError("Provider class must define a provider_code attribute")
        cls._providers[code] = provider_class

    @classmethod
    def get_provider(cls, code: str):
        """Get provider class by code. Triggers auto-discovery if not done yet."""
        cls.auto_discover()
        return cls._providers.get(code)

    @classmethod
    def get_provider_instance(cls, code: str, **kwargs):
        """Return an instantiated provider object for given provider code.

        kwargs are forwarded to provider constructor if it accepts them.
        Returns None if provider not found.
        """
        prov_cls = cls.get_provider(code)
        if not prov_cls:
            return None
        try:
            return prov_cls(**kwargs)
        except TypeError:
            # Provider doesn't accept kwargs; instantiate without args
            return prov_cls()

    @classmethod
    def list_providers(cls) -> List[Dict[str, str]]:
        """
        List all registered providers with their metadata.
        Triggers auto-discovery if not done yet.
        Returns:
            List of dicts with 'code' and 'name' keys
        """

        providers = []
        cls.auto_discover()
        for code, provider_class in cls._providers.items():
            try:
                instance = provider_class()
                name = getattr(instance, 'provider_name', None) or getattr(instance, 'name', code)
                providers.append({
                    'code': code,
                    'name': name
                    })
            except Exception:
                # Fallback if instantiation fails
                providers.append({
                    'code': code,
                    'name': code
                    })
        return providers

    @classmethod
    def auto_discover(cls) -> None:
        """Import all modules in the provider folder to trigger registration.

        This implementation scans the filesystem directly and loads each .py
        module with importlib.util to avoid executing the package's __init__.py
        which may import other modules and cause circular imports.
        """
        if cls._discovery_done:
            return
        folder = cls._get_provider_folder()
        # Resolve to absolute path: project_root/backend/app/services/<folder>
        project_root = Path(__file__).parent.parent.parent
        target_dir = project_root / 'app' / 'services' / folder

        if not target_dir.exists():
            return

        for py in target_dir.glob('*.py'):
            if py.name == '__init__.py' or not py.is_file():
                continue
            module_name = f"backend.app.services.{folder}.{py.stem}"
            try:
                spec = importlib.util.spec_from_file_location(module_name, str(py))
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
            except Exception as e:
                # Log error but don't stop discovery on single-module errors
                logger.error("Error importing provider module", module_name=module_name, error=str(e))
                continue
        cls._discovery_done = True

    # --- methods to specialize in subclasses ---
    @classmethod
    def _get_provider_folder(cls) -> str:
        raise NotImplementedError

    @classmethod
    def _get_provider_code_attr(cls) -> str:
        return "provider_code"


# Specializations
class FXProviderRegistry(AbstractProviderRegistry):
    @classmethod
    def _get_provider_folder(cls) -> str:
        return "fx_providers"


class AssetProviderRegistry(AbstractProviderRegistry):
    @classmethod
    def _get_provider_folder(cls) -> str:
        return "asset_source_providers"


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

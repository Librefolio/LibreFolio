"""Canonical asset source service package."""

from importlib import import_module as _import_module

_EXPORTS = {
    "ASSET_HISTORY_MIN_FALLBACK": (
        "backend.app.services.asset_sources.core",
        "ASSET_HISTORY_MIN_FALLBACK",
    ),
    "AssetHistoryStartDate": (
        "backend.app.services.asset_sources.core",
        "AssetHistoryStartDate",
    ),
    "AssetSourceError": (
        "backend.app.services.asset_sources.core",
        "AssetSourceError",
    ),
    "AssetSourceProvider": (
        "backend.app.services.asset_sources.core",
        "AssetSourceProvider",
    ),
    "AssetSourceManager": (
        "backend.app.services.asset_sources.manager",
        "AssetSourceManager",
    ),
    "AssetCRUDService": (
        "backend.app.services.asset_sources.crud",
        "AssetCRUDService",
    ),
    "AssetSearchService": (
        "backend.app.services.asset_sources.search",
        "AssetSearchService",
    ),
}

__all__ = list(_EXPORTS)


def __getattr__(name: str) -> object:
    target = _EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute = target
    value = getattr(_import_module(module_name), attribute)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_EXPORTS))

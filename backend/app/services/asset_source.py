"""Legacy Release 2 facade for canonical asset source services."""

from backend.app.services.asset_sources.core import (
    ASSET_HISTORY_MIN_FALLBACK,
    AssetHistoryStartDate,
    AssetSourceError,
    AssetSourceProvider,
)
from backend.app.services.asset_sources.crud import AssetCRUDService
from backend.app.services.asset_sources.manager import AssetSourceManager
from backend.app.services.asset_sources.search import AssetSearchService

__all__ = [
    "ASSET_HISTORY_MIN_FALLBACK",
    "AssetCRUDService",
    "AssetHistoryStartDate",
    "AssetSearchService",
    "AssetSourceError",
    "AssetSourceManager",
    "AssetSourceProvider",
]

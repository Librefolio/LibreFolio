"""Compatibility manager composed from responsibility modules."""

from backend.app.services.asset_sources import core
from backend.app.services.asset_sources.metadata import MetadataOperations
from backend.app.services.asset_sources.price_query import PriceQueryOperations
from backend.app.services.asset_sources.price_store import PriceStoreOperations
from backend.app.services.asset_sources.provider_management import (
    ProviderManagementOperations,
)
from backend.app.services.asset_sources.refresh import RefreshOperations


class AssetSourceManager(
    ProviderManagementOperations,
    MetadataOperations,
    PriceStoreOperations,
    PriceQueryOperations,
    RefreshOperations,
):
    """Stable public manager facade over responsibility-specific operations."""

    _parse_provider_params = staticmethod(core._parse_provider_params)

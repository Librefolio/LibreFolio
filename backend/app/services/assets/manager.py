"""Compatibility manager composed from responsibility modules."""

from backend.app.services.assets import core
from backend.app.services.assets.metadata import MetadataOperations
from backend.app.services.assets.price_query import PriceQueryOperations
from backend.app.services.assets.price_store import PriceStoreOperations
from backend.app.services.assets.provider_management import (
    ProviderManagementOperations,
)
from backend.app.services.assets.refresh import RefreshOperations


class AssetSourceManager(
    ProviderManagementOperations,
    MetadataOperations,
    PriceStoreOperations,
    PriceQueryOperations,
    RefreshOperations,
):
    """Stable public manager facade over responsibility-specific operations."""

    _parse_provider_params = staticmethod(core._parse_provider_params)

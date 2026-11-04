"""``AssetSourceManager``: the asset service, composed from the responsibility modules of this package."""

from backend.app.services.assets import core
from backend.app.services.assets.currency_change import CurrencyChangeOperations
from backend.app.services.assets.event_store import EventStoreOperations
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
    CurrencyChangeOperations,
    EventStoreOperations,
    PriceQueryOperations,
    RefreshOperations,
):
    """Stable public manager facade over responsibility-specific operations."""

    _parse_provider_params = staticmethod(core._parse_provider_params)

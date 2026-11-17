"""``mockcount``: a double counted at the call boundary like a provider that calls out (project 76, U4).

For the tests of the call limits only (the consultant's rule 3): ``mockprov`` is not counted, since a limit on it would be
an instance setting of the shared test backend and stop every test that uses it. ``mockcount`` belongs to the one suite
or spec that sets its limits. Test-only: withheld outside test mode, like every double. No network.

It answers as mockprov does for a price: 100.00 USD as of today, and 100.00 USD every day of a history. It is a double
of its own, not a subclass of mockprov's class: a plugin never imports another plugin (the plugin layout gate, rule d).
No search, no metadata, no bulk read.

Its fields are the five core call limits only, given at registration: no field of its own, no group.
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Dict

from backend.app.db import IdentifierType
from backend.app.db.models import ProviderInputType
from backend.app.schemas.prices import FACurrentValue, FAHistoricalData, FAPricePoint
from backend.app.services.assets.base import ASSET_HISTORY_MIN_FALLBACK, AssetHistoryStartDate, AssetSourceProvider
from backend.app.services.assets.registry import AssetProviderRegistry
from backend.app.services.platform.provider_registry import register_provider

#: The one price of the double, in every answer
PRICE = Decimal("100.00")
CURRENCY = "USD"


@register_provider(AssetProviderRegistry)
class MockCountProvider(AssetSourceProvider):
    """A fixed price under the code ``mockcount``, counted at the boundary. FOR TESTING ONLY."""

    test_only = True
    calls_external_service = True
    settings_fields = ()
    settings_groups = ()

    @property
    def provider_code(self) -> str:
        return "mockcount"

    @property
    def provider_name(self) -> str:
        return "Mock Counted Provider"

    @property
    def supports_meaningful_volume(self) -> bool:
        return False

    @property
    def accepted_identifier_types(self) -> list:
        return [ProviderInputType.TICKER, ProviderInputType.AUTO_GENERATED]

    @property
    def test_cases(self) -> list[dict]:
        return [{"identifier": "MOCK", "identifier_type": IdentifierType.TICKER, "provider_params": None, "expected_symbol": "MOCK"}]

    @property
    def test_search_query(self) -> str | None:
        return None

    @property
    def supports_history(self) -> bool:
        return True

    async def get_current_value(self, identifier: str, identifier_type: IdentifierType, provider_params: Dict | None = None) -> FACurrentValue:
        """100.00 USD as of today, whatever the identifier."""
        return FACurrentValue(value=PRICE, currency=CURRENCY, as_of_date=date.today(), source=self.provider_name)

    async def get_history_value(self, identifier: str, identifier_type: IdentifierType, provider_params: Dict | None, start_date: AssetHistoryStartDate, end_date: date) -> FAHistoricalData:
        """100.00 USD every day of the range, no volume."""
        current = ASSET_HISTORY_MIN_FALLBACK if start_date == "min" else start_date
        prices = []
        while current <= end_date:
            prices.append(FAPricePoint(date=current, open=PRICE, high=PRICE, low=PRICE, close=PRICE, volume=None, currency=CURRENCY))
            current += timedelta(days=1)
        return FAHistoricalData(prices=prices, events=[], currency=CURRENCY, source=self.provider_name)

    def validate_params(self, params: Dict | None) -> None:
        """Any parameters: the double reads none."""

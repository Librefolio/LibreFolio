"""
Mock provider for testing purposes only.

This provider returns fixed dummy data and should NEVER be used in production.
It's registered in the provider registry for testing the asset source framework
without external dependencies.

WARNING: This provider is for TESTING ONLY. Do not use in production code.

It declares one plugin setting of every kind (system and user, plain and secret), so that the settings infrastructure is
exercised end to end. Searching for ``SETTINGS_ECHO_QUERY`` answers with one item that describes the settings the call
received: the plain values, and for each secret only whether it is set — never its value. Searching for
``MINOR_UNIT_QUERY`` answers a line quoted in pence, ``MINOR_UNIT_IDENTIFIER``, with a quote base suggestion of 100,
which ``suggest_quote_base`` gives for it too (Z-32 d).

It reads current values in bulk (project 76): ``get_current_values_bulk`` answers every item as ``get_current_value``
would, records the keys of each call (``mock_bulk_calls``), leaves out an item that carries ``BULK_OMIT_PARAM`` and
refuses the whole call for an item that carries ``RATE_LIMITED_PARAM``.
"""

import threading
from collections import deque
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict

from backend.app.db import IdentifierType
from backend.app.db.models import ProviderInputType
from backend.app.schemas.assets.assets import FAAssetPatchItem
from backend.app.schemas.assets.metadata import (
    FAClassificationParams,
    FAGeographicArea,
    FASectorArea,
)
from backend.app.schemas.prices import (
    FACurrentValue,
    FACurrentValueRequest,
    FAHistoricalData,
    FAPricePoint,
)
from backend.app.schemas.provider import FAQuoteBaseSuggestion
from backend.app.services.assets.base import ASSET_HISTORY_MIN_FALLBACK, AssetHistoryStartDate, AssetRateLimitedError, AssetSourceError, AssetSourceProvider
from backend.app.services.assets.registry import AssetProviderRegistry
from backend.app.services.platform.provider_registry import register_provider
from backend.app.services.plugin_settings.fields import PluginSettingField, SettingOption, SettingScope, SettingType

#: The search query that makes the mock describe the settings it received.
SETTINGS_ECHO_QUERY = "lf-settings-echo"
#: The search query that makes the mock describe the values of its shared group ``mock`` (project 76, G2): the plan as it
#: is, the token only as set or unset — never its value.
GROUP_ECHO_QUERY = "lf-group-echo"
#: The search query that makes the mock refuse for too many requests, with a ``Retry-After`` of 30 s.
RATE_LIMITED_QUERY = "lf-rate-limited"
#: The provider parameter that makes the mock refuse for too many requests: a number of seconds (its ``Retry-After``) or
#: ``true`` (no ``Retry-After``). For in-process tests only: never on the shared test backend, where a pause would
#: outlive the test.
RATE_LIMITED_PARAM = "mock_rate_limited"
#: The search query that makes the mock answer a line quoted in pence (Z-32 d): ``MINOR_UNIT_IDENTIFIER``, currency
#: ``GBp``, with a quote base suggestion of 100 units per price.
MINOR_UNIT_QUERY = "lf-minor-unit"
#: The identifier of that line: ``suggest_quote_base`` suggests 100 units per price for it, nothing for any other.
MINOR_UNIT_IDENTIFIER = "MOCK_MINOR_UNIT"
#: The suggestion for that line.
_MINOR_UNIT_SUGGESTION = {"quantity": 100, "quote_currency": "GBp"}
#: The provider parameter that makes the mock leave an item out of a bulk current-value answer (project 76): no answer
#: for that asset, as a source says nothing about an identifier it does not know.
BULK_OMIT_PARAM = "mock_bulk_omit"

#: The keys of the latest bulk current-value calls, in call order: one tuple per call. Module-level, since the core makes
#: a new instance for every call, and bounded, since the mock also serves the shared test backend.
_bulk_calls: deque[tuple[str, ...]] = deque(maxlen=256)
_bulk_calls_lock = threading.Lock()


def mock_bulk_calls() -> list[tuple[str, ...]]:
    """The keys of each bulk current-value call made since the last reset, in call order (a copy)."""
    with _bulk_calls_lock:
        return list(_bulk_calls)


def reset_mock_bulk_calls() -> None:
    """Forget the recorded bulk current-value calls."""
    with _bulk_calls_lock:
        _bulk_calls.clear()


def _refuse_if_asked(provider_params: Dict | None) -> None:
    """Raise ``AssetRateLimitedError`` when the parameters ask the mock to refuse for too many requests."""
    asked = (provider_params or {}).get(RATE_LIMITED_PARAM)
    if asked is None or asked is False:
        return
    retry_after = float(asked) if isinstance(asked, (int, float)) and not isinstance(asked, bool) else None
    raise AssetRateLimitedError("Mock provider refused for too many requests (testing)", retry_after=retry_after)


@register_provider(AssetProviderRegistry)
class MockProvider(AssetSourceProvider):
    """
    Mock provider for testing - returns fixed dummy data.

    WARNING: FOR TESTING ONLY - DO NOT USE IN PRODUCTION
    """

    test_only = True
    #: A double with no network: its calls are never counted (project 76, U2)
    calls_external_service = False
    #: The test-only shared group (``plugin_settings/groups/mock.py``): nothing required, so the mock stays callable without it
    settings_groups = ("mock",)
    supports_bulk_current = True
    bulk_current_max_items = 50
    settings_fields = (
        PluginSettingField(
            key="api_key",
            type=SettingType.STRING,
            scope=SettingScope.SYSTEM,
            secret=True,
            label="API key (testing)",
            description="A secret the tests set: the mock only reports whether it is set.",
            env="LIBREFOLIO_MOCKPROV_API_KEY",
        ),
        PluginSettingField(
            key="region",
            type=SettingType.SELECT,
            scope=SettingScope.SYSTEM,
            label="Region (testing)",
            default="eu",
            options=(SettingOption("eu", "Europe"), SettingOption("us", "United States")),
        ),
        PluginSettingField(key="price_tolerance", type=SettingType.NUMBER, scope=SettingScope.SYSTEM, label="Price tolerance (testing)", default=0.5, minimum=0, maximum=10),
        PluginSettingField(key="verbose", type=SettingType.BOOLEAN, scope=SettingScope.SYSTEM, label="Verbose (testing)", default=False),
        PluginSettingField(
            key="preferred_language",
            type=SettingType.SELECT,
            scope=SettingScope.USER,
            label="Preferred language (testing)",
            default="all",
            options=(SettingOption("all", "All"), SettingOption("it", "Italian"), SettingOption("en", "English")),
        ),
        PluginSettingField(key="results_limit", type=SettingType.INTEGER, scope=SettingScope.USER, label="Results limit (testing)", default=10, minimum=1, maximum=50),
        PluginSettingField(key="personal_token", type=SettingType.STRING, scope=SettingScope.USER, secret=True, label="Personal token (testing)"),
    )

    @property
    def provider_code(self) -> str:
        return "mockprov"

    @property
    def provider_name(self) -> str:
        return "Mock Provider (TESTING ONLY)"

    @property
    def supports_meaningful_volume(self) -> bool:
        """Test double — never reports real volume ("Mock doesn't provide
        volume", see get_history_value below)."""
        return False

    @property
    def accepted_identifier_types(self) -> list:
        return [ProviderInputType.TICKER, ProviderInputType.AUTO_GENERATED]

    @property
    def test_cases(self) -> list[dict]:
        """Test cases with identifier and provider_params."""
        return [
            {
                "identifier": "MOCK",
                "identifier_type": IdentifierType.UUID,
                "provider_params": None,
                "expected_symbol": "MOCK",
            }
        ]

    async def get_current_value(
        self,
        identifier: str,
        identifier_type: IdentifierType,
        provider_params: Dict | None = None,
    ) -> FACurrentValue:
        """
        Return fixed mock current value.

        Always returns: 100.0 USD as of today
        """
        _refuse_if_asked(provider_params)
        return self._mock_quote(identifier)

    def _mock_quote(self, identifier: str) -> FACurrentValue:
        """The fixed quote of ``identifier``: 100.00 USD as of today; NOT_FOUND for ``INVALID_TICKER_12345``."""
        if identifier == "INVALID_TICKER_12345":
            raise AssetSourceError("Invalid identifier for mock provider.", error_code="NOT_FOUND")
        return FACurrentValue(
            value=Decimal("100.00"),
            currency="USD",
            as_of_date=date.today(),
            source=self.provider_name,
        )

    async def get_current_values_bulk(self, items: list[FACurrentValueRequest]) -> dict[str, FACurrentValue | AssetSourceError]:
        """Answer every item as ``get_current_value`` would, in one recorded call.

        The call is recorded first (``mock_bulk_calls``), so a refused call counts too. An item carrying
        ``RATE_LIMITED_PARAM`` refuses the whole call; one carrying ``BULK_OMIT_PARAM`` gets no answer; an unknown
        identifier answers its own ``AssetSourceError``.
        """
        with _bulk_calls_lock:
            _bulk_calls.append(tuple(item.key for item in items))
        for item in items:
            _refuse_if_asked(item.provider_params)
        answer: dict[str, FACurrentValue | AssetSourceError] = {}
        for item in items:
            if item.provider_params.get(BULK_OMIT_PARAM):
                continue
            try:
                answer[item.key] = self._mock_quote(item.identifier)
            except AssetSourceError as error:
                answer[item.key] = error
        return answer

    @property
    def supports_history(self) -> bool:
        """Whether this provider supports historical data."""
        return True

    async def get_history_value(
        self,
        identifier: str,
        identifier_type: IdentifierType,
        provider_params: Dict | None,
        start_date: AssetHistoryStartDate,
        end_date: date,
    ) -> FAHistoricalData:
        """
        Generate mock historical data.

        Returns daily prices of 100.0 for the entire date range.
        """
        _refuse_if_asked(provider_params)
        prices = []
        current = ASSET_HISTORY_MIN_FALLBACK if start_date == "min" else start_date

        while current <= end_date:
            prices.append(
                FAPricePoint(
                    date=current,
                    open=Decimal("100.00"),
                    high=Decimal("100.00"),
                    low=Decimal("100.00"),
                    close=Decimal("100.00"),
                    volume=None,  # Mock doesn't provide volume
                    currency="USD",
                )
            )
            current += timedelta(days=1)

        return FAHistoricalData(prices=prices, events=[], currency="USD", source=self.provider_name)

    @property
    def test_search_query(self) -> str | None:
        """Search query to use in tests."""
        return "TEST"

    async def search(self, query: str) -> list[dict]:
        """
        Mock search - returns dummy result for any query.

        ``SETTINGS_ECHO_QUERY`` returns one item whose display name describes the settings this call received;
        ``RATE_LIMITED_QUERY`` refuses for too many requests; ``MINOR_UNIT_QUERY`` returns a line quoted in pence with
        its quote base suggestion.
        """
        if query == RATE_LIMITED_QUERY:
            raise AssetRateLimitedError("Mock provider refused for too many requests (testing)", retry_after=30.0)
        if query == GROUP_ECHO_QUERY:
            group = self.settings.group("mock")
            summary = f"group: tier={group.get('tier')}; account_token={'set' if group.secret('account_token') else 'unset'}"
            return [{"identifier": "MOCK_GROUP", "identifier_type": IdentifierType.TICKER, "display_name": summary, "currency": "USD", "type": "MOCK"}]
        if query == MINOR_UNIT_QUERY:
            return [
                {
                    "identifier": MINOR_UNIT_IDENTIFIER,
                    "identifier_type": IdentifierType.TICKER,
                    "display_name": "Mock Asset: quoted in pence",
                    "currency": "GBp",
                    "type": "STOCK",
                    "quote_base_suggestion": dict(_MINOR_UNIT_SUGGESTION),
                }
            ]
        if query == SETTINGS_ECHO_QUERY:
            return [{"identifier": "MOCK_SETTINGS", "identifier_type": IdentifierType.TICKER, "display_name": self._settings_summary(), "currency": "USD", "type": "MOCK"}]
        return [
            {
                "identifier": f"MOCK_{query.upper()}",
                "identifier_type": IdentifierType.TICKER,  # Mock uses TICKER
                "display_name": f"Mock Asset: {query}",
                "currency": "USD",
                "type": "MOCK",
            }
        ]

    def _settings_summary(self) -> str:
        """The settings of this call, in a stable order: plain values as they are, secrets only as set or unset."""
        parts = []
        for declared in self.settings_fields:
            if declared.secret:
                parts.append(f"{declared.key}={'set' if self.settings.secret(declared.key) else 'unset'}")
            else:
                parts.append(f"{declared.key}={self.settings.get(declared.key)}")
        return "settings: " + "; ".join(parts)

    def validate_params(self, params: Dict | None) -> None:
        """
        Mock provider accepts any parameters.

        In a real provider, this would validate required params.
        """
        # Accept any params for testing flexibility

    async def fetch_asset_metadata(
        self,
        identifier: str,
        identifier_type: IdentifierType,
        provider_params: Dict | None = None,
    ) -> FAAssetPatchItem | None:
        """
        Fetch mock asset metadata for testing.

        Returns predictable mock data to test metadata auto-populate,
        refresh, and validation flows.

        Args:
            identifier: Asset identifier
            identifier_type: Type of the identifier
            provider_params: Optional parameters (unused)

        Returns:
            FAAssetPatchItem object with classification_params populated
        """
        _refuse_if_asked(provider_params)
        # Return mock data for testing as FAAssetPatchItem
        classification_params = FAClassificationParams(
            sector_area=FASectorArea(distribution={"Technology": Decimal("1.0")}),
            short_description=f"Mock test asset {identifier} - type: {identifier_type} - used for testing metadata features",
            geographic_area=FAGeographicArea(distribution={"USA": Decimal("0.6"), "ITA": Decimal("0.4")}),
        )

        return FAAssetPatchItem(asset_id=0, classification_params=classification_params)  # Will be set by caller

    async def suggest_quote_base(
        self,
        identifier: str,
        identifier_type: IdentifierType,
        provider_params: Dict | None = None,
    ) -> FAQuoteBaseSuggestion | None:
        """100 units per price for ``MINOR_UNIT_IDENTIFIER``, a line quoted in pence; nothing for any other (Z-32 d)."""
        _refuse_if_asked(provider_params)
        return FAQuoteBaseSuggestion(**_MINOR_UNIT_SUGGESTION) if identifier == MINOR_UNIT_IDENTIFIER else None

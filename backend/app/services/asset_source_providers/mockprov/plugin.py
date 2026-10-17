"""
Mock provider for testing purposes only.

This provider returns fixed dummy data and should NEVER be used in production.
It's registered in the provider registry for testing the asset source framework
without external dependencies.

WARNING: This provider is for TESTING ONLY. Do not use in production code.

It declares one plugin setting of every kind (system and user, plain and secret), so that the settings infrastructure is
exercised end to end. Searching for ``SETTINGS_ECHO_QUERY`` answers with one item that describes the settings the call
received: the plain values, and for each secret only whether it is set — never its value.
"""

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
    FAHistoricalData,
    FAPricePoint,
)
from backend.app.services.assets.base import ASSET_HISTORY_MIN_FALLBACK, AssetHistoryStartDate, AssetRateLimitedError, AssetSourceError, AssetSourceProvider
from backend.app.services.assets.registry import AssetProviderRegistry
from backend.app.services.plugin_settings.fields import PluginSettingField, SettingOption, SettingScope, SettingType
from backend.app.services.provider_registry import register_provider

#: The search query that makes the mock describe the settings it received.
SETTINGS_ECHO_QUERY = "lf-settings-echo"
#: The search query that makes the mock refuse for too many requests, with a ``Retry-After`` of 30 s.
RATE_LIMITED_QUERY = "lf-rate-limited"
#: The provider parameter that makes the mock refuse for too many requests: a number of seconds (its ``Retry-After``) or
#: ``true`` (no ``Retry-After``). For in-process tests only: never on the shared test backend, where a pause would
#: outlive the test.
RATE_LIMITED_PARAM = "mock_rate_limited"


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
        if identifier == "INVALID_TICKER_12345":
            raise AssetSourceError("Invalid identifier for mock provider.", error_code="NOT_FOUND")
        return FACurrentValue(
            value=Decimal("100.00"),
            currency="USD",
            as_of_date=date.today(),
            source=self.provider_name,
        )

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
        ``RATE_LIMITED_QUERY`` refuses for too many requests.
        """
        if query == RATE_LIMITED_QUERY:
            raise AssetRateLimitedError("Mock provider refused for too many requests (testing)", retry_after=30.0)
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

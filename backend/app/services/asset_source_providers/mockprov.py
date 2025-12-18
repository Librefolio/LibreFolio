"""
Mock provider for testing purposes only.

This provider returns fixed dummy data and should NEVER be used in production.
It's registered in the provider registry for testing the asset source framework
without external dependencies.

WARNING: This provider is for TESTING ONLY. Do not use in production code.
"""
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict

from backend.app.db import IdentifierType
from backend.app.schemas.assets import FACurrentValue, FAHistoricalData, FAPricePoint, FAClassificationParams, FAGeographicArea, FAAssetPatchItem, FASectorArea
from backend.app.services.asset_source import AssetSourceProvider, AssetSourceError
from backend.app.services.provider_registry import register_provider, AssetProviderRegistry


@register_provider(AssetProviderRegistry)
class MockProvider(AssetSourceProvider):
    """
    Mock provider for testing - returns fixed dummy data.

    WARNING: FOR TESTING ONLY - DO NOT USE IN PRODUCTION
    """

    @property
    def provider_code(self) -> str:
        return "mockprov"

    @property
    def provider_name(self) -> str:
        return "Mock Provider (TESTING ONLY)"

    @property
    def test_cases(self) -> list[dict]:
        """Test cases with identifier and provider_params."""
        return [
            {
                'identifier': 'MOCK',
                'provider_params': None
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
        if identifier == "INVALID_TICKER_12345":
            raise AssetSourceError("Invalid identifier for mock provider.", error_code="NOT_FOUND")
        return FACurrentValue(
            value=Decimal('100.00'),
            currency='USD',
            as_of_date=date.today(),
            source=self.provider_name
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
        start_date: date,
        end_date: date,
        ) -> FAHistoricalData:
        """
        Generate mock historical data.

        Returns daily prices of 100.0 for the entire date range.
        """
        prices = []
        current = start_date

        while current <= end_date:
            prices.append(FAPricePoint(
                date=current,
                open=Decimal('100.00'),
                high=Decimal('100.00'),
                low=Decimal('100.00'),
                close=Decimal('100.00'),
                volume=None,  # Mock doesn't provide volume
                currency='USD'
                ))
            current += timedelta(days=1)

        return FAHistoricalData(
            prices=prices,
            currency='USD',
            source=self.provider_name
            )

    @property
    def test_search_query(self) -> str | None:
        """Search query to use in tests."""
        return 'TEST'

    async def search(self, query: str) -> list[dict]:
        """
        Mock search - returns dummy result for any query.
        """
        return [
            {
                "identifier": f"MOCK_{query.upper()}",
                "identifier_type": IdentifierType.TICKER,  # Mock uses TICKER
                "display_name": f"Mock Asset: {query}",
                "currency": "USD",
                "type": "MOCK"
                }
            ]

    def validate_params(self, params: Dict | None) -> None:
        """
        Mock provider accepts any parameters.

        In a real provider, this would validate required params.
        """
        # Accept any params for testing flexibility
        pass

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
        # Return mock data for testing as FAAssetPatchItem
        classification_params = FAClassificationParams(
            sector_area=FASectorArea(distribution={"Technology": Decimal("1.0")}),
            short_description=f"Mock test asset {identifier} - type: {identifier_type} - used for testing metadata features",
            geographic_area=FAGeographicArea(distribution={"USA": Decimal("0.6"), "ITA": Decimal("0.4")})
            )

        return FAAssetPatchItem(
            asset_id=0,  # Will be set by caller
            classification_params=classification_params
            )

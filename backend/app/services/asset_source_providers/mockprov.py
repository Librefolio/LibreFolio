from datetime import timedelta

from backend.app.services.asset_source import AssetSourceProvider
from backend.app.services.provider_registry import register_provider, AssetProviderRegistry


@register_provider(AssetProviderRegistry)
class MockProv(AssetSourceProvider):
    provider_code = "mockprov"
    provider_name = "Mock Provider for Tests"

    async def get_current_value(self, provider_params: dict, session=None):
        from datetime import date
        return {"value": 100.0, "currency": "USD", "as_of_date": date.today(), "source": "mockprov"}

    async def get_history_value(self, provider_params: dict, start_date=None, end_date=None, session=None):
        prices = []
        current = start_date
        while current <= end_date:
            prices.append({
                "date": current,
                "close": 100.0,
                "currency": provider_params.get("currency", "USD")
                })
            current = current + timedelta(days=1)
        return {"prices": prices, "source": "mockprov"}

    def validate_params(self, params: dict) -> None:
        # Accept any params for tests
        return

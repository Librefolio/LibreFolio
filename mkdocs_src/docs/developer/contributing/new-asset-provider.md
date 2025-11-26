# How to Add a New Asset Provider

This guide provides a step-by-step walkthrough for adding a new asset pricing provider to LibreFolio.

## 🔌 Architecture Overview

The asset pricing system uses a modular provider architecture. Each provider is a Python class that inherits from `AssetSourceProvider` and is auto-discovered at startup.

-   **Location**: `backend/app/services/asset_source_providers/`
-   **Base Class**: `AssetSourceProvider` in `backend/app/services/asset_source.py`
-   **Registration**: The `@register_provider(AssetProviderRegistry)` decorator handles auto-discovery.

## 📝 Minimal Provider Template

Create a new file in `backend/app/services/asset_source_providers/` (e.g., `your_provider.py`):

```python
# backend/app/services/asset_source_providers/your_provider.py
import logging
from datetime import date
from decimal import Decimal
import httpx

from backend.app.services.asset_source import AssetSourceProvider, AssetSourceError
from backend.app.services.provider_registry import register_provider, AssetProviderRegistry
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

@register_provider(AssetProviderRegistry)
class YourProvider(AssetSourceProvider):
    """Your asset pricing provider."""
    
    @property
    def provider_code(self) -> str:
        return "yourprovider"  # Lowercase, unique identifier
    
    @property
    def provider_name(self) -> str:
        return "Your Asset Data Source"
        
    async def get_current_value(self, provider_params: dict, session: AsyncSession) -> dict:
        """Fetch the latest price for an asset."""
        # ... (API fetching and parsing logic)
        return {
            "value": Decimal("123.45"),
            "currency": "USD",
            "as_of_date": date.today(),
            "source": self.provider_code
        }

    async def get_history_value(self, provider_params: dict, start_date: date, end_date: date, session: AsyncSession) -> dict:
        """Fetch historical OHLC prices."""
        # ... (API fetching and parsing logic)
        return {
            "prices": [{
                "date": start_date,
                "close": Decimal("123.45"),
                "currency": "USD"
            }],
            "currency": "USD",
            "source": self.provider_code
        }

    async def search(self, query: str) -> list[dict]:
        """Search for assets (optional)."""
        raise AssetSourceError("Search not supported", "NOT_SUPPORTED")
```

## ✅ Required Methods and Properties

1.  **`provider_code`** (property): A unique, lowercase string identifier (e.g., "yfinance").
2.  **`provider_name`** (property): A human-readable name.
3.  **`get_current_value(...)`** (async method): Fetches the latest available price. Must return a dictionary matching the `CurrentValueModel` Pydantic model.
4.  **`get_history_value(...)`** (async method): Fetches historical OHLC prices for a date range. Must return a dictionary matching the `HistoricalDataModel`.
5.  **`search(...)`** (async method, optional): Allows searching for assets via the provider's API. If not supported, it should raise a `AssetSourceError` with the code `NOT_SUPPORTED`.
6.  **`validate_params(...)`** (method, optional): Validates the `provider_params` JSON object for the asset.

## 🧪 Testing Your Provider

The generic test suite will automatically pick up and test your new provider.

1.  Make sure your provider is correctly registered with the `@register_provider` decorator.
2.  Run the external tests:
    ```bash
    ./test_runner.py external asset-providers
    ```
    This will test the provider's metadata, current value fetching, historical data, search functionality, and error handling.

## 🕵️ How to get information on contributing a new Asset provider

To get information on contributing a new Asset provider an Agent can:

1.  Read this file.
2.  Read the [Asset Pricing Feature Guide](../features/asset-pricing.md) for an overview.
3.  Inspect existing providers in `backend/app/services/asset_source_providers/` (e.g., `yfinance.py`, `css_scraper.py`) as a reference.
4.  Examine `backend/test_scripts/test_external/test_asset_providers.py` to understand the testing requirements.

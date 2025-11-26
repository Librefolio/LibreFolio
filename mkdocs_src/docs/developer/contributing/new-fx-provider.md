# How to Add a New FX Provider

This guide provides a step-by-step walkthrough for adding a new FX (Foreign Exchange) rate provider to LibreFolio.

## 🔌 Architecture Overview

The FX system is built on a modular provider architecture. Each provider is a Python class that inherits from the `FXRateProvider` abstract base class and is automatically discovered at startup.

-   **Location**: `backend/app/services/fx_providers/`
-   **Base Class**: `FXRateProvider` in `backend/app/services/fx.py`
-   **Registration**: The `@register_provider(FXProviderRegistry)` decorator handles auto-discovery.

## 📝 Minimal Provider Template

Create a new file in `backend/app/services/fx_providers/` (e.g., `your_provider.py`):

```python
# backend/app/services/fx_providers/your_provider.py
import logging
from datetime import date
from decimal import Decimal
import httpx

from backend.app.services.fx import FXRateProvider
from backend.app.services.provider_registry import register_provider, FXProviderRegistry

logger = logging.getLogger(__name__)

@register_provider(FXProviderRegistry)
class YourProvider(FXRateProvider):
    """Your Central Bank FX rate provider."""
    
    BASE_URL = "https://api.yourcentralbank.com/..."
    
    @property
    def provider_code(self) -> str:
        return "YCB"  # Uppercase, unique identifier
    
    @property
    def provider_name(self) -> str:
        return "Your Central Bank"
    
    @property
    def base_currencies(self) -> list[str]:
        return ["EUR"] # List of supported base currencies
    
    async def fetch_rates(
        self,
        date_range: tuple[date, date],
        currencies: list[str],
        base_currency: str | None = None
    ) -> dict[str, list[tuple[date, str, str, Decimal]]]:
        """Fetch rates from the provider's API."""
        start_date, end_date = date_range
        # ... (API fetching and parsing logic)
        
        # Example return structure
        return {
            'USD': [
                (date(2025, 1, 1), 'EUR', 'USD', Decimal('1.08')),
            ]
        }
```

## ✅ Required Methods and Properties

1.  **`provider_code`** (property): A unique, uppercase string to identify your provider (e.g., "ECB").
2.  **`provider_name`** (property): A human-readable name (e.g., "European Central Bank").
3.  **`base_currencies`** (property): A list of supported base currencies (e.g., `["EUR"]`).
4.  **`fetch_rates(...)`** (async method): The core method that fetches data from the external API. It must return a dictionary where keys are currency codes and values are lists of `(date, base_currency, quote_currency, rate)` tuples.

## 🧪 Testing Your Provider

The best way to test your new provider is to add it to the generic external test suite.

1.  **Add your provider code** to the test file (if it's not discovered automatically).
2.  **Run the external tests**:
    ```bash
    ./test_runner.py external fx-providers
    ```
    This will run a standardized set of tests against your provider, including metadata validation, currency support, and live rate fetching.

## 🕵️ How to get information on contributing a new FX provider

To get information on contributing a new FX provider an Agent can:

1.  Read this file.
2.  Read the [FX System Feature Guide](../features/fx-system.md) for an overview.
3.  Inspect existing providers in `backend/app/services/fx_providers/` as a reference.
4.  Examine `backend/test_scripts/test_external/test_fx_providers.py` to understand the testing requirements.

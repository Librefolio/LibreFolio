# Asset Provider Development Guide

Quick reference guide for developing new asset pricing providers in LibreFolio.

> 📚 For complete asset pricing system documentation, see [Asset Pricing Architecture](./architecture.md)

---

## 🎯 Quick Start Checklist

- [ ] Create provider class in `backend/app/services/asset_source_providers/`
- [ ] Inherit from `AssetSourceProvider` abstract base class
- [ ] Implement all required methods
- [ ] Use `@register_provider(AssetProviderRegistry)` decorator
- [ ] Test with mock data
- [ ] Done! Your provider is ready to use

---

## 📝 Minimal Provider Template

```python
# backend/app/services/asset_source_providers/your_provider.py
"""
Your Asset Pricing Provider.

Fetches OHLC price data from [Your Data Source].
"""
import logging
from datetime import date
from decimal import Decimal
from typing import Optional
import httpx

from backend.app.services.provider_registry import register_provider, AssetProviderRegistry
from backend.app.services.asset_source import AssetSourceProvider, AssetSourceError
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@register_provider(AssetProviderRegistry)
class YourProvider(AssetSourceProvider):
    """Your asset pricing provider."""
    
    BASE_URL = "https://api.yourservice.com"
    
    @property
    def provider_code(self) -> str:
        return "yourprovider"  # Lowercase, unique identifier
    
    @property
    def provider_name(self) -> str:
        return "Your Service Name"
    
    def validate_params(self, params: dict) -> None:
        """
        Validate provider_params structure.
        
        Raises:
            AssetSourceError: If params invalid
        """
        if not params or "identifier" not in params:
            raise AssetSourceError(
                "Missing 'identifier' in provider_params",
                "INVALID_PARAMS",
                {"params": params}
            )
    
    async def get_current_value(
        self,
        provider_params: dict,
        session: AsyncSession,
    ) -> dict:
        """
        Fetch current price (latest available).
        
        Args:
            provider_params: Provider-specific config (e.g., {"identifier": "AAPL"})
            session: Database session
        
        Returns:
            Dict with shape:
            {
                "value": Decimal,
                "currency": str,
                "as_of_date": date,
                "source": str
            }
        
        Raises:
            AssetSourceError: On fetch failure
        """
        self.validate_params(provider_params)
        identifier = provider_params["identifier"]
        
        try:
            # 1. Fetch from API
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/current",
                    params={"symbol": identifier}
                )
                response.raise_for_status()
                data = response.json()
            
            # 2. Parse response
            value = Decimal(str(data["price"]))
            currency = data.get("currency", "USD")
            as_of_date = date.fromisoformat(data["date"])
            
            # 3. Return CurrentValueModel-compatible dict
            return {
                "value": value,
                "currency": currency,
                "as_of_date": as_of_date,
                "source": self.provider_code
            }
        
        except httpx.HTTPError as e:
            raise AssetSourceError(
                f"HTTP error fetching current value: {str(e)}",
                "HTTP_ERROR",
                {"identifier": identifier}
            )
        except Exception as e:
            raise AssetSourceError(
                f"Failed to fetch current value: {str(e)}",
                "FETCH_ERROR",
                {"identifier": identifier}
            )
    
    async def get_history_value(
        self,
        provider_params: dict,
        start_date: date,
        end_date: date,
        session: AsyncSession,
    ) -> dict:
        """
        Fetch historical OHLC prices for date range.
        
        Args:
            provider_params: Provider-specific config
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            session: Database session
        
        Returns:
            Dict with shape:
            {
                "prices": [
                    {
                        "date": date,
                        "open": Decimal | None,
                        "high": Decimal | None,
                        "low": Decimal | None,
                        "close": Decimal,
                        "volume": Decimal | None,
                        "currency": str
                    },
                    ...
                ],
                "currency": str,
                "source": str
            }
        
        Raises:
            AssetSourceError: On fetch failure
        """
        self.validate_params(provider_params)
        identifier = provider_params["identifier"]
        
        try:
            # 1. Fetch from API
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/history",
                    params={
                        "symbol": identifier,
                        "start": str(start_date),
                        "end": str(end_date)
                    }
                )
                response.raise_for_status()
                data = response.json()
            
            # 2. Parse response
            prices = []
            for item in data["data"]:
                prices.append({
                    "date": date.fromisoformat(item["date"]),
                    "open": Decimal(str(item["open"])) if "open" in item else None,
                    "high": Decimal(str(item["high"])) if "high" in item else None,
                    "low": Decimal(str(item["low"])) if "low" in item else None,
                    "close": Decimal(str(item["close"])),
                    "volume": Decimal(str(item["volume"])) if "volume" in item else None,
                    "currency": item.get("currency", "USD")
                })
            
            # 3. Return HistoricalDataModel-compatible dict
            return {
                "prices": prices,
                "currency": data.get("currency", "USD"),
                "source": self.provider_code
            }
        
        except httpx.HTTPError as e:
            raise AssetSourceError(
                f"HTTP error fetching history: {str(e)}",
                "HTTP_ERROR",
                {"identifier": identifier, "start": start_date, "end": end_date}
            )
        except Exception as e:
            raise AssetSourceError(
                f"Failed to fetch history: {str(e)}",
                "FETCH_ERROR",
                {"identifier": identifier, "start": start_date, "end": end_date}
            )
    
    async def search(self, query: str) -> list[dict]:
        """
        Search for assets (optional - only if API supports it).
        
        Args:
            query: Search query string
        
        Returns:
            List of dicts:
            [
                {
                    "identifier": str,
                    "display_name": str,
                    "currency": str,
                    "type": str  # "STOCK", "ETF", etc.
                },
                ...
            ]
        
        Raises:
            AssetSourceError: If search not supported or fails
        """
        # If your API doesn't support search, use default implementation:
        raise AssetSourceError(
            f"Search not supported by {self.provider_name}",
            "NOT_SUPPORTED",
            {"provider": self.provider_code}
        )
        
        # OR implement search:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/search",
                    params={"q": query}
                )
                response.raise_for_status()
                data = response.json()
            
            results = []
            for item in data["results"]:
                results.append({
                    "identifier": item["symbol"],
                    "display_name": item["name"],
                    "currency": item.get("currency", "USD"),
                    "type": item.get("type", "UNKNOWN")
                })
            
            return results
        
        except Exception as e:
            raise AssetSourceError(
                f"Search failed: {str(e)}",
                "SEARCH_ERROR",
                {"query": query}
            )
```

---

## ✅ Required Methods

### 1. `provider_code` (property)

```python
@property
def provider_code(self) -> str:
    return "yourprovider"  # lowercase, unique identifier
```

**Rules:**
- Must be **lowercase**
- Must be **unique** across all providers
- Typically one word (e.g., yfinance, alphavantage, cssscraper)
- Stored in database: `asset_provider_assignments.provider_code`

---

### 2. `provider_name` (property)

```python
@property
def provider_name(self) -> str:
    return "Your Service Name"
```

**Purpose**: Human-readable name displayed in UI and logs

---

### 3. `get_current_value()` (async method)

**Purpose**: Fetch latest available price

**Return Shape**:
```python
{
    "value": Decimal("175.50"),
    "currency": "USD",
    "as_of_date": date(2025, 11, 10),
    "source": "yourprovider"
}
```

**Error Handling**:
```python
raise AssetSourceError(
    "No data available",
    "NO_DATA",
    {"identifier": "AAPL"}
)
```

---

### 4. `get_history_value()` (async method)

**Purpose**: Fetch OHLC prices for date range

**Return Shape**:
```python
{
    "prices": [
        {
            "date": date(2025, 11, 10),
            "open": Decimal("174.80"),
            "high": Decimal("176.20"),
            "low": Decimal("174.50"),
            "close": Decimal("175.50"),
            "volume": Decimal("50000000"),
            "currency": "USD"
        },
        # ... more days
    ],
    "currency": "USD",
    "source": "yourprovider"
}
```

**Notes**:
- `open`, `high`, `low`, `volume` are optional (can be `None`)
- `close` is **required**
- Dates should be in chronological order

---

### 5. `validate_params()` (method)

**Purpose**: Validate `provider_params` structure

**Example**:
```python
def validate_params(self, params: dict) -> None:
    required = ["identifier"]
    for field in required:
        if field not in params:
            raise AssetSourceError(
                f"Missing '{field}' in provider_params",
                "INVALID_PARAMS",
                {"params": params}
            )
```

**Note**: Called before `get_current_value()` and `get_history_value()`

---

### 6. `search()` (async method, OPTIONAL)

**Purpose**: Search for assets by query string

**Return Shape**:
```python
[
    {
        "identifier": "AAPL",
        "display_name": "Apple Inc.",
        "currency": "USD",
        "type": "STOCK"
    },
    # ...
]
```

**Default Implementation** (if not supported):
```python
async def search(self, query: str) -> list[dict]:
    raise AssetSourceError(
        f"Search not supported by {self.provider_name}",
        "NOT_SUPPORTED",
        {"provider": self.provider_code}
    )
```

---

## 🎨 Provider Design Patterns

### Pattern 1: REST API Provider (Most Common)

**Example**: yfinance, Alpha Vantage, IEX Cloud

```python
async def get_history_value(self, provider_params, start_date, end_date, session):
    identifier = provider_params["identifier"]
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{self.BASE_URL}/history",
            params={"symbol": identifier, "start": start_date, "end": end_date}
        )
        response.raise_for_status()
        data = response.json()
    
    # Parse and return
    return {"prices": [...], "currency": "USD", "source": self.provider_code}
```

---

### Pattern 2: Web Scraper (HTML/CSS)

**Example**: CSS Scraper for generic websites

```python
from bs4 import BeautifulSoup

async def get_current_value(self, provider_params, session):
    url = provider_params["url"]
    selector = provider_params["selector"]
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
    
    soup = BeautifulSoup(response.text, "html.parser")
    element = soup.select_one(selector)
    
    if not element:
        raise AssetSourceError("Element not found", "NO_DATA")
    
    # Parse price from text (e.g., "€1,234.56" → Decimal("1234.56"))
    value = self._parse_price(element.text)
    
    return {
        "value": value,
        "currency": provider_params.get("currency", "EUR"),
        "as_of_date": date.today(),
        "source": self.provider_code
    }
```

---

### Pattern 3: File-Based (CSV/JSON)

**Example**: Read prices from uploaded file

```python
import csv
from pathlib import Path

async def get_history_value(self, provider_params, start_date, end_date, session):
    file_path = Path(provider_params["file_path"])
    
    prices = []
    with open(file_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            price_date = date.fromisoformat(row["date"])
            if start_date <= price_date <= end_date:
                prices.append({
                    "date": price_date,
                    "close": Decimal(row["close"]),
                    "currency": row.get("currency", "USD")
                })
    
    return {"prices": prices, "currency": "USD", "source": self.provider_code}
```

---

## 🛡️ Error Handling Best Practices

### 1. Always Use `AssetSourceError`

```python
# Good ✅
raise AssetSourceError(
    "API rate limit exceeded",
    "RATE_LIMIT",
    {"identifier": "AAPL", "retry_after": 60}
)

# Bad ❌
raise Exception("Rate limit")
```

### 2. Provide Detailed Context

```python
# Good ✅
details = {
    "identifier": identifier,
    "start_date": str(start_date),
    "end_date": str(end_date),
    "api_response": response.status_code
}
raise AssetSourceError("API error", "API_ERROR", details)

# Bad ❌
raise AssetSourceError("Error", "ERROR")
```

### 3. Log Before Raising

```python
import logging
logger = logging.getLogger(__name__)

try:
    response = await client.get(...)
except httpx.HTTPError as e:
    logger.error(f"HTTP error fetching {identifier}: {e}")
    raise AssetSourceError(...)
```

---

## 🧪 Testing Your Provider

### 1. Manual Test Script

```python
# test_your_provider.py
import asyncio
from backend.app.services.provider_registry import AssetProviderRegistry
from backend.app.db.session import get_async_engine
from sqlalchemy.ext.asyncio import AsyncSession

async def test():
    # Force auto-discovery
    AssetProviderRegistry.auto_discover()
    
    # Get provider instance
    provider = AssetProviderRegistry.get_provider_instance("yourprovider")
    
    if not provider:
        print("Provider not found!")
        return
    
    # Test current value
    async with AsyncSession(get_async_engine()) as session:
        result = await provider.get_current_value(
            {"identifier": "AAPL"},
            session
        )
        print(f"Current value: {result}")
    
    print("✅ Test passed!")

if __name__ == "__main__":
    asyncio.run(test())
```

### 2. Integration Test

Add to `backend/test_scripts/test_services/test_asset_source_providers.py`:

```python
async def test_your_provider():
    provider = AssetProviderRegistry.get_provider_instance("yourprovider")
    
    async with AsyncSession(get_async_engine()) as session:
        # Test current value
        current = await provider.get_current_value(
            {"identifier": "TEST"},
            session
        )
        assert "value" in current
        assert "currency" in current
        
        # Test history
        history = await provider.get_history_value(
            {"identifier": "TEST"},
            date(2025, 1, 1),
            date(2025, 1, 31),
            session
        )
        assert "prices" in history
        assert len(history["prices"]) > 0
```

---

## 📊 Common Gotchas

### 1. Decimal vs Float

```python
# Good ✅
value = Decimal(str(data["price"]))

# Bad ❌ (loses precision)
value = Decimal(float(data["price"]))
```

### 2. Date Format Consistency

```python
# Good ✅
from datetime import date
price_date = date.fromisoformat("2025-11-10")

# Bad ❌ (inconsistent formats)
price_date = "11/10/2025"
```

### 3. Optional Fields

```python
# Good ✅
"open": Decimal(str(item["open"])) if "open" in item else None

# Bad ❌ (crashes if missing)
"open": Decimal(str(item["open"]))
```

### 4. Currency Handling

```python
# Good ✅ (explicit fallback)
currency = data.get("currency", "USD")

# Bad ❌ (implicit assumption)
currency = data["currency"]
```

---

## 🚀 Advanced Features

### 1. Caching (if API is expensive)

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def _get_supported_currencies_cached(self) -> tuple:
    # Expensive API call
    return tuple(currencies)

async def get_supported_currencies(self) -> list[str]:
    return list(self._get_supported_currencies_cached())
```

### 2. Rate Limiting

```python
import time
from collections import deque

class RateLimitedProvider(AssetSourceProvider):
    def __init__(self):
        self._request_times = deque(maxlen=10)  # 10 requests
        self._window = 60  # per 60 seconds
    
    async def _wait_for_rate_limit(self):
        now = time.time()
        if len(self._request_times) == 10:
            oldest = self._request_times[0]
            if now - oldest < self._window:
                wait_time = self._window - (now - oldest)
                await asyncio.sleep(wait_time)
        
        self._request_times.append(now)
```

### 3. Retry Logic

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def _fetch_with_retry(self, url: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()
```

---

## 📚 Related Documentation

- [Asset Pricing Architecture](./architecture.md) - System overview
- [FX Provider Development](../fx/provider-development.md) - Similar patterns for FX
- [API Development Guide](../api-development-guide.md) - API endpoint creation

---

## 🎓 Real-World Examples

See existing providers for reference:
- **yfinance**: `backend/app/services/asset_source_providers/yahoo_finance.py`
- **mockprov**: `backend/app/services/asset_source_providers/mockprov.py` (simple test provider)

---

**Last Updated**: 2025-11-10  
**Version**: 1.0.0


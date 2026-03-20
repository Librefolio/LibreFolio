# 📈 Asset Plugin Guide

How to create a new **Asset Source Provider** to fetch prices from a new data source.

**Base class**: `AssetSourceProvider` (in `backend/app/services/asset_source.py`)
**Plugin folder**: `backend/app/services/asset_source_providers/`
**Registry**: `AssetProviderRegistry`

---

## 🔄 Flow

The system calls provider methods in three distinct phases:

```mermaid
graph TD
    subgraph "Phase 1 — Search (user looks for asset)"
        S1["search(query)<br/><small>e.g., 'Apple'</small>"] --> S2["Returns: list of<br/>{identifier, display_name,<br/>currency, type}"]
    end

    subgraph "Phase 2 — Current Price (dashboard, refresh)"
        C1["get_current_value(<br/>identifier, type, params)"] --> C2["Returns: FACurrentValue<br/><small>(price, currency, date)</small>"]
    end

    subgraph "Phase 3 — Historical Data (charts, analysis)"
        H1["get_history_value(<br/>identifier, ..., start, end)"] --> H2["Returns: FAHistoricalData<br/><small>(prices[], currency)</small>"]
        H2 --> H3["Core fills gaps<br/><small>weekends, holidays<br/>→ backward_filled=True</small>"]
    end

    S2 ~~~ C1
    C2 ~~~ H1

    style S1 fill:#e3f2fd,stroke:#1565c0
    style S2 fill:#e3f2fd,stroke:#1565c0
    style C1 fill:#e8f5e9,stroke:#2e7d32
    style C2 fill:#e8f5e9,stroke:#2e7d32
    style H1 fill:#fff3e0,stroke:#e65100
    style H2 fill:#fff3e0,stroke:#e65100
    style H3 fill:#f3e5f5,stroke:#7b1fa2
```

**Phase 1** is optional but **strongly recommended** — enables users to discover and link assets without knowing the exact identifier. See [Asset Search](#asset-search) below.

**Phase 2** fetches the latest price for the dashboard or manual refresh.

**Phase 3** fetches historical OHLCV data. The plugin returns only actual trading days — core fills gaps (weekends, holidays) with last known value.

**Plugin responsibility**: Fetch raw price data from external source. Return only actual data points (trading days).
**Core responsibility**: Gap filling (weekends/holidays → `backward_filled=True`), caching, database storage, currency conversion.

---

## 📋 ABC Methods

### ✅ Required (Abstract)

| Method | Signature | Description |
|--------|-----------|-------------|
| `provider_code` | `@property → str` | Unique identifier (e.g., `"yfinance"`) |
| `provider_name` | `@property → str` | Display name (e.g., `"Yahoo Finance"`) |
| `test_cases` | `@property → list[dict]` | Test cases for automated testing (`identifier`, `identifier_type`, `provider_params`) |
| `test_search_query` | `@property → str \| None` | Search query for automated tests. `None` if search not supported. |
| `get_current_value(identifier, type, params)` | `async → FACurrentValue` | Fetch latest price. Returns `value`, `currency`, `as_of_date`, `source`. |
| `get_history_value(identifier, type, params, start, end)` | `async → FAHistoricalData` | Fetch historical OHLCV data for date range. Return raw data only — no gap filling. |

### 💪 Strongly Recommended (Override)

!!! tip "Implementing `search()` is strongly recommended"
    Without search, users must know the exact asset identifier (ticker, ISIN, URL) upfront. With search, they can type a name like "Apple" and pick from results.

| Method | Default | Description |
|--------|---------|-------------|
| `search(query)` | Raises `NOT_SUPPORTED` | Search for assets by name, ticker, or ISIN. Returns `[{identifier, identifier_type, display_name, currency, type}]`. |
| `test_search_query` | — | Query string for automated search tests (e.g., `"Apple"`). Return `None` if search not supported. |

### 🔧 Optional (Override)

| Method | Default | Description |
|--------|---------|-------------|
| `get_icon` | `None` | Provider icon URL for the UI |
| `supports_history` | `True` | Set `False` for providers that only support current prices (e.g., web scrapers) |
| `validate_params(params)` | — | Validate provider-specific configuration (raise on invalid) |
| `generate_static_url(path)` | — | Helper to build `/api/v1/uploads/plugin/asset/{path}` |

---

## 🔎 Asset Search

The `search(query)` method allows users to **discover assets** by name, ticker, or ISIN across all providers simultaneously.

### ⚙️ How It Works

1. User types a query in the UI (e.g., "Apple", "MSCI World", "IE00B4L5Y983")
2. Frontend calls `GET /api/v1/assets/provider/search?q=Apple`
3. Backend queries **all providers in parallel** via `AssetSearchService.search()` (`asyncio.gather`)
4. Providers that don't implement search (default raises `NOT_SUPPORTED`) are silently skipped
5. Results are aggregated and returned to the user

### 🔌 Provider Support

| Provider | `search()` | `test_search_query` | Notes |
|----------|-----------|---------------------|-------|
| **Yahoo Finance** | ✅ | `"Apple"` | Full ticker search with caching (10 min TTL) |
| **JustETF** | ✅ | `"iShares Core S&P 500"` | ISIN-based search across cached ETF list |
| **CSS Scraper** | ❌ | `None` | No search — URL must be provided manually |
| **Scheduled Investment** | ❌ | `None` | Synthetic provider, no external search |

### 🌐 API Endpoint

```
GET /api/v1/assets/provider/search?q=Apple&providers=yfinance,justetf
```

**Query parameters**:

- `q` (required): Search query, min 1 character
- `providers` (optional): Comma-separated provider codes. Default: all providers with search support.

**Response**:

```json
{
  "query": "Apple",
  "total_results": 5,
  "results": [
    {
      "identifier": "AAPL",
      "display_name": "Apple Inc.",
      "provider_code": "yfinance",
      "currency": "USD",
      "asset_type": "stock"
    }
  ],
  "providers_queried": ["yfinance", "justetf"],
  "providers_with_errors": []
}
```

- Searches are executed **in parallel** — one slow provider won't block others
- Provider-specific errors are logged but don't fail the entire request
- Errors are reported in `providers_with_errors` for debugging

---

## 💻 Implementation Example

```python
# backend/app/services/asset_source_providers/my_provider.py

from datetime import date
from decimal import Decimal
from backend.app.services.asset_source import AssetSourceProvider, IdentifierType
from backend.app.services.provider_registry import register_provider, AssetProviderRegistry
from backend.app.schemas.assets import FACurrentValue, FAHistoricalData, FAPricePoint

@register_provider(AssetProviderRegistry)
class MyProvider(AssetSourceProvider):

    @property
    def provider_code(self) -> str:
        return "my_provider"

    @property
    def provider_name(self) -> str:
        return "My Data Provider"

    @property
    def test_cases(self) -> list[dict]:
        return [
            {"identifier": "AAPL", "identifier_type": IdentifierType.TICKER, "provider_params": None}
        ]

    async def get_current_value(
        self, identifier: str, identifier_type: IdentifierType, provider_params: dict
    ) -> FACurrentValue:
        # Fetch latest price from your API
        price = await self._fetch_price(identifier)
        return FACurrentValue(
            value=Decimal(str(price)),
            currency="USD",
            as_of_date=date.today(),
            source=self.provider_name,
        )

    async def get_history_value(
        self, identifier: str, identifier_type: IdentifierType,
        provider_params: dict | None, start_date: date, end_date: date
    ) -> FAHistoricalData:
        # Fetch historical data — return ONLY actual trading days
        raw_data = await self._fetch_history(identifier, start_date, end_date)
        prices = [
            FAPricePoint(date=d, close=Decimal(str(p)), open=None, high=None, low=None, volume=None)
            for d, p in raw_data
        ]
        return FAHistoricalData(prices=prices, currency="USD", source=self.provider_name)
```

---

## 🔗 Related Documentation

- [Asset Architecture](../../backend/assets/architecture.md) — Provider interface, caching, refresh logic
- [System Providers](../../backend/assets/system_providers.md) — Built-in providers (Scheduled Investment, Manual)
- [Providers List](../../backend/assets/providers_list.md) — All available providers
- [Registry Pattern Overview](registry_pattern.md) — How the plugin system works


# Asset Pricing System Architecture

Detailed technical architecture of the LibreFolio Asset Pricing system.

> 💡 **Want to understand async patterns?** See [Async Architecture Guide](../async-architecture.md)  
> 📚 **For FX system architecture**, see [FX Architecture Guide](../fx/architecture.md)

---

## 🏗️ System Architecture

### Multi-Provider System

LibreFolio uses a **plugin-based provider architecture** to support multiple asset pricing data sources:

```
      ┌──────────────────────────────────────────────┐
      │         Service Layer                        │
      │    (asset_source.py - orchestration)         │
      │                                              │
      │  • AssetSourceManager (bulk-first)           │
      │  • get_prices() + backward-fill              │
      │  • bulk_refresh_prices() + concurrency       │
      │  • bulk_upsert_prices() / bulk_delete_prices │
      │  • Synthetic yield calculation (runtime)     │
      └────────────────┬─────────────────────────────┘
                       │
                       ▼
      ┌────────────────────────────────────────────┐
      │      AssetProviderRegistry                 │
      │       (provider auto-discovery)            │
      │                                            │
      │  • get_provider(code)                      │
      │  • get_provider_instance(code)             │
      │  • auto_discover()                         │
      └────┬─────────┬──────────┬─────────┬────────┘
           │         │          │         │
           ▼         ▼          ▼         ▼
      ┌────────┐ ┌───────┐ ┌─────────┐ ┌──────┐
      │yfinance│ │  CSS  │ │Synthetic│ │Custom│
      │ Yahoo  │ │Scraper│ │ Yield   │ │ ...  │
      │Finance │ │  Web  │ │(Runtime)│ │      │
      └────────┘ └───────┘ └─────────┘ └──────┘
         │           │          │          │
         └───────────┴──────────┴──────────┘
                       │
                       ▼
      ┌─────────────────────────────────┐
      │   Database (price_history)      │
      │   + asset_provider_assignments  │
      └─────────────────────────────────┘
```

**Key Difference from FX System:**
- **Asset Pricing**: OHLC data (open/high/low/close) + volume + currency
- **FX Rates**: Single rate value + alphabetical normalization
- **Shared**: `BackwardFillInfo`, `AbstractProviderRegistry` pattern

---

## 🔄 Data Flow

### 1. Price Refresh Flow (Provider-Driven)

```
┌─────────────┐
│   API/CLI   │ Request price refresh for asset(s) + date range
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────┐
│  Service: bulk_refresh_prices()         │
│  • Resolve provider for each asset      │
│  • Group by provider_code               │
│  • Parallel async with semaphore        │
└──────┬──────────────────────────────────┘
       │
       ├─→ Prefetch: Query existing DB prices (async)
       │
       └─→ Fetch: Call provider.get_history_value() (async)
       │
       ▼
┌─────────────────────────────────────────┐
│  Provider: get_history_value()          │
│  • HTTP call to data source API         │
│  • Parse response (JSON/CSV/HTML)       │
│  • Return: {prices: [PricePoint], ...}  │
└──────┬──────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│  Service: bulk_upsert_prices()          │
│  • Truncate to DB precision             │
│  • DELETE existing dates + INSERT new   │
│  • Update last_fetch_at                 │
└─────────────────────────────────────────┘
```

### 2. Price Query Flow (with Backward-Fill)

```
┌─────────────┐
│   Request   │ Get prices for asset from 2025-01-01 to 2025-01-05
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────┐
│  Service: get_prices()                  │
│  • Check asset.valuation_model          │
└──────┬──────────────────────────────────┘
       │
       ├─→ SCHEDULED_YIELD: Calculate synthetic value (runtime)
       │   • find_active_rate()
       │   • calculate_accrued_interest()
       │   • Return calculated values (no DB query)
       │
       └─→ MARKET_PRICE: Query price_history table
           │
           ▼
       ┌─────────────────────────────────────────┐
       │  Backward-Fill Logic                    │
       │  • Query DB for date range              │
       │  • For each requested date:             │
       │    - Exact match → return price         │
       │    - No match → use last known price    │
       │    - Add BackwardFillInfo if backfilled │
       └─────────────────────────────────────────┘
```

### 3. Manual Price Management Flow

```
┌─────────────┐
│   API/CLI   │ Manual price upsert/delete
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────┐
│  Service: bulk_upsert_prices()          │
│  • Parse Decimal values                 │
│  • Truncate to NUMERIC(18,6)            │
│  • DELETE existing + INSERT new         │
│  • Set source_plugin_key = "MANUAL"     │
└─────────────────────────────────────────┘
```

---

## 🧩 Core Components

### 1. Abstract Base Class: `AssetSourceProvider`

**File**: `backend/app/services/asset_source.py`

```python
class AssetSourceProvider(ABC):
    """Abstract base for all asset pricing providers."""
    
    @property
    @abstractmethod
    def provider_code(self) -> str:
        """Provider code (e.g., 'yfinance', 'cssscraper')"""
        pass
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable name"""
        pass
    
    @abstractmethod
    async def get_current_value(
        self, provider_params: dict, session: AsyncSession
    ) -> dict:
        """Fetch current price (latest available)"""
        pass
    
    @abstractmethod
    async def get_history_value(
        self, provider_params: dict, 
        start_date: date, end_date: date, 
        session: AsyncSession
    ) -> dict:
        """Fetch historical OHLC prices for date range"""
        pass
    
    async def search(self, query: str) -> list[dict]:
        """Search for assets (optional, raises NOT_SUPPORTED if unavailable)"""
        raise AssetSourceError("Search not supported", "NOT_SUPPORTED")
    
    def validate_params(self, params: dict) -> None:
        """Validate provider_params structure"""
        pass
```

**Provider Registration:**
```python
from backend.app.services.provider_registry import register_provider, AssetProviderRegistry

@register_provider(AssetProviderRegistry)
class YahooFinanceProvider(AssetSourceProvider):
    provider_code = "yfinance"
    provider_name = "Yahoo Finance"
    # ...
```

---

### 2. Manager Class: `AssetSourceManager`

**File**: `backend/app/services/asset_source.py`

**Design Pattern**: Bulk-first (all operations have bulk version as PRIMARY)

**Provider Assignment:**
- `bulk_assign_providers(assignments, session)` - PRIMARY
- `assign_provider(asset_id, code, params, session)` - calls bulk
- `bulk_remove_providers(asset_ids, session)` - PRIMARY
- `remove_provider(asset_id, session)` - calls bulk

**Price CRUD (Manual):**
- `bulk_upsert_prices(data, session)` - PRIMARY (delete + insert pattern)
- `upsert_prices(asset_id, prices, session)` - calls bulk
- `bulk_delete_prices(data, session)` - PRIMARY (complex WHERE with ranges)
- `delete_prices(asset_id, ranges, session)` - calls bulk

**Price Query:**
- `get_prices(asset_id, start, end, session)` - backward-fill + synthetic yield

**Price Refresh (Provider):**
- `bulk_refresh_prices(requests, session, concurrency, timeout)` - PRIMARY
  - Parallel async with `asyncio.Semaphore`
  - Prefetch DB + remote fetch in parallel
  - Per-item reporting (fetched_count, inserted_count, errors)
- `refresh_price(asset_id, start, end, session)` - calls bulk

---

### 3. Pydantic Schemas

**File**: `backend/app/schemas/assets.py` (Pydantic v2)

```python
class CurrentValueModel(BaseModel):
    value: Decimal
    currency: str
    as_of_date: date
    source: Optional[str] = None
    
    @field_validator("value", mode="before")
    @classmethod
    def parse_decimal(cls, v):
        return Decimal(str(v))

class PricePointModel(BaseModel):
    date: date
    open: Optional[Decimal] = None
    high: Optional[Decimal] = None
    low: Optional[Decimal] = None
    close: Decimal
    volume: Optional[Decimal] = None
    currency: Optional[str] = None
    backward_fill_info: Optional[BackwardFillInfo] = None
    
    @field_validator("open", "high", "low", "close", "volume", mode="before")
    @classmethod
    def parse_optional_decimal(cls, v):
        if v is None:
            return None
        return Decimal(str(v))

class HistoricalDataModel(BaseModel):
    prices: List[PricePointModel]
    currency: Optional[str] = None
    source: Optional[str] = None
```

**Shared Schema**: `BackwardFillInfo` (in `schemas/common.py`)

---

## 📊 Database Schema

### Table: `price_history`

```sql
CREATE TABLE price_history (
    id INTEGER PRIMARY KEY,
    asset_id INTEGER NOT NULL,
    date DATE NOT NULL,
    open NUMERIC(18, 6),
    high NUMERIC(18, 6),
    low NUMERIC(18, 6),
    close NUMERIC(18, 6),
    adjusted_close NUMERIC(18, 6),
    volume NUMERIC(18, 6),
    currency VARCHAR(3),
    source_plugin_key VARCHAR(50),
    fetched_at TIMESTAMP,
    UNIQUE(asset_id, date),
    FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE
);
```

### Table: `asset_provider_assignments`

```sql
CREATE TABLE asset_provider_assignments (
    id INTEGER PRIMARY KEY,
    asset_id INTEGER NOT NULL UNIQUE,
    provider_code VARCHAR(50) NOT NULL,
    provider_params TEXT,  -- JSON string
    last_fetch_at TIMESTAMP,
    fetch_interval INTEGER,  -- Minutes between fetches (NULL = default 1440 = 24h)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE
);
```

**Key Design:**
- **1-to-1 relationship**: One asset = one provider (UNIQUE constraint on asset_id)
- **JSON params**: Stored as TEXT (JSON string)
- **last_fetch_at**: Tracks last fetch attempt (NULL = never fetched)
- **fetch_interval**: Refresh frequency in minutes (NULL = default 24h, used by scheduled refresh system)

---

## 🎯 Design Principles

### 1. Bulk-First Architecture

All manager methods follow this pattern:
- **Bulk methods are PRIMARY** (optimized queries, minimal roundtrips)
- **Single methods call bulk** with 1 element (no code duplication)

Example:
```python
# PRIMARY (1 DELETE + 1 INSERT for all assets)
await AssetSourceManager.bulk_assign_providers([...], session)

# CONVENIENCE (calls bulk internally)
await AssetSourceManager.assign_provider(asset_id, code, params, session)
```

### 2. Provider Registry Pattern

- **Auto-discovery**: Scans `backend/app/services/asset_source_providers/` folder
- **Decorator registration**: `@register_provider(AssetProviderRegistry)`
- **Instance factory**: `AssetProviderRegistry.get_provider_instance(code)`
- **Shared with FX**: Same `AbstractProviderRegistry` base class

### 3. Synthetic Yield as Runtime Logic

**NOT a provider** because:
- Values change based on transaction history
- Calculated on-demand (no DB write)
- Automatically applied in `get_prices()` when `asset.valuation_model == SCHEDULED_YIELD`

**Why?**
- Providers fetch external data (cached)
- Synthetic values depend on internal state (always fresh)

### 4. Backward-Fill Strategy

Similar to FX system, but for asset prices:
- **Goal**: Fill gaps in price history using last known price
- **Use case**: Weekends, holidays, illiquid assets
- **Implementation**: Iterator pattern in `get_prices()`
- **Transparency**: `backward_fill_info` field indicates backfilled data

### 5. Database Precision

**Problem**: Python Decimal has arbitrary precision, database has fixed precision (18, 6)

**Solution**:
- `truncate_price_to_db_precision()` helper
- Prevents false update detection when re-fetching identical values
- Applied before all DB writes

### 6. Concurrency Control

**Challenge**: Fetching prices for 100 assets in parallel can overwhelm APIs

**Solution**:
- `asyncio.Semaphore` in `bulk_refresh_prices()`
- Configurable concurrency limit (default: 5)
- Timeout per item (default: 60s)

---

## ⚡ Performance Optimizations

### 1. Parallel Fetch + DB Prefetch

```python
# Run in parallel:
db_task = asyncio.create_task(_fetch_db_existing())
fetch_task = asyncio.create_task(_fetch_remote())

db_existing, remote_data = await asyncio.gather(db_task, fetch_task)
```

### 2. SQLite Upsert Pattern

```python
# Efficient upsert (no ON CONFLICT overhead):
await session.execute(delete(...).where(...))  # Remove existing
session.add_all([...])  # Bulk insert new
await session.commit()  # Single transaction
```

### 3. Batch Operations

```python
# Bad: N queries
for asset_id in asset_ids:
    await delete_provider(asset_id)

# Good: 1 query
await bulk_remove_providers(asset_ids)
```

---

## 🔍 Error Handling

### Exception Hierarchy

```python
class AssetSourceError(Exception):
    """Base exception for asset pricing errors"""
    def __init__(self, message: str, error_code: str, details: dict):
        self.message = message
        self.error_code = error_code
        self.details = details

# Usage in providers:
raise AssetSourceError(
    "No data available for ticker",
    "NO_DATA",
    {"ticker": "AAPL", "date": "2025-01-01"}
)
```

### Per-Item Error Reporting

`bulk_refresh_prices()` returns:
```python
[
    {
        "asset_id": 1,
        "fetched_count": 10,
        "inserted_count": 10,
        "updated_count": 0,
        "errors": []
    },
    {
        "asset_id": 2,
        "fetched_count": 0,
        "inserted_count": 0,
        "updated_count": 0,
        "errors": ["Provider fetch failed: Timeout"]
    }
]
```

**Benefit**: One failed asset doesn't block others

---

## 🧪 Testing Strategy

### Test Structure

```python
# Test pattern (from test_asset_source.py):
def test_something():
    """Test description."""
    print_section("Test N: Test Name")
    
    try:
        # Setup
        # Action
        # Assertions
        return {"passed": True, "message": "Success message"}
    except Exception as e:
        return {"passed": False, "message": f"Failed: {e}"}
```

### Test Coverage

1. **Helper Functions**: Precision, truncation, ACT/365 calculation
2. **Provider Assignment**: Bulk/single assign and remove
3. **Price CRUD**: Bulk/single upsert and delete
4. **Backward-Fill**: Gap filling logic
5. **Refresh**: Provider orchestration (smoke test)

**Command**: `pipenv run python -m backend.test_scripts.test_services.test_asset_source`

---

## 📝 Comparison: FX vs Asset Pricing

| Feature | FX System | Asset Pricing System |
|---------|-----------|---------------------|
| **Data Type** | Single rate (Decimal) | OHLC + volume |
| **Table** | `fx_rates` | `price_history` |
| **Lookup Key** | `(date, base, quote)` | `(date, asset_id)` |
| **Normalization** | Alphabetical (EUR/USD) | None |
| **Backward-Fill** | Yes | Yes |
| **Providers** | ECB, FED, BOE, SNB, etc. | yfinance, CSS scraper, etc. |
| **Registry** | `FXProviderRegistry` | `AssetProviderRegistry` |
| **Synthetic Data** | No | Yes (SCHEDULED_YIELD) |
| **Shared** | `BackwardFillInfo`, registry pattern | Same |

---

### 1. Advanced Scheduling

**Features**:
- Smart refresh based on `last_fetch_at` + `fetch_interval`
- Avoid redundant fetches for recently updated data
### 2. Provider Fallback

**Scenario**: Primary provider fails, fallback to secondary

**Implementation**:
### 2. Provider Fallback
# In asset_provider_assignments:
```
provider_code: "yfinance"
fallback_provider_code: "alpha_vantage"
```

### 4. Caching Layer

**Use case**: Repeated queries for same date range

**Solution**: Redis cache for frequently accessed price ranges
### 3. Caching Layer
---

## 📚 Related Documentation
**Solution**: In-memory cache (LRU) for frequently accessed price ranges
- [Provider Development Guide](./provider-development.md) - How to create new providers
- [FX Architecture](../fx/architecture.md) - Similar pattern for FX rates
- [Async Architecture](../async-architecture.md) - Understanding async patterns
- [Database Schema](../database-schema.md) - Complete DB schema reference

---

**Last Updated**: 2025-11-10  
**Version**: 1.0.0


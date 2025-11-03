# FX System Architecture

Detailed technical architecture of the LibreFolio FX system.

> 💡 **Want to understand async patterns?** See [Async Architecture Guide](../async-architecture.md)

---

## 🏗️ System Architecture

### Multi-Provider System

LibreFolio uses a **plugin-based provider architecture** to support multiple FX data sources:

```
      ┌──────────────────────────────────────────────┐
      │            Service Layer                     │
      │         (fx.py - orchestration)              │
      │                                              │
      │  • normalize_rate_for_storage()              │
      │  • ensure_rates_multi_source(provider, base) │
      │  • convert() / convert_bulk()                │
      └────────────────┬─────────────────────────────┘
                       │
                       ▼
      ┌────────────────────────────────────────────┐
      │           FXProviderFactory                │
      │       (provider registration)              │
      │                                            │
      │  • get_provider(code)                      │
      │  • get_all_providers() → metadata          │
      └──┬────────┬────────┬────────┬──────────────┘
         │        │        │        │
         ▼        ▼        ▼        ▼
      ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐
      │ ECB  │ │ FED  │ │ BOE  │ │ SNB  │
      │ EUR  │ │ USD  │ │ GBP  │ │ CHF  │
      │[EUR] │ │[USD] │ │[GBP] │ │[CHF] │ ← base_currencies
      └──────┘ └──────┘ └──────┘ └──────┘
         │        │        │        │
         └────────┴────────┴────────┘
                       │
                       ▼
            ┌───────────────────────┐
            │   Database (fx_rates) │
            │  Alphabetical storage │
            └───────────────────────┘
```

---

## 🔄 Data Flow

### 1. Rate Fetching Flow

```
┌─────────────┐
│   API/CLI   │ Request rates for date range + currencies
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────┐
│  Service: ensure_rates_multi_source()   │
│  • Validates provider + base_currency   │
│  • Calls provider.fetch_rates()         │
└──────┬──────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│  Provider: fetch_rates()                │
│  • HTTP call to central bank API        │
│  • Parse response (JSON/CSV)            │
│  • Apply multi-unit adjustment          │
│  • Return: [(date, base, quote, rate)]  │
└──────┬──────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│  Service: normalize_rate_for_storage()  │
│  • Enforce alphabetical: base < quote   │
│  • Invert rate if needed                │
└──────┬──────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│  Database: UPSERT fx_rates              │
│  • Constraint: unique(date,base,quote)  │
│  • Idempotent: safe to re-run           │
└─────────────────────────────────────────┘
```

### 2. Conversion Flow

```
┌─────────────┐
│   Request   │ Convert 100 USD to EUR on 2025-01-15
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────┐
│  Service: convert()                     │
│  • Identify conversion type             │
└──────┬──────────────────────────────────┘
       │
       ├─→ Identity (USD→USD): return amount
       │
       ├─→ Direct (EUR→USD): lookup EUR/USD rate
       │
       ├─→ Inverse (USD→EUR): lookup EUR/USD, invert
       │
       └─→ Cross (USD→GBP): USD→EUR→GBP (2 lookups)
```

---

## 🧩 Core Components

### 1. Abstract Base Class: `FXRateProvider`

**File**: `backend/app/services/fx.py`

```python
class FXRateProvider(ABC):
    """Abstract base for all FX providers."""
    
    @property
    @abstractmethod
    def code(self) -> str:
        """Provider code (e.g., 'ECB', 'FED')"""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name"""
        pass
    
    @property
    @abstractmethod
    def base_currency(self) -> str:
        """Primary base currency"""
        pass
    
    @property
    def base_currencies(self) -> list[str]:
        """All supported base currencies (for multi-base providers)"""
        return [self.base_currency]
    
    @property
    def multi_unit_currencies(self) -> set[str]:
        """Currencies quoted per 100 units (e.g., JPY, SEK)"""
        return set()
    
    @abstractmethod
    async def get_supported_currencies(self) -> list[str]:
        """Get list of supported currencies"""
        pass
    
    @abstractmethod
    async def fetch_rates(
        self,
        date_range: tuple[date, date],
        currencies: list[str],
        base_currency: str | None = None
    ) -> dict[str, list[tuple[date, str, str, Decimal]]]:
        """
        Fetch rates from provider API.
        
        Returns:
            dict mapping currency -> [(date, base, quote, rate), ...]
            
        Rate semantics: 1 base = rate × quote
        """
        pass
```

---

### 2. Provider Factory: `FXProviderFactory`

**File**: `backend/app/services/fx.py`

**Purpose**: Registry and instantiation of providers

**Methods**:
- `register(provider_class)` - Register a provider (auto-called on import)
- `get_provider(code)` - Get provider instance by code
- `get_all_providers()` - Get metadata for all providers
- `is_registered(code)` - Check if provider exists

**Example**:
```python
# Get provider
provider = FXProviderFactory.get_provider('ECB')

# List all
providers = FXProviderFactory.get_all_providers()
# [{'code': 'ECB', 'name': '...', 'base_currencies': ['EUR'], ...}, ...]
```

---

### 3. Service Layer Functions

#### `normalize_rate_for_storage(base, quote, rate)`

**Purpose**: Enforce alphabetical storage (base < quote)

**Example**:
```python
# EUR/USD: already alphabetical
normalize_rate_for_storage('EUR', 'USD', Decimal('1.08'))
# → ('EUR', 'USD', Decimal('1.08'))

# USD/EUR: needs inversion
normalize_rate_for_storage('USD', 'EUR', Decimal('0.93'))
# → ('EUR', 'USD', Decimal('1.075...'))  # inverted
```

---

#### `ensure_rates_multi_source(session, date_range, currencies, provider_code, base_currency)`

**Purpose**: Orchestrate rate fetching from any provider

**Flow**:
1. Get provider from factory
2. Validate base_currency (if specified)
3. Fetch rates from provider
4. Normalize for storage
5. Batch upsert to database

**Returns**:
```python
{
    'provider': 'ECB',
    'base_currency': 'EUR',
    'total_fetched': 100,
    'total_changed': 50,
    'currencies_synced': ['USD', 'GBP']
}
```

---

#### `convert(session, amount, from_currency, to_currency, as_of_date)`

**Purpose**: Convert amount between currencies

**Strategies**:
- **Identity**: USD→USD (return as-is)
- **Direct**: EUR→USD (lookup EUR/USD)
- **Inverse**: USD→EUR (lookup EUR/USD, invert)
- **Cross**: USD→GBP (USD→EUR→GBP via pivot)

**Backward-fill**: If no rate for exact date, searches backward in time for most recent past rate

---

## 🗄️ Database Schema

### `fx_rates` Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Primary key |
| `date` | DATE | Rate date |
| `base` | VARCHAR | Base currency (ISO 4217) |
| `quote` | VARCHAR | Quote currency (ISO 4217) |
| `rate` | DECIMAL(18,6) | Exchange rate: 1 base = rate × quote |
| `source` | VARCHAR | Provider code ("ECB", "FED", "BOE", "SNB") |
| `fetched_at` | DATETIME | Fetch timestamp |

**Constraints**:
- `UNIQUE (date, base, quote)` - One rate per day per pair
- `CHECK (base < quote)` - Alphabetical ordering enforced

**Why alphabetical?**
- Prevents duplicates (EUR/USD vs USD/EUR)
- Reduces storage (one record per pair)
- Inverse computed on-the-fly: `1/rate`

---

### `fx_currency_pair_sources` Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Primary key |
| `base` | VARCHAR | Base currency |
| `quote` | VARCHAR | Quote currency |
| `provider` | VARCHAR | Preferred provider code |

**Purpose**: Configure which provider to use for each currency pair

**Example**:
```sql
-- Use FED for USD-based pairs
INSERT INTO fx_currency_pair_sources (base, quote, provider)
VALUES ('USD', 'EUR', 'FED');

-- Use ECB for EUR-based pairs
INSERT INTO fx_currency_pair_sources (base, quote, provider)
VALUES ('EUR', 'GBP', 'ECB');
```

---

## 🔧 Multi-Base Currency Support

### Single-Base Providers (Current)

All current providers (ECB, FED, BOE, SNB) are **single-base**:

```python
@property
def base_currencies(self) -> list[str]:
    return [self.base_currency]  # Only one base

async def fetch_rates(self, ..., base_currency: str | None = None):
    # Validate: must be None or match self.base_currency
    if base_currency is not None and base_currency != self.base_currency:
        raise ValueError(f"Only {self.base_currency} supported")
```

---

### Multi-Base Providers (Future)

Commercial APIs may support multiple base currencies:

```python
class MultiBaseProvider(FXRateProvider):
    @property
    def base_currency(self) -> str:
        return "USD"  # Default
    
    @property
    def base_currencies(self) -> list[str]:
        return ["EUR", "GBP", "USD"]  # Multiple!
    
    async def fetch_rates(self, ..., base_currency: str | None = None):
        actual_base = base_currency or self.base_currency
        
        # Validate
        if actual_base not in self.base_currencies:
            raise ValueError(f"Base {actual_base} not supported")
        
        # Fetch with specified base
        # ...
```

**Usage**:
```python
# Fetch with EUR as base
await ensure_rates_multi_source(
    session, date_range, ["JPY", "CHF"],
    provider_code="MULTI",
    base_currency="EUR"  # Explicit choice
)
```

---

## 🎯 Multi-Unit Currencies

Some central banks quote certain currencies **per 100 units** instead of per 1 unit.

**Common multi-unit currencies**: JPY, SEK, NOK, DKK

**Example** (SNB):
- API returns: `100 JPY = 0.67 CHF`
- Provider adjusts: `1 JPY = 0.0067 CHF`
- Stored as: `CHF/JPY = 149.25` (inverted + alphabetical)

**Implementation**:
```python
@property
def multi_unit_currencies(self) -> set[str]:
    return {'JPY', 'SEK', 'NOK', 'DKK'}

async def fetch_rates(self, ...):
    # API gives rate per 100 units
    api_rate = Decimal("0.67")  # 100 JPY = 0.67 CHF
    
    # Adjust to per-1-unit
    if currency in self.multi_unit_currencies:
        rate_value = api_rate / Decimal("100")  # 1 JPY = 0.0067 CHF
    
    return (date, 'CHF', 'JPY', rate_value)
```

---

## 📊 Testing Architecture

Tests organized in 4 layers:

### 1. External Services (Provider Tests)
- No server required
- Real API calls to central banks
- Validates provider implementation
- **File**: `backend/test_scripts/test_external/test_fx_providers.py`

### 2. Database Layer (Persistence Tests)
- No server required
- Tests storage and constraints
- Idempotency validation
- **File**: `backend/test_scripts/test_db/test_fx_rates_persistence.py`

### 3. Service Layer (Conversion Tests)
- No server required
- Tests conversion algorithms
- Forward-fill logic
- **File**: `backend/test_scripts/test_services/test_fx_conversion.py`

### 4. API Layer (Endpoint Tests)
- Requires running server
- Tests REST API
- **File**: `backend/test_scripts/test_api/test_fx_api.py`

---

## 🔗 Related Documentation

- **[Available Providers](./providers.md)** - ECB, FED, BOE, SNB details
- **[Provider Development Guide](./provider-development.md)** - How to add new providers
- **[API Reference](./api-reference.md)** - REST API endpoints
- **[Database Schema](../database-schema.md)** - Full database documentation
- **[Testing Guide](../testing-guide.md)** - How to run tests


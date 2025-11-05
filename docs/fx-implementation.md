# FX (Foreign Exchange) System

Complete guide to the LibreFolio FX rate system.

> 🎯 **Quick Start**: [API Reference](./fx/api-reference.md) | [Available Providers](./fx/providers.md) | [Add New Provider](./fx/provider-development.md)

---

## 📋 What is the FX System?

The **FX (Foreign Exchange) system** in LibreFolio handles everything related to currency exchange rates:

- 💱 **Fetching rates** from multiple central banks (ECB, FED, BOE, SNB)
- 💾 **Storing rates** in database with smart deduplication
- 🔄 **Converting amounts** between any currencies
- 🌐 **REST API** for frontend/external integrations
- 🔌 **Plugin architecture** to add new data sources

---

## ✨ Key Features

### 🏦 Multi-Provider Support

Access rates from **4 central banks**:

| Provider | Base Currency | Coverage | Multi-Unit |
|----------|---------------|----------|------------|
| **ECB** (European Central Bank) | EUR | 45+ currencies | No |
| **FED** (Federal Reserve) | USD | 20+ currencies | No |
| **BOE** (Bank of England) | GBP | 15+ currencies | No |
| **SNB** (Swiss National Bank) | CHF | 10+ currencies | ✅ Yes |

📖 **[See all providers →](./fx/providers.md)**

---

### 🔄 Smart Currency Conversion

Automatically handles multiple conversion strategies:

- **Identity**: USD → USD (instant)
- **Direct**: EUR → USD (single lookup)
- **Inverse**: USD → EUR (inverts EUR/USD)
- **Cross-currency**: USD → GBP (via EUR pivot)

**Backward-fill**: Missing rates? Uses most recent available from past dates.

---

### 🎯 Multi-Base Currency Ready

Current providers are **single-base** (ECB=EUR, FED=USD, etc.).

Future providers can support **multiple base currencies**:
```python
# Example: commercial API with EUR, GBP, USD bases
await sync_rates(
    currencies=['JPY', 'CHF'],
    provider='COMMERCIAL_API',
    base_currency='EUR'  # Choose which base to use
)
```

---

### 📊 Storage Optimization

**Alphabetical ordering**: `base < quote` alphabetically
- Prevents duplicates (EUR/USD vs USD/EUR)
- One record per pair
- Inverse computed on-fly: `1/rate`

**Example**:
```sql
-- Stored as EUR/USD (E < U)
INSERT INTO fx_rates (date, base, quote, rate)
VALUES ('2025-01-15', 'EUR', 'USD', 1.0850);
-- Means: 1 EUR = 1.0850 USD

-- To get USD → EUR: 1 / 1.0850 = 0.9217 EUR
```

---

## 🚀 Quick Start

Ready to start using the FX system?

📖 **[Go to API Reference →](./fx/api-reference.md)**

The API Reference includes:
- ✅ Complete endpoint documentation
- ✅ Step-by-step examples with `curl`
- ✅ Request/response formats
- ✅ Error handling
- ✅ Best practices

**Or use interactive Swagger UI**: Start the server and visit `http://localhost:8000/docs` to try API calls directly in your browser!

---

## 📚 Documentation Structure

### 🎓 Getting Started

- **[API Reference](./fx/api-reference.md)** - REST endpoints, examples, best practices
- **[Available Providers](./fx/providers.md)** - ECB, FED, BOE, SNB details

### 🔧 Technical

- **[Architecture](./fx/architecture.md)** - System design, data flow, components
- **[Provider Development](./fx/provider-development.md)** - How to add new providers

### 🧪 Testing

- **[Testing Guide](./testing-guide.md)** - How to run FX tests
- **[Async Architecture](./async-architecture.md)** - Understanding async patterns

---

## 🗄️ Database Schema

### `fx_rates` - Exchange Rates

Stores daily exchange rates from providers.

| Column | Type | Description |
|--------|------|-------------|
| `date` | DATE | Rate date |
| `base` | VARCHAR | Base currency (ISO 4217) |
| `quote` | VARCHAR | Quote currency (ISO 4217) |
| `rate` | DECIMAL | 1 base = rate × quote |
| `source` | VARCHAR | Provider code (ECB, FED, BOE, SNB) |

**Constraints**:
- `UNIQUE (date, base, quote)` - One rate per day per pair
- `CHECK (base < quote)` - Alphabetical ordering

---

### `fx_currency_pair_sources` - Provider Configuration

Configure which provider to use for each currency pair.

| Column | Type | Description |
|--------|------|-------------|
| `base` | VARCHAR | Base currency |
| `quote` | VARCHAR | Quote currency |
| `provider` | VARCHAR | Preferred provider |

**Example**:
```sql
-- Use FED for USD/EUR
INSERT INTO fx_currency_pair_sources (base, quote, provider)
VALUES ('EUR', 'USD', 'FED');
```

📖 **[Full Schema Documentation →](./database-schema.md)**



---

## 🧪 Testing

The FX system has comprehensive test coverage across all layers:

- **External Services** - Test real API calls to providers
- **Database Layer** - Test persistence and constraints  
- **Service Layer** - Test conversion algorithms
- **API Layer** - Test REST endpoints

📖 **[Full Testing Guide →](./testing-guide.md)**

**Quick test commands:**
```bash
# Test all FX providers
./test_runner.py external all

# Test FX database persistence
./test_runner.py db fx-rates

# Test conversion logic
./test_runner.py services fx

# Test API endpoints (requires server)
./test_runner.py api fx
```

---

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PORTFOLIO_BASE_CURRENCY` | Base currency for portfolio calculations | `EUR` |

📖 **[Full Configuration Guide →](./environment-variables.md)**

---

## 🔍 Troubleshooting

**Problem:** No rates found for conversion  
**Solution:** Sync rates first: `POST /api/v1/fx/sync/bulk?start=...&end=...&currencies=...`

**Problem:** "Unknown FX provider"  
**Solution:** Valid providers: ECB, FED, BOE, SNB. Check [Available Providers](./fx/providers.md)

**Problem:** "Provider does not support base currency"  
**Solution:** Current providers are single-base. Check [Architecture](./fx/architecture.md#multi-base-currency-support)

**Problem:** Forward-fill applied unexpectedly  
**Explanation:** Normal for weekends/holidays. System uses most recent available rate.

**Problem:** Multi-unit currency rates incorrect (JPY)  
**Solution:** Use SNB provider for correct multi-unit handling. See [Providers](./fx/providers.md#-snb---swiss-national-bank)

📖 **[More troubleshooting →](./fx/architecture.md)**

---

## 🔧 Advanced Features

### Multi-Base Currency Support

The FX system supports providers with multiple base currencies through the `base_currencies` property.

#### Current Providers (Single-Base)

All current providers support a single base currency:

```python
# ECB (European Central Bank)
base_currencies = ["EUR"]  # Only EUR as base

# FED (Federal Reserve)
base_currencies = ["USD"]  # Only USD as base

# BOE (Bank of England)
base_currencies = ["GBP"]  # Only GBP as base

# SNB (Swiss National Bank)
base_currencies = ["CHF"]  # Only CHF as base
```

#### Future: Multi-Base Providers

Future providers (e.g., commercial APIs) can support multiple bases:

```python
class HypotheticalMultiBaseProvider(FXRateProvider):
    @property
    def base_currencies(self) -> list[str]:
        return ["EUR", "USD", "GBP"]  # Multiple bases supported
    
    async def fetch_rates(
        self,
        date_range: tuple[date, date],
        currencies: list[str],
        base_currency: str | None = None
    ) -> dict[str, list[tuple[date, str, str, Decimal]]]:
        # base_currency parameter selects which base to use
        if base_currency not in self.base_currencies:
            raise ValueError(f"Unsupported base: {base_currency}")
        
        # Fetch rates with selected base...
```

#### When to Use `base_currency` Parameter

**Current behavior** (single-base providers):
```bash
# base_currency is ignored (provider has only one base)
curl -X POST ".../sync/bulk?currencies=USD,GBP&provider=ECB"
# Uses EUR (ECB's only base)
```

**Future behavior** (multi-base providers):
```bash
# Specify which base to use
curl -X POST ".../sync/bulk?currencies=JPY,CHF&provider=MULTI&base_currency=EUR"
# Fetches EUR/JPY and EUR/CHF

curl -X POST ".../sync/bulk?currencies=JPY,CHF&provider=MULTI&base_currency=USD"
# Fetches USD/JPY and USD/CHF (different rates!)
```

**Use cases**:
- Commercial APIs with flexible base selection
- Providers that quote rates differently based on base
- Future optimization: choose base closest to your portfolio's native currency

---

### Auto-Configuration System

The `fx_currency_pair_sources` table enables **automated provider selection** for currency pairs.

#### Configuration Table

```sql
CREATE TABLE fx_currency_pair_sources (
    id INTEGER PRIMARY KEY,
    base VARCHAR(3) NOT NULL,
    quote VARCHAR(3) NOT NULL,
    provider_code VARCHAR(10) NOT NULL,
    priority INTEGER NOT NULL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    UNIQUE(base, quote, priority)
);
```

**Fields**:
- `base`, `quote`: Currency pair (e.g., EUR/USD)
- `provider_code`: Which provider to use (ECB, FED, BOE, SNB)
- `priority`: Provider priority (1 = primary, 2+ = fallback)

#### How It Works

**1. Configure pairs** (one-time setup):
```bash
curl -X POST "http://localhost:8000/api/v1/fx/pair-sources/bulk" \
  -H "Content-Type: application/json" \
  -d '{
    "sources": [
      {"base": "EUR", "quote": "USD", "provider_code": "ECB", "priority": 1},
      {"base": "GBP", "quote": "USD", "provider_code": "BOE", "priority": 1}
    ]
  }'
```

**2. Sync without specifying provider**:
```bash
# System automatically uses configured providers
curl -X POST "http://localhost:8000/api/v1/fx/sync/bulk?start=2025-01-01&end=2025-01-31&currencies=USD,EUR,GBP"
# EUR/USD → uses ECB (from config)
# GBP/USD → uses BOE (from config)
```

#### Inverse Pairs Support

EUR/USD and USD/EUR are **semantically different** and can coexist with different providers:

```bash
# Configure both directions
curl -X POST ".../pair-sources/bulk" -d '{
  "sources": [
    {"base": "EUR", "quote": "USD", "provider_code": "ECB", "priority": 1},
    {"base": "USD", "quote": "EUR", "provider_code": "FED", "priority": 1}
  ]
}'
# EUR → USD conversions use ECB (EUR base)
# USD → EUR conversions use FED (USD base)
```

**Constraint**: Inverse pairs **cannot have same priority** (would cause ambiguity).

✅ **Valid**: EUR/USD priority=1, USD/EUR priority=2  
❌ **Invalid**: EUR/USD priority=1, USD/EUR priority=1 (conflict!)

#### Benefits

- ✅ **No provider parameter needed**: Sync just specifies currencies
- ✅ **Centralized configuration**: Change provider without code changes
- ✅ **Per-pair optimization**: Use best provider for each currency pair
- ✅ **Fallback support**: Multiple priorities enable automatic retry

---

### Provider Fallback Logic

Configure **multiple priorities** per pair to enable automatic fallback on failures.

#### Configuration Example

```bash
# Primary: ECB, Fallback: FED
curl -X POST ".../pair-sources/bulk" -d '{
  "sources": [
    {"base": "EUR", "quote": "USD", "provider_code": "ECB", "priority": 1},
    {"base": "EUR", "quote": "USD", "provider_code": "FED", "priority": 2}
  ]
}'
```

#### Fallback Behavior

When syncing EUR/USD:

1. **Try priority=1** (ECB):
   - ✅ Success → use ECB rates
   - ❌ Failure (API error, connection timeout) → try fallback

2. **Try priority=2** (FED):
   - ✅ Success → use FED rates
   - ❌ Failure → try next priority (if exists)

3. **All failed** → return error to user

**Logging**:
```
INFO: Syncing EUR/USD using ECB (priority=1)...
WARNING: ECB failed: Connection timeout
INFO: Trying fallback: FED (priority=2)...
INFO: FED succeeded: 31 rates synced
```

#### Use Cases

- **Redundancy**: Continue working if one provider has downtime
- **Data quality**: Fall back to alternative if primary data is stale
- **Coverage**: Primary for common dates, fallback for historical gaps
- **Testing**: Try new provider as fallback before making it primary

#### Performance

- ⚡ **Fast path**: Only calls primary provider if successful (no redundant API calls)
- 🔄 **Retry logic**: Automatic retry on provider-level errors (not HTTP 4xx client errors)
- 📊 **Merge results**: Can use different providers for different currency pairs in single sync

---

### Rate Management

The system provides comprehensive rate management with DELETE operations.

#### DELETE Operations

Delete rates for specific currency pairs and date ranges:

```bash
# Delete single day
curl -X DELETE ".../rate-set/bulk" -d '{
  "deletions": [{
    "from": "EUR",
    "to": "USD",
    "start_date": "2025-01-15"
  }]
}'

# Delete range
curl -X DELETE ".../rate-set/bulk" -d '{
  "deletions": [{
    "from": "EUR",
    "to": "USD",
    "start_date": "2025-01-01",
    "end_date": "2025-01-31"
  }]
}'
```

#### Chunked Deletion Strategy

**Problem**: SQLite has limits on SQL statement complexity (typically ~1000 parameters).

**Solution**: Chunked deletion in batches of **500 IDs**.

**Example** (deleting 10,000 rates):
```python
# Backend automatically chunks into 20 batches
# Batch 1: DELETE FROM fx_rates WHERE id IN (1, 2, ..., 500)
# Batch 2: DELETE FROM fx_rates WHERE id IN (501, 502, ..., 1000)
# ... 
# Batch 20: DELETE FROM fx_rates WHERE id IN (9501, ..., 10000)
```

**Performance**:
- ⚡ **Fast**: ~0.5ms per batch (500 IDs)
- 🔄 **Transactional**: All batches in single transaction (all-or-nothing)
- 📊 **Scalable**: Can delete millions of rates efficiently

#### Idempotency Guarantees

All DELETE operations are **idempotent**:

```bash
# First call: Deletes 31 rates
curl -X DELETE ".../rate-set/bulk" -d '{"deletions": [...]}'
# Response: {"deleted_count": 31}

# Second call: No rates to delete
curl -X DELETE ".../rate-set/bulk" -d '{"deletions": [...]}'
# Response: {"deleted_count": 0, "message": "No rates found"}
```

**Safe to**:
- Re-run failed deletions
- Include non-existent pairs in bulk requests
- Delete already-deleted ranges

#### Integration with Backward-Fill

After deleting rates, conversions automatically use **backward-fill**:

**Before DELETE**:
```sql
-- Rates exist for every day
2025-01-14: EUR/USD = 1.0850
2025-01-15: EUR/USD = 1.0855  ← Exact match
2025-01-16: EUR/USD = 1.0860
```

**After DELETE** (deleted 2025-01-15):
```sql
-- Rate missing for 2025-01-15
2025-01-14: EUR/USD = 1.0850
-- (gap)
2025-01-16: EUR/USD = 1.0860
```

**Conversion for 2025-01-15**:
```json
{
  "conversion_date": "2025-01-15",
  "rate": "1.0850",
  "rate_date": "2025-01-14",
  "backward_fill_info": {
    "actual_rate_date": "2025-01-14",
    "days_back": 1
  }
}
```

**Use cases**:
- Correct erroneous rates by deleting and re-syncing
- Remove test data without breaking conversions
- Archive old rates while maintaining conversion capability

---

## 🛠️ Developing New Providers

Want to add support for a new central bank or data source?

📘 **[Provider Development Guide →](./fx/provider-development.md)**

**Problem:** Backward-fill applied unexpectedly  
**Explanation:** Normal for weekends/holidays. System uses most recent available rate from past dates.
- ✅ Copy-paste ready template
- ✅ Required methods explanation
- ✅ Multi-base provider examples
- ✅ Testing instructions

**Quick reference examples:**
- Simple: `backend/app/services/fx_providers/boe.py`
- Dynamic list: `backend/app/services/fx_providers/ecb.py`
- Multi-unit: `backend/app/services/fx_providers/snb.py`

---

## 📚 Related Documentation

### Core Documentation
- **[Architecture](./fx/architecture.md)** - System design and data flow
- **[API Reference](./fx/api-reference.md)** - Complete REST API docs
- **[Providers](./fx/providers.md)** - ECB, FED, BOE, SNB details
- **[Provider Development](./fx/provider-development.md)** - Add new providers

### General Documentation
- **[Testing Guide](./testing-guide.md)** - How to run and write tests
- **[Async Architecture](./async-architecture.md)** - Understanding async patterns
- **[Database Schema](./database-schema.md)** - Full database documentation
- **[API Development Guide](./api-development-guide.md)** - How endpoints are built
- **[Environment Variables](./environment-variables.md)** - Configuration options


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


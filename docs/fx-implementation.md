# FX (Foreign Exchange) Implementation

This document describes the FX rate system implementation for LibreFolio.

---

## 📋 Overview

The FX system provides:
- **Currency rate fetching** from ECB (European Central Bank) API
- **Persistent storage** in SQLite database with alphabetical base/quote ordering
- **Currency conversion** with forward-fill logic
- **REST API endpoints** for frontend integration

---

## 🗄️ Database Schema

### `fx_rates` Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Primary key |
| `date` | DATE | Rate date (no intraday data) |
| `base` | VARCHAR | Base currency (ISO 4217) |
| `quote` | VARCHAR | Quote currency (ISO 4217) |
| `rate` | DECIMAL(18,6) | Exchange rate: **1 base = rate × quote** |
| `source` | VARCHAR | Data source (default: "ECB") |
| `fetched_at` | DATETIME | Timestamp of fetch |

**Constraints:**
- **UNIQUE** (`date`, `base`, `quote`) - One rate per day per pair
- **CHECK** (`base` < `quote`) - Alphabetical ordering to prevent duplicates

**Example:**
```sql
-- Stored as EUR/USD (alphabetically: EUR < USD)
date: 2025-01-15, base: EUR, quote: USD, rate: 1.0850
-- Meaning: 1 EUR = 1.0850 USD

-- Stored as CHF/EUR (alphabetically: CHF < EUR)
date: 2025-01-15, base: CHF, quote: EUR, rate: 1.0650
-- Meaning: 1 CHF = 1.0650 EUR
```

**Why alphabetical ordering?**
- Prevents duplicate pairs (EUR/USD and USD/EUR)
- Reduces storage (only one record per pair)
- Inverse rate computed on-the-fly: `1/rate`

---

## 🔧 Backend Components

### 1. Service Layer: `backend/app/services/fx.py`

**`get_available_currencies() -> list[str]`**
- Fetches list of available currencies from ECB API
- Returns ISO 4217 currency codes

**`ensure_rates(session, date_range, currencies) -> int`**
- Fetches missing rates from ECB for specified date range and currencies
- ECB provides: 1 EUR = X {currency}
- Converts to alphabetical storage format
- Returns number of new rates inserted
- Idempotent: safe to call multiple times

**`convert(session, amount, from_currency, to_currency, as_of_date) -> Decimal`**
- Converts amount between currencies
- Handles:
  - **Identity**: Same currency → return amount unchanged
  - **Direct**: Stored pair → apply rate
  - **Inverse**: Reverse pair → apply `1/rate`
  - **Cross-currency**: Convert via intermediate (typically EUR)
- **Forward-fill**: Uses most recent rate if exact date unavailable (with warning log)

### 2. API Layer: `backend/app/api/v1/fx.py`

**`GET /api/v1/fx/currencies`**
- Returns list of available currencies from ECB
- Response: `{ currencies: [...], count: N }`

**`POST /api/v1/fx/sync`**
- Syncs FX rates for specified date range and currencies
- Query params: `start`, `end`, `currencies` (comma-separated)
- Response: `{ synced: N, date_range: [...], currencies: [...] }`

**`GET /api/v1/fx/convert`**
- Converts amount between currencies
- Query params: `amount`, `from`, `to`, `date` (optional, defaults to today)
- Response: `{ amount, from_currency, to_currency, converted_amount, rate, rate_date }`

---

## 🌐 ECB API Parameters

LibreFolio fetches currency exchange rates from the **European Central Bank (ECB) Statistical Data Warehouse** API.

### Official Documentation

- **ECB SDW Web Services**: https://data.ecb.europa.eu/help/api/overview
- **Data Navigation Tree**: https://data.ecb.europa.eu/data/datasets (explore available datasets)
- **SDMX 2.1 RESTful API**: https://github.com/sdmx-twg/sdmx-rest

### URL Structure

```
/data/{dataset}/{frequency}.{currency}.{reference_area}.{series}.{exr_type}
```

**Example:**
```
https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A
```

This fetches daily spot rates for USD against EUR (1 EUR = X USD).

### Parameter Explanation

| Parameter | Value in LibreFolio | Description | Other Options |
|-----------|---------------------|-------------|---------------|
| **dataset** | `EXR` | Exchange Rates dataset | `ICP` (prices), `MNA` (national accounts), etc. |
| **frequency** | `D` | Daily frequency | `M` (monthly), `Q` (quarterly), `A` (annual) |
| **currency** | `USD`, `GBP`, etc. | Target currency code (ISO 4217) | Any ECB-supported currency (~45 available) |
| **reference_area** | `EUR` | Base/reference currency | Typically EUR for exchange rates |
| **series** | `SP00` | Series variation - Spot rate | `SP00` (spot), other variations for averages |
| **exr_type** | `A` | Exchange rate type - Average | `A` (average), `E` (end of period) |

### Query Parameters

When fetching data, we use these query parameters:

| Parameter | Description | Example |
|-----------|-------------|---------|
| `format` | Response format | `jsondata` (JSON), `csvdata` (CSV) |
| `startPeriod` | Start date (ISO 8601) | `2025-01-01` |
| `endPeriod` | End date (ISO 8601) | `2025-01-31` |
| `detail` | Detail level | `dataonly` (data only), `full` (with metadata) |
| `lastNObservations` | Last N observations | `1` (latest only), `30` (last 30 days) |

### Example API Call

**Fetch USD/EUR rates for January 2025:**
```
GET https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A
    ?format=jsondata
    &startPeriod=2025-01-01
    &endPeriod=2025-01-31
```

**Response structure:**
```json
{
  "dataSets": [{
    "series": {
      "0:0:0:0:0": {
        "observations": {
          "0": [1.0850],  // 2025-01-01: 1 EUR = 1.0850 USD
          "1": [1.0875],  // 2025-01-02: 1 EUR = 1.0875 USD
          ...
        }
      }
    }
  }],
  "structure": {
    "dimensions": {
      "observation": [{
        "id": "TIME_PERIOD",
        "values": [
          {"id": "2025-01-01"},
          {"id": "2025-01-02"},
          ...
        ]
      }]
    }
  }
}
```

### How LibreFolio Uses ECB API

1. **Fetch available currencies**: Query all series to get list of supported currencies
2. **Fetch rates**: For each currency, fetch daily rates for specified date range
3. **Parse response**: Extract date and rate from observations
4. **Transform**: Convert ECB format (1 EUR = X currency) to alphabetical storage format
5. **Persist**: Store in database with deduplication

**Code reference:** See `backend/app/services/fx.py` for implementation details.

---

## 🧪 Testing Structure

Tests are organized into **4 logical categories**: External Services → Database → Backend Services → API Endpoints

### External Services Tests (No server required)

**1. ECB API Connection** (`test_external/test_ecb_api.py`)
```bash
python test_runner.py external ecb
```
- Verifies connection to ECB API
- Checks availability of common currencies (USD, GBP, CHF, JPY, etc.)
- Tests data format and API response

**Run all external tests:**
```bash
python test_runner.py external all
```

### Database Tests (No server required)

**2. FX Rates Persistence** (`test_db/test_fx_rates_persistence.py`)
```bash
python test_runner.py db fx-rates
```
- Fetches rates from ECB API
- Persists to database
- Verifies idempotency (no duplicates on re-sync)
- Tests database constraints (unique, check)

**Mock Data Population** (`test_db/populate_mock_data.py`)
```bash
python test_runner.py db populate
```
- Populates database with comprehensive MOCK DATA
- Useful for frontend development and testing
- Includes: brokers, assets, transactions, FX rates (30 days)

**Run all DB tests:**
```bash
python test_runner.py db all         # All DB tests (create → validate → fx-rates → populate)
```

### Backend Services Tests (No server required)

**3. FX Conversion Logic** (`test_services/test_fx_conversion.py`)
```bash
python test_runner.py services fx
```
- Identity conversion (EUR→EUR)
- Direct conversion (EUR→USD using stored rate)
- Inverse conversion (USD→EUR using 1/rate)
- Roundtrip verification (EUR→USD→EUR ≈ original)
- Cross-currency (USD→GBP via EUR)
- Forward-fill (future date uses latest available rate)
- Error handling (missing rate raises exception)

**Run all services tests:**
```bash
python test_runner.py services all
```

### API Tests (Requires running server)

**4. FX API Endpoints** (`test_api/test_fx_api.py`)
```bash
# Start server first
./dev.sh server

# In another terminal
python test_runner.py api fx
```

Tests:
- `GET /fx/currencies` - List available currencies
- `POST /fx/sync` - Sync rates (with idempotency check)
- `GET /fx/convert` - Convert amounts (identity, roundtrip)
- Error handling (missing rates, invalid inputs)
- Validation (negative amounts, invalid date ranges)

**Run all API tests:**
```bash
python test_runner.py api all
```

### Run ALL Tests (Optimal Order)

```bash
python test_runner.py all
```

Executes all test categories in optimal order:
1. External Services (ECB API)
2. Database Layer (schema, persistence, mock data)
3. Backend Services (conversion logic)
4. API Endpoints (skipped if server not running)

---

## 🌐 ECB API Integration

**Data Source:** European Central Bank (ECB)  
**Base URL:** `https://data-api.ecb.europa.eu/service/data`  
**Dataset:** `EXR` (Exchange Rates)  
**Frequency:** Daily (`D`)  
**Reference:** EUR (all rates vs EUR)

**Example API Call:**
```
GET https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A
  ?format=jsondata
  &startPeriod=2025-01-01
  &endPeriod=2025-01-31
```

Returns: Daily USD/EUR rates (1 EUR = X USD)

**No API Key Required** ✅

---

## 📊 Usage Examples

### Backend Service Usage

```python
from backend.app.services.fx import ensure_rates, convert, get_available_currencies
from datetime import date

# 1. Get available currencies
currencies = await get_available_currencies()
print(currencies)  # ['AUD', 'BGN', 'BRL', ..., 'USD', 'ZAR']

# 2. Fetch rates for last 30 days
await ensure_rates(
    session,
    date_range=(date(2025, 1, 1), date(2025, 1, 31)),
    currencies=["USD", "GBP", "CHF"]
)

# 3. Convert 100 USD to EUR
eur_amount = convert(
    session,
    amount=Decimal("100.00"),
    from_currency="USD",
    to_currency="EUR",
    as_of_date=date(2025, 1, 15)
)
print(f"100 USD = {eur_amount} EUR")  # ~92.17 EUR
```

### API Usage (Frontend)

```javascript
// 1. Get available currencies
const response = await fetch('/api/v1/fx/currencies');
const { currencies } = await response.json();

// 2. Sync rates
await fetch('/api/v1/fx/sync?start=2025-01-01&end=2025-01-31&currencies=USD,GBP', {
  method: 'POST'
});

// 3. Convert currency
const response = await fetch('/api/v1/fx/convert?amount=100&from=USD&to=EUR&date=2025-01-15');
const { converted_amount } = await response.json();
console.log(`100 USD = ${converted_amount} EUR`);
```

---

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PORTFOLIO_BASE_CURRENCY` | Base currency for portfolio calculations | `EUR` |

See [Environment Variables](./environment-variables.md) for more details.

---

## 🔍 Troubleshooting

**Problem:** No rates found for conversion  
**Solution:** Run sync first: `POST /api/v1/fx/sync?start=...&end=...&currencies=...`

**Problem:** ECB API timeout  
**Solution:** Check internet connection. ECB API is public and doesn't require authentication.

**Problem:** Forward-fill warnings in logs  
**Explanation:** This is expected behavior when requesting rates for future dates or weekends. The system uses the most recent available rate.

**Problem:** "base < quote" constraint violation  
**Explanation:** Always store pairs alphabetically. The conversion service handles this automatically.

---

## 📚 Related Documentation

- [Database Schema](./database-schema.md) - Full database documentation
- [Environment Variables](./environment-variables.md) - Configuration options
- [Alembic Guide](./alembic-guide.md) - Database migrations

---

**Next Steps:**
- Implement scheduler for automatic nightly rate sync (Step 08)
- Add caching layer for frequently used conversions (future optimization)
- Support additional data sources beyond ECB (future enhancement)


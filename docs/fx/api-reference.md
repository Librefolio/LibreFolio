# FX API Reference

REST API endpoints for FX rate management and currency conversion.

> ⚡ **Interactive Documentation**: Start the server and visit `http://localhost:8000/docs` to access **Swagger UI** with live API documentation. You can try all endpoints directly in your browser!
>
> 📌 **Documentation Freshness**: The Swagger UI at `/docs` is **auto-generated from code** and always up-to-date. This guide may lag behind. If you find discrepancies, please [open an issue](https://github.com/your-repo/issues) to help us maintain it!


---

## 🚀 Quick Start Guide

### Step 1: Get Available Currencies

First, check which currencies a provider supports:

```bash
curl "http://localhost:8000/api/v1/fx/currencies?provider=ECB"
```

**What this does**: Ask the backend to queries the European Central Bank to get the list of all currencies they provide rates for (45+ currencies).

**Response**: JSON with array of currency codes (USD, GBP, JPY, etc.)

---

### Step 2: Sync Historical Rates

Fetch and store exchange rates for specific currencies and date range:

```bash
curl -X POST "http://localhost:8000/api/v1/fx/sync?start=2025-01-01&end=2025-01-31&currencies=USD,GBP,JPY"
```

**What this does**: 
- Fetches daily rates from ECB for USD, GBP, JPY from Jan 1-31, 2025
- Stores them in the database
- Returns how many rates were inserted/updated

**Response**: JSON with sync statistics (`synced`, `date_range`, `currencies`)

**Note**: This is idempotent - safe to run multiple times. Re-running updates existing rates if they changed.

---

### Step 3: Convert Currency

Convert an amount from one currency to another:

```bash
curl -X POST "http://localhost:8000/api/v1/fx/convert" \
  -H "Content-Type: application/json" \
  -d '{
    "conversions": [{
      "amount": 100.00,
      "from": "USD",
      "to": "EUR",
      "date": "2025-01-15"
    }]
  }'
```

**What this does**:
- Converts 100 USD to EUR using the rate from January 15, 2025
- Automatically finds the best conversion strategy (direct, inverse, or cross-currency)
- Applies backward-fill if exact date not available (uses most recent past rate)

**Response**: JSON with converted amount, rate used, and backward-fill info

---

### Step 4: Try Different Providers

Fetch rates using USD as base instead of EUR:

```bash
curl -X POST "http://localhost:8000/api/v1/fx/sync?start=2025-01-01&end=2025-01-31&currencies=EUR,GBP&provider=FED"
```

**What this does**: Same as Step 2, but uses Federal Reserve (USD base) instead of ECB (EUR base).

**Why useful**: Different providers have different base currencies and coverage. Choose based on your needs!

---

## 📍 Base URL

```
http://localhost:8000/api/v1/fx
```

---

## 🌐 Endpoints

### GET `/currencies`

Get list of supported currencies from a provider.

#### Request

**Query Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `provider` | string | No | `"ECB"` | Provider code (ECB, FED, BOE, SNB) |

#### Response

**Status**: `200 OK`

```json
{
  "currencies": ["AUD", "BGN", "BRL", "CAD", "CHF", "CNY", "EUR", "GBP", "JPY", "USD", "..."],
  "count": 45
}
```

#### Examples

```bash
# Get currencies from ECB (default)
curl "http://localhost:8000/api/v1/fx/currencies"

# Get currencies from Federal Reserve
curl "http://localhost:8000/api/v1/fx/currencies?provider=FED"

# Get currencies from Bank of England
curl "http://localhost:8000/api/v1/fx/currencies?provider=BOE"
```

#### Error Responses

**400 Bad Request** - Unknown provider
```json
{
  "detail": "Unknown FX provider: XYZ. Available providers: BOE, ECB, FED, SNB"
}
```

**502 Bad Gateway** - Provider API error
```json
{
  "detail": "Failed to fetch currencies: Connection timeout"
}
```

---

### POST `/sync`

Synchronize FX rates from a provider for specified date range and currencies.

#### Request

**Query Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `start` | date | Yes | - | Start date (ISO: YYYY-MM-DD) |
| `end` | date | Yes | - | End date (ISO: YYYY-MM-DD) |
| `currencies` | string | No | `"USD,GBP,CHF,JPY"` | Comma-separated currency codes |
| `provider` | string | No | `"ECB"` | Provider code |
| `base_currency` | string | No | - | Base currency (for multi-base providers) |

#### Response

**Status**: `200 OK`

```json
{
  "synced": 120,
  "date_range": ["2025-01-01", "2025-01-31"],
  "currencies": ["USD", "GBP", "CHF", "JPY"]
}
```

**Fields**:
- `synced` (int): Number of rates changed (inserted or updated)
- `date_range` (array): Date range synced [start, end]
- `currencies` (array): Currencies actually synced (may differ if some not available)

#### Examples

```bash
# Sync USD and GBP rates from ECB for January 2025
curl -X POST "http://localhost:8000/api/v1/fx/sync?start=2025-01-01&end=2025-01-31&currencies=USD,GBP"

# Sync from Federal Reserve (USD base)
curl -X POST "http://localhost:8000/api/v1/fx/sync?start=2025-01-01&end=2025-01-31&currencies=EUR,GBP&provider=FED"

# Sync from Swiss National Bank (includes multi-unit currencies)
curl -X POST "http://localhost:8000/api/v1/fx/sync?start=2025-01-01&end=2025-01-31&currencies=USD,EUR,JPY&provider=SNB"

# Multi-base provider with explicit base (future)
curl -X POST "http://localhost:8000/api/v1/fx/sync?start=2025-01-01&end=2025-01-31&currencies=JPY,CHF&provider=MULTI&base_currency=EUR"
```

#### Behavior

- **Idempotent**: Safe to call multiple times with same parameters
- **Upsert**: Updates existing rates if they change
- **Atomic**: All-or-nothing transaction per currency
- **Weekends/Holidays**: Returns 0 synced if no rates available (normal)

#### Error Responses

**400 Bad Request** - Invalid parameters
```json
{
  "detail": "Start date must be before or equal to end date"
}
```

**400 Bad Request** - Unknown provider
```json
{
  "detail": "Unknown FX provider: XYZ"
}
```

**400 Bad Request** - Unsupported base currency
```json
{
  "detail": "Provider ECB does not support USD as base. Supported bases: EUR"
}
```

**502 Bad Gateway** - Provider API error
```json
{
  "detail": "Failed to sync rates: ECB API error: Connection timeout"
}
```

---

### POST `/convert`

Convert amount between currencies using stored rates.

#### Request

**Body** (JSON):

```json
{
  "conversions": [
    {
      "amount": 100.00,
      "from": "USD",
      "to": "EUR",
      "date": "2025-01-15"
    },
    {
      "amount": 50.00,
      "from": "GBP",
      "to": "JPY",
      "date": "2025-01-15"
    }
  ]
}
```

**Fields**:
- `amount` (decimal): Amount to convert (must be positive)
- `from` (string): Source currency (ISO 4217, 3 letters)
- `to` (string): Target currency (ISO 4217, 3 letters)
- `date` (string, optional): Conversion date (ISO: YYYY-MM-DD). If omitted, uses today.

#### Response

**Status**: `200 OK`

```json
{
  "conversions": [
    {
      "amount": 100.00,
      "from_currency": "USD",
      "to_currency": "EUR",
      "converted_amount": 92.17,
      "rate": 0.9217,
      "rate_date": "2025-01-15",
      "backward_fill": {
        "applied": false,
        "requested_date": "2025-01-15",
        "actual_rate_date": "2025-01-15",
        "days_back": 0
      }
    },
    {
      "amount": 50.00,
      "from_currency": "GBP",
      "to_currency": "JPY",
      "converted_amount": 9675.00,
      "rate": 193.5,
      "rate_date": "2025-01-15",
      "backward_fill": {
        "applied": false,
        "requested_date": "2025-01-15",
        "actual_rate_date": "2025-01-15",
        "days_back": 0
      }
    }
  ],
  "success_count": 2,
  "errors": []
}
```

**Fields**:
- `converted_amount` (decimal): Result of conversion
- `rate` (decimal): Effective rate used (from → to)
- `rate_date` (string): Date of rate actually used
- `backward_fill.applied` (bool): Whether backward-fill was used
- `backward_fill.days_back` (int): Days back from requested date (0 = exact match)

#### Examples

```bash
# Single conversion
curl -X POST "http://localhost:8000/api/v1/fx/convert" \
  -H "Content-Type: application/json" \
  -d '{
    "conversions": [{
      "amount": 100.00,
      "from": "USD",
      "to": "EUR",
      "date": "2025-01-15"
    }]
  }'

# Multiple conversions (batch)
curl -X POST "http://localhost:8000/api/v1/fx/convert" \
  -H "Content-Type: application/json" \
  -d '{
    "conversions": [
      {"amount": 100, "from": "USD", "to": "EUR", "date": "2025-01-15"},
      {"amount": 50, "from": "GBP", "to": "JPY", "date": "2025-01-15"},
      {"amount": 1000, "from": "EUR", "to": "CHF", "date": "2025-01-15"}
    ]
  }'

# Conversion without date (uses today)
curl -X POST "http://localhost:8000/api/v1/fx/convert" \
  -H "Content-Type: application/json" \
  -d '{
    "conversions": [{
      "amount": 100.00,
      "from": "USD",
      "to": "EUR"
    }]
  }'
```

#### Conversion Strategies

The API automatically chooses the best conversion strategy:

1. **Identity** (USD → USD): Returns amount as-is
2. **Direct** (EUR → USD): Uses stored EUR/USD rate
3. **Inverse** (USD → EUR): Uses stored EUR/USD rate, inverts
4. **Cross** (USD → GBP): Converts via pivot (USD → EUR → GBP)

#### Backward-Fill Behavior

If no rate exists for the requested date:
- Searches **backward in time** for the most recent available rate
- Uses the closest rate from a past date
- Sets `backward_fill.applied = true`
- Includes `days_back` count (how many days back it went)

**Example**: Request rate for Sunday (no markets open) → uses Friday's rate (2 days back)

**Why "backward"?** We look back in time from the requested date to find historical data, never forward into the future.

#### Error Responses

**400 Bad Request** - Invalid amount
```json
{
  "detail": "Amount must be positive"
}
```

**400 Bad Request** - Invalid currency code
```json
{
  "detail": "Currency codes must be exactly 3 characters"
}
```

**404 Not Found** - No rate available
```json
{
  "conversions": [],
  "success_count": 0,
  "errors": [
    "No FX rate found for USD → ZZZ"
  ]
}
```

---

### POST `/rate` (Manual Rate Upsert)

Manually insert or update FX rates.

#### Request

**Body** (JSON):

```json
{
  "rates": [
    {
      "date": "2025-01-15",
      "base": "EUR",
      "quote": "USD",
      "rate": 1.0850
    },
    {
      "date": "2025-01-15",
      "base": "EUR",
      "quote": "GBP",
      "rate": 0.8500
    }
  ]
}
```

**Fields**:
- `date` (string): Rate date (ISO: YYYY-MM-DD)
- `base` (string): Base currency (ISO 4217, 3 letters)
- `quote` (string): Quote currency (ISO 4217, 3 letters)
- `rate` (decimal): Exchange rate (1 base = rate × quote)

**Notes**:
- Automatic alphabetical ordering applied (base < quote)
- Automatic rate inversion if needed
- Upsert behavior (updates if exists)

#### Response

**Status**: `200 OK`

```json
{
  "results": [
    {
      "date": "2025-01-15",
      "base": "EUR",
      "quote": "USD",
      "rate": 1.0850,
      "status": "inserted"
    },
    {
      "date": "2025-01-15",
      "base": "EUR",
      "quote": "GBP",
      "rate": 0.8500,
      "status": "updated"
    }
  ],
  "success_count": 2,
  "errors": []
}
```

**Status values**:
- `"inserted"` - New rate inserted
- `"updated"` - Existing rate updated

#### Examples

```bash
# Insert single rate
curl -X POST "http://localhost:8000/api/v1/fx/rate" \
  -H "Content-Type: application/json" \
  -d '{
    "rates": [{
      "date": "2025-01-15",
      "base": "EUR",
      "quote": "USD",
      "rate": 1.0850
    }]
  }'

# Bulk insert/update
curl -X POST "http://localhost:8000/api/v1/fx/rate" \
  -H "Content-Type: application/json" \
  -d '{
    "rates": [
      {"date": "2025-01-15", "base": "EUR", "quote": "USD", "rate": 1.0850},
      {"date": "2025-01-15", "base": "EUR", "quote": "GBP", "rate": 0.8500},
      {"date": "2025-01-15", "base": "EUR", "quote": "JPY", "rate": 165.50}
    ]
  }'
```

---

## 🔐 Authentication

Currently, **no authentication required** for FX endpoints.

Future versions may implement:
- API key authentication
- Rate limiting per client
- Role-based access (read-only vs write)

---

## 📊 Rate Limiting

Currently, **no rate limiting** imposed by LibreFolio.

However, be aware of provider API limits:
- **ECB**: No documented limit
- **FED**: No documented limit (CSV download)
- **BOE**: No documented limit
- **SNB**: No documented limit

**Recommendation**: Don't sync more than once per hour for same date range.

---

## 🎯 Best Practices

### 1. Sync Strategy

**Daily Sync** (recommended):
```bash
# Every day at 9 AM UTC, sync yesterday's rates
curl -X POST "http://localhost:8000/api/v1/fx/sync?start=2025-01-14&end=2025-01-14&currencies=USD,GBP,JPY,CHF"
```

**Initial Backfill**:
```bash
# Sync last 30 days for all major currencies
curl -X POST "http://localhost:8000/api/v1/fx/sync?start=2025-01-01&end=2025-01-30&currencies=USD,GBP,JPY,CHF,CAD,AUD"
```

### 2. Currency Selection

**Core Currencies** (recommended minimum):
- USD, EUR, GBP, JPY, CHF

**Extended** (for global portfolios):
- Add: CAD, AUD, CNY, INR, BRL

**Avoid** syncing currencies you don't need (saves API calls and storage).

### 3. Error Handling

Always check for errors in batch operations:

```javascript
const response = await fetch('/api/v1/fx/convert', {
  method: 'POST',
  body: JSON.stringify({ conversions: [...] })
});

const data = await response.json();

if (data.errors.length > 0) {
  console.error('Some conversions failed:', data.errors);
  // Handle partial failure
}
```

### 4. Caching

FX rates are **immutable once published** (historical rates don't change).

**Safe to cache**:
- Rates for past dates (indefinitely)
- Rates for future dates (backward-fill from past may change as new data arrives)

**Don't cache**:
- Rates for today (may update during day)
- Rates for future dates (forward-fill may change)

---

## 🔗 Related Documentation

- **[Architecture](./architecture.md)** - System architecture
- **[Providers](./providers.md)** - Available providers
- **[Provider Development](./provider-development.md)** - Add new providers


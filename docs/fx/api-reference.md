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
curl -X POST "http://localhost:8000/api/v1/fx/sync/bulk?start=2025-01-01&end=2025-01-31&currencies=USD,GBP,JPY"
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
curl -X POST "http://localhost:8000/api/v1/fx/convert/bulk" \
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
curl -X POST "http://localhost:8000/api/v1/fx/sync/bulk?start=2025-01-01&end=2025-01-31&currencies=EUR,GBP&provider=FED"
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
# Explicit provider mode (backward compatible)
curl -X POST "http://localhost:8000/api/v1/fx/sync/bulk?start=2025-01-01&end=2025-01-31&currencies=USD,GBP&provider=ECB"

# Auto-configuration mode (uses fx_currency_pair_sources table)
curl -X POST "http://localhost:8000/api/v1/fx/sync/bulk?start=2025-01-01&end=2025-01-31&currencies=USD,GBP"
# Note: Requires pair-sources configured via POST /pair-sources/bulk
# System automatically selects provider based on configuration and priority

# Sync from Federal Reserve (USD base)
curl -X POST "http://localhost:8000/api/v1/fx/sync/bulk?start=2025-01-01&end=2025-01-31&currencies=EUR,GBP&provider=FED"

# Sync from Swiss National Bank (includes multi-unit currencies)
curl -X POST "http://localhost:8000/api/v1/fx/sync/bulk?start=2025-01-01&end=2025-01-31&currencies=USD,EUR,JPY&provider=SNB"

# Auto-configuration with fallback (multiple providers)
# First, configure pair-sources with priorities:
# curl -X POST "http://localhost:8000/api/v1/fx/pair-sources/bulk" \
#   -H "Content-Type: application/json" \
#   -d '{"sources": [
#     {"base": "EUR", "quote": "USD", "provider_code": "ECB", "priority": 1},
#     {"base": "EUR", "quote": "USD", "provider_code": "FED", "priority": 2}
#   ]}'
# Then sync without provider parameter:
curl -X POST "http://localhost:8000/api/v1/fx/sync/bulk?start=2025-01-01&end=2025-01-31&currencies=USD,EUR"
# System tries ECB first (priority=1), falls back to FED (priority=2) if ECB fails
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

### POST `/convert/bulk`

Convert amount between currencies using stored rates. Supports single date or date range conversions.

#### Request

**Body** (JSON):

```json
{
  "conversions": [
    {
      "amount": 100.00,
      "from": "USD",
      "to": "EUR",
      "start_date": "2025-01-15"
    },
    {
      "amount": 50.00,
      "from": "GBP",
      "to": "JPY",
      "start_date": "2025-01-01",
      "end_date": "2025-01-31"
    }
  ]
}
```

**Fields**:
- `amount` (decimal): Amount to convert (must be positive)
- `from` (string): Source currency (ISO 4217, 3 letters)
- `to` (string): Target currency (ISO 4217, 3 letters)
- `start_date` (string): Conversion date or start of range (ISO: YYYY-MM-DD) - **required**
- `end_date` (string, optional): End of range (ISO: YYYY-MM-DD). If present, converts for each day in `[start_date, end_date]`

#### Response

**Status**: `200 OK`

**Single Date Response**:
```json
{
  "results": [
    {
      "amount": "100.00",
      "from_currency": "USD",
      "to_currency": "EUR",
      "conversion_date": "2025-01-15",
      "converted_amount": "92.1700000000",
      "rate": "0.9217000000",
      "rate_date": "2025-01-15",
      "backward_fill_info": null
    }
  ],
  "errors": []
}
```

**Range Response** (one result per day):
```json
{
  "results": [
    {
      "amount": "50.00",
      "from_currency": "GBP",
      "to_currency": "JPY",
      "conversion_date": "2025-01-01",
      "converted_amount": "9650.0000000000",
      "rate": "193.0000000000",
      "rate_date": "2024-12-31",
      "backward_fill_info": {
        "actual_rate_date": "2024-12-31",
        "days_back": 1
      }
    },
    {
      "amount": "50.00",
      "from_currency": "GBP",
      "to_currency": "JPY",
      "conversion_date": "2025-01-02",
      "converted_amount": "9675.0000000000",
      "rate": "193.5000000000",
      "rate_date": "2025-01-02",
      "backward_fill_info": null
    }
  ],
  "errors": []
}
```

**Fields**:
- `conversion_date` (string): Date for this conversion (requested date)
- `converted_amount` (decimal): Result of conversion
- `rate` (decimal): Effective rate used (from → to)
- `rate_date` (string): Date of rate actually used
- `backward_fill_info` (object|null): Present only if backward-fill was used
  - `actual_rate_date` (string): Date of rate used (older than requested)
  - `days_back` (int): Days back from conversion_date

**Note**: `backward_fill_info` is `null` when exact rate is found (no backward-fill needed)

#### Examples

```bash
# Single date conversion
curl -X POST "http://localhost:8000/api/v1/fx/convert/bulk" \
  -H "Content-Type: application/json" \
  -d '{
    "conversions": [{
      "amount": "100.00",
      "from": "USD",
      "to": "EUR",
      "start_date": "2025-01-15"
    }]
  }'

# Range conversion (generates daily conversions)
curl -X POST "http://localhost:8000/api/v1/fx/convert/bulk" \
  -H "Content-Type: application/json" \
  -d '{
    "conversions": [{
      "amount": "100.00",
      "from": "USD",
      "to": "EUR",
      "start_date": "2025-01-01",
      "end_date": "2025-01-31"
    }]
  }'
# Returns 31 results (one per day)

# Multiple conversions (batch)
curl -X POST "http://localhost:8000/api/v1/fx/convert/bulk" \
  -H "Content-Type: application/json" \
  -d '{
    "conversions": [
      {"amount": "100", "from": "USD", "to": "EUR", "start_date": "2025-01-15"},
      {"amount": "50", "from": "GBP", "to": "JPY", "start_date": "2025-01-15"},
      {"amount": "1000", "from": "EUR", "to": "CHF", "start_date": "2025-01-01", "end_date": "2025-01-07"}
    ]
  }'
# Returns: 1 + 1 + 7 = 9 results total

# Today's conversion (omit dates - NOT SUPPORTED, must specify start_date)
# curl -X POST "http://localhost:8000/api/v1/fx/convert/bulk" \
#   -H "Content-Type: application/json" \
#   -d '{
#     "conversions": [{
#       "amount": "100.00",
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

### POST `/rate-set/bulk` (Manual Rate Upsert)

Manually insert or update FX rates in bulk.

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
# Insert single rate (via bulk endpoint with single item)
curl -X POST "http://localhost:8000/api/v1/fx/rate-set/bulk" \
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
curl -X POST "http://localhost:8000/api/v1/fx/rate-set/bulk" \
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

### DELETE `/rate-set/bulk` (Delete Rates)

Delete FX rates for specific currency pairs and date ranges.

#### Request

**Body** (JSON):

```json
{
  "deletions": [
    {
      "from": "EUR",
      "to": "USD",
      "start_date": "2025-01-01",
      "end_date": "2025-01-31"
    },
    {
      "from": "GBP",
      "to": "JPY",
      "start_date": "2025-01-15"
    }
  ]
}
```

**Fields**:
- `from` (string): Source currency (ISO 4217, 3 letters)
- `to` (string): Target currency (ISO 4217, 3 letters)
- `start_date` (string): Start date (ISO: YYYY-MM-DD) - **required**
- `end_date` (string, optional): End date (ISO: YYYY-MM-DD) - if omitted, deletes only `start_date`

**Notes**:
- Automatic alphabetical normalization (EUR/USD or USD/EUR both work)
- Deletes all rates in range `[start_date, end_date]` (both inclusive)
- Safe to delete non-existent rates (returns success with count=0)

#### Response

**Status**: `200 OK`

```json
{
  "results": [
    {
      "success": true,
      "base": "EUR",
      "quote": "USD",
      "start_date": "2025-01-01",
      "end_date": "2025-01-31",
      "existing_count": 31,
      "deleted_count": 31,
      "message": null
    },
    {
      "success": true,
      "base": "GBP",
      "quote": "JPY",
      "start_date": "2025-01-15",
      "end_date": null,
      "existing_count": 1,
      "deleted_count": 1,
      "message": null
    }
  ],
  "total_deleted": 32,
  "errors": []
}
```

**Fields**:
- `success` (bool): Whether deletion succeeded
- `existing_count` (int): Number of rates found for this request
- `deleted_count` (int): Number of rates actually deleted
- `message` (string|null): Warning/info message (e.g., "No rates found")
- `total_deleted` (int): Sum of all deleted_count values

#### Examples

```bash
# Delete single day
curl -X DELETE "http://localhost:8000/api/v1/fx/rate-set/bulk" \
  -H "Content-Type: application/json" \
  -d '{
    "deletions": [{
      "from": "EUR",
      "to": "USD",
      "start_date": "2025-01-15"
    }]
  }'

# Delete date range
curl -X DELETE "http://localhost:8000/api/v1/fx/rate-set/bulk" \
  -H "Content-Type: application/json" \
  -d '{
    "deletions": [{
      "from": "EUR",
      "to": "USD",
      "start_date": "2025-01-01",
      "end_date": "2025-01-31"
    }]
  }'

# Bulk delete (multiple pairs)
curl -X DELETE "http://localhost:8000/api/v1/fx/rate-set/bulk" \
  -H "Content-Type: application/json" \
  -d '{
    "deletions": [
      {"from": "EUR", "to": "USD", "start_date": "2025-01-01", "end_date": "2025-01-31"},
      {"from": "GBP", "to": "JPY", "start_date": "2025-01-01", "end_date": "2025-01-31"},
      {"from": "CHF", "to": "CAD", "start_date": "2025-01-15"}
    ]
  }'

# Delete inverted pair (USD/EUR → EUR/USD)
curl -X DELETE "http://localhost:8000/api/v1/fx/rate-set/bulk" \
  -H "Content-Type: application/json" \
  -d '{
    "deletions": [{
      "from": "USD",
      "to": "EUR",
      "start_date": "2025-01-01"
    }]
  }'
# Note: System automatically finds EUR/USD if stored that way
```

#### Behavior

**Idempotency**: Safe to re-run same deletion - returns `deleted_count=0` with informational message.

**Normalization**: Pairs are normalized to alphabetical order internally. Requesting `USD/EUR` will delete `EUR/USD` if that's how it's stored.

**Performance**: Optimized chunked deletion (500 IDs per batch) to avoid SQLite limits. Can efficiently delete thousands of rates.

**After Deletion**: 
- Conversions for deleted dates will use backward-fill from earlier dates
- If no earlier rate exists, conversion will fail with "No FX rate found"

#### Error Responses

**400 Bad Request** - Invalid date range
```json
{
  "detail": "Start date must be before or equal to end date"
}
```

**400 Bad Request** - Same from/to currency
```json
{
  "detail": "Base and quote must be different"
}
```

**422 Unprocessable Entity** - Invalid date format
```json
{
  "detail": [
    {
      "type": "date_from_datetime_parsing",
      "loc": ["body", "deletions", 0, "start_date"],
      "msg": "Input should be a valid date"
    }
  ]
}
```

---

### GET `/providers`

Get list of available FX rate providers with their metadata.

#### Request

No parameters required.

#### Response

**Status**: `200 OK`

```json
{
  "providers": [
    {
      "code": "ECB",
      "name": "European Central Bank",
      "base_currencies": ["EUR"],
      "description": "Official exchange rates from European Central Bank"
    },
    {
      "code": "FED",
      "name": "Federal Reserve",
      "base_currencies": ["USD"],
      "description": "Official exchange rates from Federal Reserve (H.10 Release)"
    },
    {
      "code": "BOE",
      "name": "Bank of England",
      "base_currencies": ["GBP"],
      "description": "Official exchange rates from Bank of England"
    },
    {
      "code": "SNB",
      "name": "Swiss National Bank",
      "base_currencies": ["CHF"],
      "description": "Official exchange rates from Swiss National Bank"
    }
  ],
  "count": 4
}
```

**Fields**:
- `code` (string): Provider identifier (used in API calls)
- `name` (string): Human-readable provider name
- `base_currencies` (array): Base currencies this provider supports
- `description` (string): Provider description

#### Example

```bash
curl "http://localhost:8000/api/v1/fx/providers"
```

**Note**: No API key required. All providers are free public APIs from central banks.

---

### GET `/pair-sources`

Get configured currency pairs with their provider assignments.

#### Request

No parameters required.

#### Response

**Status**: `200 OK`

```json
{
  "sources": [
    {
      "id": 1,
      "base": "EUR",
      "quote": "USD",
      "provider_code": "ECB",
      "priority": 1,
      "created_at": "2025-11-05T14:00:00Z",
      "updated_at": "2025-11-05T14:00:00Z"
    },
    {
      "id": 2,
      "base": "GBP",
      "quote": "USD",
      "provider_code": "BOE",
      "priority": 1,
      "created_at": "2025-11-05T14:00:00Z",
      "updated_at": "2025-11-05T14:00:00Z"
    },
    {
      "id": 3,
      "base": "EUR",
      "quote": "USD",
      "provider_code": "FED",
      "priority": 2,
      "created_at": "2025-11-05T14:00:00Z",
      "updated_at": "2025-11-05T14:00:00Z"
    }
  ],
  "count": 3
}
```

**Fields**:
- `id` (int): Database ID
- `base` (string): Base currency
- `quote` (string): Quote currency
- `provider_code` (string): Provider to use for this pair
- `priority` (int): Provider priority (1 = primary, 2 = fallback, etc.)
- `created_at` / `updated_at` (string): Timestamps

**Notes**:
- Multiple priorities allowed per pair (for fallback logic)
- Inverse pairs (EUR/USD and USD/EUR) can coexist with different priorities

#### Example

```bash
curl "http://localhost:8000/api/v1/fx/pair-sources"
```

---

### POST `/pair-sources/bulk`

Create or update currency pair source configurations.

#### Request

**Body** (JSON):

```json
{
  "sources": [
    {
      "base": "EUR",
      "quote": "USD",
      "provider_code": "ECB",
      "priority": 1
    },
    {
      "base": "GBP",
      "quote": "USD",
      "provider_code": "BOE",
      "priority": 1
    },
    {
      "base": "EUR",
      "quote": "USD",
      "provider_code": "FED",
      "priority": 2
    }
  ]
}
```

**Fields**:
- `base` (string): Base currency (ISO 4217, 3 letters)
- `quote` (string): Quote currency (ISO 4217, 3 letters)
- `provider_code` (string): Provider code (ECB, FED, BOE, SNB)
- `priority` (int): Priority level (1 = primary, higher = fallback)

**Constraints**:
- `base` ≠ `quote` (must be different currencies)
- Unique constraint: `(base, quote, priority)` combination must be unique
- **Inverse pair validation**: EUR/USD priority=1 + USD/EUR priority=1 = **ERROR**
- Inverse pairs OK if different priorities: EUR/USD priority=1 + USD/EUR priority=2 = **OK**

#### Response

**Status**: `201 Created` (success)

```json
{
  "success_count": 3,
  "error_count": 0,
  "results": [
    {
      "success": true,
      "action": "created",
      "base": "EUR",
      "quote": "USD",
      "provider_code": "ECB",
      "priority": 1,
      "message": null
    },
    {
      "success": true,
      "action": "created",
      "base": "GBP",
      "quote": "USD",
      "provider_code": "BOE",
      "priority": 1,
      "message": null
    },
    {
      "success": true,
      "action": "created",
      "base": "EUR",
      "quote": "USD",
      "provider_code": "FED",
      "priority": 2,
      "message": null
    }
  ],
  "errors": []
}
```

**Action values**:
- `"created"` - New configuration inserted
- `"updated"` - Existing configuration updated (if same base+quote+priority)

**Status**: `400 Bad Request` (validation error)

```json
{
  "detail": {
    "message": "Validation failed for 1 source(s). Transaction rolled back.",
    "results": [
      {
        "success": false,
        "action": "error",
        "base": "EUR",
        "quote": "USD",
        "provider_code": "ECB",
        "priority": 1,
        "message": "Conflict: Inverse pair USD/EUR with priority=1 already exists. Use different priority."
      }
    ]
  }
}
```

#### Examples

```bash
# Create single configuration
curl -X POST "http://localhost:8000/api/v1/fx/pair-sources/bulk" \
  -H "Content-Type: application/json" \
  -d '{
    "sources": [{
      "base": "EUR",
      "quote": "USD",
      "provider_code": "ECB",
      "priority": 1
    }]
  }'

# Create with fallback provider
curl -X POST "http://localhost:8000/api/v1/fx/pair-sources/bulk" \
  -H "Content-Type: application/json" \
  -d '{
    "sources": [
      {"base": "EUR", "quote": "USD", "provider_code": "ECB", "priority": 1},
      {"base": "EUR", "quote": "USD", "provider_code": "FED", "priority": 2}
    ]
  }'

# Create inverse pairs (different priorities)
curl -X POST "http://localhost:8000/api/v1/fx/pair-sources/bulk" \
  -H "Content-Type: application/json" \
  -d '{
    "sources": [
      {"base": "EUR", "quote": "USD", "provider_code": "ECB", "priority": 1},
      {"base": "USD", "quote": "EUR", "provider_code": "FED", "priority": 1}
    ]
  }'
# Note: EUR/USD and USD/EUR are semantically different!
```

#### Behavior

**Atomic Transaction**: All sources inserted/updated in single transaction. If any validation fails, entire request is rolled back.

**Batch Validation**: Inverse pair conflicts detected with single optimized query (not N queries).

**Upsert Logic**: If `(base, quote, priority)` exists, provider_code is updated. Otherwise, new record inserted.

---

### DELETE `/pair-sources/bulk`

Delete currency pair source configurations.

#### Request

**Body** (JSON):

```json
{
  "sources": [
    {
      "base": "EUR",
      "quote": "USD",
      "priority": 1
    },
    {
      "base": "GBP",
      "quote": "USD"
    }
  ]
}
```

**Fields**:
- `base` (string): Base currency (ISO 4217, 3 letters)
- `quote` (string): Quote currency (ISO 4217, 3 letters)
- `priority` (int, optional): Specific priority to delete. If omitted, deletes **all priorities** for this pair.

#### Response

**Status**: `200 OK`

```json
{
  "results": [
    {
      "success": true,
      "deleted_count": 1,
      "base": "EUR",
      "quote": "USD",
      "priority": 1,
      "message": null
    },
    {
      "success": true,
      "deleted_count": 2,
      "base": "GBP",
      "quote": "USD",
      "priority": null,
      "message": "Deleted all priorities for GBP/USD"
    }
  ],
  "total_deleted": 3,
  "errors": []
}
```

**Fields**:
- `success` (bool): Whether deletion succeeded
- `deleted_count` (int): Number of records deleted
- `message` (string|null): Info/warning message
- `total_deleted` (int): Sum of all deleted_count values

#### Examples

```bash
# Delete specific priority
curl -X DELETE "http://localhost:8000/api/v1/fx/pair-sources/bulk" \
  -H "Content-Type: application/json" \
  -d '{
    "sources": [{
      "base": "EUR",
      "quote": "USD",
      "priority": 1
    }]
  }'

# Delete all priorities for a pair
curl -X DELETE "http://localhost:8000/api/v1/fx/pair-sources/bulk" \
  -H "Content-Type: application/json" \
  -d '{
    "sources": [{
      "base": "EUR",
      "quote": "USD"
    }]
  }'

# Bulk delete
curl -X DELETE "http://localhost:8000/api/v1/fx/pair-sources/bulk" \
  -H "Content-Type: application/json" \
  -d '{
    "sources": [
      {"base": "EUR", "quote": "USD", "priority": 1},
      {"base": "GBP", "quote": "USD"},
      {"base": "CHF", "quote": "JPY"}
    ]
  }'
```

#### Behavior

**Idempotency**: Safe to delete non-existent configurations. Returns `deleted_count=0` with warning message.

**Cascade**: Deleting pair-source configuration does **NOT** delete FX rates. Rates remain in database.

**Impact on Auto-Sync**: If you delete all configurations for a currency pair, auto-configuration sync will fail for that pair.

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
curl -X POST "http://localhost:8000/api/v1/fx/sync/bulk?start=2025-01-14&end=2025-01-14&currencies=USD,GBP,JPY,CHF"
```

**Initial Backfill**:
```bash
# Sync last 30 days for all major currencies
curl -X POST "http://localhost:8000/api/v1/fx/sync/bulk?start=2025-01-01&end=2025-01-30&currencies=USD,GBP,JPY,CHF,CAD,AUD"
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
const response = await fetch('/api/v1/fx/convert/bulk', {
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


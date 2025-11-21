# Asset Management API Examples

**Last Updated**: November 21, 2025  
**Base URL**: `http://localhost:8000/api/v1` (production) or `http://localhost:8001/api/v1` (test)

This guide provides practical examples for managing assets via the LibreFolio REST API.

---

## 📋 Table of Contents

1. [Create Assets](#create-assets)
2. [List Assets](#list-assets)
3. [Delete Assets](#delete-assets)
4. [Common Patterns](#common-patterns)

---

## 🆕 Create Assets

### POST /assets/bulk

Create one or more assets in a single request (bulk operation with partial success support).

#### Single Asset

```bash
curl -X POST "http://localhost:8000/api/v1/assets/bulk" \
  -H "Content-Type: application/json" \
  -d '{
    "assets": [
      {
        "display_name": "Apple Inc.",
        "identifier": "AAPL",
        "identifier_type": "TICKER",
        "currency": "USD",
        "asset_type": "STOCK",
        "valuation_model": "MARKET_PRICE"
      }
    ]
  }'
```

**Response** (201 Created):
```json
{
  "results": [
    {
      "asset_id": 1,
      "success": true,
      "message": "Asset created successfully",
      "display_name": "Apple Inc.",
      "identifier": "AAPL"
    }
  ],
  "success_count": 1,
  "failed_count": 0
}
```

#### Multiple Assets

```bash
curl -X POST "http://localhost:8000/api/v1/assets/bulk" \
  -H "Content-Type: application/json" \
  -d '{
    "assets": [
      {
        "display_name": "Apple Inc.",
        "identifier": "AAPL",
        "currency": "USD",
        "asset_type": "STOCK"
      },
      {
        "display_name": "Microsoft Corporation",
        "identifier": "MSFT",
        "currency": "USD",
        "asset_type": "STOCK"
      },
      {
        "display_name": "Vanguard S&P 500 ETF",
        "identifier": "VOO",
        "currency": "USD",
        "asset_type": "ETF"
      }
    ]
  }'
```

**Response** (201 Created):
```json
{
  "results": [
    {
      "asset_id": 1,
      "success": true,
      "message": "Asset created successfully",
      "display_name": "Apple Inc.",
      "identifier": "AAPL"
    },
    {
      "asset_id": 2,
      "success": true,
      "message": "Asset created successfully",
      "display_name": "Microsoft Corporation",
      "identifier": "MSFT"
    },
    {
      "asset_id": 3,
      "success": true,
      "message": "Asset created successfully",
      "display_name": "Vanguard S&P 500 ETF",
      "identifier": "VOO"
    }
  ],
  "success_count": 3,
  "failed_count": 0
}
```

#### With Classification Metadata

```bash
curl -X POST "http://localhost:8000/api/v1/assets/bulk" \
  -H "Content-Type: application/json" \
  -d '{
    "assets": [
      {
        "display_name": "Apple Inc.",
        "identifier": "AAPL",
        "currency": "USD",
        "asset_type": "STOCK",
        "classification_params": {
          "investment_type": "stock",
          "sector": "Technology",
          "short_description": "Apple Inc. - Consumer electronics and software",
          "geographic_area": {
            "USA": "0.6",
            "EUR": "0.25",
            "CHN": "0.15"
          }
        }
      }
    ]
  }'
```

#### Scheduled Yield Asset (Bond/Loan)

```bash
curl -X POST "http://localhost:8000/api/v1/assets/bulk" \
  -H "Content-Type: application/json" \
  -d '{
    "assets": [
      {
        "display_name": "ReInvest24 - Property Loan #123",
        "identifier": "REINVEST24_123",
        "currency": "EUR",
        "asset_type": "P2P_LOAN",
        "valuation_model": "SCHEDULED_YIELD",
        "face_value": "10000.00",
        "maturity_date": "2026-12-31",
        "interest_schedule": "{\"schedule\": [{\"start_date\": \"2025-01-01\", \"end_date\": \"2026-12-31\", \"annual_rate\": \"0.08\", \"compounding\": \"SIMPLE\", \"day_count\": \"ACT/365\"}]}",
        "late_interest": "{\"annual_rate\": \"0.12\", \"grace_period_days\": 30, \"compounding\": \"SIMPLE\", \"day_count\": \"ACT/365\"}"
      }
    ]
  }'
```

#### Partial Success (Duplicate Handling)

```bash
# First create an asset
curl -X POST "http://localhost:8000/api/v1/assets/bulk" \
  -H "Content-Type: application/json" \
  -d '{"assets": [{"display_name": "Test", "identifier": "TEST123", "currency": "USD"}]}'

# Try to create duplicate + valid asset
curl -X POST "http://localhost:8000/api/v1/assets/bulk" \
  -H "Content-Type: application/json" \
  -d '{
    "assets": [
      {"display_name": "Valid Asset", "identifier": "VALID1", "currency": "USD"},
      {"display_name": "Duplicate", "identifier": "TEST123", "currency": "USD"},
      {"display_name": "Another Valid", "identifier": "VALID2", "currency": "EUR"}
    ]
  }'
```

**Response** (201 Created - partial success):
```json
{
  "results": [
    {
      "asset_id": 5,
      "success": true,
      "message": "Asset created successfully",
      "display_name": "Valid Asset",
      "identifier": "VALID1"
    },
    {
      "asset_id": null,
      "success": false,
      "message": "Asset with identifier 'TEST123' already exists",
      "display_name": "Duplicate",
      "identifier": "TEST123"
    },
    {
      "asset_id": 6,
      "success": true,
      "message": "Asset created successfully",
      "display_name": "Another Valid",
      "identifier": "VALID2"
    }
  ],
  "success_count": 2,
  "failed_count": 1
}
```

---

## 📋 List Assets

### GET /assets/list

Retrieve assets with optional filters.

#### List All Active Assets

```bash
curl "http://localhost:8000/api/v1/assets/list"
```

**Response** (200 OK):
```json
[
  {
    "id": 1,
    "display_name": "Apple Inc.",
    "identifier": "AAPL",
    "identifier_type": "TICKER",
    "currency": "USD",
    "asset_type": "STOCK",
    "valuation_model": "MARKET_PRICE",
    "active": true,
    "has_provider": true,
    "has_metadata": true
  },
  {
    "id": 2,
    "display_name": "Microsoft Corporation",
    "identifier": "MSFT",
    "identifier_type": "TICKER",
    "currency": "USD",
    "asset_type": "STOCK",
    "valuation_model": "MARKET_PRICE",
    "active": true,
    "has_provider": false,
    "has_metadata": false
  }
]
```

#### Filter by Currency

```bash
curl "http://localhost:8000/api/v1/assets/list?currency=USD"
```

Returns only assets with `currency = "USD"`.

#### Filter by Asset Type

```bash
curl "http://localhost:8000/api/v1/assets/list?asset_type=STOCK"
```

Returns only assets with `asset_type = "STOCK"`.

#### Filter by Valuation Model

```bash
curl "http://localhost:8000/api/v1/assets/list?valuation_model=SCHEDULED_YIELD"
```

Returns only scheduled-yield assets (bonds, loans).

#### Include Inactive Assets

```bash
curl "http://localhost:8000/api/v1/assets/list?active=false"
```

Returns only inactive assets (default is `active=true`).

#### Search by Name or Identifier

```bash
curl "http://localhost:8000/api/v1/assets/list?search=Apple"
```

Case-insensitive search in `display_name` or `identifier` fields.

#### Combine Multiple Filters

```bash
curl "http://localhost:8000/api/v1/assets/list?currency=USD&asset_type=STOCK&search=tech"
```

Returns USD stocks with "tech" in name/identifier.

---

## 🗑️ Delete Assets

### DELETE /assets/bulk

Delete one or more assets (bulk operation with partial success support).

**⚠️ Warning**: This CASCADE deletes:
- Provider assignments (`asset_provider_assignments`)
- Price history (`price_history`)

**Blocks deletion** if asset has transactions (foreign key constraint).

#### Delete Single Asset

```bash
curl -X DELETE "http://localhost:8000/api/v1/assets/bulk" \
  -H "Content-Type: application/json" \
  -d '{
    "asset_ids": [1]
  }'
```

**Response** (200 OK):
```json
{
  "results": [
    {
      "asset_id": 1,
      "success": true,
      "message": "Asset deleted successfully"
    }
  ],
  "success_count": 1,
  "failed_count": 0
}
```

#### Delete Multiple Assets

```bash
curl -X DELETE "http://localhost:8000/api/v1/assets/bulk" \
  -H "Content-Type: application/json" \
  -d '{
    "asset_ids": [1, 2, 3]
  }'
```

#### Partial Success (Asset with Transactions)

```bash
curl -X DELETE "http://localhost:8000/api/v1/assets/bulk" \
  -H "Content-Type: application/json" \
  -d '{
    "asset_ids": [1, 2]
  }'
```

**Response** (200 OK - partial success):
```json
{
  "results": [
    {
      "asset_id": 1,
      "success": true,
      "message": "Asset deleted successfully"
    },
    {
      "asset_id": 2,
      "success": false,
      "message": "Cannot delete asset 2: has existing transactions"
    }
  ],
  "success_count": 1,
  "failed_count": 1
}
```

#### Asset Not Found

```bash
curl -X DELETE "http://localhost:8000/api/v1/assets/bulk" \
  -H "Content-Type: application/json" \
  -d '{
    "asset_ids": [999]
  }'
```

**Response** (200 OK):
```json
{
  "results": [
    {
      "asset_id": 999,
      "success": false,
      "message": "Asset with ID 999 not found"
    }
  ],
  "success_count": 0,
  "failed_count": 1
}
```

---

## 🔄 Common Patterns

### 1. Create → Assign Provider → Add Prices

```bash
# Step 1: Create asset
ASSET_ID=$(curl -s -X POST "http://localhost:8000/api/v1/assets/bulk" \
  -H "Content-Type: application/json" \
  -d '{"assets": [{"display_name": "Apple", "identifier": "AAPL", "currency": "USD"}]}' \
  | jq -r '.results[0].asset_id')

# Step 2: Assign yfinance provider
curl -X POST "http://localhost:8000/api/v1/assets/provider/bulk" \
  -H "Content-Type: application/json" \
  -d "{\"assignments\": [{\"asset_id\": $ASSET_ID, \"provider_code\": \"yfinance\", \"provider_params\": {}}]}"

# Step 3: Fetch prices
curl -X POST "http://localhost:8000/api/v1/assets/$ASSET_ID/prices-refresh"
```

### 2. Bulk Import from CSV

```python
import csv
import requests

with open('assets.csv', 'r') as f:
    reader = csv.DictReader(f)
    assets = [
        {
            "display_name": row['name'],
            "identifier": row['ticker'],
            "currency": row['currency'],
            "asset_type": "STOCK"
        }
        for row in reader
    ]

response = requests.post(
    "http://localhost:8000/api/v1/assets/bulk",
    json={"assets": assets}
)

print(f"Created: {response.json()['success_count']}")
print(f"Failed: {response.json()['failed_count']}")
```

### 3. Cleanup Test Assets

```bash
# List all test assets
TEST_IDS=$(curl -s "http://localhost:8000/api/v1/assets/list?search=TEST" \
  | jq -r '.[].id' \
  | jq -s '.')

# Delete them
curl -X DELETE "http://localhost:8000/api/v1/assets/bulk" \
  -H "Content-Type: application/json" \
  -d "{\"asset_ids\": $TEST_IDS}"
```

### 4. Filter Portfolio by Geography

```bash
# Get all US-heavy assets (>50% USA exposure)
curl -s "http://localhost:8000/api/v1/assets/list" \
  | jq '[.[] | select(.has_metadata == true)] | 
        map(select(.classification_params.geographic_area.USA > 0.5))'
```

---

## 📚 Related Endpoints

**Provider Management**:
- `POST /assets/provider/bulk` - Assign providers to assets
- `DELETE /assets/provider/bulk` - Remove provider assignments

**Price Management**:
- `POST /assets/prices/bulk` - Manually add prices
- `GET /assets/{asset_id}/prices` - Get price history
- `DELETE /assets/prices/bulk` - Delete price ranges

**Metadata Management**:
- `PATCH /assets/metadata` - Update classification metadata
- `POST /assets/metadata/refresh/bulk` - Refresh metadata from providers

See full API documentation at `/api/v1/docs`.

---

## 🐛 Common Errors

### 422 Unprocessable Entity

**Cause**: Invalid request body (missing required fields, wrong types)

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "assets", 0, "currency"],
      "msg": "Field required"
    }
  ]
}
```

**Solution**: Check request schema, ensure all required fields are present.

### 201 with Partial Failures

**Cause**: Some assets couldn't be created (duplicate identifier, validation error)

```json
{
  "results": [...],
  "success_count": 2,
  "failed_count": 1
}
```

**Solution**: Check `results` array for per-asset error messages.

### 500 Internal Server Error

**Cause**: Unexpected server error

**Solution**: Check server logs, report bug if issue persists.

---

## 💡 Tips

1. **Use bulk operations** - More efficient than single-asset endpoints
2. **Check partial success** - Always inspect `success_count` and `failed_count`
3. **Unique identifiers** - Ensure identifiers are unique before creating assets
4. **CASCADE deletes** - Be aware that deleting an asset removes all related data
5. **Transaction blocking** - Assets with transactions cannot be deleted (integrity constraint)

---

**For more information**, see:
- [API Reference](/api/v1/docs)
- [Database Schema](../database-schema.md)
- [Asset Provider Development](../assets/provider-development.md)


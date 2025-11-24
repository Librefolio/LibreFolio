# LibreFolio - Asset Management E2E Testing Guide

**Last Updated**: November 22, 2025  
**Purpose**: Manual step-by-step testing guide for Asset Management features  
**Prerequisites**: Backend server running, curl installed, jq (optional for JSON formatting)

---

## 📋 Overview

This guide walks through testing the complete Asset Management subsystem end-to-end, covering:
- Asset creation (CRUD)
- Provider assignment (yfinance auto-metadata)
- Metadata management (PATCH operations)
- Price operations
- Bulk operations

**Expected Duration**: 15-20 minutes

---

## 🚀 Setup

### 1. Start the Backend Server

```bash
cd /Users/ea_enel/Documents/00_My/LibreFolio
./dev.sh server
```

**Expected Output**:
```
INFO:     Uvicorn running on http://localhost:8000
INFO:     Application startup complete.
```

### 2. Set Base URL

```bash
export BASE_URL="http://localhost:8000/api/v1"
```

### 3. Verify Server is Running

```bash
curl -s "$BASE_URL/health" | jq
```

**Expected Output**:
```json
{
  "status": "ok"
}
```

---

## 📝 Test Scenario 1: Create Asset with Manual Metadata

### Step 1.1: Create Single Asset

```bash
curl -X POST "$BASE_URL/assets/bulk" \
  -H "Content-Type: application/json" \
  -d '{
    "assets": [
      {
        "display_name": "Apple Inc.",
        "identifier": "AAPL",
        "identifier_type": "TICKER",
        "currency": "USD",
        "asset_type": "STOCK",
        "valuation_model": "MARKET_PRICE",
        "classification_params": {
          "investment_type": "stock",
          "sector": "Technology",
          "short_description": "Apple Inc. designs, manufactures, and markets smartphones",
          "geographic_area": {
            "USA": "0.60",
            "CHN": "0.25",
            "EUR": "0.15"
          }
        }
      }
    ]
  }' | jq
```

**Expected Output**:
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

**✅ Verify**:
- Status code: 201 Created
- `success_count` = 1
- `asset_id` is returned (save it as `ASSET_ID_1`)

```bash
export ASSET_ID_1=1  # Replace with actual ID from response
```

### Step 1.2: Verify Asset Created with Metadata

```bash
curl -X POST "$BASE_URL/assets" \
  -H "Content-Type: application/json" \
  -d "{\"asset_ids\": [$ASSET_ID_1]}" | jq
```

**Expected Output**:
```json
[
  {
    "asset_id": 1,
    "display_name": "Apple Inc.",
    "identifier": "AAPL",
    "identifier_type": "TICKER",
    "currency": "USD",
    "asset_type": "STOCK",
    "valuation_model": "MARKET_PRICE",
    "active": true,
    "classification_params": {
      "investment_type": "stock",
      "sector": "Technology",
      "short_description": "Apple Inc. designs, manufactures, and markets smartphones",
      "geographic_area": {
        "USA": "0.6000",
        "CHN": "0.2500",
        "EUR": "0.1500"
      }
    }
  }
]
```

**✅ Verify**:
- `classification_params` is present
- `geographic_area` sums to 1.0 (or close due to rounding)
- `sector` = "Technology"

---

## 🔌 Test Scenario 2: Create Asset with yfinance Provider (Auto-Metadata)

### Step 2.1: Create Asset without Metadata

```bash
curl -X POST "$BASE_URL/assets/bulk" \
  -H "Content-Type: application/json" \
  -d '{
    "assets": [
      {
        "display_name": "Microsoft Corporation",
        "identifier": "MSFT",
        "identifier_type": "TICKER",
        "currency": "USD",
        "asset_type": "STOCK",
        "valuation_model": "MARKET_PRICE"
      }
    ]
  }' | jq
```

**Expected Output**:
```json
{
  "results": [
    {
      "asset_id": 2,
      "success": true,
      "message": "Asset created successfully",
      "display_name": "Microsoft Corporation",
      "identifier": "MSFT"
    }
  ],
  "success_count": 1,
  "failed_count": 0
}
```

```bash
export ASSET_ID_2=2  # Replace with actual ID
```

### Step 2.2: Assign yfinance Provider

```bash
curl -X POST "$BASE_URL/assets/${ASSET_ID_2}/provider" \
  -H "Content-Type: application/json" \
  -d '{
    "provider_code": "yfinance"
  }' | jq
```

**Expected Output**:
```json
{
  "asset_id": 2,
  "success": true,
  "message": "Provider yfinance assigned",
  "metadata_updated": true,
  "metadata_changes": [
    {
      "field": "investment_type",
      "old": null,
      "new": "\"stock\""
    },
    {
      "field": "sector",
      "old": null,
      "new": "\"Technology\""
    },
    {
      "field": "short_description",
      "old": null,
      "new": "\"Microsoft Corporation develops...\""
    },
    {
      "field": "geographic_area",
      "old": null,
      "new": "{\"USA\": \"0.6000\", ...}"
    }
  ]
}
```

**✅ Verify**:
- `metadata_updated` = true
- `metadata_changes` contains 3-4 fields
- yfinance fetched real data from Yahoo Finance

### Step 2.3: Verify Metadata Auto-Populated

```bash
curl -X POST "$BASE_URL/assets" \
  -H "Content-Type: application/json" \
  -d "{\"asset_ids\": [$ASSET_ID_2]}" | jq '.[] | {asset_id, display_name, classification_params}'
```

**Expected Output**:
```json
{
  "asset_id": 2,
  "display_name": "Microsoft Corporation",
  "classification_params": {
    "investment_type": "stock",
    "sector": "Technology",
    "short_description": "Microsoft Corporation develops, licenses, and supports software...",
    "geographic_area": {
      "USA": "0.6000",
      "CHN": "0.2000",
      "EMEA": "0.2000"
    }
  }
}
```

**✅ Verify**:
- `classification_params` is NOT null
- `sector` is auto-populated (e.g., "Technology")
- `short_description` is auto-populated
- `geographic_area` might be present (depends on yfinance data availability)

---

## ✏️ Test Scenario 3: PATCH Metadata with Geographic Area

### ⚠️ **IMPORTANT: Country Code Normalization**

The system **automatically normalizes** country codes to **ISO 3166-1 alpha-3** format (3-letter uppercase codes).

**✅ Use ISO 3166-1 alpha-3 codes** (recommended):
```json
{
  "geographic_area": {
    "USA": "0.60",  // United States
    "CHN": "0.20",  // China
    "FRA": "0.10",  // France
    "DEU": "0.05",  // Germany
    "GBR": "0.05"   // United Kingdom
  }
}
```

**❌ Avoid ambiguous codes** (they may normalize unexpectedly):
- `"eur"` → May become `"FRA"`, `"CZE"`, or other EU countries (fuzzy match)
- `"cina"` → Normalizes to `"CHN"` (Italian name)
- `"usa"` → Normalizes to `"USA"` (lowercase → uppercase)
- `"ASIA"` → Not a country code! (region, not specific country)

**💡 Common ISO 3166-1 alpha-3 Codes**:
- USA - United States
- CHN - China
- JPN - Japan
- DEU - Germany
- GBR - United Kingdom
- FRA - France
- ITA - Italy
- ESP - Spain
- BRA - Brazil
- IND - India
- RUS - Russia
- CAN - Canada

**Normalization Rules**:
1. System accepts ISO-2 (US), ISO-3 (USA), or country names (United States)
2. All inputs are normalized to ISO-3 via `pycountry` fuzzy matching
3. **Ambiguous inputs** (like "eur") may normalize to unexpected countries
4. Always use ISO-3 codes for predictable results

---

### Step 3.1: Update Geographic Area Only

```bash
curl -X PATCH "$BASE_URL/assets/metadata" \
  -H "Content-Type: application/json" \
  -d "{
    \"assets\": [
      {
        \"asset_id\": $ASSET_ID_2,
        \"patch\": {
          \"geographic_area\": {
            \"USA\": \"0.50\",
            \"FRA\": \"0.30\",
            \"CHN\": \"0.20\"
          }
        }
      }
    ]
  }" | jq
```

**Expected Output**:
```json
[
  {
    "asset_id": 2,
    "success": true,
    "message": "Metadata updated successfully",
    "changes": [
      {
        "field": "geographic_area",
        "old_value": "{\"USA\": \"0.6000\", \"CHN\": \"0.2000\", \"GBR\": \"0.2000\"}",
        "new_value": "{\"USA\": \"0.5000\", \"FRA\": \"0.3000\", \"CHN\": \"0.2000\"}"
      }
    ]
  }
]
```

**✅ Verify**:
- `success` = true
- `changes` array shows geographic_area change with `old_value` and `new_value`
- Other fields (sector, investment_type) are NOT in changes (PATCH semantics = absent fields ignored)

### Step 3.2: Verify Changes Persisted

```bash
curl -X POST "$BASE_URL/assets" \
  -H "Content-Type: application/json" \
  -d "{\"asset_ids\": [$ASSET_ID_2]}" | jq '.[].classification_params.geographic_area'
```

**Expected Output**:
```json
{
  "USA": "0.5000",
  "FRA": "0.3000",
  "CHN": "0.2000"
}
```

**✅ Verify**:
- Geographic area matches PATCH request (codes normalized to ISO-3)
- Sum = 1.0
- Country codes are uppercase ISO-3

### Step 3.3: Clear a Field with null

```bash
curl -X PATCH "$BASE_URL/assets/metadata" \
  -H "Content-Type: application/json" \
  -d "{
    \"assets\": [
      {
        \"asset_id\": $ASSET_ID_2,
        \"patch\": {
          \"short_description\": null
        }
      }
    ]
  }" | jq
```

**Expected Output**:
```json
[
  {
    "asset_id": 2,
    "success": true,
    "message": "updated",
    "changes": [
      {
        "field": "short_description",
        "old": "\"Microsoft Corporation develops...\"",
        "new": "null"
      }
    ]
  }
]
```

**✅ Verify**:
- `short_description` cleared (old value shown, new = null)
- Other fields unchanged

---

## 📊 Test Scenario 4: Bulk Read Assets

### Step 4.1: List All Assets

```bash
curl -X GET "$BASE_URL/assets/list?active=true" | jq
```

**Expected Output**:
```json
[
  {
    "asset_id": 1,
    "display_name": "Apple Inc.",
    "identifier": "AAPL",
    "identifier_type": "TICKER",
    "currency": "USD",
    "asset_type": "STOCK",
    "valuation_model": "MARKET_PRICE",
    "active": true,
    "has_provider": false,
    "has_metadata": true
  },
  {
    "asset_id": 2,
    "display_name": "Microsoft Corporation",
    "identifier": "MSFT",
    "identifier_type": "TICKER",
    "currency": "USD",
    "asset_type": "STOCK",
    "valuation_model": "MARKET_PRICE",
    "active": true,
    "has_provider": true,
    "has_metadata": true
  }
]
```

**✅ Verify**:
- Both assets returned
- `has_provider` = true for MSFT (yfinance assigned)
- `has_provider` = false for AAPL (no provider)
- `has_metadata` = true for both

### Step 4.2: Filter by Currency

```bash
curl -X GET "$BASE_URL/assets/list?currency=USD" | jq 'length'
```

**Expected Output**: `2` (both assets are USD)

### Step 4.3: Search by Name

```bash
curl -X GET "$BASE_URL/assets/list?search=Apple" | jq 'length'
```

**Expected Output**: `1` (only Apple matches)

### Step 4.4: Bulk Read Specific Assets (with full metadata)

```bash
curl -X POST "$BASE_URL/assets" \
  -H "Content-Type: application/json" \
  -d "{\"asset_ids\": [$ASSET_ID_1, $ASSET_ID_2]}" | jq
```

**Expected Output**:
```json
[
  {
    "asset_id": 1,
    "display_name": "Apple Inc.",
    "classification_params": { ... },
    ...
  },
  {
    "asset_id": 2,
    "display_name": "Microsoft Corporation",
    "classification_params": { ... },
    ...
  }
]
```

**✅ Verify**:
- Both assets returned in request order
- Full `classification_params` included

---

## 🔄 Test Scenario 5: Refresh Metadata from Provider

### Step 5.1: Single Asset Metadata Refresh

```bash
curl -X POST "$BASE_URL/assets/${ASSET_ID_2}/metadata/refresh" | jq
```

**Expected Output**:
```json
{
  "asset_id": 2,
  "success": true,
  "message": "Metadata refreshed from provider yfinance",
  "changes": [
    {
      "field": "sector",
      "old": "\"Technology\"",
      "new": "\"Technology\""
    }
  ]
}
```

**✅ Verify**:
- `success` = true
- `changes` array may be empty if no updates from provider
- If provider data changed, new values are merged

### Step 5.2: Bulk Metadata Refresh

```bash
curl -X POST "$BASE_URL/assets/metadata/refresh/bulk" \
  -H "Content-Type: application/json" \
  -d "{\"asset_ids\": [$ASSET_ID_1, $ASSET_ID_2]}" | jq
```

**Expected Output**:
```json
{
  "results": [
    {
      "asset_id": 1,
      "success": false,
      "message": "No provider assigned for asset 1"
    },
    {
      "asset_id": 2,
      "success": true,
      "message": "Metadata refreshed from provider yfinance",
      "changes": []
    }
  ],
  "success_count": 1,
  "failed_count": 1
}
```

**✅ Verify**:
- Asset 1 fails (no provider)
- Asset 2 succeeds (yfinance assigned)
- Partial success allowed

---

## 💰 Test Scenario 6: Price Operations

### Step 6.1: Fetch Prices from yfinance

```bash
curl -X POST "$BASE_URL/assets/${ASSET_ID_2}/prices-refresh?start_date=2025-11-01&end_date=2025-11-22&force=false" | jq
```

**Expected Output**:
```json
{
  "asset_id": 2,
  "inserted_count": 15,
  "updated_count": 0,
  "skipped_count": 0,
  "message": "Prices refreshed successfully from provider yfinance"
}
```

**✅ Verify**:
- `inserted_count` > 0 (working days between dates)
- Prices fetched from Yahoo Finance

### Step 6.2: Query Prices with Backward-Fill

```bash
curl -X GET "$BASE_URL/assets/${ASSET_ID_2}/prices?start_date=2025-11-15&end_date=2025-11-22" | jq 'length'
```

**Expected Output**: `8` (includes weekends via backward-fill)

**Check backward-fill info**:
```bash
curl -X GET "$BASE_URL/assets/${ASSET_ID_2}/prices?start_date=2025-11-16&end_date=2025-11-17" | jq
```

**Expected Output** (if 2025-11-16 is Saturday):
```json
[
  {
    "date": "2025-11-16",
    "close": "420.50",
    "currency": "USD",
    "backward_fill_info": {
      "actual_rate_date": "2025-11-15",
      "days_back": 1
    }
  },
  {
    "date": "2025-11-17",
    "close": "420.50",
    "currency": "USD",
    "backward_fill_info": {
      "actual_rate_date": "2025-11-15",
      "days_back": 2
    }
  }
]
```

**✅ Verify**:
- Weekend dates have `backward_fill_info`
- `days_back` increments correctly

---

## 🗑️ Test Scenario 7: Delete Assets

### Step 7.1: Try Delete Asset with Provider Assigned

```bash
curl -X DELETE "$BASE_URL/assets/bulk" \
  -H "Content-Type: application/json" \
  -d "{\"asset_ids\": [$ASSET_ID_2]}" | jq
```

**Expected Output**:
```json
{
  "results": [
    {
      "asset_id": 2,
      "success": true,
      "message": "Asset deleted successfully"
    }
  ],
  "success_count": 1,
  "failed_count": 0
}
```

**✅ Verify**:
- Asset deleted (CASCADE deletes provider_assignment and price_history)

### Step 7.2: Verify Asset Deleted

```bash
curl -X GET "$BASE_URL/assets/list" | jq 'length'
```

**Expected Output**: `1` (only Apple remains)

### Step 7.3: Delete Remaining Asset

```bash
curl -X DELETE "$BASE_URL/assets/bulk" \
  -H "Content-Type: application/json" \
  -d "{\"asset_ids\": [$ASSET_ID_1]}" | jq
```

**Expected Output**:
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

### Step 7.4: Verify All Assets Deleted

```bash
curl -X GET "$BASE_URL/assets/list" | jq
```

**Expected Output**: `[]` (empty array)

---

## 🎯 Test Scenario 8: Edge Cases & Error Handling

### Test 8.1: Duplicate Identifier

```bash
curl -X POST "$BASE_URL/assets/bulk" \
  -H "Content-Type: application/json" \
  -d '{
    "assets": [
      {"display_name": "Test1", "identifier": "DUP", "identifier_type": "TICKER", "currency": "USD", "asset_type": "STOCK", "valuation_model": "MARKET_PRICE"},
      {"display_name": "Test2", "identifier": "DUP", "identifier_type": "TICKER", "currency": "USD", "asset_type": "STOCK", "valuation_model": "MARKET_PRICE"}
    ]
  }' | jq
```

**Expected Output**:
```json
{
  "results": [
    {
      "asset_id": 3,
      "success": true,
      "message": "Asset created successfully",
      "display_name": "Test1",
      "identifier": "DUP"
    },
    {
      "asset_id": null,
      "success": false,
      "message": "Asset with identifier 'DUP' already exists",
      "display_name": "Test2",
      "identifier": "DUP"
    }
  ],
  "success_count": 1,
  "failed_count": 1
}
```

**✅ Verify**:
- First asset created
- Second asset rejected (duplicate identifier)
- Partial success allowed

### Test 8.2: Invalid Geographic Area (sum != 1.0)

```bash
curl -X PATCH "$BASE_URL/assets/metadata" \
  -H "Content-Type: application/json" \
  -d '{
    "assets": [
      {
        "asset_id": 3,
        "patch": {
          "geographic_area": {
            "USA": "0.50",
            "EUR": "0.60"
          }
        }
      }
    ]
  }' | jq
```

**Expected Output**:
```json
[
  {
    "asset_id": 3,
    "success": false,
    "message": "Geographic area values must sum to 1.0 (got 1.10)"
  }
]
```

**✅ Verify**:
- Update rejected
- Clear error message

### Test 8.3: Lowercase Currency Auto-Uppercase

```bash
curl -X POST "$BASE_URL/assets/bulk" \
  -H "Content-Type: application/json" \
  -d '{
    "assets": [
      {
        "display_name": "Test Lowercase",
        "identifier": "TESTLC",
        "identifier_type": "TICKER",
        "currency": "eur",
        "asset_type": "STOCK",
        "valuation_model": "MARKET_PRICE"
      }
    ]
  }' | jq '.results[].display_name, .results[].identifier' && \
curl -X POST "$BASE_URL/assets" \
  -H "Content-Type: application/json" \
  -d '{"asset_ids": [4]}' | jq '.[].currency'
```

**Expected Output**:
```
"Test Lowercase"
"TESTLC"
"EUR"
```

**✅ Verify**:
- Currency auto-uppercased from "eur" to "EUR"
- Validator works correctly

---

## 🧹 Cleanup

### Delete All Test Assets

```bash
# Get all asset IDs
ASSET_IDS=$(curl -s -X GET "$BASE_URL/assets/list" | jq '[.[].asset_id]')

# Delete all
curl -X DELETE "$BASE_URL/assets/bulk" \
  -H "Content-Type: application/json" \
  -d "{\"asset_ids\": $ASSET_IDS}" | jq
```

**Verify cleanup**:
```bash
curl -X GET "$BASE_URL/assets/list" | jq 'length'
```

**Expected Output**: `0`

---

## ✅ Success Criteria Checklist

After completing all test scenarios, verify:

- [x] **Asset Creation**: Single and bulk creation works
- [x] **Provider Assignment**: yfinance provider assigns successfully
- [x] **Metadata Auto-Population**: yfinance fetches real metadata
- [x] **PATCH Operations**: Geographic area update works, absent fields ignored
- [x] **Bulk Read**: List and bulk read return correct data
- [x] **Metadata Refresh**: Single and bulk refresh work
- [x] **Price Operations**: Fetch and query with backward-fill work
- [x] **Delete Operations**: CASCADE deletion works
- [x] **Edge Cases**: Duplicates rejected, validation errors handled
- [x] **Validators**: Currency uppercase, geographic_area sum validation
- [x] **Partial Success**: Bulk operations allow per-item failures

---

## 🐛 Troubleshooting

### Server Not Starting
```bash
# Check if port 8000 is in use
lsof -i :8000

# Kill existing process
pkill -f "uvicorn backend.app.main:app"

# Restart server
./dev.sh server
```

### yfinance Provider Fails
```bash
# Check internet connection
curl -I https://finance.yahoo.com

# Check provider is registered
curl -X GET "$BASE_URL/assets/providers" | jq '.[] | select(.code == "yfinance")'
```

### Database Errors
```bash
# Reset test database
rm backend/data/sqlite/app.db

# Recreate with migrations
cd backend
pipenv run alembic upgrade head
```

---

## 📚 Additional Resources

- **API Documentation**: `http://localhost:8000/api/v1/docs` (Swagger UI)
- **Asset Management Examples**: `docs/api-examples/asset-management.md`
- **Schema Reference**: `backend/app/schemas/assets.py`
- **Service Logic**: `backend/app/services/asset_crud.py`

---

**Testing Complete!** 🎉

If all scenarios pass, the Asset Management subsystem is working correctly and ready for integration with the Transaction system (Phase 5).


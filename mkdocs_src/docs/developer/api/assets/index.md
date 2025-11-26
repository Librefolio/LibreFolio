# Asset Management API Examples

This guide provides practical `curl` examples for managing assets in LibreFolio.

**Base URL**: `http://localhost:8000/api/v1`

---

## Asset Management

### Create Assets

`POST /assets/bulk`

Create one or more assets in a single request.

**Single Asset:**
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

**With Metadata:**
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
          "geographic_area": { "USA": "1.0" }
        }
      }
    ]
  }'
```

### List Assets

`GET /assets/list`

Retrieve assets with optional filters.

**List all active assets:**
```bash
curl "http://localhost:8000/api/v1/assets/list"
```

**Filter by currency:**
```bash
curl "http://localhost:8000/api/v1/assets/list?currency=USD"
```

### Delete Assets

`DELETE /assets/bulk`

Delete one or more assets.

```bash
curl -X DELETE "http://localhost:8000/api/v1/assets/bulk" \
  -H "Content-Type: application/json" \
  -d '{
    "asset_ids": [1, 2, 3]
  }'
```

---

## Metadata Management

### Update Asset Metadata

`PATCH /assets/metadata`

Partially update the metadata for one or more assets.

```bash
curl -X PATCH http://localhost:8000/api/v1/assets/metadata \
  -H "Content-Type: application/json" \
  -d '{
    "assets": [
      {
        "asset_id": 1,
        "patch": {
          "sector": "Technology"
        }
      }
    ]
  }'
```

### Read Asset Metadata

`POST /assets`

Read the full details, including metadata, for a list of assets.
```bash
curl -X POST http://localhost:8000/api/v1/assets \
  -H "Content-Type: application/json" \
  -d '{
    "asset_ids": [1, 2]
  }'
```

### Refresh Metadata from Provider

`POST /assets/{asset_id}/metadata/refresh`

Trigger a refresh of an asset's metadata from its assigned data provider.

```bash
curl -X POST http://localhost:8000/api/v1/assets/1/metadata/refresh
```
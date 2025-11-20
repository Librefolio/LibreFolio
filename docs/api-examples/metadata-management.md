# Asset Metadata Management - API Examples

This document provides practical examples for managing asset classification metadata through the LibreFolio API.

## Table of Contents

1. [PATCH Metadata with Geographic Area](#patch-metadata-with-geographic-area)
2. [Bulk Read Assets with Metadata](#bulk-read-assets-with-metadata)
3. [Refresh Metadata from Provider](#refresh-metadata-from-provider)
4. [Common Validation Errors](#common-validation-errors)

---

## PATCH Metadata with Geographic Area

### Endpoint
```
PATCH /api/v1/assets/metadata
```

### Update Investment Type and Geographic Area

**Request**:
```bash
curl -X PATCH http://localhost:8000/api/v1/assets/metadata \
  -H "Content-Type: application/json" \
  -d '{
    "assets": [
      {
        "asset_id": 1,
        "patch": {
          "investment_type": "etf",
          "sector": "Technology",
          "geographic_area": {
            "USA": "0.6",
            "GBR": "0.3",
            "ITA": "0.1"
          }
        }
      }
    ]
  }'
```

**Response** (200 OK):
```json
[
  {
    "asset_id": 1,
    "success": true,
    "message": "updated",
    "changes": [
      {
        "field": "investment_type",
        "old": "stock",
        "new": "etf"
      },
      {
        "field": "sector",
        "old": null,
        "new": "Technology"
      },
      {
        "field": "geographic_area",
        "old": null,
        "new": "{\"USA\": \"0.6000\", \"GBR\": \"0.3000\", \"ITA\": \"0.1000\"}"
      }
    ],
    "warnings": null
  }
]
```

### Clear a Field with null

**Request**:
```bash
curl -X PATCH http://localhost:8000/api/v1/assets/metadata \
  -H "Content-Type: application/json" \
  -d '{
    "assets": [
      {
        "asset_id": 1,
        "patch": {
          "sector": null
        }
      }
    ]
  }'
```

**Response** (200 OK):
```json
[
  {
    "asset_id": 1,
    "success": true,
    "message": "updated",
    "changes": [
      {
        "field": "sector",
        "old": "Technology",
        "new": null
      }
    ]
  }
]
```

### Update Multiple Assets

**Request**:
```bash
curl -X PATCH http://localhost:8000/api/v1/assets/metadata \
  -H "Content-Type: application/json" \
  -d '{
    "assets": [
      {
        "asset_id": 1,
        "patch": {
          "sector": "Finance"
        }
      },
      {
        "asset_id": 2,
        "patch": {
          "investment_type": "stock",
          "geographic_area": {
            "ITA": "1.0"
          }
        }
      }
    ]
  }'
```

**Response** (200 OK, partial success):
```json
[
  {
    "asset_id": 1,
    "success": true,
    "message": "updated",
    "changes": [...]
  },
  {
    "asset_id": 2,
    "success": false,
    "message": "Invalid country code: INVALID"
  }
]
```

### PATCH Semantics Summary

| Field in Patch | Behavior |
|----------------|----------|
| Absent | Field unchanged |
| `null` | Field cleared |
| Value | Field updated |

**Geographic Area Special Rules**:
- Full replacement (not merge)
- Countries normalized to ISO-3166-A3 (US → USA, GB → GBR, etc.)
- Weights must sum to 1.0 (±0.0001 tolerance)
- Weights quantized to 4 decimal places

---

## Bulk Read Assets with Metadata

### Endpoint
```
POST /api/v1/assets
```

### Read Multiple Assets

**Request**:
```bash
curl -X POST http://localhost:8000/api/v1/assets \
  -H "Content-Type: application/json" \
  -d '{
    "asset_ids": [1, 2, 3]
  }'
```

**Response** (200 OK):
```json
[
  {
    "asset_id": 1,
    "display_name": "Apple Inc.",
    "identifier": "AAPL",
    "currency": "USD",
    "classification_params": {
      "investment_type": "stock",
      "sector": "Technology",
      "short_description": "Consumer electronics and software",
      "geographic_area": {
        "USA": "1.0000"
      }
    }
  },
  {
    "asset_id": 2,
    "display_name": "Vanguard S&P 500 ETF",
    "identifier": "VOO",
    "currency": "USD",
    "classification_params": {
      "investment_type": "etf",
      "geographic_area": {
        "USA": "1.0000"
      }
    }
  },
  {
    "asset_id": 3,
    "display_name": "BTP Italia 2025",
    "identifier": "IT0005424251",
    "currency": "EUR",
    "classification_params": null
  }
]
```

**Notes**:
- Assets returned in request order
- Missing asset IDs silently skipped
- `classification_params` may be `null` if not set

---

## Refresh Metadata from Provider

### Single Asset Refresh

**Endpoint**:
```
POST /api/v1/assets/{asset_id}/metadata/refresh
```

**Request**:
```bash
curl -X POST http://localhost:8000/api/v1/assets/1/metadata/refresh
```

**Response** (200 OK, success):
```json
{
  "asset_id": 1,
  "success": true,
  "message": "Metadata refreshed from yfinance",
  "changes": [
    {
      "field": "sector",
      "old": null,
      "new": "Technology"
    },
    {
      "field": "investment_type",
      "old": "stock",
      "new": "stock"
    }
  ],
  "warnings": null
}
```

**Response** (200 OK, no provider):
```json
{
  "asset_id": 1,
  "success": false,
  "message": "No provider assigned to asset",
  "changes": null,
  "warnings": null
}
```

**Response** (200 OK, provider doesn't support metadata):
```json
{
  "asset_id": 1,
  "success": false,
  "message": "Provider cssscraper does not support metadata",
  "changes": null,
  "warnings": null
}
```

### Bulk Metadata Refresh

**Endpoint**:
```
POST /api/v1/assets/metadata/refresh/bulk
```

**Request**:
```bash
curl -X POST http://localhost:8000/api/v1/assets/metadata/refresh/bulk \
  -H "Content-Type: application/json" \
  -d '{
    "asset_ids": [1, 2, 3]
  }'
```

**Response** (200 OK, partial success):
```json
{
  "results": [
    {
      "asset_id": 1,
      "success": true,
      "message": "Metadata refreshed from yfinance",
      "changes": [
        {"field": "sector", "old": null, "new": "Technology"}
      ]
    },
    {
      "asset_id": 2,
      "success": false,
      "message": "No provider assigned to asset"
    },
    {
      "asset_id": 3,
      "success": true,
      "message": "No metadata changes"
    }
  ],
  "success_count": 2,
  "failed_count": 1
}
```

**Provider Requirements**:
- Asset must have a provider assigned (`POST /api/v1/assets/provider/bulk`)
- Provider must support metadata fetching (e.g., `yfinance`)
- Provider-fetched data takes precedence over existing metadata

---

## Common Validation Errors

### Invalid Country Code

**Request**:
```json
{
  "assets": [
    {
      "asset_id": 1,
      "patch": {
        "geographic_area": {
          "INVALID": "1.0"
        }
      }
    }
  ]
}
```

**Response**:
```json
[
  {
    "asset_id": 1,
    "success": false,
    "message": "Invalid country code: INVALID"
  }
]
```

### Geographic Area Sum != 1.0

**Request**:
```json
{
  "assets": [
    {
      "asset_id": 1,
      "patch": {
        "geographic_area": {
          "USA": "0.5",
          "GBR": "0.4"
        }
      }
    }
  ]
}
```

**Response**:
```json
[
  {
    "asset_id": 1,
    "success": false,
    "message": "Geographic area weights must sum to 1.0 (got 0.9)"
  }
]
```

### Negative Weight

**Request**:
```json
{
  "assets": [
    {
      "asset_id": 1,
      "patch": {
        "geographic_area": {
          "USA": "-0.5",
          "GBR": "1.5"
        }
      }
    }
  ]
}
```

**Response**:
```json
[
  {
    "asset_id": 1,
    "success": false,
    "message": "Geographic area weights must be non-negative"
  }
]
```

---

## Country Code Normalization

The API automatically normalizes country identifiers to ISO-3166-A3 codes:

| Input | Normalized Output |
|-------|------------------|
| `US` | `USA` |
| `GB` | `GBR` |
| `IT` | `ITA` |
| `FR` | `FRA` |
| `United States` | `USA` |
| `Italy` | `ITA` |

**Example**:
```json
// Input
{
  "geographic_area": {
    "US": "0.6",
    "Italy": "0.4"
  }
}

// Stored as
{
  "geographic_area": {
    "USA": "0.6000",
    "ITA": "0.4000"
  }
}
```

---

## Tolerance Rules

### Geographic Area Sum Tolerance

- **Target**: 1.0
- **Tolerance**: ±0.0001 (0.01%)
- **Behavior**: Values within tolerance are renormalized to exactly 1.0

**Example**:
```json
// Input (sum = 0.999999)
{
  "USA": "0.333333",
  "GBR": "0.333333",
  "ITA": "0.333333"
}

// Normalized (sum = 1.0000)
{
  "USA": "0.3333",
  "GBR": "0.3334",
  "ITA": "0.3333"
}
```

---

## Weight Quantization

All geographic area weights are quantized to **4 decimal places** using ROUND_HALF_EVEN:

```
0.123456789 → 0.1235
0.60375 → 0.6038
0.6 → 0.6000
```

---

## Related Endpoints

- `GET /api/v1/assets/providers` - List available providers
- `POST /api/v1/assets/provider/bulk` - Assign providers to assets
- `POST /api/v1/assets/prices/bulk` - Bulk upsert prices
- `POST /api/v1/assets/refresh/bulk` - Bulk refresh prices (triggers metadata refresh)

---

## See Also

- [Database Schema Documentation](../database-schema.md) - classification_params field structure
- [Metadata Management Guide](../metadata-management.md) - Developer guide
- [API Development Guide](../api-development-guide.md) - General API patterns


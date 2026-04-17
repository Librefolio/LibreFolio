---
applyTo: "backend/app/schemas/**"
---

# Pydantic Schemas Reference

## Structure

```text
backend/app/schemas/
├── common.py          # Shared base classes (Currency, BackwardFillInfo, BaseBulkResponse, etc.)
├── assets.py          # Asset CRUD schemas (FAAssetCreateItem, FAinfoResponse, etc.)
├── prices.py          # Price schemas (FAUpsert, FAPriceQueryItem, etc.)
├── provider.py        # Provider schemas (FAProviderInfo, FAProviderAssignmentItem, etc.)
├── refresh.py         # Refresh/sync schemas
├── fx.py              # FX rate schemas
├── brim.py            # Broker import schemas (BRIMPluginInfo, BRIMExtractedAssetInfo, etc.)
├── brokers.py         # Broker CRUD schemas
├── transactions.py    # Transaction schemas
├── auth.py            # Auth schemas
├── settings.py        # Settings schemas
├── uploads.py         # File upload schemas
├── users.py           # User schemas
└── utilities.py       # Country/sector/currency list schemas
```

## Key Base Class: `common.py`

The `common.py` module provides shared building blocks used across all subsystems:

### Currency
- Validates codes against ISO 4217 (via pycountry) + crypto dictionary
- Supports arithmetic: `+`, `-`, negation, comparison (same currency only)
- `Currency.validate_code(v)` — static method for use in `@field_validator` on any schema
- Cached validation via `@lru_cache(256)` for performance

### Response Base Classes (Generic)

| Class | Use | Key Fields |
|-------|-----|------------|
| `BaseListResponse[T]` | List/collection endpoints | `items: List[T]` |
| `BaseBulkResponse[T]` | Bulk operation results | `results`, `success_count`, computed `failed_count` |
| `BaseBulkDeleteResponse[T]` | Bulk deletion results | Extends BaseBulkResponse + `total_deleted` |
| `BaseDeleteResult` | Single delete result | `success`, `deleted_count`, `message` |

### Other Shared Models

| Model | Use |
|-------|-----|
| `BackwardFillInfo` | Gap-fill info when exact date has no data (shared by FA and FX) |
| `DateRangeModel` | Inclusive date range [start, end] with validation |
| `OldNew[T]` | Field change representation (old/new values) for metadata refresh |

## Naming Conventions

| Prefix | Domain |
|--------|--------|
| `FA*` | Financial Assets (e.g. `FAAssetCreateItem`, `FAUpsert`) |
| `FX*` | Foreign Exchange (e.g. `FXRateResponse`) |
| `BRIM*` | Broker Report Import (e.g. `BRIMPluginInfo`) |

## Design Rules

- **`ConfigDict(extra="forbid")`** on all schemas — reject unknown fields
- **Decimal columns**: use `Decimal` type, serialize as string in JSON
- **Date fields**: accept ISO string, `date`, or `datetime` via `parse_ISO_date()` validators
- **Optional fields with `Field(None)`**: explicit about nullability
- **No backward compatibility**: clean refactoring preferred over legacy support


---
applyTo: "backend/app/schemas/**"
---

# Pydantic Schemas Reference

## Structure

```text
backend/app/schemas/
├── common.py          # Shared base classes (Currency, BackwardFillInfo, BaseBulkResponse, etc.)
├── assets/            # Asset schemas, one module per theme (C3):
│   ├── assets.py      #   the asset and its CRUD (FAAssetCreateItem, FAinfoResponse, patch, merge, etc.)
│   ├── metadata.py    #   distributions, classification, metadata (FAClassificationParams, FAGeographicArea, etc.)
│   ├── scheduled_investment.py  # financial enums and the interest schedule (FAScheduledInvestmentSchedule, etc.)
│   └── events.py      #   asset events (FAAssetEventPoint, event CRUD)
├── prices.py          # Price schemas (FAUpsert, FAPriceQueryItem, etc.)
├── provider.py        # Provider schemas (FAProviderInfo, FAProviderAssignmentItem, etc.)
├── refresh.py         # Refresh/sync schemas
├── fx.py              # FX rate schemas
├── brim.py            # Broker import schemas (BRIMPluginInfo, BRIMExtractedAssetInfo, etc.)
├── brokers.py         # Broker CRUD schemas
├── transactions/      # Transaction schemas (TX*), one module per theme; __init__.py holds only a docstring
│   ├── transactions.py   # Items: TXCreateItem, TXReadItem, TXUpdateItem, TXQueryParams, TXDeleteItem
│   ├── batch.py          # POST /transactions/validate and /commit: TXMixedBatch, TXBatchResponse, TXValidationIssue, …
│   ├── event_suggest.py  # POST /transactions/events/suggest
│   ├── promotion.py      # Pair promotion and its suggestions (POST /transactions/transfers/promote, …)
│   └── type_metadata.py  # TX_TYPE_METADATA, event type metadata, GET /transactions/types
├── auth.py            # Auth schemas
├── settings.py        # Settings schemas
├── uploads.py         # File upload schemas
├── users.py           # User schemas
└── utilities.py       # Country/sector/currency list schemas
```

## Key Base Class: `common.py`

The `common.py` module provides shared building blocks used across all subsystems:

### Currency
- Validates codes against ISO 4217 (via pycountry)
- Supports arithmetic: `+`, `-`, negation, comparison (same currency only)
- `Currency.validate_code(v)` — static method for use in `@field_validator` on any schema
- Cached validation via `@lru_cache(256)` for performance
- **Writes are strict, reads are lenient (E-18).** `Currency.validate_code` and `CurrencyCode` also accept a currency
  name or a numeric code (`"Euro"`, `"978"`) and return them as given, so they are for what is read back from the
  database only. A field a request **stores** uses the strict rule: `IsoCurrencyCode` (a `str` field) or
  `IsoCurrencyAmount` (a `Currency` field, same class and wire shape), both built on `iso_currency_code()` — an ISO
  4217 alphabetic code, any case. Never let the strict rule reach a model the read paths also build from stored rows:
  `FXConversionRouteReadItem` subclasses the request `FXConversionRouteItem`, so it turns the check off with its
  `ClassVar` `iso_currencies_required = False`.
- **What a stored value stands for (E-19a).** `suggested_iso_currency(value)` gives the one ISO code a value means
  (`"978"`, `"Euro"` → `EUR`; a valid code upper-cased), or `None`: no code, two codes (`"Bolívar Soberano"`), past 80
  characters, or a subunit code of `NEVER_RELABELLED_CURRENCY_CODES` (`GBX`, `ZAC`, `ILA`: cents, never relabelled).
  `is_canonical_iso_currency(value)` says whether a value is stored exactly as `iso_currency_code` stores it (`"eur"` is
  not). Quote a refused or stored currency text through `shown_currency_text()` (16 characters), never whole.

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
- **Legacy support decided case-by-case**: prefer migrating to the correct design over keeping an old/wrong path; retain backward compatibility only with a concrete reason (e.g. not breaking a released schema or API)

# Quick Reference: New Patterns After Phase 5 Refactoring

**Date**: November 18, 2025  
**Purpose**: Quick guide for developers working on Phase 6+ tasks

---

## 🎯 Key Changes to Remember

### 1. Schema Organization (CRITICAL)

**❌ OLD WAY** (before Phase 5):

```python
# In api/v1/assets.py - WRONG, don't do this anymore!
class PriceUpsertItem(BaseModel):
    date: date
    close: Decimal
    # ... inline definition
```

**✅ NEW WAY** (after Phase 5):

```python
# In api/v1/assets.py - Import from dedicated modules
from backend.app.schemas.prices import FAUpsertItem, FABulkUpsertRequest
from backend.app.schemas.assets import PricePointModel, CurrentValueModel


@router.post("/prices/bulk", response_model=FABulkUpsertResponse)
async def upsert_prices_bulk(request: FABulkUpsertRequest, ...):
# Use imported schemas, never define inline
```

### 2. Schema Module Map

| What You Need        | Import From           | Class Name Pattern                                  |
|----------------------|-----------------------|-----------------------------------------------------|
| Price point data     | `schemas/assets.py`   | `PricePointModel`                                   |
| Current value        | `schemas/assets.py`   | `CurrentValueModel`                                 |
| Historical data      | `schemas/assets.py`   | `HistoricalDataModel`                               |
| Provider assignment  | `schemas/provider.py` | `FAProviderInfo`, `FABulkAssignRequest`             |
| Price upsert/delete  | `schemas/prices.py`   | `FAUpsertItem`, `FABulkUpsertRequest`               |
| Price refresh        | `schemas/refresh.py`  | `FABulkRefreshRequest`, `FABulkRefreshResponse`     |
| Scheduled investment | `schemas/assets.py`   | `ScheduledInvestmentSchedule`, `InterestRatePeriod` |
| Common utilities     | `schemas/common.py`   | `BackwardFillInfo`, `DateRangeModel`                |
| FX operations        | `schemas/fx.py`       | `FXConvertRequest`, `FXUpsertItem`, etc.            |

### 3. Naming Conventions

**FA Prefix** = Financial Assets (stocks, ETFs, bonds, loans)

- `FAProviderInfo` - Provider metadata
- `FAUpsertItem` - Single price to upsert
- `FABulkAssignRequest` - Bulk provider assignment request
- `FARefreshItem` - Asset refresh request

**FX Prefix** = Foreign Exchange (currency rates)

- `FXProviderInfo` - FX provider metadata
- `FXUpsertItem` - Single rate to upsert
- `FXConvertRequest` - Currency conversion request
- `FXSyncResponse` - Rate sync response

**No Prefix** = Core/shared models

- `PricePointModel` - Foundational price data structure
- `BackwardFillInfo` - Shared backward-fill metadata
- `DateRangeModel` - Reusable date range

### 4. Import Pattern Examples

```python
# Provider development (Phase 6)
from backend.app.schemas.assets import CurrentValueModel, HistoricalDataModel


class MyProvider(AssetProviderBase):
    def get_current_value(self, identifier: str, params: dict) -> CurrentValueModel:
        return CurrentValueModel(
            date=date.today(),
            value=Decimal("100.50"),
            currency="USD"
            )


# API endpoint development
from backend.app.schemas.provider import FAProviderInfo, FABulkAssignRequest
from backend.app.schemas.prices import FABulkUpsertRequest, FABulkUpsertResponse


@router.post("/prices/bulk", response_model=FABulkUpsertResponse)
async def upsert_prices(request: FABulkUpsertRequest):
    # Implementation
    pass


# Service layer
from backend.app.schemas.assets import PricePointModel
from backend.app.schemas.prices import FAUpsertResult


def process_prices(data: list) -> list[FAUpsertResult]:
    # Implementation
    return results
```

---

## 📂 Directory Structure (After Phase 5)

```
backend/app/
├── schemas/                    # All Pydantic models here
│   ├── __init__.py            # 32 exports
│   ├── common.py              # Shared schemas
│   ├── assets.py              # FA core schemas
│   ├── provider.py            # Provider assignment (FA + FX)
│   ├── prices.py              # FA price operations
│   ├── refresh.py             # FA refresh + FX sync
│   └── fx.py                  # FX-specific operations
│
├── api/v1/                    # API endpoints (NO inline Pydantic!)
│   ├── assets.py              # FA endpoints
│   └── fx.py                  # FX endpoints
│
├── services/                  # Business logic
│   ├── asset_source.py        # AssetSourceManager
│   ├── fx.py                  # FX operations
│   └── asset_source_providers/  # Provider plugins
│       ├── yfinance.py
│       ├── cssscraper.py
│       ├── scheduled_investment.py
│       └── mockprov.py
│
└── utils/                     # Utilities
    ├── financial_math.py      # Compound interest, day count
    └── datetime_utils.py      # utcnow()
```

---

## 🧪 Testing Patterns

### Import Test Data

```python
# Use Pydantic schemas for test data construction
from backend.app.schemas.prices import FAUpsertItem
from backend.app.schemas.assets import ScheduledInvestmentSchedule

test_price = FAUpsertItem(
    date=date(2025, 1, 1),
    close=Decimal("100.50"),
    currency="USD"
    )
```

### Provider Testing

```python
# Providers return schema models
from backend.app.schemas.assets import CurrentValueModel


def test_provider_returns_current_value():
    provider = MyProvider()
    result = provider.get_current_value("AAPL", {})

    assert isinstance(result, CurrentValueModel)
    assert result.value > 0
```

---

## 📖 Documentation Structure (Phase 5 Additions)

### Financial Calculations

```
docs/financial-calculations/
├── README.md                           # Overview + links
├── day-count-conventions.md            # ACT/365, ACT/360, etc.
├── interest-types.md                   # Simple vs Compound
├── compounding-frequencies.md          # Annual, quarterly, etc.
└── scheduled-investment-provider.md    # Provider architecture
```

### Testing Guides

```
docs/testing/
├── README.md                           # Overview + test runner
├── utils-tests.md                      # Day count, compound, schemas
├── services-tests.md                   # FX, asset source, synthetic
├── database-tests.md                   # Schema, constraints, integrity
├── api-tests.md                        # REST endpoints
└── synthetic-yield-e2e.md              # Integration scenarios
```

### API Development

```
docs/api-development-guide.md
└── Schema Organization section (NEW)
    ├── Module structure
    ├── Naming conventions (FA/FX)
    ├── Import patterns
    └── FA vs FX comparison table
```

---

## 🚨 Common Mistakes to Avoid

### ❌ DON'T: Define schemas inline

```python
# api/v1/assets.py - WRONG!
class MyRequest(BaseModel):
    field: str
```

### ✅ DO: Import from schemas

```python
# api/v1/assets.py - CORRECT!
from backend.app.schemas.prices import FAUpsertItem
```

### ❌ DON'T: Use old class names

```python
PriceQueryResult  # Removed in Phase 4
ProviderAssignmentItem  # Now FAProviderAssignmentItem
SyncResponseModel  # Now FXSyncResponse
```

### ✅ DO: Use new FA/FX prefixed names

```python
from backend.app.schemas.provider import FAProviderAssignmentItem
from backend.app.schemas.refresh import FXSyncResponse
```

### ❌ DON'T: Mix FA/FX patterns

```python
# FA uses 3-level nesting (Item → Asset → Bulk)
# FX uses 2-level nesting (Item → Bulk)
# Don't mix them!
```

### ✅ DO: Follow domain patterns

```python
# FA: Group by asset first
FABulkUpsertRequest(
    assets=[
        FAUpsert(asset_id=1, prices=[...]),
        FAUpsert(asset_id=2, prices=[...])
        ]
    )

# FX: Direct flat list
FXBulkUpsertRequest(
    rates=[
        FXUpsertItem(...),
        FXUpsertItem(...)
        ]
    )
```

---

## 🎯 Phase 6 Quick Start

Ready to implement new providers? Here's the checklist:

1. ✅ **Import schemas** from `schemas/assets.py`:
   ```python
   from backend.app.schemas.assets import CurrentValueModel, HistoricalDataModel
   ```

2. ✅ **Use decorator**:
   ```python
   @register_provider(AssetProviderRegistry)
   class MyProvider(AssetProviderBase):
       ...
   ```

3. ✅ **Return schema models** (not dicts):
   ```python
   def get_current_value(self, identifier: str, params: dict) -> CurrentValueModel:
       return CurrentValueModel(date=..., value=..., currency=...)
   ```

4. ✅ **Follow test patterns** from existing providers:
    - `test_external/test_yfinance.py`
    - `test_external/test_cssscraper.py`
    - `test_services/test_synthetic_yield.py`

5. ✅ **NO inline Pydantic** in provider code (import from schemas/)

---

## 📚 Reference Documents

### Phase 5 Work

- `05_mid_REMEDIATION_PLAN.md` - Full remediation plan
- `05_mid_REMEDIATION_CHECKLIST.md` - All tasks completed
- `05c_mid_codeFactoring.md` - Schema refactoring checklist (Phase 1-9)

### Reports

- `SCHEMA_REFACTORING_COMPLETE_REPORT.md` - Comprehensive final report
- `SCHEMA_REFACTORING_PHASE7_1_5_REPORT.md` - Phase 1-5 details
- `SCHEMA_REFACTORING_PHASE7_6_7_REPORT.md` - Phase 6-7 details

### Updated Checklist

- `05_implementation_checklist.md` - **NOW UPDATED** with Phase 5 complete

---

**Questions? Check**:

1. `api-development-guide.md` - Schema organization section
2. Existing providers in `services/asset_source_providers/`
3. Reports in `LibreFolio_developer_journal/SCHEMA_REFACTORING_*.md`


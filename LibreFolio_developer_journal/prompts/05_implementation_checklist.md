# Step 05: Asset Provider System - Implementation Checklist

**Reference Document**: [`05_plugins_yfinance_css_synthetic_yield.md`](./05_plugins_yfinance_css_synthetic_yield.md)

**Project**: LibreFolio - Asset Pricing Provider System  
**Start Date**: 6 November 2025  
**Estimated Duration**: 6-8 days  
**Status**: 🟢 Ready to commit — Phase 0 and 0.2.2 completed, test-runner & test DB safety fixes applied, Phase 1 partially implemented

**Last Updated**: 2025-11-07

---

## 📌 High-level status summary

Completed (verified):
- Phase 0 (Database migration + `asset_provider_assignments`) — completed and applied to test/prod DBs
- Phase 0.2.2 (Asset Source Service foundation + tests) — implemented; all service-level tests passing (11/11)
- Test environment safety fixes: `backend/test_scripts/test_db_config.py` and `test_runner.py` updated so tests use `TEST_DATABASE_URL` and never touch prod DB

Current focus / next steps:
- Phase 1: Provider registry and yfinance provider implementation (in progress)
- Phase 2: CSS scraper provider
- Phase 4: Complete synthetic yield logic (deferred, complex)

---

## Phase 0: Database Setup + Common Schemas (1 day)

### 0.1 Database Migration: `asset_provider_assignments` Table

**Reference**: [Phase 0.1 in main doc](./05_plugins_yfinance_css_synthetic_yield.md#phase-0-database-migration--shared-pricing-layer-1-giorno)

- [x] **Create migration file**
  - File: `backend/alembic/versions/5ae234067d65_add_asset_provider_assignments_table.py`
  - Command: `./dev.sh db:migrate "add asset_provider_assignments table"`
  - Table: `asset_provider_assignments`
    - `id` (PK), `asset_id` (UNIQUE, FK), `provider_code`, `provider_params` (JSON)
    - Index: `idx_asset_provider_asset_id`
    - Unique constraint: `uq_asset_provider_asset_id`

- [x] **Create model**
  - File: `backend/app/db/models.py`
  - Class: `AssetProviderAssignment`
  - Export in: `backend/app/db/__init__.py` and `backend/app/db/base.py`

- [x] **Update schema validation test**
  - File: `backend/test_scripts/test_db/db_schema_validate.py`
  - Test is dynamic - automatically detected new table
  - UNIQUE constraint verified automatically
  - FK to `assets` with CASCADE verified automatically

- [x] **Apply migration**
  - Test DB: `./dev.sh db:upgrade backend/data/sqlite/test_app.db` ✅
  - Prod DB: `./dev.sh db:upgrade backend/data/sqlite/app.db` ✅

- [x] **Verify schema validation test passes**
  - Run: `./test_runner.py db validate` ✅

**Notes**:
```
# Migration notes
- Migration revision: 5ae234067d65
- Revises: c19f65d87398 (remove_base_less_than_quote_constraint)
- Foreign key with CASCADE delete to assets table
- 1-to-1 relationship enforced via UNIQUE constraint on asset_id
- Downgrade tested successfully (rollback and reapply)

# Issues encountered
- None - migration applied successfully on both databases

# Completion date
2025-11-06 12:14 CET
```

---

### 0.1.2 Data Migration & Cleanup: Plugin Data → asset_provider_assignments

**Reference**: [Phase 0.1.2 in main doc](./05_plugins_yfinance_css_synthetic_yield.md#012-data-migration--cleanup-move-plugin-data-to-asset_provider_assignments)

**Purpose**: Migrate existing plugin assignments to new table and DROP old columns (DEV environment - safe to drop).

**Design Decision**: Only 2 columns needed (provider_code, provider_params)
- Single provider per asset handles BOTH current and historical data
- `history_data_plugin_*` fields IGNORED (assumed same or unused)
- Provider uses same params for both current and history queries

- [x] **Delete existing databases** (clean slate approach)
  - Backup: `test_app.db` → `test_app.db.backup_before_0.1.2` ✅
  - Backup: `app.db` → `app.db.backup_before_0.1.2` ✅
  - Delete: `test_app.db` ✅
  - Delete: `app.db` ✅

- [x] **Update Asset model FIRST**
  - File: `backend/app/db/models.py` ✅
  - **REMOVED** all 4 plugin_* fields completely ✅
  - Updated docstring to reference asset_provider_assignments table ✅

- [x] **Recreate databases from migrations**
  - Test DB: `./dev.sh db:upgrade backend/data/sqlite/test_app.db` ✅
  - Prod DB: `./dev.sh db:upgrade backend/data/sqlite/app.db` ✅
  - Both at revision: 5ae234067d65 ✅

- [x] **Create migration for column removal**
  - File: `backend/alembic/versions/a63a8001e62c_remove_plugin_columns_from_assets_table.py` ✅
  - Command: `./dev.sh db:migrate "remove plugin columns from assets table"` ✅
  - Alembic auto-detected 4 column removals ✅
  - Fixed: Removed auto-generated FK constraint noise ✅

- [x] **Apply migration to test_app.db**
  - Command: `./dev.sh db:upgrade backend/data/sqlite/test_app.db` ✅
  - Migration applied successfully ✅

- [x] **Verify columns dropped**
  - Query: `SELECT name FROM pragma_table_info('assets')` ✅
  - Confirmed: NO plugin_* columns present ✅

- [x] **Test downgrade**
  - Command: `./dev.sh db:downgrade backend/data/sqlite/test_app.db` ✅
  - Verified: 4 plugin_* columns re-added ✅

- [x] **Re-apply upgrade (final state)**
  - Command: `./dev.sh db:upgrade backend/data/sqlite/test_app.db` ✅
  - Verified: Columns dropped again ✅

- [x] **Apply migration to app.db**
  - Command: `./dev.sh db:upgrade backend/data/sqlite/app.db` ✅

- [x] **Run schema validation test**
  - Command: `./test_runner.py db validate` ✅
  - Result: PASSED ✅

**Notes**:
```
# Migration strategy - DEV environment clean slate
- Deleted existing databases and recreated from scratch
- No data to migrate (fresh start)
- Model updated BEFORE migration (Alembic auto-detected changes)

# Migration details
- Migration revision: a63a8001e62c
- Revises: 5ae234067d65 (add asset_provider_assignments table)
- Upgrade: DROP 4 columns using batch_alter_table
- Downgrade: Re-add 4 columns (schema-only)

# Verification results
- Test DB: Columns dropped: YES ✅
- Test DB: Downgrade/upgrade cycle: SUCCESSFUL ✅
- Prod DB: Columns dropped: YES ✅
- Schema validation: PASSED ✅

# Issues encountered
- Initial FK constraint drop error (auto-generated by Alembic)
- Fixed: Removed unnecessary FK changes from migration

# Completion date
2025-11-06 15:04 CET ✅

# Design note
- Single provider model: 1 asset = 1 provider for both current and history
- asset_provider_assignments: 3 columns (provider_code, provider_params, last_fetch_at)
  - last_fetch_at: Added 2025-11-06 for scheduling/monitoring
- fx_currency_pair_sources: Added fetch_interval column (2025-11-06)
  - fetch_interval: Minutes between fetches (NULL = 1440 = 24h default)

# Migration 001_initial updates (2025-11-06)
- Added last_fetch_at to asset_provider_assignments (NULL = never fetched)
- Added fetch_interval to fx_currency_pair_sources (NULL = default 24h)
- Databases recreated from scratch (DEV environment)
- Schema validation: PASSED ✅
- Models updated to match migration
```

---

### 0.2 Common Schemas + Asset Source Service

**Reference**: [Phase 0.2 in main doc](./05_plugins_yfinance_css_synthetic_yield.md#02-common-schemas--asset-source-service-foundation)

**Decision**: Keep FX (`fx.py`) and Asset (`asset_source.py`) DB operations **SEPARATE**.
- Different tables: `fx_rates` vs `price_history`
- Different query patterns: (base,quote,date) vs (asset_id,date)  
- Different fields: rate vs OHLC
- Share only: `BackwardFillInfo` schema and provider registry pattern

#### 0.2.1 Common Schemas

- [x] **Create common.py**
  - File: `backend/app/schemas/common.py` (NEW folder + file) ✅
  - Contains: `BackwardFillInfo` TypedDict ✅
  - Used by both FX and Asset systems ✅
  - Exact same structure as FX uses now ✅
  - Created `__init__.py` for schemas package ✅

#### 0.2.2 Asset Source Service (with Synthetic Yield)

- [x] **Create asset_source.py**
  - File: `backend/app/services/asset_source.py` ✅
  - Pattern: Similar to `fx.py` but for `price_history` table ✅

- [x] **Define Pydantic Schemas** (migrated from TypedDict) ✅
  - File: `backend/app/schemas/assets.py` (Pydantic v2)
  - `CurrentValueModel` → {value, currency, as_of_date, source} ✅
  - `PricePointModel` → {date, open?, high?, low?, close, volume?, currency, backward_fill_info?} ✅
  - `HistoricalDataModel` → {prices, currency, source} ✅
  - `AssetProviderAssignmentModel` → {asset_id, provider_code, provider_params, last_fetch_at} ✅
  - Import `BackwardFillInfo` from `schemas.common` (shared with FX) ✅
  - Field validators with `@field_validator` for Decimal coercion ✅

- [x] **Define ProviderError exception**
  - Class: `AssetSourceError(Exception)` ✅
  - Fields: `message`, `error_code`, `details` ✅

- [x] **Create abstract base class**
  - Class: `AssetSourceProvider(ABC)` ✅
  - Properties: `provider_code`, `provider_name` ✅
  - Methods: `get_current_value()`, `get_history_value()`, `search()`, `validate_params()` ✅

- [x] **Implement AssetSourceManager** ✅
  - **Provider Assignment**: `bulk_assign_providers()`, `bulk_remove_providers()`, singles ✅
  - **Manual Price CRUD**: `bulk_upsert_prices()`, `bulk_delete_prices()`, singles ✅
  - **Price Query**: `get_prices()` → with backward-fill ✅
  - All bulk operations PRIMARY, singles call bulk with 1 element ✅
  - Note: Provider refresh methods will be added in Phase 1 with yfinance plugin

- [x] **Implement helper functions** ✅
  - `get_price_column_precision(column_name)` → (precision, scale) ✅
  - `truncate_price_to_db_precision(value, column_name)` → Decimal ✅
  - Backward-fill logic integrated in get_prices() ✅

- [x] **Implement synthetic yield module** (integrated in asset_source.py) ✅
  - `calculate_days_between_act365(start, end)` → ACT/365 day fraction ✅
  - Note: Full synthetic yield implementation deferred to Phase 4
  - ACT/365 day count tested and working ✅

- [x] **Create test file** ✅
  - File: `backend/test_scripts/test_services/test_asset_source.py` ✅
  - Pattern: Matches `test_fx_conversion.py` structure ✅
    - Tests return dict with {"passed": bool, "message": str}
    - Results collected in dictionary (not list)
    - Final summary displayed with print_test_summary()
    - Follows same format as other service tests ✅
  
  **Tests implemented and passing** (11/11):
  - ✅ Test 1: Price Column Precision - All 5 columns NUMERIC(18, 6) verified
  - ✅ Test 2: Price Truncation - 4 test cases with different precisions
  - ✅ Test 3: ACT/365 Day Count - 3 test cases (30d, 364d, 365d)
  - ✅ Test 4: Bulk Assign Providers - 3 assets assigned to 2 providers
  - ✅ Test 5: Single Assign Provider - Calls bulk with 1 element
  - ✅ Test 6: Bulk Remove Providers - 3 providers removed
  - ✅ Test 7: Single Remove Provider - Calls bulk with 1 element
  - ✅ Test 8: Bulk Upsert Prices - 3 prices upserted across 2 assets
  - ✅ Test 9: Single Upsert Prices - Calls bulk with 1 element
  - ✅ Test 10: Get Prices with Backward-Fill - 5 days queried, 3 backfilled
  - ✅ Test 11: Bulk Delete Prices - 3 prices deleted across 2 assets
  
  **Test refactored**: 2025-11-07
  - Changed from print-as-you-go to collect-then-display pattern
  - Now matches test_fx_conversion.py structure exactly
  - All tests pass with clean summary output ✅

- [x] **Run tests** ✅
  - Run: `pipenv run python -m backend.test_scripts.test_services.test_asset_source` ✅
  - Result: **All 11 tests passed** ✅

**Notes**:
```
# MIGRATION COMPLETED: TypedDict → Pydantic BaseModel (2025-11-06)
# Schemas moved to backend/app/schemas/assets.py (Pydantic v2)
# - CurrentValueModel, PricePointModel, HistoricalDataModel, AssetProviderAssignmentModel
# - Field validators with @field_validator for Decimal coercion
# - ConfigDict for extra validation and JSON serialization

# Implementation completed (2025-11-06 18:30 CET) ✅
- Created asset_source.py with Pydantic models, abstract base, manager
- Implemented ALL manager methods:
  - Provider assignment (bulk + singles)
  - Price CRUD (bulk upsert/delete + singles)
  - Price query with backward-fill
  - Provider refresh (bulk + singles) - ADDED 2025-11-07
- Implemented helper functions:
  - get_price_column_precision() - inspects SQLAlchemy model
  - truncate_price_to_db_precision() - Decimal truncation
  - parse_decimal_value() - safe Decimal conversion
- Implemented ACT/365 day count calculation
- Implemented synthetic yield calculation (find_active_rate, calculate_accrued_interest, calculate_synthetic_value)
- Created comprehensive test suite (11 tests)
- All tests passing ✅

# Refresh Implementation (2025-11-07) ✅
- bulk_refresh_prices() with concurrency control (asyncio.Semaphore)
- Parallel DB prefetch + remote API fetch
- Per-item reporting (fetched_count, inserted_count, errors)
- Updates last_fetch_at on success
- Smoke test in test_asset_source_refresh.py

# Test results summary
- Test 1-2: Price precision and truncation ✅
- Test 3: ACT/365 day count (30d, 364d, 365d) ✅
- Test 4-7: Provider assignment/removal (bulk + singles) ✅
- Test 8-9: Price upsert (bulk + singles) ✅
- Test 10: Backward-fill logic (5 days, 3 backfilled) ✅
- Test 11: Price deletion (bulk) ✅

# Known Issues
⚠️ yahoo_finance.py imports CurrentValue, PricePoint, HistoricalData from asset_source.py
   but they don't exist there - should import from schemas.assets as *Model

# Next steps (see Phase 1.2 TODOs)
- Fix yahoo_finance.py imports
- Implement API endpoints in backend/app/api/v1/assets.py
- Add advanced refresh tests
- Document provider development guide

# Completion date
2025-11-06 18:30 CET (core functionality) ✅
2025-11-07 (refresh + smoke test) ✅
```

---

## Phase 1: Unified Provider Registry + Asset Source Foundation (2-3 days)

### 1.1 Unified Provider Registry (Abstract Base + Specializations)

**Reference**: [Phase 1.1 in main doc](./05_plugins_yfinance_css_synthetic_yield.md#11-unified-provider-registry-abstract-base--specializations)

- [x] **Create provider_registry.py**
  - File: `backend/app/services/provider_registry.py` ✅
  - Abstract base: `AbstractProviderRegistry[T]` (Generic)
  - Methods: `auto_discover()`, `register()`, `get_provider()`, `list_providers()`, `clear()`

- [x] **Implement FX specialization**
  - Class: `FXProviderRegistry(AbstractProviderRegistry)` ✅
  - `_get_provider_folder()` → `"fx_providers"` ✅
  - `_get_provider_code_attr()` → `"provider_code"` (default) ✅

- [x] **Implement Asset specialization**
  - Class: `AssetProviderRegistry(AbstractProviderRegistry)` ✅
  - `_get_provider_folder()` → `"asset_source_providers"` ✅
  - `_get_provider_code_attr()` → `"provider_code"` (default) ✅

- [x] **Create decorator**
  - Function: `register_provider(registry_class)` → decorator factory ✅
  - Usage: `@register_provider(AssetProviderRegistry)` ✅

- [x] **Add auto-discovery calls**
  - At module bottom: `FXProviderRegistry.auto_discover()` ✅
  - At module bottom: `AssetProviderRegistry.auto_discover()` ✅

- [x] **Create test file**
  - File: `backend/test_scripts/test_services/test_provider_registry.py` ✅
  - Tests included: basic auto-discovery check for `yfinance` provider ✅

**Verification**:
- `AssetProviderRegistry` and `FXProviderRegistry` present and auto-discover executed on import.
- `asset_source_providers/yahoo_finance.py` uses `@register_provider(AssetProviderRegistry)` and provides `provider_code='yfinance'`.
- Quick test exists to assert `yfinance` is registered (see test_provider_registry.py).

**Status**: ✅ Phase 1.1 completed and verified locally (test file present).  
**Last Verified**: 2025-11-07

---

### 1.2 Asset Source Base Class, Pydantic Schemas & Manager
**Reference**: [Phase 1.2 in main doc](./05_plugins_yfinance_css_synthetic_yield.md#12-Asset-Source-Base-Class,-TypedDicts-&-Manager)

**Status**: ✅ **100% COMPLETED** (2025-11-10) - All core functionality implemented, tested, and API endpoints created

---

#### Summary of Implementation

**COMPLETED COMPONENTS:**

1. **Pydantic Schemas** (Pydantic v2) ✅
   - File: `backend/app/schemas/assets.py`
   - Models: `CurrentValueModel`, `PricePointModel`, `HistoricalDataModel`, `AssetProviderAssignmentModel`
   - File: `backend/app/schemas/common.py`
   - Model: `BackwardFillInfo` (shared with FX system)
   - ✅ Field validators with `@field_validator` for Decimal coercion
   - ✅ ConfigDict for extra validation and JSON serialization

2. **AssetSourceProvider Abstract Base Class** ✅
   - File: `backend/app/services/asset_source.py`
   - Abstract methods: `get_current_value()`, `get_history_value()`, `search()`, `validate_params()`
   - Properties: `provider_code`, `provider_name`
   - Exception: `AssetSourceError(message, error_code, details)`

3. **AssetSourceManager** (Manager Class) ✅
   - **Provider Assignment Methods**:
     - `bulk_assign_providers()` - PRIMARY bulk method ✅
     - `assign_provider()` - single (calls bulk) ✅
     - `bulk_remove_providers()` - PRIMARY bulk method ✅
     - `remove_provider()` - single (calls bulk) ✅
     - `get_asset_provider()` - fetch assignment ✅
   
   - **Manual Price CRUD Methods**:
     - `bulk_upsert_prices()` - PRIMARY bulk method ✅
     - `upsert_prices()` - single (calls bulk) ✅
     - `bulk_delete_prices()` - PRIMARY bulk method ✅
     - `delete_prices()` - single (calls bulk) ✅
   
   - **Price Query with Backward-Fill**:
     - `get_prices()` - with backward-fill and synthetic yield support ✅
   
   - **Provider Refresh Methods** (NEW):
     - `bulk_refresh_prices()` - PRIMARY bulk refresh with concurrency control ✅
     - `refresh_price()` - single (calls bulk) ✅
     - Features: Parallel provider calls, prefetch DB, semaphore for concurrency, per-item reporting

4. **Helper Functions** ✅
   - `get_price_column_precision(column_name)` → (precision, scale)
   - `truncate_price_to_db_precision(value, column_name)` → Decimal truncation
   - `parse_decimal_value(v)` → safe Decimal conversion
   - `calculate_days_between_act365(start, end)` → ACT/365 day fraction

5. **Synthetic Yield Calculation** (Internal Module) ✅
   - `find_active_rate()` - find applicable interest rate for date
   - `calculate_accrued_interest()` - SIMPLE interest calculation with ACT/365
   - `calculate_synthetic_value()` - runtime valuation for SCHEDULED_YIELD assets
   - Integration: Automatic calculation in `get_prices()` when asset.valuation_model == SCHEDULED_YIELD

6. **Test Coverage** ✅
   - File: `backend/test_scripts/test_services/test_asset_source.py`
   - Status: **11/11 tests PASSING** ✅
   - Tests cover: precision, truncation, ACT/365, provider assignment, price CRUD, backward-fill, deletion
   - File: `backend/test_scripts/test_services/test_asset_source_refresh.py`
   - Status: Smoke test for refresh orchestration ✅

7. **Provider Implementations** ✅
   - `backend/app/services/asset_source_providers/yahoo_finance.py` - YahooFinanceProvider ✅
   - `backend/app/services/asset_source_providers/mockprov.py` - MockProv (test provider) ✅
   - Both use `@register_provider(AssetProviderRegistry)` decorator

---

#### Technical Details

**Data Types & Schemas:**
- **Migration from TypedDict to Pydantic**: Originally planned as TypedDict, implemented as Pydantic BaseModel for better validation and API integration
- **Pydantic v2**: All schemas use `model_config = ConfigDict(...)` and `@field_validator`
- **Decimal Handling**: Field validators coerce inputs to Decimal with `Decimal(str(v))`
- **Backward-Fill**: Integrated in `get_prices()`, returns `BackwardFillInfo` when data is backfilled

**Database Strategy:**
- **SQLite Upsert**: Uses delete+insert pattern (no native ON CONFLICT for optional fields)
- **Provider Params**: Stored as JSON string in TEXT column
- **Precision**: All price columns use NUMERIC(18, 6) - validated in tests

**Concurrency & Performance:**
- **Bulk-First Design**: All operations have bulk version as PRIMARY, singles call bulk with 1 element
- **Parallel Fetching**: `bulk_refresh_prices()` uses `asyncio.gather()` with semaphore for concurrency control
- **DB Optimization**: Prefetch existing prices while calling remote API (parallel async tasks)
- **Per-Item Reporting**: Refresh returns detailed results per asset (fetched_count, inserted_count, errors)

**Architectural Decisions:**
- **FX vs Asset Separation**: Separate service files, shared only `BackwardFillInfo` and registry pattern
- **Synthetic Yield**: NOT a provider, calculated on-demand in `get_prices()` (no DB write)
- **Test Safety**: Tests force `LIBREFOLIO_TEST_MODE` and `DATABASE_URL` to use `test_app.db`

---

#### Known Issues & TODOs

⚠️ **CRITICAL - Import Error in yahoo_finance.py**:
```python
# CURRENT (BROKEN):
from backend.app.services.asset_source import CurrentValue, HistoricalData, PricePoint

# SHOULD BE:
from backend.app.schemas.assets import CurrentValueModel, PricePointModel, HistoricalDataModel
# OR: Define type aliases in asset_source.py for backward compatibility
```

**Pending Tasks:**

1. **HIGH PRIORITY**:
   - ✅ ~~Fix yahoo_finance.py imports to use Pydantic models from `schemas.assets`~~ **COMPLETED 2025-11-10**
   - ✅ ~~Create API endpoints in `backend/app/api/v1/assets.py` (bulk assign/remove, price upsert/delete, refresh)~~ **COMPLETED 2025-11-10**
     - 12 endpoints implemented following bulk-first pattern
   - 🔴 Add advanced refresh tests (provider fallback, per-item errors, concurrency limits)

2. **MEDIUM PRIORITY**:
   - Factor utilities to `backend/app/utils/number.py` for reuse with FX system
   - Document provider development guide (similar to `docs/fx/provider-development.md`)

3. **LOW PRIORITY**:
   - Make `last_fetch_at` timezone-aware (currently naive UTC)
   - Complete Step 03 TODO: Check if loan repaid via transactions in synthetic yield

---

#### Testing Commands

```bash
# Run full asset source service tests (11 tests)
pipenv run python -m backend.test_scripts.test_services.test_asset_source

# Run refresh smoke test
pipenv run python -m backend.test_scripts.test_services.test_asset_source_refresh

# Via test_runner (if configured)
./test_runner.py services asset-source
./test_runner.py services asset-source-refresh
```

---

#### Acceptance Criteria

- [x] Service tests passing (11/11) ✅
- [x] `bulk_refresh_prices()` implemented with concurrency control ✅
- [x] Pydantic schemas created in `backend/app/schemas/assets.py` ✅
- [ ] Provider imports fixed to use Pydantic models ⚠️ **BLOCKING**
- [ ] API endpoints implemented and tested
- [ ] Provider development guide documented

**Last Updated**: 2025-11-10  
**Completion Date**: 2025-11-06 (core functionality) + 2025-11-07 (refresh + tests) + 2025-11-10 (API endpoints, fetch_interval, extras)

---

#### Extra Work (2025-11-10)

1. **✅ Added `info:api` command to dev.sh**
   - Command: `./dev.sh info:api`
   - Lists all API endpoints grouped by tag (FX, Assets, Default)
   - Shows HTTP methods and first line of docstring
   - Total endpoint count displayed
   - Implementation:
     - Created `list_api_endpoints.py` Python script
     - Added `list_api_endpoints()` function in dev.sh
     - Added command to case statement and help menu
   - Usage example:
     ```bash
     ./dev.sh info:api
     # Output:
     # [ASSETS]
     #   POST  /api/v1/assets/prices/bulk  Bulk upsert prices manually
     #   ...
     # [FX]
     #   POST  /api/v1/assets/fx/sync/bulk  Synchronize FX rates...
     #   ...
     # Total endpoints: 27
     ```

2. **✅ Fixed Assets Router Registration**
   - Problem: Assets API endpoints (12 total) were not accessible
   - Cause: `router.include_router(assets.router)` missing in `backend/app/api/v1/router.py`
   - Fix: Added assets router import and registration
   - Result: 27 total endpoints now (12 Assets + 9 FX + 6 Default)

3. **⚠️ FX API Test 4.3 Issue (Known Issue)**
   - Test: `test_fx_api.py` - Test 4.3 (Auto-Configuration Mode)
   - Problem: Auto-config sync returns 0 synced rates
   - Configuration: EUR/USD → FED priority=1
   - Expected: FED syncs at least one rate
   - Actual: `synced=0`, `currencies=[]`
   - Status: **Test fixed to better report error**, but underlying sync issue remains
   - TODO: Investigate why FED provider returns 0 rates in auto-config mode
   - Note: This is a FX system issue, not related to Assets implementation

---

## Phase 1.3 Provider Folder Setup (Auto-Discovery)

**Reference**: [Phase 1.3 in main doc](./05_plugins_yfinance_css_synthetic_yield.md#13-provider-folder-setup-was-plugin-registry--factory)

- [ ] **Create provider folder**
  - Folder: `backend/app/services/asset_source_providers/`

- [ ] **Create __init__.py**
  - File: `backend/app/services/asset_source_providers/__init__.py`
  - Content: Empty with docstring (auto-discovery via registry)

- [ ] **Test auto-discovery**
  - Create dummy provider in folder
  - Verify `AssetProviderRegistry.auto_discover()` finds it
  - Verify `@register_provider(AssetProviderRegistry)` works
  - Remove dummy provider

- [ ] **Verify in test_provider_registry.py**
  - Test already created in Phase 1.1
  - Run: `pipenv run python -m backend.test_scripts.test_services.test_provider_registry`

---

### 1.4 Migrate existing FX providers to the unified registry

**Purpose**: Bring the legacy FX provider implementations (ECB, FED, BOE, SNB, etc.) to the new auto-registration model so they are discoverable through `FXProviderRegistry` and usable by the services via the registry API. Add tests to validate auto-discovery and listing for FX providers.

- [ ] **Update FX provider classes**
  - Ensure each provider class in `backend/app/services/fx_providers/` exposes a `provider_code` attribute (string) and a human `name` property.
  - Replace legacy factory-registration (if present) with the decorator usage:
    ```py
    from backend.app.services.provider_registry import register_provider, FXProviderRegistry

    @register_provider(FXProviderRegistry)
    class ECBProvider(...):
        provider_code = "ECB"
        # ...
    ```
  - Keep backward-compatible API on provider classes; prefer minimal changes inside implementations.

- [ ] **Remove or adapt legacy FX factory usage where applicable**
  - Search for `FXProviderFactory` usages and prefer `FXProviderRegistry.get_provider_instance(code)` or `FXProviderRegistry.get_provider(code)`.
  - Update code in `backend/app/services/fx.py` (or any caller) to use the registry when resolving providers by code.

- [ ] **Add FX provider auto-discovery tests**
  - Create/extend `backend/test_scripts/test_services/test_provider_registry.py` to assert presence of major FX providers, e.g.: `ECB, FED, BOE, SNB`.
  - Test should run after registry auto_discover is executed on import (test already imports registry module).

- [ ] **Run integration check**
  - Start a small smoke test script or run the updated `test_provider_registry.py` to verify all FX providers are registered.

**Verification**:
- Expect `FXProviderRegistry.list_providers()` to include: `ECB, FED, BOE, SNB` (at least).  
- Existing FX-related tests should be updated to resolve providers via registry instead of factory where applicable.

**Notes**:
- Keep changes minimal and backward compatible. If parts of the codebase still expect the old factory API, provide a thin shim for `FXProviderFactory.get(code)` that forwards to the registry for the transition period.
- Add the registry-based provider resolution to the API layer where provider code strings are accepted in requests (sync endpoints), so auto-configuration and provider selection use the registry uniformly.

**Status**: ⬜ Not started — awaiting implementation & tests.  
**Last Edited**: 2025-11-07


## Phase 1.5: FX Pydantic Schemas Migration (Pydantic v2)

**Goal**: centralize FX request/response shapes into a single Pydantic v2 module `backend/app/schemas/fx.py`, migrate any V1 validators to v2 (`@validator` -> `@field_validator`), use `Decimal` consistently, and update imports + tests to use the new schemas.

Why now
- Improves clarity and reusability across `api`, `services`, and `tests`.
- Removes duplicated shapes and keeps serialization rules (Decimal handling) consistent.
- Prepares base for OpenAPI docs and runtime validation.

Checklist (do these in order)
- [ ] Identify current FX-shaped DTOs used across the codebase (search for Pydantic models / TypedDicts used by FX endpoints and services).
  - Targets: `backend/app/api/v1/fx.py`, `backend/app/services/fx.py`, tests in `backend/test_scripts/*`.
- [ ] Create `backend/app/schemas/fx.py` with Pydantic v2 models (examples below):
  - `BackwardFillInfo` (if not already in `schemas/common.py` reuse it)
  - `RatePointModel` (date: date, rate: Decimal)
  - `FXProviderMetadataModel` (code, name, base_currency, description?)
  - `FXCurrenciesListResponseModel` (List[str] / metadata)
  - `FXSyncRequestModel` / `FXSyncResponseModel` (bulk sync payload shapes)
  - `FXRateSetItemModel` / `FXRateSetBulkRequest` / `FXRateSetBulkResponse`
  - `FXConvertRequestItem` / `FXConvertResponseItem` / `FXConvertBulkRequest`
  - `model_config` entries for Decimal serialization (prefer string output) and extra policy
  - Field validators with `@field_validator(..., mode="before")` for Decimal coercion and currency uppercasing
- [ ] Add `backend/app/schemas/__init__.py` exports if needed (export `fx` models for convenience)
- [ ] Replace imports in code to reference the new models (minimal-change approach):
  - `backend/app/api/v1/fx.py` → request/response models
  - `backend/app/services/fx.py` → internal validation/response shaping
  - tests under `backend/test_scripts/test_api` and `backend/test_scripts/test_services` → use the new models for assertions where appropriate
- [ ] Update tests to assert on model-validated output when relevant (use `.model_dump()` for comparisons)
- [ ] Run the targeted tests and fix issues:
  - `pipenv run python -m backend.test_scripts.test_external.test_fx_providers` (providers connectivity / normalization)
  - `pipenv run python -m backend.test_scripts.test_api.test_fx_api` (API request/response shapes)
  - `pipenv run python -m backend.test_scripts.test_services.test_fx_conversion` (conversion logic)
- [ ] Document serialization choice (Decimal -> string) in `docs/fx/api-reference.md` and mention that runtime Swagger is authoritative
- [ ] Commit changes with clear message: "Add Pydantic v2 FX schemas (backend/app/schemas/fx.py); migrate validators and Decimal handling; update imports and tests."

Example skeleton for `backend/app/schemas/fx.py` (to implement)

- Use Pydantic v2 style: `model_config = ConfigDict(...)` and `@field_validator` validators.
- Use `Decimal` for monetary/rate fields and configure JSON encoder to return string (to preserve precision).

Minimal structure (for the actual file implementation):

- RatePointModel(date: date, rate: Decimal)
- BackwardFillInfo (reuse from `schemas.common` if present)
- FXConvertRequestItem(amount: Decimal, from_currency: str, to_currency: str, start_date: date, end_date: Optional[date] = None)
- FXConvertResponseItem(converted_amount: Decimal, rate: Optional[Decimal], actual_rate_date: Optional[date], backfill_info: Optional[BackwardFillInfo])

Notes & choices
- Decimal representation in JSON: prefer string to avoid precision loss in JS/clients. Document this choice.
- Pydantic v2: use `@field_validator(..., mode='before')` to coerce string inputs into `Decimal`.
- BackwardFillInfo reuse: avoid duplication, import from `schemas.common`.

Risks & mitigation
- If project still contains Pydantic v1-only code, migration may raise deprecation warnings. Run full test-suite and fix validators incrementally.
- Tests that previously compared floats/strings may need updates to compare normalized strings/Decimals. Use `.model_dump()` or `.model_dump_json()` with consistent settings in tests.

Acceptance criteria for Phase 1.5
- `backend/app/schemas/fx.py` created and exported
- All FX-related code imports the new models where appropriate
- Provider & API tests pass that validate request/response shapes
- Documentation updated to reflect JSON Decimal serialization policy

---

## Phase 2: yfinance Provider (1-2 days)

**Reference**: [Phase 2 in main doc](./05_plugins_yfinance_css_synthetic_yield.md#phase-2-yfinance-provider-1-2-giorni)

- [ ] **Install dependencies**
  - Run: `pipenv install yfinance`
  - Run: `pipenv install pandas`

- [ ] **Create yahoo_finance.py**
  - File: `backend/app/services/asset_source_providers/yahoo_finance.py`
  - Class: `YahooFinanceProvider(AssetSourceProvider)`
  - Decorator: `@register_provider(AssetProviderRegistry)`

- [ ] **Implement properties**
  - `provider_code` → `"yfinance"`
  - `provider_name` → `"Yahoo Finance"`
  - `test_identifier` → `"AAPL"`
  - `test_expected_currency` → `"USD"`

- [ ] **Implement get_current_value()**
  - Try `fast_info.last_price` first (faster)
  - Fallback to `history(period='5d')` if fast_info fails
  - Auto-detect currency from `ticker.info`
  - Return `CurrentValue` TypedDict

- [ ] **Implement get_history_value()**
  - Use `ticker.history(start, end)` with date range
  - Note: end date is exclusive in yfinance
  - Convert pandas DataFrame to list of `PricePoint`
  - Handle NaN values for OHLC fields
  - Return `HistoricalData` TypedDict

- [ ] **Implement search()**
  - Cache results for 10 minutes (TTL = 600s)
  - Use exact ticker match (yfinance has no native search)
  - Return list with `{identifier, display_name, currency, type}`
  - Cache both found and not-found results

- [ ] **Error handling**
  - Raise `ProviderError` with appropriate error codes
  - Handle: NO_DATA, FETCH_ERROR, SEARCH_ERROR

- [ ] **Verify auto-discovery**
  - Provider should be automatically registered on import
  - Check: `AssetProviderRegistry.list_providers()` includes "yfinance"

**Notes**:
```
# Implementation notes


# Issues encountered


# Completion date

```

---

## Phase 3: CSS Scraper Provider (1-2 days)

**Reference**: [Phase 3 in main doc](./05_plugins_yfinance_css_synthetic_yield.md#phase-3-css-scraper-provider-1-2-giorni)

- [ ] **Install dependencies**
  - Run: `pipenv install beautifulsoup4`
  - Note: httpx already present

- [ ] **Create css_scraper.py**
  - File: `backend/app/services/asset_source_providers/css_scraper.py`
  - Class: `CSSScraperProvider(AssetSourceProvider)`
  - Decorator: `@register_provider(AssetProviderRegistry)`

- [ ] **Implement properties**
  - `provider_code` → `"cssscraper"`
  - `provider_name` → `"CSS Web Scraper"`

- [ ] **Implement validate_params()**
  - Required: `current_url`, `current_css_selector`, `currency`
  - Optional: `history_url`, `history_css_selector`
  - Raise `ProviderError` if missing required params

- [ ] **Implement parse_float()**
  - Handle US format: "1,234.56"
  - Handle EU format: "1.234,56"
  - Handle space separator: "1 234,56"
  - Handle currency symbols: "€1,234.56"
  - Return `Decimal`

- [ ] **Implement get_current_value()**
  - Use `httpx.AsyncClient` with timeout=30
  - Parse HTML with `BeautifulSoup`
  - Select element with `soup.select_one(selector)`
  - Parse float with `parse_float()`
  - Return `CurrentValue` with today's date

- [ ] **Implement get_history_value()**
  - Check if `history_url` and `history_css_selector` in params
  - If not present: return empty `HistoricalData`
  - If present: scrape history (TODO for future if needed)

- [ ] **Implement search()**
  - Raise `ProviderError` with NOT_SUPPORTED
  - CSS scraper requires manual URL configuration

- [ ] **Error handling**
  - Raise `ProviderError` for: MISSING_PARAMS, PARSE_ERROR, SELECTOR_NOT_FOUND, HTTP_ERROR, SCRAPE_ERROR

- [ ] **Verify auto-discovery**
  - Check: `AssetProviderRegistry.list_providers()` includes "cssscraper"

**Notes**:
```
# Implementation notes


# Issues encountered


# Completion date

```

---

## Phase 4: Complete Synthetic Yield Implementation (3-4 days) ⚠️ MOST COMPLEX

**Reference**: [Phase 4 in main doc](./05_plugins_yfinance_css_synthetic_yield.md#phase-4-complete-synthetic-yield-implementation-3-4-giorni--most-complex)

**Status**: Deferred from Phase 0.2.2  
**Current State**: Only ACT/365 day count helper implemented in asset_source.py  
**Implementation Type**: Integrated logic in `asset_source.py`, **NOT a separate provider**

**What's Already Done (Phase 0.2.2)**:
- ✅ `calculate_days_between_act365(start, end)` in asset_source.py

**What Needs Implementation (Phase 4)**:
- Rate schedule logic (find_active_rate)
- Accrued interest calculation (SIMPLE interest, ACT/365)
- Full synthetic value calculation
- Integration in get_prices() for SCHEDULED_YIELD assets
- Transaction-aware logic (check if repaid/sold)

- [x] **Implement calculate_days_between_act365()** ✅ Phase 0.2.2
  - Location: `backend/app/services/asset_source.py`
  - Use ACT/365: actual_days / 365
  - Return `Decimal` fraction
  - Tests passing (30d, 364d, 365d) ✅

- [ ] **Implement find_active_rate()**
  - Location: `backend/app/services/asset_source.py` (add to existing file)
  - Parse interest schedule (list of {start_date, end_date, rate})
  - Find rate for target_date
  - Handle maturity + grace period → late_interest.rate
  - Return `Decimal` rate

- [ ] **Implement calculate_accrued_interest()**
  - Location: `backend/app/services/asset_source.py` (add to existing file)
  - Use SIMPLE interest: principal * sum(rate * time_fraction)
  - Iterate day-by-day from start to end
  - Apply ACT/365 day count for each day
  - Sum daily accruals
  - Return `Decimal` accrued interest

- [ ] **Implement calculate_synthetic_value()**
  - Location: `backend/app/services/asset_source.py` (add to existing file)
  - Calculate: face_value + accrued_interest_to_target_date
  - Requires asset data from DB (face_value, interest_schedule, maturity_date)
  - Return synthetic price point
  - **Decision needed**: Pass asset object or fetch inside function?

- [ ] **Integrate with get_prices()**
  - Modify: `AssetSourceManager.get_prices()` method
  - Check: `if asset.valuation_model == SCHEDULED_YIELD`
  - If true: Calculate synthetic values using above helpers
  - If false: Query price_history table normally
  - Return prices with backward_fill_info when applicable
  - **Important**: Synthetic values calculated on-demand, NOT written to DB

- [ ] **Handle edge cases**
  - Maturity date passed
  - Grace period (late_interest.grace_period_days)
  - Late interest rate application
  - **TODO (Step 03)**: Check if loan was repaid via transactions
  - Empty interest schedule → default to 0 rate
  - Missing maturity_date → error or assume indefinite?

- [ ] **Add tests**
  - File: `backend/test_scripts/test_services/test_asset_source.py` (add to existing)
  - Test find_active_rate (simple schedule, maturity, late interest)
  - Test calculate_accrued_interest (SIMPLE, rate changes)
  - Test calculate_synthetic_value (current + historical)
  - Test get_prices with SCHEDULED_YIELD asset (uses synthetic, no DB write)
  - Test get_prices with non-SCHEDULED_YIELD asset (normal DB query)

**Notes**:
```
# ACT/365 is hardcoded for simplicity (not a separate provider anymore)
# True profits = sell_proceeds - buy_cost
# This is just for portfolio valuation estimates

# Implementation approach:
- Integrated in asset_source.py as helper functions
- NOT a separate provider (SCHEDULED_YIELD is a valuation model, not a data source)
- get_prices() automatically detects SCHEDULED_YIELD and calculates on-demand
- No DB writes for synthetic values (always calculated fresh)

# DB access strategy:
- Fetch asset object in get_prices() before synthetic calculation
- Pass asset data to calculate_synthetic_value()
- All calculations use asset fields: face_value, interest_schedule, maturity_date, late_interest

# Completion status (Phase 0.2.2):
- ✅ ACT/365 day count implemented and tested
- ⏳ Remaining work deferred to Phase 4

# Issues encountered


# Completion date (full implementation)

```

---

## Phase 4: Generic Provider Tests (1 day)

**Reference**: [Phase 2 Test section in main doc](./05_plugins_yfinance_css_synthetic_yield.md#test-backendtest_scriptstest_servicestest_asset_providerspy)

- [ ] **Create test_asset_providers.py**
  - File: `backend/test_scripts/test_services/test_asset_providers.py`
  - Pattern: Similar to `test_external/test_fx_providers.py`

- [ ] **Implement test discovery**
  - Use `AssetProviderRegistry.list_providers()` to get all registered
  - Iterate over each provider and run uniform tests

- [ ] **Implement uniform test functions**
  - `test_provider_metadata(provider)` → verify provider_code, provider_name
  - `test_provider_current_value(provider)` → with test_identifier if available
  - `test_provider_history(provider)` → 7 days range
  - `test_provider_search(provider)` → if supports_search
  - `test_provider_errors(provider)` → error handling

- [ ] **Run for each provider**
  - yfinance: All tests with AAPL ticker
  - CSS scraper: Metadata, errors (skip current/history without URL)

- [ ] **Run tests**
  - Run: `pipenv run python -m backend/test_scripts.test_services.test_asset_providers`

**Notes**:
```
# This replaces individual test files per provider
# All providers tested uniformly
# Synthetic yield is NOT a provider - tested in test_pricing.py

# Test results


# Issues encountered


# Completion date

```

---

## Phase 5: API Endpoints & Integration (2 days)

Goal: expose provider assignment and pricing features via REST with consistent bulk-oriented endpoints, clear validation, and minimal DB work. Keep parity with FX endpoints naming (use `/bulk` suffix), and implement deletion-by-range semantics for manual rate/price deletion.

Primary principles:
- Bulk-first: all mutating endpoints accept arrays and single-item variants call the bulk handler.
- Deterministic date semantics: `start_date` required, `end_date` optional; if `end_date` missing treat as single day. The service processes inclusive ranges day-by-day when needed.
- Minimal DB roundtrips: consolidate bulk payloads into as few statements as possible (single multi-row INSERT/UPSERT, single DELETE with OR/IN clauses) and avoid per-item queries when possible.
- Pydantic-based API schemas: use the `backend.app.schemas.*` models (e.g., `PricePointModel`, `HistoricalDataModel`, `BackwardFillInfo`) for request/response validation and OpenAPI docs.
- Backward-fill info: present in responses only when applicable; follow the same shape and naming as FX (`backfill_info` with `actual_rate_date` / `days_back`).
- Provider selection & priority rules: API validates input and warns; selection/fallback logic lives in service layer (try highest priority first, fall back to next on provider errors). API does not raise 500 for mis-ordered priorities — it returns an error only if no provider can be used.

Endpoints to implement (file: `backend/app/api/v1/assets.py`) — use `router` under `/api/v1` and consistent naming:
- GET `/assets/{asset_id}/scraber`
  - Returns assigned provider (nullable) using a Pydantic model (e.g., `AssetProviderAssignmentModel`).
- POST `/assets/scraber/bulk`
  - Request: list of `{asset_id, provider_code, provider_params}`
  - Response: list of `{asset_id, success, message}`
  - Behavior: calls `AssetSourceManager.bulk_assign_providers()`; single assign endpoint delegates here.
- DELETE `/assets/scraber/bulk`
  - Request: list of `{asset_id}` or `{asset_id, provider_code?}`; delete by asset_id (or combined filter). Returns counts per asset.
  - Behavior: calls `AssetSourceManager.bulk_remove_providers()`.

Price endpoints (file: `backend/app/api/v1/assets.py` or `assets_pricing.py`):
- POST `/assets/price/upsert/bulk`
  - Request: list of `{asset_id, prices: [{date (YYYY-MM-DD), open?, high?, low?, close, volume?, currency?}, ...]}`
  - Response: `{inserted_count, updated_count, results: [...]}`
  - Behavior: calls `AssetSourceManager.bulk_upsert_prices()`; ensure inputs validated by `PricePointModel` (Pydantic).
- DELETE `/assets/price/delete/bulk`
  - Request: list of `{asset_id, date_ranges: [{start_date: YYYY-MM-DD, end_date?: YYYY-MM-DD}, ...]}`
  - Behavior: calls `AssetSourceManager.bulk_delete_prices()`; server converts to single DELETE with OR of ranges.
  - Response: `{deleted_count, results: [...]}` (report per item counts — it's fine to approximate but tests should expect deterministic deletes when given explicit ranges).
- GET `/assets/{asset_id}/price-set`
  - Query params: `start_date` (required), `end_date` (optional). If only `start_date` present treat as single date.
  - Response: list of `PricePointModel` with optional `backfill_info`.
  - Behavior: if asset is `SCHEDULED_YIELD` calculate synthetic prices (no DB writes); otherwise query `price_history` with backward-fill.

FX endpoints (file: `backend/app/api/v1/fx.py`) — align and extend current design:
- POST `/fx/sync/bulk` (already present) — ensure auto-configuration mode uses `fx_currency_pair_sources` query order and fallback logic described in services.
- POST `/fx/rate-set/bulk` (manual upsert) — accept list of `{base, quote, date, rate, source?}`; store ordered base/quote alphabetically for storage but preserve input ordering when responding.
- DELETE `/fx/rate-set/bulk` (manual delete) — accept list of `{base, quote, start_date, end_date?}`; backend will canonicalize pair (alphabetical) for storage lookup and then delete the inclusive range. Response: counts present and counts removed.
- POST `/fx/convert/bulk` — support `start_date` (required) and optional `end_date` to allow range conversions; if range provided, service returns an array of daily conversions for the interval (processed one day at a time). Keep `identity` conversions handling optimized (return rate=null where base==quote).

Validation & Behavior notes:
- Use Pydantic for request validation; FastAPI will return 422 for malformed inputs. Add additional semantic checks in endpoint logic (e.g., start <= end).
- `start_date` must be present and ISO date; `end_date` if present must be >= `start_date`.
- For FX auto-configuration (no `provider` param) the endpoint should consult `fx_currency_pair_sources` following `priority` ordering. If a top provider fails, try the next one; if all fail, return 502/503 with provider errors details.
- Manual rate upsert/delete: the API accepts pairs in any order; backend will canonicalize stored pairs to the normalized representation used by `fx_rates` table (but must record source and original direction in response metadata if useful).

Tests to add / update:
- `backend/test_scripts/test_api/test_assets_api.py` (new)
  - Full coverage for assign/remove (bulk & single), upsert/delete prices (bulk & single), get prices with backfill, SCHEDULED_YIELD synthetic value (no DB writes) and validation errors.
  - Ensure tests assert the response schema using Pydantic models where appropriate.
- Update `backend/test_scripts/test_api/test_fx_api.py`
  - Add tests for DELETE `/fx/rate-set/bulk` semantics and for convert bulk range behavior (start_date + optional end_date).
  - Test auto-configuration fallback ordering by configuring `fx_currency_pair_sources` in test DB prior to sync call and verifying provider selection flow.
- Update any server helper tests (`backend/test_scripts/test_server_helper.py`) to ensure test server prints DB used (already requested elsewhere).

DB and performance considerations:
- For bulk deletes/upserts prefer single SQL statements where possible:
  - DELETE with `WHERE (asset_id = A AND date BETWEEN ...) OR (asset_id = B AND date BETWEEN ...)`
  - INSERT many rows with a single transaction via `session.add_all()` or core executemany depending on DB backend
- Be mindful of SQLite parameter limits; if payloads are extremely large, chunk them (server-side chunking) or return 413 if too big.
- Ensure endpoints run within proper transactions and commit only after validation passes for the whole bulk (or support partial success semantics with clear reporting).

API docs & examples:
- Update `docs/api-reference` pages with the new endpoints and include curl examples for:
  - Bulk upsert prices
  - Bulk delete rates/prices
  - Convert bulk with start_date vs range
- Add note: runtime Swagger UI (`/docs`) is authoritative and can be used to exercise endpoints live; maintenance issues should be reported with an issue.

Security & UX:
- For providers that do not require API keys (recommended), document that in `docs/fx/providers.md` and note in API responses when a provider requires additional config.
- Return helpful errors: validation (400/422), provider failures (502/503 with details), partial failures in bulk (200 with per-item results stating success/error).

Acceptance criteria for Phase 5:
- All endpoints implemented with the exact route names above and documented in OpenAPI
- Request/response shapes validated by Pydantic models and used in tests
- Bulk operations consolidate DB work into minimal queries and return clear per-item results
- Tests added/updated and passing: `backend/test_scripts/test_api/test_assets_api.py`, updated `test_fx_api.py` tests for new delete/convert behavior

Run & verify:
- Start test server and run API tests (test runner starts/stops server automatically):

```bash
./test_runner.py -v api all
```

- Run individual API test file during development:

```bash
pipenv run python -m backend.test_scripts.test_api.test_assets_api
```

---

## Phase 6: Documentation, Guides and Developer Notes (1 day)

**Goal**: Update docs to reflect new architecture, plugin registry behavior, API changes and developer workflows.

- [ ] Docs to update/create (all in English):
  - `docs/fx/providers.md` – update to show registry-based discovery and mention providers that require no API key
  - `docs/fx/api-reference.md` – ensure it points to runtime-generated Swagger and includes curl examples (explain what each step does)
  - `docs/fx/provider-development.md` – keep, but mark minimal: reference the main developer guide (detailed implementation in `docs/fx/` subfolder)
  - `docs/assets/provider-development.md` (NEW) – how to implement an `AssetSourceProvider`, required methods, register decorator, params validation
  - `docs/testing-guide.md` – update to show how to run db creation, populate mock data with `--force`, and how to run service + API tests
  - `docs/alembic-squash-guide.md` (NEW) – step-by-step for squashing migrations (see Phase 7 below)

- [ ] Cross-linking: ensure new pages link back to `README.md` and to `LibreFolio_developer_journal/prompts/*` where appropriate.

- [ ] Update changelog: short notes about migrating plugin columns into `asset_provider_assignments` and removing plugin_* fields from `assets`.


## Phase 7: Migrations maintenance & Squash (manual step, careful) (1 day)

**Goal**: Produce a single consolidated baseline revision for the schema (development convenience). This step is destructive for migration history; perform only after agreement and backups.

Options considered:
- Option A: Use Alembic's "stamp" workflow + one new baseline revision that recreates the full schema SQL.
- Option B: Generate a single initial migration file that contains the full CREATE TABLE statements (what we want) and retire previous versions.

Recommended safe approach (manual but reproducible):
1. Create a branch and tag the current migration head(s).
2. Ensure working databases are backed up (both `app.db` and `test_app.db`).
3. Create a new revision file `000_base_squash.py` (autogenerate will not include CHECK constraints reliably) but include hand-edited SQL reflecting current models; include explicit CHECK constraints and indexes.
4. Run tests against a freshly deleted DB to validate the new single revision (do `./dev.sh db:upgrade backend/data/sqlite/test_app.db`).
5. If OK, replace `alembic/versions/*` with the single file and `alembic_version` content updated (or instruct CI to run `alembic stamp head` when deploying).

**Checklist**:
- [ ] Backups created
- [ ] New `000_base_squash.py` created and reviewed
- [ ] Test DB recreated and validated
- [ ] Developers informed and docs updated (`docs/alembic-squash-guide.md`)

**Caveats**: If you use CI that expects previous migrations, coordinate before removing old revisions.


## Phase 8: Final QA, Release Prep and Handover (1-2 days)

- [ ] Run full test-suite: `./test_runner.py all` (or subset as needed)
- [ ] Sanity checks: start server, run a few manual API calls against test server
- [ ] Create short release notes (what changed, how to run migrations, new API endpoints)
- [ ] Move completed prompts to `prompts/Step-Completati/` and update `LibreFolio_developer_journal/01-Riassunto_generale.md`
- [ ] Tag repo (e.g., `v0.5-dev-sources`) and push branch for code review


## Immediate next actions (what I'll do next if you want me to proceed)

1. Implement Phase 1.2: complete `backend/app/services/asset_source.py` manager methods left unchecked (bulk refresh, pricing helpers) and unit tests.
2. Add API endpoints for assignment + pricing (Phase 5) stubs and tests.
3. Create `docs/assets/provider-development.md` and update `docs/testing-guide.md` with `--force` semantics.
4. Draft an `alembic` squash migration file `backend/alembic/versions/000_base_squash.py` for your review (do NOT apply until you approve).


## Notes / decisions captured (summary)
- FX and Asset DB operations remain separate. Only shared code: `BackwardFillInfo` schema, provider registration pattern, and some helper utilities (truncation logic may be duplicated but consistent).
- `assets` table: plugin_* columns are removed; assignment moved to `asset_provider_assignments` with `provider_code` + `provider_params` (single assignment per asset).
- `fx_currency_pair_sources` keeps `fetch_interval` for scheduling; `asset_provider_assignments` includes `last_fetch_at` for monitoring.
- Bulk API endpoints should always attempt to consolidate DB work into minimal statements (single multi-row INSERT/UPSERT and single DELETE where possible).


---

# Step 05: Asset Provider System - Implementation Checklist

**Reference Document**: [`05_plugins_yfinance_css_synthetic_yield.md`](./05_plugins_yfinance_css_synthetic_yield.md)

**Project**: LibreFolio - Asset Pricing Provider System  
**Start Date**: 6 November 2025  
**Estimated Duration**: 6-8 days  
**Status**: 🟡 Not Started

---

## 📋 Quick Overview

This checklist tracks the implementation of a modular asset pricing system with:
- **Unified Provider Registry** (abstract base for FX + Assets)
- **2 Asset Providers**: yfinance, CSS scraper
- **Synthetic Yield Logic**: Internal to `asset_source.py` (NOT a provider, calculated at runtime for SCHEDULED_YIELD assets)
- **Separated Service Layers**: `fx.py` and `asset_source.py` remain independent (different tables, different queries)
- **Shared Schemas Only**: `BackwardFillInfo` common format, but independent implementations
- **Backward-Fill Logic**: Similar pattern in both systems, but separate code
- **Bulk-First Design**: All operations bulk-primary, singles call bulk with 1 element

**Key Principles**: 
- **Pragmatic Separation**: Don't force abstraction where tables differ (fx_rates ≠ price_history)
- **Docker-friendly auto-discovery**: Drop `.py` file → auto-register
- **Synthetic yield**: Calculated on-demand, NOT stored in DB
- **Code duplication acceptable**: ~20 lines of backward-fill logic duplicated > fragile generic layer

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
- asset_provider_assignments: only 2 columns (provider_code, provider_params)
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

- [ ] **Create asset_source.py**
  - File: `backend/app/services/asset_source.py`
  - Pattern: Similar to `fx.py` but for `price_history` table

- [ ] **Define TypedDicts**
  - `CurrentValue` → {value, currency, as_of_date, source}
  - `PricePoint` → {date, open?, high?, low?, close, volume?, currency}
  - `HistoricalData` → {prices, currency, source}
  - Import `BackwardFillInfo` from `schemas.common`

- [ ] **Define ProviderError exception**
  - Class: `ProviderError(Exception)`
  - Fields: `message`, `error_code`, `details`

- [ ] **Create abstract base class**
  - Class: `AssetSourceProvider(ABC)`
  - Properties: `provider_code`, `provider_name`
  - Methods: `get_current_value()`, `get_history_value()`, `search()`

- [ ] **Implement AssetSourceManager**
  - **Provider Assignment**: `bulk_assign_providers()`, `bulk_remove_providers()`, singles
  - **Price Refresh**: `bulk_refresh_prices()`, `refresh_price()` (via providers)
  - **Manual Price CRUD**: `bulk_upsert_prices()`, `bulk_delete_prices()`, singles
  - **Price Query**: `get_prices()` → with backward-fill + SCHEDULED_YIELD check
  - All bulk operations PRIMARY, singles call bulk with 1 element

- [ ] **Implement helper functions**
  - `get_price_column_precision(column_name)` → (precision, scale)
  - `truncate_price_to_db_precision(value, column_name)` → Decimal
  - `apply_backward_fill_logic(requested_date, available_prices)` → {data, BackwardFillInfo}

- [ ] **Implement synthetic yield module** (integrated in asset_source.py)
  - `calculate_synthetic_value(asset, target_date, session)` → runtime calculation
  - `calculate_days_between_act365(start, end)` → ACT/365 day fraction
  - `find_active_rate(schedule, target_date, maturity, late_interest)` → rate lookup
  - `calculate_accrued_interest(...)` → SIMPLE interest
  - **Important**: Values calculated on-demand, NOT written to DB
  - Called automatically by `get_prices()` when `asset.valuation_model == SCHEDULED_YIELD`

- [ ] **Create test file**
  - File: `backend/test_scripts/test_services/test_asset_source.py`
  
  **Price CRUD tests** (price_history table):
  - Test bulk_upsert_prices, bulk_delete_prices
  - Test single operations call bulk
  - Verify DB query optimization
  - Test decimal truncation
  
  **Price query + backward-fill tests**:
  - Test get_prices exact match (backward_fill_info = null)
  - Test get_prices with backfill (backward_fill_info present)
  - Test backward-fill matches FX pattern
  
  **Synthetic yield tests**:
  - Test calculate_days_between_act365
  - Test find_active_rate (schedule, maturity, late interest)
  - Test calculate_accrued_interest (SIMPLE)
  - Test calculate_synthetic_value (current + historical)
  - Test get_prices with SCHEDULED_YIELD (uses synthetic, no DB write)
  - Test get_prices with non-SCHEDULED_YIELD (normal DB query)
  
  **Provider assignment tests**:
  - Test bulk_assign_providers, bulk_remove_providers
  
  **Provider refresh tests**:
  - Test bulk_refresh_prices (parallel provider calls)

- [ ] **Run tests**
  - Run: `pipenv run python -m backend.test_scripts.test_services.test_asset_source`

**Notes**:
```
# TODO: Schema factorization (future)
# Move Pydantic schemas to:
# - backend/app/schemas/fx.py
# - backend/app/schemas/assets.py
# - backend/app/schemas/common.py

# Implementation notes


# Issues encountered


# Completion date

```

---

## Phase 1: Unified Provider Registry + Asset Source Foundation (2-3 days)

### 1.1 Unified Provider Registry (Abstract Base + Specializations)

**Reference**: [Phase 1.1 in main doc](./05_plugins_yfinance_css_synthetic_yield.md#11-unified-provider-registry-abstract-base--specializations)

- [ ] **Create provider_registry.py**
  - File: `backend/app/services/provider_registry.py`
  - Abstract base: `AbstractProviderRegistry[T]` (Generic)
  - Methods: `auto_discover()`, `register()`, `get_provider()`, `list_providers()`, `clear()`

- [ ] **Implement FX specialization**
  - Class: `FXProviderRegistry(AbstractProviderRegistry)`
  - `_get_provider_folder()` → `"fx_providers"`
  - `_get_provider_code_attr()` → `"provider_code"`

- [ ] **Implement Asset specialization**
  - Class: `AssetProviderRegistry(AbstractProviderRegistry)`
  - `_get_provider_folder()` → `"asset_source_providers"`
  - `_get_provider_code_attr()` → `"provider_code"`

- [ ] **Create decorator**
  - Function: `register_provider(registry_class)` → decorator factory
  - Usage: `@register_provider(AssetProviderRegistry)`

- [ ] **Add auto-discovery calls**
  - At module bottom: `FXProviderRegistry.auto_discover()`
  - At module bottom: `AssetProviderRegistry.auto_discover()`

- [ ] **Create test file**
  - File: `backend/test_scripts/test_services/test_provider_registry.py`
  - Test auto_discover scans folders
  - Test register via decorator
  - Test get_provider by code
  - Test get_provider raises error if not found
  - Test list_providers
  - Test clear() for test isolation
  - Test both FX and Asset registries

- [ ] **Run tests**
  - Run: `pipenv run python -m backend.test_scripts.test_services.test_provider_registry`

**Notes**:
```
# TODO (Future): Refactor existing FX providers to use this registry

# Implementation notes


# Issues encountered


# Completion date

```

---

### 1.2 Asset Source Base Class, TypedDicts & Manager

**Reference**: [Phase 1.2 in main doc](./05_plugins_yfinance_css_synthetic_yield.md#12-asset-source-base-class-typeddicts--manager)

- [ ] **Create asset_source.py**
  - File: `backend/app/services/asset_source.py`
  - Pattern: Follow `fx.py` structure

- [ ] **Define TypedDicts**
  - `CurrentValue` → {value, currency, as_of_date, source}
  - `PricePoint` → {date, open?, high?, low?, close, volume?, currency}
  - `HistoricalData` → {prices, currency, source}

- [ ] **Define ProviderError exception**
  - Class: `ProviderError(Exception)`
  - Fields: `message`, `error_code`, `details`

- [ ] **Create abstract base class**
  - Class: `AssetSourceProvider(ABC)`
  - Properties: `provider_code`, `provider_name`
  - Methods: `get_current_value()`, `get_history_value()`, `search()`, `validate_params()`

- [ ] **Implement AssetSourceManager**
  - **Provider Assignment Methods**:
    - `bulk_assign_providers(assignments, session)` → PRIMARY bulk
    - `assign_provider(asset_id, provider_code, params, session)` → calls bulk
    - `bulk_remove_providers(asset_ids, session)` → PRIMARY bulk
    - `remove_provider(asset_id, session)` → calls bulk
    - `get_asset_provider(asset_id, session)` → single query
  
  - **Price Refresh Methods**:
    - `bulk_refresh_prices(requests, session)` → PRIMARY bulk, parallel calls
    - `refresh_price(asset_id, start, end, session)` → calls bulk
  
  - **Manual Price CRUD Methods**:
    - `bulk_upsert_prices(data, session)` → delegates to `pricing.bulk_upsert_asset_prices()`
    - `upsert_prices(asset_id, prices, session)` → calls bulk
    - `bulk_delete_prices(data, session)` → delegates to `pricing.bulk_delete_asset_prices()`
    - `delete_prices(asset_id, ranges, session)` → calls bulk
    - `get_prices(asset_id, start, end, session)` → delegates to `pricing.get_asset_prices()`

- [ ] **Implement helper functions**
  - `get_price_column_precision(column_name)` → (precision, scale)
  - `truncate_price_to_db_precision(value, column_name)` → Decimal
  - `apply_backward_fill_logic(requested_date, available_prices)` → {price_data, backward_fill_info}

- [ ] **Create test file**
  - File: `backend/test_scripts/test_services/test_asset_source_manager.py`
  - Test bulk_assign_providers (3 assets)
  - Test assign_provider (single, calls bulk)
  - Test bulk_remove_providers (3 assets)
  - Test remove_provider (single, calls bulk)
  - Test bulk_refresh_prices (2 assets, parallel)
  - Test refresh_price (single, calls bulk)
  - Test bulk_upsert_prices (2 assets)
  - Test upsert_prices (single, calls bulk)
  - Test bulk_delete_prices (2 assets)
  - Test delete_prices (single, calls bulk)
  - Test get_prices with backfill
  - Test DB query optimization
  - Test backward_fill_info matches FX

- [ ] **Run tests**
  - Run: `pipenv run python -m backend.test_scripts.test_services.test_asset_source_manager`

**Notes**:
```
# Implementation notes


# Issues encountered


# Completion date

```

---

### 1.3 Provider Folder Setup (Auto-Discovery)

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

**Notes**:
```
# Implementation notes


# Issues encountered


# Completion date

```

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

## Phase 4: Synthetic Yield Provider (3-4 days) ⚠️ COMPLEX

**Reference**: [Phase 4 in main doc](./05_plugins_yfinance_css_synthetic_yield.md#phase-4-synthetic_yield-plugin-3-4-giorni--più-complesso)

**Note**: This provider is the most complex - calculates synthetic valuation for loan/bond assets using ACT/365.

- [ ] **Create synthetic_yield.py**
  - File: `backend/app/services/asset_source_providers/synthetic_yield.py`
  - Class: `SyntheticYieldProvider(AssetSourceProvider)`
  - Decorator: `@register_provider(AssetProviderRegistry)`

- [ ] **Implement properties**
  - `provider_code` → `"synthetic_yield"`
  - `provider_name` → `"Synthetic Yield Calculator"`

- [ ] **Implement calculate_days_between()**
  - Use ACT/365: actual_days / 365
  - Return `Decimal` fraction

- [ ] **Implement find_active_rate()**
  - Parse interest schedule (list of {start_date, end_date, rate})
  - Find rate for target_date
  - Handle maturity + grace period → late_interest.rate
  - Return `Decimal` rate

- [ ] **Implement calculate_accrued_interest()**
  - Use SIMPLE interest: principal * sum(rate * time_fraction)
  - Iterate day-by-day from start to end
  - Apply ACT/365 day count for each day
  - Sum daily accruals
  - Return `Decimal` accrued interest

- [ ] **Implement get_current_value()**
  - Fetch asset from DB (asset_id from identifier)
  - Calculate: face_value + accrued_interest_to_today
  - Return `CurrentValue`
  - **TODO**: Needs DB access - pass session or fetch asset first

- [ ] **Implement get_history_value()**
  - Generate daily price series from start_date to end_date
  - For each day: calculate face_value + accrued_interest_to_that_day
  - Return `HistoricalData` with daily `PricePoint` list
  - **TODO**: Needs DB access for asset data

- [ ] **Implement search()**
  - Raise `ProviderError` with NOT_SUPPORTED
  - Synthetic yield works on existing assets in DB

- [ ] **Handle edge cases**
  - Maturity date passed
  - Grace period (late_interest.grace_period_days)
  - Late interest rate application
  - **TODO (Step 03)**: Check if loan was repaid via transactions

- [ ] **Verify auto-discovery**
  - Check: `AssetProviderRegistry.list_providers()` includes "synthetic_yield"

**Notes**:
```
# ACT/365 is hardcoded for simplicity
# True profits = sell_proceeds - buy_cost
# This is just for portfolio valuation estimates

# Implementation notes


# DB access strategy:
# Option 1: Pass session to provider methods
# Option 2: Fetch asset data before calling provider
# Decision:


# Issues encountered


# Completion date

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
  - Run: `pipenv run python -m backend.test_scripts.test_services.test_asset_providers`

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

## Phase 5: API Endpoints (2-3 days)

**Reference**: [API Endpoints Overview in main doc](./05_plugins_yfinance_css_synthetic_yield.md#api-endpoints-overview)

**File**: `backend/app/api/v1/assets.py` (unified: assets + providers)

### 5.1 Provider Discovery Endpoints

- [ ] **GET /api/v1/asset-providers**
  - List all available providers
  - Response: `[{code, name, description, supports_search}, ...]`
  - Uses: `AssetProviderRegistry.list_providers()`

- [ ] **GET /api/v1/asset-providers/{provider_code}/search**
  - Search assets via provider
  - Query param: `q` (query string)
  - Response: List of `{identifier, display_name, currency, type}`
  - Cache: 10 minutes
  - Returns 404 if provider doesn't support search

### 5.2 Provider Assignment Endpoints

- [ ] **POST /api/v1/assets/provider/bulk**
  - Bulk assign providers to assets
  - Request: `[{asset_id, provider_code, provider_params}, ...]`
  - Response: `{success_count, failed_count, results: [...]}`
  - Calls: `AssetSourceManager.bulk_assign_providers()`

- [ ] **DELETE /api/v1/assets/provider/bulk**
  - Bulk remove provider assignments
  - Request: `[{asset_id}, ...]`
  - Response: `{success_count, failed_count, results: [...]}`
  - Calls: `AssetSourceManager.bulk_remove_providers()`

- [ ] **POST /api/v1/assets/{id}/provider**
  - Single assign (convenience)
  - Calls bulk with 1 element

- [ ] **DELETE /api/v1/assets/{id}/provider**
  - Single remove (convenience)
  - Calls bulk with 1 element

### 5.3 Price Data Read Endpoints

- [ ] **GET /api/v1/assets/{id}/prices**
  - Query stored prices with backward-fill
  - Query params: `start` (required), `end` (optional)
  - Response: `{prices: [{date, close, backward_fill_info}, ...]}`
  - **Special**: If asset.type = SCHEDULED_YIELD, uses synthetic calculation
  - Calls: `AssetSourceManager.get_prices()`

### 5.4 Manual Price Management Endpoints

- [ ] **POST /api/v1/assets/prices/bulk**
  - Bulk upsert prices manually
  - Request: `[{asset_id, prices: [{date, open?, high?, low?, close, volume?}, ...]}, ...]`
  - Response: `{inserted_count, updated_count, failed_count, results: [...]}`
  - Calls: `AssetSourceManager.bulk_upsert_prices()`

- [ ] **DELETE /api/v1/assets/prices/bulk**
  - Bulk delete price ranges
  - Request: `[{asset_id, date_ranges: [{start, end?}, ...]}, ...]`
  - Response: `{deleted_count, results: [...]}`
  - Calls: `AssetSourceManager.bulk_delete_prices()`

- [ ] **POST /api/v1/assets/{id}/prices**
  - Single upsert (convenience)
  - Calls bulk with 1 element

- [ ] **DELETE /api/v1/assets/{id}/prices**
  - Single delete (convenience)
  - Calls bulk with 1 element

### 5.5 Provider-Driven Price Refresh Endpoints

- [ ] **POST /api/v1/assets/prices-refresh/bulk**
  - Bulk refresh via providers
  - Request: `[{asset_id, start_date, end_date?}, ...]`
  - **Note**: Only for assets WITH provider assignment
  - SCHEDULED_YIELD assets don't need refresh (calculated runtime)
  - Execution flow:
    1. Group by provider_code
    2. Parallel async calls via asyncio.gather
    3. Each provider processes in parallel
    4. Batch writes via pricing.py
  - Response: `{success_count, failed_count, results: [...]}`
  - Calls: `AssetSourceManager.bulk_refresh_prices()`

- [ ] **POST /api/v1/assets/{id}/prices-refresh**
  - Single refresh (convenience)
  - Query params: `start`, `end` (optional)
  - Calls bulk with 1 element

### 5.6 Pydantic Models

- [ ] **Define request/response models**
  - `ProviderListResponse`
  - `ProviderSearchResponse`
  - `AssignProviderRequest`, `AssignProviderResponse`
  - `PriceQueryResponse` (with `BackwardFillInfo`)
  - `UpsertPricesRequest`, `UpsertPricesResponse`
  - `DeletePricesRequest`, `DeletePricesResponse`
  - `RefreshPricesRequest`, `RefreshPricesResponse`

- [ ] **BackwardFillInfo model** (identical to FX)
  - Fields: `actual_rate_date: str`, `days_back: int`
  - Used when backfill applied (null when exact match)

**Notes**:
```
# Implementation notes


# Issues encountered


# Completion date

```

---

## Phase 6: API Tests (1-2 days)

**Reference**: API Endpoints section in main doc

- [ ] **Create test_asset_api.py**
  - File: `backend/test_scripts/test_api/test_asset_api.py`
  - Pattern: Similar to `test_fx_api.py`

- [ ] **Test provider discovery**
  - GET /api/v1/asset-providers
  - Verify all registered providers listed

- [ ] **Test provider search**
  - GET /api/v1/asset-providers/yfinance/search?q=AAPL
  - Verify results returned
  - Test 404 for non-search providers (cssscraper)

- [ ] **Test provider assignment**
  - POST /api/v1/assets/provider/bulk (3 assets)
  - POST /api/v1/assets/{id}/provider (single)
  - DELETE /api/v1/assets/provider/bulk (3 assets)
  - DELETE /api/v1/assets/{id}/provider (single)

- [ ] **Test price queries**
  - GET /api/v1/assets/{id}/prices (with backward-fill)
  - Verify backward_fill_info structure

- [ ] **Test manual price management**
  - POST /api/v1/assets/prices/bulk (2 assets)
  - POST /api/v1/assets/{id}/prices (single)
  - DELETE /api/v1/assets/prices/bulk (2 assets)
  - DELETE /api/v1/assets/{id}/prices (single)

- [ ] **Test provider-driven refresh**
  - POST /api/v1/assets/prices-refresh/bulk (2 assets)
  - POST /api/v1/assets/{id}/prices-refresh (single)
  - Verify parallel execution

- [ ] **Test error cases**
  - Invalid provider_code
  - Missing required params
  - Invalid date ranges
  - Asset not found

- [ ] **Run tests**
  - Add to test_runner.py: `./test_runner.py api assets`
  - Run: `./test_runner.py -v api assets`

**Notes**:
```
# Test results


# Issues encountered


# Completion date

```

---

## Phase 7: Integration & Documentation (1-2 days)

### 7.1 Update Mock Data

- [ ] **Update populate_mock_data.py**
  - File: `backend/test_scripts/test_db/populate_mock_data.py`
  - Add sample provider assignments
  - Example: AAPL → yfinance
  - Note: SCHEDULED_YIELD assets don't need provider (calculated runtime)

### 7.2 Documentation

- [ ] **Update docs/README.md**
  - Add link to asset provider documentation

- [ ] **Verify/update existing docs**
  - `docs/database-schema.md` → add asset_provider_assignments table
  - `docs/api-development-guide.md` → add asset provider endpoints
  - `docs/testing-guide.md` → add asset provider test info
  - Document synthetic yield calculation (pricing.py module)

- [ ] **Create provider-specific docs** (if needed)
  - How to add new provider (reference to main doc)

### 7.3 Update test_runner.py

- [ ] **Add asset provider tests**
  - Add category: `asset-providers` or similar
  - Include: service tests, API tests
  - Update help text

### 7.4 Final Integration Test

- [ ] **Full workflow test**
  1. Start fresh test DB
  2. Assign yfinance provider to stock asset
  3. Refresh prices via provider
  4. Query prices with backward-fill (normal asset)
  5. Query prices for SCHEDULED_YIELD asset (synthetic calculation)
  6. Verify synthetic values NOT written to DB
  7. Manually update prices
  8. Delete price ranges
  9. Verify all operations work end-to-end

- [ ] **Run all tests**
  - `./test_runner.py db all`
  - `./test_runner.py services all`
  - `./test_runner.py api all`

**Notes**:
```
# Integration test results


# Issues encountered


# Completion date

```

---

## Post-Implementation

### Refactoring & Optimization

- [ ] **Schema factorization** (TODO from Phase 0.2)
  - Move Pydantic models to `backend/app/schemas/`
  - Organize by category: fx.py, assets.py, common.py

- [ ] **FX provider migration** (TODO from Phase 1.1)
  - Migrate existing FX providers to use unified registry
  - Update imports and decorator usage

- [ ] **Performance optimization**
  - Profile DB queries
  - Optimize bulk operations if needed
  - Add caching where appropriate

### Future Enhancements

- [ ] **Additional providers**
  - Alpha Vantage
  - Polygon.io
  - Custom API providers

- [ ] **Enhanced synthetic yield logic**
  - COMPOUND interest support
  - Additional day-count conventions (ACT/360, 30/360)
  - More complex dividend schedule handling

- [ ] **Transaction integration** (Step 03)
  - Fallback to last BUY transaction price if no price_history
  - Check if loan repaid via transactions (synthetic yield module)

**Notes**:
```
# Future work


```

---

## Implementation Log

### Day 1 (Date: ______)
```
Phase: 
Tasks completed:

Issues:

Notes:

```

### Day 2 (Date: ______)
```
Phase: 
Tasks completed:

Issues:

Notes:

```

### Day 3 (Date: ______)
```
Phase: 
Tasks completed:

Issues:

Notes:

```

### Day 4 (Date: ______)
```
Phase: 
Tasks completed:

Issues:

Notes:

```

### Day 5 (Date: ______)
```
Phase: 
Tasks completed:

Issues:

Notes:

```

### Day 6 (Date: ______)
```
Phase: 
Tasks completed:

Issues:

Notes:

```

### Day 7 (Date: ______)
```
Phase: 
Tasks completed:

Issues:

Notes:

```

### Day 8 (Date: ______)
```
Phase: 
Tasks completed:

Issues:

Notes:

```

---

## Quick Reference

### Key Commands

```bash
# Database
./dev.sh db:migrate "message"
./dev.sh db:upgrade [path]
./dev.sh db:current [path]

# Tests
./test_runner.py db all
./test_runner.py services all
./test_runner.py api all
pipenv run python -m backend.test_scripts.test_services.test_pricing
pipenv run python -m backend.test_scripts.test_services.test_asset_providers

# Server
./dev.sh server           # Production mode
./dev.sh server:test      # Test mode
```

### Key Files

```
backend/
├── alembic/versions/5ae234067d65_add_asset_provider_assignments.py ✅
├── app/
│   ├── schemas/
│   │   └── common.py (BackwardFillInfo - shared by FX + Assets)
│   ├── db/
│   │   ├── models.py (AssetProviderAssignment) ✅
│   │   ├── base.py (exports) ✅
│   │   └── __init__.py (exports) ✅
│   ├── services/
│   │   ├── provider_registry.py (AbstractProviderRegistry, FX/Asset specializations)
│   │   ├── fx.py (UNCHANGED - handles fx_rates table independently)
│   │   ├── asset_source.py (NEW - handles price_history + synthetic yield)
│   │   │   ├── TypedDicts, AssetSourceProvider, AssetSourceManager
│   │   │   ├── DB operations for price_history table
│   │   │   ├── Backward-fill logic (independent from FX)
│   │   │   └── Synthetic yield module (calculate_synthetic_value, helpers)
│   │   └── asset_source_providers/
│   │       ├── __init__.py
│   │       ├── yahoo_finance.py (YahooFinanceProvider)
│   │       └── css_scraper.py (CSSScraperProvider)
│   └── api/v1/assets.py (unified assets + providers endpoints)
└── test_scripts/
    ├── test_services/
    │   ├── test_asset_source.py (NEW - price CRUD, backfill, synthetic yield)
    │   ├── test_provider_registry.py
    │   └── test_asset_providers.py (generic suite for providers only)
    └── test_api/
        └── test_asset_api.py
```

### Contact & Support

- **Main Doc**: [`05_plugins_yfinance_css_synthetic_yield.md`](./05_plugins_yfinance_css_synthetic_yield.md)
- **Project**: LibreFolio
- **Step**: 05 - Asset Provider System

---

**Last Updated**: 6 November 2025


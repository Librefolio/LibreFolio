# Step 05: Asset Provider System - yfinance, CSS Scraper + Synthetic Yield Logic

**Data Creazione**: 5 Novembre 2025  
**Prerequisiti**: Step 02 (DB Schema) ✅, Step 04 (FX Multi-Provider) ✅  
**Stima Tempo**: 6-8 giorni  
**Complessità**: Media

**Schema Update (2025-11-06)**:
- `asset_provider_assignments.last_fetch_at` → Track last fetch attempt (NULL = never fetched)
- `fx_currency_pair_sources.fetch_interval` → Refresh frequency in minutes (NULL = 1440 = 24h default)
- Both columns added to support smart scheduling and monitoring (migration 001_initial updated)

---

## 🎯 Goal

Implementare un **provider system modulare** per acquisizione dati asset con:

1. **yfinance Provider**: Fetch prezzi stocks/ETFs da Yahoo Finance
2. **CSS Scraper Provider**: Scraping prezzi da pagine web con CSS selectors
3. **Synthetic Yield Logic**: Calcolo runtime per asset SCHEDULED_YIELD (interno a `pricing.py`, **NON un provider**)

**Nota Importante**: Synthetic yield NON è un provider perché calcola valori a runtime basandosi su dati transazionali che possono cambiare. I valori non vengono salvati in DB ma calcolati on-demand.

---

## 📋 Requirements Overview

### Core Asset Source System
- Main service file: `services/asset_source.py` (like `fx.py`)
  - Contains abstract base class `AssetSource`
  - Contains `AssetSourceManager` class (like FX service functions)
  - TypedDicts: `CurrentValue`, `PricePoint`, `HistoricalData`
  - Error handling: `AssetSourceError`
  - Helper functions for precision
- Provider implementations in separate folder: `services/asset_source_providers/`

**Folder structure**:
```
backend/app/
├── schemas/                             # Shared Pydantic schemas (NEW)
│   └── common.py                        # BackwardFillInfo (used by FX + Assets)
│
├── services/
│   ├── provider_registry.py             # Abstract base registry + factory (system service)
│   │   ├── AbstractProviderRegistry (base class)
│   │   ├── FXProviderRegistry (FX specialization)
│   │   └── AssetProviderRegistry (Asset pricing specialization)
│   │
│   ├── fx.py                            # FX service (existing, UNCHANGED)
│   │   └── DB operations for fx_rates table
│   │
│   ├── asset_source.py                  # Asset pricing service (NEW)
│   │   ├── TypedDicts (CurrentValue, PricePoint, HistoricalData)
│   │   ├── AssetSourceProvider (abstract base class)
│   │   ├── AssetSourceManager (manager class, bulk-first)
│   │   ├── DB operations for price_history table
│   │   ├── Backward-fill logic (similar to FX, but for different table)
│   │   ├── Synthetic yield calculation (for SCHEDULED_YIELD assets)
│   │   └── Helper functions
│   │
│   ├── fx_providers/                    # FX provider implementations (existing)
│   │   ├── __init__.py                  # Auto-discovery via provider_registry
│   │   ├── ecb.py
│   │   ├── fed.py
│   │   └── ... (other FX providers)
│   │
│   └── asset_source_providers/          # Asset pricing provider implementations (NEW)
│       ├── __init__.py                  # Auto-discovery via provider_registry
│       ├── yahoo_finance.py             # YahooFinanceProvider
│       └── css_scraper.py               # CSSScraperProvider
```

**Key Design Principles**:
- **Separate DB Layers**: `fx.py` and `asset_source.py` remain SEPARATE
  - Different tables: `fx_rates` vs `price_history`
  - Different query patterns: (base,quote,date) vs (asset_id,date)
  - Different fields: rate vs OHLC (open/high/low/close/volume) (Open-high-low-close chart)
  - Backward-fill logic similar but not totally equal, implement independently
- **Unified Registry**: `provider_registry.py` contains abstract base + specializations for FX and Assets
- **Shared Schemas Only**: `BackwardFillInfo` TypedDict shared via `schemas/common.py`
- **Auto-Discovery**: Providers auto-register on import via decorator, reading all `.py` files in provider folders
- **Synthetic Yield**: NOT a provider, calculated on-demand in `asset_source.py`
  - Integrated in `get_prices()` method
  - Checks asset.valuation_model during read operations
  - If SCHEDULED_YIELD: calculates value from asset fields + transactions
  - Returns calculated value without DB write
- **Manager Integration**: No separate `manager.py`, all manager logic in main service file
- **Bulk-First Design**: All operations have bulk version as PRIMARY, single-item calls bulk

### Database: Asset Provider Assignments (Nuova Tabella)

**Table**: `asset_provider_assignments`

```sql
CREATE TABLE asset_provider_assignments (
    id INTEGER PRIMARY KEY,
    asset_id INTEGER NOT NULL UNIQUE,  -- 1-to-1 relationship
    provider_code VARCHAR(50) NOT NULL,
    provider_params TEXT,  -- JSON configuration
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE
);

CREATE INDEX idx_asset_provider_asset_id ON asset_provider_assignments(asset_id);
```

**Purpose**: 
- Associa ogni asset al suo provider di pricing (max 1 provider per asset)
- Memorizza configurazione provider (provider_params JSON)
- Sostituisce i campi deprecati in `assets`:
  - ~~current_data_plugin_key~~
  - ~~current_data_plugin_params~~
  - ~~history_data_plugin_key~~
  - ~~history_data_plugin_params~~

**Note**:
- UNIQUE constraint su asset_id (1 asset = 1 provider massimo)
- CASCADE delete (se elimini asset, elimini assignment)
- provider_params è JSON che poi viene ridato al provider ed usato per identificare asset (ticker, URL, ecc) in maniera univoca su piattaforma connessa, è il risultato della ricerca (chiamata dal metodo search descritto sotto)

### API Endpoints Overview

**File**: `backend/app/api/v1/assets.py` (unified endpoint for assets + providers)

All endpoints follow **bulk-first design**: bulk operations are primary, single-item operations internally call bulk with 1 element.

#### Provider Discovery
- `GET /api/v1/asset-providers` - List all available asset pricing providers
  - Response: `[{code, name, description, supports_search}, ...]`

#### Asset Discovery
- `GET /api/v1/assets` - List all assets with provider assignments
  - Response: Asset list with `provider_assignment` field (null if manual)
- `GET /api/v1/assets/{id}` - Get single asset details with provider assignment

#### Provider Search (for asset identification)
- `GET /api/v1/asset-providers/{provider_code}/search?q=<query>` - Search assets via provider
  - Example: `/api/v1/asset-providers/yfinance/search?q=AAPL`
  - Returns list of matching assets with identifiers to use in `provider_params`
  - Response cached 10 minutes
  - Returns 404 if provider doesn't support search (e.g., synthetic_yield)

#### Provider Assignment (Associate asset with provider)
- `POST /api/v1/assets/provider/bulk` - **Bulk assign/update** provider to assets
  - Request: `[{asset_id, provider_code, provider_params}, ...]`
  - Response: `{success_count, failed_count, results: [{asset_id, success, message}, ...]}`
  - Optimized: 1 read query (if validation needed), 1 delete, 1 insert
- `DELETE /api/v1/assets/provider/bulk` - **Bulk remove** provider assignments
  - Request: `[{asset_id}, ...]`
  - Converts assets to manual pricing mode
  - Optimized: 1 delete query with WHERE IN

**Single-item convenience methods** (call bulk internally):
- `POST /api/v1/assets/{id}/provider` - Assign provider to single asset (calls bulk with 1 element)
- `DELETE /api/v1/assets/{id}/provider` - Remove provider from single asset (calls bulk with 1 element)

#### Price Data (Read from DB with Backfill Info)
- `GET /api/v1/assets/{id}/prices?start=<date>&end=<date>` - Query stored prices
  - `end` optional (defaults to `start` for single day)
  - `start` required
  - **Backfill Policy**: If no exact date match, uses most recent available price (like FX)
  - Response includes backfill info (like FX system):
    ```json
    {
      "prices": [
        {
          "date": "2025-11-05",
          "close": "175.50",
          "backward_fill_info": null
        },
        {
          "date": "2025-11-06",
          "close": "175.50",
          "backward_fill_info": {
            "actual_rate_date": "2025-11-05",
            "days_back": 1
          }
        }
      ]
    }
    ```
  - **Note**: `backward_fill_info` is `null` when exact date match, present when backfilled
  - Returns prices as stored in DB (not multiplied by quantity - that's for portfolio valuation later)
  - **TODO (Step 03)**: When transactions implemented, fallback to last BUY price if no price data exists

#### Manual Price Management (No provider)
- `POST /api/v1/assets/prices/bulk` - **Bulk upsert** prices manually
  - Request: `[{asset_id, prices: [{date, open?, high?, low?, close, volume?}, ...]}, ...]`
  - Response: `{inserted_count, updated_count, failed_count, results: [...]}`
  - Optimized: Uses shared `pricing.py` layer, batch upserts per asset
- `DELETE /api/v1/assets/prices/bulk` - **Bulk delete** price ranges
  - Request: `[{asset_id, date_ranges: [{start, end?}, ...]}, ...]`
  - `end` optional (single day if omitted)
  - Response: `{deleted_count, results: [{asset_id, deleted, message}, ...]}`
  - Optimized: Uses shared `pricing.py` layer, 1 DELETE with complex WHERE

**Single-item convenience methods** (call bulk internally):
- `POST /api/v1/assets/{id}/prices` - Upsert prices for single asset (calls bulk with 1 asset)
- `DELETE /api/v1/assets/{id}/prices` - Delete price ranges for single asset (calls bulk with 1 asset)

#### Provider-Driven Price Refresh
- `POST /api/v1/assets/prices-refresh/bulk` - **Bulk refresh** prices via providers
  - Request: `[{asset_id, start_date, end_date?}, ...]`
  - If only `start_date`: fetch single day (current price)
  - If `start_date` + `end_date`: fetch historical range
  - **Execution Flow**:
    1. API groups requests by `provider_code` (from `asset_provider_assignments`)
    2. Parallel async calls to each provider (via `asyncio.gather`)
    3. Each provider processes its requests in parallel where possible
    4. All providers write to DB via shared `pricing.py` in optimized batch operations
  - Response: `{success_count, failed_count, results: [{asset_id, fetched_count, success, message, backfill_info?}, ...]}`
  - Optimized: Parallel provider calls, batch DB writes via `pricing.py`

**Single-item convenience methods** (call bulk internally):
- `POST /api/v1/assets/{id}/prices-refresh?start=<date>&end=<date>` - Refresh single asset (calls bulk with 1 element)

---

### Provider Implementations

#### 1. Yahoo Finance Provider
- **Purpose**: Fetch market prices for stocks, ETFs, mutual funds
- **Data Source**: Yahoo Finance API (via yfinance library)
- **File**: `asset_source_providers/yahoo_finance.py`
- **Class**: `YahooFinanceProvider`
- **Methods**: 
  - `get_current_value()` - Latest available price
  - `get_history_value(start, end)` - OHLC historical series
  - `search(query)` - Search tickers (cached 10 min)
- **Features**: Auto currency detection, robust error handling

#### 2. CSS Scraper Provider
- **Purpose**: Web scraping for generic websites
- **Dependencies**: httpx + BeautifulSoup4
- **File**: `asset_source_providers/css_scraper.py`
- **Class**: `CSSScraperProvider`
- **Configuration**: URL, CSS selector, currency
- **Methods**:
  - `get_current_value()` - Parse price from HTML
  - `get_history_value()` - Not supported (returns empty)
  - `search()` - Not applicable (requires manual configuration)
- **Features**: Robust float parsing (1,234.56 and 1.234,56), configurable selectors

---

### Synthetic Yield Calculation (Internal Logic)

**⚠️ NOT A PROVIDER** - This is internal logic in `pricing.py`, not a separate provider.

- **Purpose**: Calculate synthetic valuation for SCHEDULED_YIELD assets (loans, bonds) at runtime
- **Location**: `backend/app/services/pricing.py` (integrated in read operations)
- **Why Not a Provider?**: 
  - Values calculated on-demand from asset fields + transactions
  - Results can change based on transaction history
  - No DB write (values are ephemeral)
  - Automatically applied during `get_asset_prices()` when asset type = SCHEDULED_YIELD

- **Input**: Asset fields from DB
  - `interest_schedule` - List of {start_date, end_date, rate}
  - `dividend_schedule` - Optional dividend payments
  - `maturity_date` - Loan maturity
  - `late_interest` - {rate, grace_period_days}
  - `face_value` - Principal amount

- **Output**: Calculated prices (principal + accrued interest - dividends if present)

- **Features**: 
  - Day-count: ACT/365 only (simplicity)
  - Interest type: SIMPLE only
  - Maturity + grace period + late interest handling
  - **TODO (Step 03)**: Check if loan was repaid via transactions

- **Implementation**: See [Phase 0.2 - Synthetic Yield Module](./05_plugins_yfinance_css_synthetic_yield.md#02-shared-pricing-layer) for details
  - Maturity + grace period + late interest handling

### Service Layer (AssetSourceManager)

**Main Service** (`services/asset_source.py`):
- `AssetSource` - Abstract base class (like `FXRateProvider`)
- `AssetSourceManager` - Manager class with **bulk-first methods**:

#### Plugin Assignment Methods
- `bulk_assign_plugins(assignments: list[dict], session)` - **PRIMARY** bulk assignment
  - Input: `[{asset_id, plugin_key, plugin_params}, ...]`
  - Optimized: 1 read (if validation), 1 delete, 1 insert query
  - Returns: List of results per asset
- `assign_plugin(asset_id, plugin_key, params, session)` - Single assign (calls bulk with 1 element)
- `bulk_remove_plugins(asset_ids: list[int], session)` - **PRIMARY** bulk removal
  - Optimized: 1 DELETE query with WHERE IN
- `remove_plugin(asset_id, session)` - Single remove (calls bulk with 1 element)
- `get_asset_plugin(asset_id, session)` - Fetch plugin assignment from DB

#### Price Refresh Methods (via plugins)
- `bulk_refresh_prices(requests: list[dict], session)` - **PRIMARY** bulk refresh
  - Input: `[{asset_id, start_date, end_date?}, ...]`
  - Fetches current or historical based on parameters
  - Parallel plugin calls where possible
  - Batch DB writes for efficiency
- `refresh_price(asset_id, start, end, session)` - Single refresh (calls bulk with 1 element)

#### Manual Price CRUD Methods
- `bulk_upsert_prices(data: list[dict], session)` - **PRIMARY** bulk upsert
  - Input: `[{asset_id, prices: [{date, open?, high?, low?, close, volume?}, ...]}, ...]`
  - Optimized: Batch upserts, minimize DB roundtrips
- `upsert_prices(asset_id, prices, session)` - Single upsert (calls bulk with 1 element)
- `bulk_delete_prices(data: list[dict], session)` - **PRIMARY** bulk delete
  - Input: `[{asset_id, date_ranges: [{start, end?}, ...]}, ...]`
  - Optimized: 1 DELETE query with complex WHERE
- `delete_prices(asset_id, date_ranges, session)` - Single delete (calls bulk with 1 element)
- `get_prices(asset_id, start, end, session)` - Query stored prices

#### Helper Functions
- Decimal precision helpers for truncating db problem (like FX system)
- Provider resolution from `asset_provider_assignments`
- Date range utilities
- **Backfill logic**: Identical to FX system
  - Returns `backward_fill_info: {actual_rate_date, days_back}` when backfilled
  - Returns `null` when exact date match
  - **TODO (Step 03)**: Fallback to last BUY transaction price if no price_history data

#### Shared DB Layer
All price write operations delegate to `pricing.py`:
- `pricing.bulk_upsert_asset_prices()` - Batch upserts with minimal queries
- `pricing.bulk_delete_asset_prices()` - Optimized DELETE with complex WHERE
- Used by both manual operations and provider-driven refreshes

**Note**: Like FX system, everything in one main file (`asset_source.py`)

**DB Optimization Strategy**:
- All bulk methods minimize DB queries (typically 1-3 max)
- Use `WHERE IN` for batch operations
- Parallel async operations where possible (provider fetches)
- All DB writes go through shared `pricing.py` layer
- Batch writes after all provider calls complete



---

## 📐 Day-Count Convention: ACT/365

### ⚠️ Important Note: This is an Estimate

**Accrued interest calculations are for portfolio valuation only**.

**True profits** = `sell_proceeds - buy_cost`

There's no point splitting hairs for estimative calculations. ACT/365 is chosen for:
- ✅ **Simplicity**: Intuitive calculation
- ✅ **Sufficient accuracy**: For valuation purposes
- ✅ **Standard**: Used in many markets (Europe, UK)

For complete mathematical reasoning, see [docs/financial-calculations.md](../docs/financial-calculations.md)

---

## 🏗️ Detailed Implementation Plan

### Phase 0: Database Setup + Common Schemas (1 day)

#### 0.1 Create Table: asset_provider_assignments

**File**: `backend/alembic/versions/xxx_add_asset_provider_assignments.py`

**Migration**:
```python
"""Add asset_provider_assignments table

Revision ID: xxx
Revises: c19f65d87398
Create Date: 2025-11-06
"""
from alembic import op
import sqlalchemy as sa

def upgrade() -> None:
    op.create_table(
        'asset_provider_assignments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('asset_id', sa.Integer(), nullable=False),
        sa.Column('provider_code', sa.String(50), nullable=False),
        sa.Column('provider_params', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_asset_provider_asset_id', 'asset_provider_assignments', ['asset_id'])
    op.create_unique_constraint('uq_asset_provider_asset_id', 'asset_provider_assignments', ['asset_id'])

def downgrade() -> None:
    op.drop_index('idx_asset_provider_asset_id', table_name='asset_provider_assignments')
    op.drop_table('asset_provider_assignments')
```

**Model**: `backend/app/db/models.py`

```python
class AssetProviderAssignment(SQLModel, table=True):
    """
    Asset provider assignment (1-to-1 relationship).
    
    Each asset can have at most one provider assigned for pricing.
    """
    __tablename__ = "asset_provider_assignments"
    
    id: int | None = Field(default=None, primary_key=True)
    asset_id: int = Field(foreign_key="assets.id", unique=True, nullable=False)
    provider_code: str = Field(max_length=50, nullable=False)
    provider_params: str | None = Field(default=None)  # JSON
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

**Test**: `backend/test_scripts/test_db/db_schema_validate.py`
- [ ] Aggiungi verifica tabella asset_provider_assignments
- [ ] Verifica UNIQUE constraint su asset_id
- [ ] Verifica FK verso assets con CASCADE

**Checklist**:
- [ ] Migration creata con ./dev.sh db:migrate
- [ ] Migration testata (up/down)
- [ ] Model aggiunto a db/models.py
- [ ] Model esportato in db/__init__.py
- [ ] Test schema validation passa
- [ ] Migration applicata a test_app.db

---

#### 0.1.2 Data Migration & Cleanup: Move Plugin Data to asset_provider_assignments

**Purpose**: Migrate existing plugin assignments from old `assets` table columns to new `asset_provider_assignments` table, then DROP old columns.

**Old columns in `assets` table** (to be removed):
- `current_data_plugin_key` → maps to `provider_code`
- `current_data_plugin_params` → maps to `provider_params`
- `history_data_plugin_key` → IGNORED (same as current, provider handles both)
- `history_data_plugin_params` → IGNORED (same as current, provider handles both)

**Why only 2 columns in new table?**
- Single provider per asset handles BOTH current and historical data
- Provider uses `provider_params` (e.g., ticker "AAPL") for both current and history queries
- Simplifies design: 1-to-1 relationship between asset and provider

**Migration strategy**:
1. **Copy data**: For each asset with `current_data_plugin_key` NOT NULL:
   - INSERT INTO `asset_provider_assignments` (asset_id, provider_code, provider_params)
   - Map: `current_data_plugin_key` → `provider_code`, `current_data_plugin_params` → `provider_params`
   - Ignore `history_data_plugin_*` fields (assumed to be same or unused)

2. **Drop old columns**: After data copy, DROP all 4 plugin columns from `assets` table
   - We're in DEV environment → safe to drop directly
   - No deprecation period needed
   
3. **Update model**: Remove old fields from `Asset` model

**File**: `backend/alembic/versions/xxx_migrate_plugin_data_to_assignments.py`

```python
"""migrate plugin data to asset_provider_assignments and drop old columns

Revision ID: xxx
Revises: 5ae234067d65
Create Date: 2025-11-06
"""
from alembic import op
import sqlalchemy as sa

def upgrade() -> None:
    """
    1. Copy plugin assignments from assets table to asset_provider_assignments
    2. Drop old plugin columns from assets table (DEV environment - safe to drop)
    """
    # Step 1: Copy data
    op.execute("""
        INSERT INTO asset_provider_assignments (asset_id, provider_code, provider_params, created_at, updated_at)
        SELECT 
            id,
            current_data_plugin_key,
            current_data_plugin_params,
            datetime('now'),
            datetime('now')
        FROM assets
        WHERE current_data_plugin_key IS NOT NULL
    """)
    
    # Step 2: Drop old columns (SQLite limitation - need to recreate table)
    # Note: In production, would use batch_alter_table, but for SQLite we recreate
    with op.batch_alter_table('assets', schema=None) as batch_op:
        batch_op.drop_column('current_data_plugin_key')
        batch_op.drop_column('current_data_plugin_params')
        batch_op.drop_column('history_data_plugin_key')
        batch_op.drop_column('history_data_plugin_params')

def downgrade() -> None:
    """
    1. Re-add old plugin columns to assets table
    2. Copy data back from asset_provider_assignments
    3. Clear asset_provider_assignments
    
    Note: This allows full rollback if needed.
    """
    # Step 1: Re-add columns
    with op.batch_alter_table('assets', schema=None) as batch_op:
        batch_op.add_column(sa.Column('current_data_plugin_key', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('current_data_plugin_params', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('history_data_plugin_key', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('history_data_plugin_params', sa.Text(), nullable=True))
    
    # Step 2: Copy data back
    op.execute("""
        UPDATE assets
        SET 
            current_data_plugin_key = (
                SELECT provider_code FROM asset_provider_assignments 
                WHERE asset_provider_assignments.asset_id = assets.id
            ),
            current_data_plugin_params = (
                SELECT provider_params FROM asset_provider_assignments 
                WHERE asset_provider_assignments.asset_id = assets.id
            )
        WHERE id IN (SELECT asset_id FROM asset_provider_assignments)
    """)
    
    # Step 3: Clear new table
    op.execute("DELETE FROM asset_provider_assignments")
```

**Model Update**: `backend/app/db/models.py`

**REMOVE** old plugin fields from `Asset` model (they no longer exist in DB):

```python
class Asset(SQLModel, table=True):
    # ...existing fields...
    
    # OLD FIELDS REMOVED:
    # - current_data_plugin_key
    # - current_data_plugin_params  
    # - history_data_plugin_key
    # - history_data_plugin_params
    
    # Use asset_provider_assignments table instead (1-to-1 relationship)
```

**Checklist**:
- [ ] Migration created with ./dev.sh db:migrate
- [ ] Data migration SQL tested on copy of production data
- [ ] **BEFORE applying**: Backup both databases (just in case)
- [ ] Migration applied to test_app.db
- [ ] Verify: `current_data_plugin_*` columns no longer in assets table
- [ ] Verify: Data copied to asset_provider_assignments correctly
- [ ] Test downgrade (re-adds columns, copies data back, clears new table)
- [ ] Re-apply upgrade (final state)
- [ ] Migration applied to app.db
- [ ] Model updated: Remove old plugin fields from Asset class
- [ ] Schema validation test passes

**Verification Queries**:
```sql
-- BEFORE migration: Check how many rows to migrate
SELECT COUNT(*) FROM assets WHERE current_data_plugin_key IS NOT NULL;

-- AFTER migration: Verify columns dropped
PRAGMA table_info(assets);
-- Should NOT show: current_data_plugin_key, current_data_plugin_params, 
--                  history_data_plugin_key, history_data_plugin_params

-- AFTER migration: Verify data copied
SELECT COUNT(*) FROM asset_provider_assignments;
-- Should match count from first query
```

---

#### 0.2 Common Schemas + Asset Source Service Foundation

**Decision**: Keep FX and Asset DB operations **SEPARATE** (different tables, different structures).
**Share only**: Common schemas (BackwardFillInfo) and provider registry pattern.

**Why separate?**
- `fx_rates` table: base/quote pairs, single rate field
- `price_history` table: asset_id, OHLC fields (open/high/low/close/volume)
- Different query patterns, different constraints
- Backward-fill logic is similar but queries are too different to force abstraction
- ~20 lines of duplicated backward-fill code is acceptable vs fragile generic layer

**What we share**:
- `BackwardFillInfo` TypedDict (common response format)
- Provider registry pattern (abstract base for FX + Assets)
- Common utility functions (if genuinely reusable)

---

**Phase 0.2.1: Common Schemas**

**File**: `backend/app/schemas/common.py` (NEW)

```python
"""
Common schemas shared across subsystems.
"""
from typing import TypedDict


class BackwardFillInfo(TypedDict):
    """
    Backward-fill information (used by both FX and Asset pricing).
    
    Present when requested date has no data and we use an older date.
    Null when exact date match found.
    """
    actual_rate_date: str  # ISO date of actual data used
    days_back: int  # Number of days back from requested date
```

**Phase 0.2.2: Asset Source Service (Foundation + ACT/365 Only)**

**File**: `backend/app/services/asset_source.py`

Asset pricing service with DB operations for `price_history` table.
Pattern identical to `fx.py` but for different table structure.

**Synthetic Yield - Phase Implementation**:
- **Phase 0.2.2 (Current)**: Only ACT/365 day count calculation implemented
- **Phase 4 (Future)**: Full synthetic yield logic (rate schedules, accrued interest, maturity handling)

```python
"""
Asset pricing service.

Handles asset price fetching and management with support for multiple providers.
Similar structure to fx.py but for price_history table.

Note: Full synthetic yield calculation (SCHEDULED_YIELD assets) will be implemented in Phase 4.
Currently only ACT/365 day count helper is available.
"""
from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal
from typing import TypedDict
from sqlalchemy.ext.asyncio import AsyncSession

# Import common schema
from backend.app.schemas.common import BackwardFillInfo

# ============ TypedDicts ============

class CurrentValue(TypedDict):
    """Current asset value."""
    value: Decimal
    currency: str
    as_of_date: date
    source: str  # Provider name

class PricePoint(TypedDict):
    """Single price observation."""
    date: date
    open: Decimal | None
    high: Decimal | None
    low: Decimal | None
    close: Decimal
    volume: int | None
    currency: str

class HistoricalData(TypedDict):
    """Historical price series."""
    prices: list[PricePoint]
    currency: str
    source: str

# ============ Exceptions ============

class ProviderError(Exception):
    """Provider-specific error."""
    def __init__(self, message: str, error_code: str, details: dict | None = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)

# ============ Abstract Base Class ============

class AssetSourceProvider(ABC):
    """Abstract base class for asset pricing providers."""
    
    @property
    @abstractmethod
    def provider_code(self) -> str:
        """Unique provider identifier (e.g., 'yfinance', 'cssscraper')."""
        pass
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider name."""
        pass
    
    @abstractmethod
    async def get_current_value(
        self, 
        identifier: str, 
        provider_params: dict | None = None
    ) -> CurrentValue:
        """Fetch current value for an asset."""
        pass
    
    @abstractmethod
    async def get_history_value(
        self,
        identifier: str,
        start_date: date,
        end_date: date,
        provider_params: dict | None = None
    ) -> HistoricalData:
        """Fetch historical price series."""
        pass
    
    @abstractmethod
    async def search(self, query: str) -> list[dict]:
        """Search for assets matching query string."""
        pass

# ============ Manager Class (Bulk-first design) ============

class AssetSourceManager:
    """Manager for asset pricing operations."""
    
    # Provider assignment methods
    @staticmethod
    async def bulk_assign_providers(...) -> list[dict]:
        """PRIMARY: Bulk assign providers to assets."""
        pass
    
    @staticmethod
    async def assign_provider(...) -> dict:
        """Single assign (calls bulk with 1 element)."""
        pass
    
    # Price refresh methods (via providers)
    @staticmethod
    async def bulk_refresh_prices(...) -> list[dict]:
        """PRIMARY: Bulk refresh via providers."""
        pass
    
    @staticmethod
    async def refresh_price(...) -> dict:
        """Single refresh (calls bulk with 1 element)."""
        pass
    
    # Manual price CRUD (price_history table)
    @staticmethod
    async def bulk_upsert_prices(
        data: list[dict],
        session: AsyncSession
    ) -> dict:
        """PRIMARY: Bulk upsert prices to price_history table."""
        pass
    
    @staticmethod
    async def bulk_delete_prices(
        data: list[dict],
        session: AsyncSession
    ) -> dict:
        """PRIMARY: Bulk delete price ranges from price_history table."""
        pass
    
    @staticmethod
    async def get_prices(
        asset_id: int,
        start_date: date,
        end_date: date | None,
        session: AsyncSession
    ) -> list[dict]:
        """
        Query stored prices with backward-fill logic.
        
        Special handling:
        - If asset.valuation_model == SCHEDULED_YIELD:
          → call calculate_synthetic_value() (runtime, no DB)
        - Else:
          → query price_history table with backward-fill
        
        Returns prices with backward_fill_info (like FX).
        """
        pass

# ============ Helper Functions ============

def get_price_column_precision(column_name: str) -> tuple[int, int]:
    """Get precision for price_history decimal columns (18, 6)."""
    pass

def truncate_price_to_db_precision(value: Decimal, column_name: str) -> Decimal:
    """Truncate decimal to DB precision."""
    pass

def apply_backward_fill_logic(
    requested_date: date,
    available_prices: list[dict]
) -> dict:
    """
    Apply backward-fill logic (identical to FX).
    
    Returns: {
        price_data: dict,
        backward_fill_info: BackwardFillInfo | None
    }
    """
    pass

# ============ Synthetic Yield Calculation (SCHEDULED_YIELD Assets) ============

async def calculate_synthetic_value(
    asset: Asset,
    target_date: date,
    session: AsyncSession
) -> Decimal:
    """
    Calculate synthetic value for SCHEDULED_YIELD asset at specific date.
    
    This is called automatically by get_asset_prices() when asset.type = SCHEDULED_YIELD.
    Values are calculated on-demand, NOT written to DB.
    
    Args:
        asset: Asset object with interest_schedule, face_value, etc.
        target_date: Date to calculate value for
        session: DB session (for fetching transactions if needed)
        
    Returns:
        Synthetic value = face_value + accrued_interest - dividends_paid
        
    Formula:
        value = principal + accrued_interest
        
    Where:
        - principal = asset.face_value
        - accrued_interest = calculated via ACT/365 SIMPLE interest
        - dividends = sum of dividend_schedule payments up to target_date
        
    Day-count: ACT/365 (actual days / 365)
    Interest type: SIMPLE only
    
    TODO (Step 03): Check if loan repaid via transactions
    """
    pass

def calculate_days_between_act365(start: date, end: date) -> Decimal:
    """
    Calculate day fraction using ACT/365.
    
    Args:
        start: Start date
        end: End date
        
    Returns:
        Decimal fraction (actual_days / 365)
    """
    days = (end - start).days
    return Decimal(days) / Decimal(365)

def find_active_rate(
    schedule: list[dict],
    target_date: date,
    maturity_date: date,
    late_interest: dict | None
) -> Decimal:
    """
    Find active interest rate for specific date from schedule.
    
    Args:
        schedule: List of {start_date, end_date, rate} periods
        target_date: Date to find rate for
        maturity_date: Asset maturity date
        late_interest: {rate, grace_period_days} for overdue periods
        
    Returns:
        Active rate as Decimal
        
    Logic:
        1. Check if target_date within any schedule period → return that rate
        2. If past maturity + grace → return late_interest.rate
        3. Otherwise → 0
    """
    pass

def calculate_accrued_interest(
    principal: Decimal,
    schedule: list[dict],
    start_date: date,
    end_date: date,
    maturity_date: date,
    late_interest: dict | None
) -> Decimal:
    """
    Calculate accrued SIMPLE interest from start to end date.
    
    Args:
        principal: Face value / principal amount
        schedule: Interest rate schedule
        start_date: Accrual start
        end_date: Accrual end
        maturity_date: Asset maturity
        late_interest: Late interest config
        
    Returns:
        Total accrued interest
        
    Formula (SIMPLE interest):
        interest = principal * sum(rate * time_fraction)
        
    Where time_fraction = days / 365 (ACT/365)
    
    Implementation:
        - Iterate day-by-day from start to end
        - For each day: find active rate
        - Calculate daily accrual: principal * rate * (1/365)
        - Sum all daily accruals
    """
    pass
```

**Test**: `backend/test_scripts/test_services/test_asset_source.py`

**Price CRUD operations** (price_history table):
- [ ] Test bulk_upsert_prices (2 assets, multiple prices each)
- [ ] Test bulk_delete_prices (2 assets, multiple date ranges)
- [ ] Test upsert_prices single (calls bulk internally)
- [ ] Test delete_prices single (calls bulk internally)
- [ ] Verify DB query count optimization (minimize queries)
- [ ] Test decimal truncation handling

**Price query with backward-fill**:
- [ ] Test get_prices with exact date match (backward_fill_info = null)
- [ ] Test get_prices with missing date (backward_fill_info present)
- [ ] Test get_prices with date range
- [ ] Test backward-fill logic matches FX pattern
- [ ] Test backward-fill respects SCHEDULED_YIELD special handling

**Synthetic yield calculation** (SCHEDULED_YIELD assets):
- [x] Test calculate_days_between_act365 (various date ranges) ✅ Phase 0.2.2
- [ ] Test find_active_rate with simple schedule - **DEFERRED TO PHASE 4**
- [ ] Test find_active_rate with maturity + grace period - **DEFERRED TO PHASE 4**
- [ ] Test find_active_rate with late interest - **DEFERRED TO PHASE 4**
- [ ] Test calculate_accrued_interest SIMPLE (single rate) - **DEFERRED TO PHASE 4**
- [ ] Test calculate_accrued_interest with rate changes - **DEFERRED TO PHASE 4**
- [ ] Test calculate_synthetic_value (current date) - **DEFERRED TO PHASE 4**
- [ ] Test calculate_synthetic_value (historical date) - **DEFERRED TO PHASE 4**
- [ ] Test get_prices automatically uses synthetic for SCHEDULED_YIELD assets - **DEFERRED TO PHASE 4**
- [ ] Test synthetic values NOT written to DB - **DEFERRED TO PHASE 4**

**Provider assignment operations**:
- [ ] Test bulk_assign_providers (3 assets)
- [ ] Test bulk_remove_providers (3 assets)
- [ ] Test assign_provider single (calls bulk)
- [ ] Test remove_provider single (calls bulk)

**Provider refresh operations**:
- [ ] Test bulk_refresh_prices (2 assets, parallel provider calls)
- [ ] Test refresh_price single (calls bulk)

**Checklist**:
- [x] common.py created with BackwardFillInfo schema ✅
- [x] asset_source.py created (similar structure to fx.py) ✅
- [x] Synthetic yield module (PARTIAL): ACT/365 day count only ✅ Phase 0.2.2
  - [ ] Full implementation (rate schedules, accrued interest) - **DEFERRED TO PHASE 4**
- [ ] get_prices() checks asset.valuation_model for SCHEDULED_YIELD - **DEFERRED TO PHASE 4**
- [x] Helper functions for decimal precision ✅
- [x] Backward-fill logic similar to FX but independent implementation ✅
- [x] Tests pass with DB optimization verified ✅ (11/11 tests passing)
- [x] FX and Asset systems remain independent ✅

---

### Phase 1: Unified Provider Registry + Asset Source Foundation (2-3 giorni)

#### 1.1 Unified Provider Registry (Abstract Base + Specializations)

**File**: `backend/app/services/provider_registry.py`

Unified registry system for all provider types (FX, Assets, future extensions):

```python
"""
Unified provider registry and factory system.

Supports auto-discovery of providers from designated folders:
- fx_providers/
- asset_source_providers/
"""
import os
import importlib
import logging
from abc import ABC, abstractmethod
from typing import Type, TypeVar, Generic
from pathlib import Path

logger = logging.getLogger(__name__)

T = TypeVar('T')

class AbstractProviderRegistry(ABC, Generic[T]):
    """
    Abstract base class for provider registries.
    
    Subclasses implement specific provider types (FX, Assets, etc.).
    Supports auto-discovery via folder scanning + decorator.
    """
    
    _providers: dict[str, Type[T]] = {}
    
    @classmethod
    @abstractmethod
    def _get_provider_folder(cls) -> str:
        """Return provider folder name (e.g., 'fx_providers', 'asset_source_providers')."""
        pass
    
    @classmethod
    @abstractmethod
    def _get_provider_code_attr(cls) -> str:
        """Return attribute name for provider code (e.g., 'provider_code', 'plugin_key')."""
        pass
    
    @classmethod
    def auto_discover(cls) -> None:
        """
        Auto-discover all providers in designated folder.
        
        Scans folder, imports all .py files (except __init__.py).
        Providers must use @register_provider decorator to register.
        """
        folder_name = cls._get_provider_folder()
        services_path = Path(__file__).parent
        provider_folder = services_path / folder_name
        
        if not provider_folder.exists():
            logger.warning(f"Provider folder not found: {provider_folder}")
            return
        
        logger.info(f"Auto-discovering providers in: {folder_name}")
        
        for file in provider_folder.glob("*.py"):
            if file.name.startswith("__"):
                continue
            
            module_name = f"backend.app.services.{folder_name}.{file.stem}"
            try:
                importlib.import_module(module_name)
                logger.debug(f"Imported provider module: {module_name}")
            except Exception as e:
                logger.error(f"Failed to import {module_name}: {e}")
    
    @classmethod
    def register(cls, provider_class: Type[T]) -> None:
        """Register a provider class."""
        instance = provider_class()
        code_attr = cls._get_provider_code_attr()
        code = getattr(instance, code_attr)
        
        if code in cls._providers:
            logger.warning(f"Provider {code} already registered, overwriting")
        
        cls._providers[code] = provider_class
        logger.info(f"Registered provider: {code}")
    
    @classmethod
    def get_provider(cls, code: str) -> T:
        """Get provider instance by code."""
        if code not in cls._providers:
            available = ", ".join(cls._providers.keys())
            raise ValueError(
                f"Provider '{code}' not found. Available: {available}"
            )
        
        provider_class = cls._providers[code]
        return provider_class()
    
    @classmethod
    def list_providers(cls) -> list[dict]:
        """List all registered providers."""
        providers = []
        code_attr = cls._get_provider_code_attr()
        
        for code, provider_class in cls._providers.items():
            instance = provider_class()
            providers.append({
                "code": code,
                "name": getattr(instance, "provider_name", code)
            })
        return providers
    
    @classmethod
    def clear(cls) -> None:
        """Clear all registered providers (for testing)."""
        cls._providers.clear()


# Specialization for FX Providers
class FXProviderRegistry(AbstractProviderRegistry):
    """Registry for FX rate providers."""
    
    @classmethod
    def _get_provider_folder(cls) -> str:
        return "fx_providers"
    
    @classmethod
    def _get_provider_code_attr(cls) -> str:
        return "provider_code"


# Specialization for Asset Source Providers
class AssetProviderRegistry(AbstractProviderRegistry):
    """Registry for asset pricing providers."""
    
    @classmethod
    def _get_provider_folder(cls) -> str:
        return "asset_source_providers"
    
    @classmethod
    def _get_provider_code_attr(cls) -> str:
        return "provider_code"


# Decorator for auto-registration
def register_provider(registry_class: Type[AbstractProviderRegistry]):
    """
    Decorator factory for provider registration.
    
    Usage:
        @register_provider(AssetProviderRegistry)
        class YahooFinanceProvider:
            ...
    """
    def decorator(provider_class):
        registry_class.register(provider_class)
        return provider_class
    return decorator


# Auto-discover all providers on module import
FXProviderRegistry.auto_discover()
AssetProviderRegistry.auto_discover()
```

**Note**: 
- Docker-friendly: Just drop `.py` file in provider folder, auto-discovered on startup
- Decorator registers provider: `@register_provider(AssetProviderRegistry)`
- Each provider type has its own registry (FX, Assets)
- **TODO**: Refactor existing FX providers to use this system

**Test**: `backend/test_scripts/test_services/test_provider_registry.py`
- [ ] Test auto_discover scans folder correctly
- [ ] Test register provider via decorator
- [ ] Test get_provider by code
- [ ] Test get_provider raises error if not found
- [ ] Test list_providers returns all registered
- [ ] Test clear() for test isolation
- [ ] Test FXProviderRegistry specialization
- [ ] Test AssetProviderRegistry specialization

**Checklist**:
- [ ] provider_registry.py created with abstract base
- [ ] FXProviderRegistry and AssetProviderRegistry implemented
- [ ] Auto-discovery via folder scanning works
- [ ] Decorator @register_provider works
- [ ] Tests pass for both registry types
- [ ] Docker-compatible (file drop in folder = auto-register)

---

#### 1.2 Asset Source Base Class, TypedDicts & Manager

**File**: `backend/app/services/asset_source.py`

**Structure** (following `fx.py` pattern):
```python
"""
Asset Source service.
Handles asset price fetching and management with support for multiple providers.
"""
# Imports
# Helper functions (like get_column_decimal_precision, truncate_decimal_to_db_precision)
# TypedDicts
# Abstract base class AssetSourceProvider
# AssetSourceManager class
# No provider imports here - handled by registry auto-discovery
```

**Implementa**:
```python
from abc import ABC, abstractmethod
from typing import TypedDict
from datetime import date
from decimal import Decimal

# TypedDicts for type safety
class CurrentValue(TypedDict):
    """Current asset value."""
    value: Decimal
    currency: str
    as_of_date: date
    source: str  # Plugin name

class PricePoint(TypedDict):
    """Single price observation."""
    date: date
    open: Decimal | None
    high: Decimal | None
    low: Decimal | None
    close: Decimal
    volume: int | None
    currency: str

class HistoricalData(TypedDict):
    """Historical price series."""
    prices: list[PricePoint]
    currency: str
    source: str

# Exception
class ProviderError(Exception):
    """Provider-specific error."""
    def __init__(self, message: str, error_code: str, details: dict | None = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)

# Abstract Base Class
class AssetSourceProvider(ABC):
    """Abstract base class for asset pricing providers."""
    
    @property
    @abstractmethod
    def provider_code(self) -> str:
        """Unique provider identifier (e.g., 'yfinance', 'cssscraper')."""
        pass
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider name."""
        pass
    
    @abstractmethod
    async def get_current_value(
        self, 
        identifier: str, 
        provider_params: dict | None = None
    ) -> CurrentValue:
        """
        Fetch current value for an asset.
        
        Args:
            identifier: Asset identifier (ticker, ISIN, etc.)
            provider_params: Provider-specific configuration (JSON)
            
        Returns:
            CurrentValue with latest price
            
        Raises:
            ProviderError: If fetch fails
        """
        pass
    
    @abstractmethod
    async def get_history_value(
        self,
        identifier: str,
        start_date: date,
        end_date: date,
        provider_params: dict | None = None
    ) -> HistoricalData:
        """
        Fetch historical price series.
        
        Args:
            identifier: Asset identifier
            start_date: Start of range (inclusive)
            end_date: End of range (inclusive)
            provider_params: Provider-specific configuration
            
        Returns:
            HistoricalData with price series
            
        Raises:
            ProviderError: If fetch fails
        """
        pass
    
    def validate_params(self, provider_params: dict | None) -> dict:
        """
        Validate and normalize provider parameters.
        
        Override in subclass to add custom validation.
        
        Returns:
            Normalized params dict
            
        Raises:
            ProviderError: If validation fails
        """
        return provider_params or {}
    
    @abstractmethod
    async def search(self, query: str) -> list[dict]:
        """
        Search for assets matching query string.
        
        Returns list of matches with exact identifiers to use.
        
        Args:
            query: Search string (ticker, name, ISIN, etc.)
            
        Returns:
            List of dicts: [
                {
                    "identifier": "AAPL",  # Exact value to store in provider_params
                    "display_name": "Apple Inc.",
                    "currency": "USD",
                    "type": "Stock"  # or ETF, etc.
                },
                ...
            ]
            
        Raises:
            ProviderError: If search fails
            
        Note:
            Results should be cached (10 min TTL) to avoid excessive API calls.
        """
        pass
```

**AssetSourceManager Class**:

Manager class with bulk-first design + backfill logic + pricing.py integration:

```python
class AssetSourceManager:
    """Manager for asset pricing operations."""
    
    # ============ Provider Assignment Methods ============
    
    @staticmethod
    async def bulk_assign_providers(
        assignments: list[dict],
        session: AsyncSession
    ) -> list[dict]:
        """
        PRIMARY bulk method: Assign providers to multiple assets.
        
        Args:
            assignments: [{asset_id, provider_code, provider_params}, ...]
            session: DB session
            
        Returns:
            [{asset_id, success, message}, ...]
            
        Optimization: 1 read (validation), 1 delete, 1 insert
        """
        pass
    
    @staticmethod
    async def assign_provider(
        asset_id: int,
        provider_code: str,
        provider_params: dict | None,
        session: AsyncSession
    ) -> dict:
        """Single assign (calls bulk with 1 element)."""
        results = await AssetSourceManager.bulk_assign_providers(
            [{"asset_id": asset_id, "provider_code": provider_code, "provider_params": provider_params}],
            session
        )
        return results[0]
    
    @staticmethod
    async def bulk_remove_providers(
        asset_ids: list[int],
        session: AsyncSession
    ) -> list[dict]:
        """
        PRIMARY bulk method: Remove provider assignments.
        
        Args:
            asset_ids: [1, 2, 3, ...]
            session: DB session
            
        Returns:
            [{asset_id, success, message}, ...]
            
        Optimization: 1 DELETE with WHERE IN
        """
        pass
    
    @staticmethod
    async def remove_provider(
        asset_id: int,
        session: AsyncSession
    ) -> dict:
        """Single remove (calls bulk with 1 element)."""
        results = await AssetSourceManager.bulk_remove_providers([asset_id], session)
        return results[0]
    
    @staticmethod
    async def get_asset_provider(
        asset_id: int,
        session: AsyncSession
    ) -> dict | None:
        """Get provider assignment for single asset."""
        pass
    
    # ============ Price Refresh Methods (via providers) ============
    
    @staticmethod
    async def bulk_refresh_prices(
        requests: list[dict],
        session: AsyncSession
    ) -> list[dict]:
        """
        PRIMARY bulk method: Refresh prices via providers.
        
        Args:
            requests: [{asset_id, start_date, end_date?}, ...]
            session: DB session
            
        Returns:
            [{asset_id, fetched_count, success, message, backfill_info?}, ...]
            
        Optimization: Parallel provider calls, batch DB writes via pricing.py
        """
        pass
    
    @staticmethod
    async def refresh_price(
        asset_id: int,
        start: date,
        end: date | None,
        session: AsyncSession
    ) -> dict:
        """Single refresh (calls bulk with 1 element)."""
        results = await AssetSourceManager.bulk_refresh_prices(
            [{"asset_id": asset_id, "start_date": start, "end_date": end}],
            session
        )
        return results[0]
    
    # ============ Manual Price CRUD Methods ============
    
    @staticmethod
    async def bulk_upsert_prices(
        data: list[dict],
        session: AsyncSession
    ) -> dict:
        """
        PRIMARY bulk method: Upsert prices manually.
        
        Args:
            data: [{asset_id, prices: [{date, open?, high?, low?, close, volume?}, ...]}, ...]
            session: DB session
            
        Returns:
            {inserted_count, updated_count, failed_count, results: [...]}
            
        Optimization: Delegates to pricing.bulk_upsert_asset_prices()
        """
        # Delegate to shared pricing layer
        return await pricing.bulk_upsert_asset_prices(data, session)
    
    @staticmethod
    async def upsert_prices(
        asset_id: int,
        prices: list[dict],
        session: AsyncSession
    ) -> dict:
        """Single upsert (calls bulk with 1 element)."""
        result = await AssetSourceManager.bulk_upsert_prices(
            [{"asset_id": asset_id, "prices": prices}],
            session
        )
        return result
    
    @staticmethod
    async def bulk_delete_prices(
        data: list[dict],
        session: AsyncSession
    ) -> dict:
        """
        PRIMARY bulk method: Delete price ranges.
        
        Args:
            data: [{asset_id, date_ranges: [{start, end?}, ...]}, ...]
            session: DB session
            
        Returns:
            {deleted_count, results: [{asset_id, deleted, message}, ...]}
            
        Optimization: Delegates to pricing.bulk_delete_asset_prices()
        """
        # Delegate to shared pricing layer
        return await pricing.bulk_delete_asset_prices(data, session)
    
    @staticmethod
    async def delete_prices(
        asset_id: int,
        date_ranges: list[dict],
        session: AsyncSession
    ) -> dict:
        """Single delete (calls bulk with 1 element)."""
        result = await AssetSourceManager.bulk_delete_prices(
            [{"asset_id": asset_id, "date_ranges": date_ranges}],
            session
        )
        return result
    
    @staticmethod
    async def get_prices(
        asset_id: int,
        start: date,
        end: date | None,
        session: AsyncSession
    ) -> list[dict]:
        """
        Query stored prices for date range with backward-fill logic.
        
        Returns prices with backward_fill_info: {actual_rate_date, days_back} | None
        (identical to FX system).
        
        TODO (Step 03): Fallback to last BUY transaction price if no price_history data.
        """
        # Delegate to shared pricing layer
        return await pricing.get_asset_prices(asset_id, start, end, session)
```

**Helper Functions**:
```python
def get_price_column_precision(column_name: str) -> tuple[int, int]:
    """Get precision for price_history decimal columns."""
    # Same pattern as FX
    pass

def truncate_price_to_db_precision(value: Decimal, column_name: str) -> Decimal:
    """Truncate decimal to DB precision."""
    # Same pattern as FX
    pass

def apply_backward_fill_logic(
    requested_date: date,
    available_prices: list[dict]
) -> dict:
    """
    Apply backward-fill logic to find most recent price.
    
    Returns: {
        price_data: dict,
        backward_fill_info: {actual_rate_date: str, days_back: int} | None
    }
    
    Identical to FX system logic.
    """
    pass
```

**Test**: `backend/test_scripts/test_services/test_asset_source_manager.py`
- [ ] Test bulk_assign_providers (3 assets)
- [ ] Test assign_provider (single, calls bulk)
- [ ] Test bulk_remove_providers (3 assets)
- [ ] Test remove_provider (single, calls bulk)
- [ ] Test bulk_refresh_prices (2 assets, parallel)
- [ ] Test refresh_price (single, calls bulk)
- [ ] Test bulk_upsert_prices (2 assets, multiple prices each)
- [ ] Test upsert_prices (single, calls bulk)
- [ ] Test bulk_delete_prices (2 assets, multiple ranges each)
- [ ] Test delete_prices (single, calls bulk)
- [ ] Test get_prices with backfill (exact match + backfilled)
- [ ] Test DB query optimization (count queries per operation)
- [ ] Test backfill_info structure matches FX pattern

**Checklist**:
- [ ] All bulk methods are PRIMARY implementations
- [ ] All single-item methods call bulk with 1 element
- [ ] DB queries minimized (1-3 max per bulk operation)
- [ ] All DB writes delegate to pricing.py
- [ ] Backfill logic implemented (like FX)
- [ ] Helper functions for decimal precision + backfill
- [ ] Comprehensive tests cover bulk-first design
- [ ] Tests pass

---

#### 1.3 Provider Folder Setup (Was "Plugin Registry & Factory")

**Note**: Registry is now in Phase 1.1 as unified system. This phase is just folder setup.

**Implementa**:
```python
from typing import Type
import logging

from backend.app.services.plugins.base import DataPlugin, PluginError

**Note**: Registry system is now in Phase 1.1 (unified `provider_registry.py`).

This phase focuses on folder setup for auto-discovery:

**Folder**: `backend/app/services/asset_source_providers/`

Create folder structure:
```
backend/app/services/asset_source_providers/
├── __init__.py          # Empty (auto-discovery via registry)
├── yahoo_finance.py     # Will be implemented in Phase 2
├── css_scraper.py       # Will be implemented in Phase 3
└── synthetic_yield.py   # Will be implemented in Phase 4
```

**File**: `backend/app/services/asset_source_providers/__init__.py`
```python
"""
Asset pricing providers.

Providers are auto-discovered by AssetProviderRegistry.
No manual imports needed.
"""
# Empty - auto-discovery handles registration
```

**How it works**:
1. `AssetProviderRegistry.auto_discover()` scans this folder
2. Imports all `.py` files (except `__init__.py`)
3. Providers use `@register_provider(AssetProviderRegistry)` decorator
4. **Docker-friendly**: Drop new provider file → auto-registered on startup

**Test**: Verify auto-discovery in `test_provider_registry.py` (from Phase 1.1)
- [ ] Create dummy provider file in folder
- [ ] Verify auto-discovery finds it
- [ ] Verify decorator registration works
- [ ] Remove dummy provider

**Checklist**:
- [ ] Folder `asset_source_providers/` created
- [ ] `__init__.py` created (empty with docstring)
- [ ] Auto-discovery tested with dummy provider
- [ ] Ready for Phase 2 (yfinance implementation)
- [ ] Test get_plugin raises PluginError if not found
- [ ] Test list_plugins returns all registered
- [ ] Test decorator @register_plugin auto-registers
- [ ] Test clear() for testing isolation

**Checklist**:
- [ ] Registry implementato come singleton
- [ ] Auto-discovery via decorator
- [ ] Error handling con PluginError
- [ ] list_plugins per debugging
- [ ] clear() per test isolation
- [ ] Test registry passa

---

### Phase 2: yfinance Provider (1-2 giorni)

**File**: `backend/app/services/asset_source_providers/yahoo_finance.py`

**Implementa**:
```python
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
import yfinance as yf
import pandas as pd

from backend.app.services.asset_source import (
    AssetSourceProvider,
    ProviderError,
    CurrentValue,
    PricePoint,
    HistoricalData,
)
from backend.app.services.provider_registry import AssetProviderRegistry, register_provider

logger = logging.getLogger(__name__)

@register_provider(AssetProviderRegistry)
class YahooFinanceProvider(AssetSourceProvider):
    """Yahoo Finance data provider."""
    
    # Cache for search results (10 min TTL)
    _search_cache: dict[str, tuple[list[dict], datetime]] = {}
    _CACHE_TTL_SECONDS = 600  # 10 minutes
    
    @property
    def provider_code(self) -> str:
        return "yfinance"
    
    @property
    def provider_name(self) -> str:
        return "Yahoo Finance"
    
    @property
    def test_identifier(self) -> str:
        """Identifier to use in tests (for comparison)."""
        return "AAPL"
    
    @property
    def test_expected_currency(self) -> str:
        """Expected currency for test identifier."""
        return "USD"
    
    async def get_current_value(
        self,
        identifier: str,
        provider_params: dict | None = None
    ) -> CurrentValue:
        """
        Fetch current price from Yahoo Finance.
        
        Uses fast_info.last_price for speed, falls back to history.
        """
        try:
            ticker = yf.Ticker(identifier)
            
            # Try fast_info first (faster)
            try:
                last_price = ticker.fast_info.get('lastPrice')
                if last_price:
                    currency = ticker.fast_info.get('currency', 'USD')
                    return CurrentValue(
                        value=Decimal(str(last_price)),
                        currency=currency,
                        as_of_date=date.today(),
                        source=self.provider_name
                    )
            except Exception as e:
                logger.debug(f"fast_info failed for {identifier}, trying history: {e}")
            
            # Fallback to history (last close)
            hist = ticker.history(period='5d')
            if hist.empty:
                raise ProviderError(
                    f"No data available for {identifier}",
                    error_code="NO_DATA",
                    details={"ticker": identifier}
                )
            
            last_row = hist.iloc[-1]
            last_date = hist.index[-1].date()
            
            # Get currency from info
            currency = 'USD'  # Default
            try:
                info = ticker.info
                currency = info.get('currency', 'USD')
            except Exception:
                logger.warning(f"Could not get currency for {identifier}, using USD")
            
            return CurrentValue(
                value=Decimal(str(last_row['Close'])),
                currency=currency,
                as_of_date=last_date,
                source=self.provider_name
            )
            
        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError(
                f"Failed to fetch current value for {identifier}: {e}",
                error_code="FETCH_ERROR",
                details={"ticker": identifier, "error": str(e)}
            )
    
    async def get_history_value(
        self,
        identifier: str,
        start_date: date,
        end_date: date,
        provider_params: dict | None = None
    ) -> HistoricalData:
        """
        Fetch historical OHLC data from Yahoo Finance.
        """
        try:
            ticker = yf.Ticker(identifier)
            
            # Fetch history
            hist = ticker.history(
                start=start_date.isoformat(),
                end=(end_date + timedelta(days=1)).isoformat()  # end is exclusive
            )
            
            if hist.empty:
                raise ProviderError(
                    f"No historical data for {identifier}",
                    error_code="NO_DATA",
                    details={"ticker": identifier, "start": str(start_date), "end": str(end_date)}
                )
            
            # Get currency
            currency = 'USD'
            try:
                info = ticker.info
                currency = info.get('currency', 'USD')
            except Exception:
                logger.warning(f"Could not get currency for {identifier}, using USD")
            
            # Convert to PricePoint list
            prices = []
            for idx, row in hist.iterrows():
                prices.append(PricePoint(
                    date=idx.date(),
                    open=Decimal(str(row['Open'])) if pd.notna(row['Open']) else None,
                    high=Decimal(str(row['High'])) if pd.notna(row['High']) else None,
                    low=Decimal(str(row['Low'])) if pd.notna(row['Low']) else None,
                    close=Decimal(str(row['Close'])),
                    volume=int(row['Volume']) if pd.notna(row['Volume']) else None,
                    currency=currency
                ))
            
            return HistoricalData(
                prices=prices,
                currency=currency,
                source=self.provider_name
            )
            
        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError(
                f"Failed to fetch history for {identifier}: {e}",
                error_code="FETCH_ERROR",
                details={"ticker": identifier, "error": str(e)}
            )
    
    async def search(self, query: str) -> list[dict]:
        """
        Search Yahoo Finance for matching tickers.
        
        Results cached for 10 minutes.
        """
        # Check cache
        cache_key = query.upper()
        if cache_key in self._search_cache:
            results, timestamp = self._search_cache[cache_key]
            age = (datetime.utcnow() - timestamp).total_seconds()
            if age < self._CACHE_TTL_SECONDS:
                logger.debug(f"Cache hit for '{query}' (age: {age:.0f}s)")
                return results
        
        try:
            # yfinance doesn't have native search, so we try exact match
            # For production, use a proper search API
            ticker = yf.Ticker(query.upper())
            
            try:
                info = ticker.info
                if not info or 'symbol' not in info:
                    # Not found
                    return []
                
                result = [{
                    "identifier": info.get('symbol', query.upper()),
                    "display_name": info.get('longName', info.get('shortName', query.upper())),
                    "currency": info.get('currency', 'USD'),
                    "type": info.get('quoteType', 'Unknown')  # EQUITY, ETF, etc.
                }]
                
                # Cache result
                self._search_cache[cache_key] = (result, datetime.utcnow())
                logger.info(f"Search for '{query}': found {info.get('symbol')}")
                return result
                
            except Exception as e:
                logger.debug(f"Ticker '{query}' not found: {e}")
                # Cache empty result
                self._search_cache[cache_key] = ([], datetime.utcnow())
                return []
            
        except Exception as e:
            raise ProviderError(
                f"Search failed for '{query}': {e}",
                error_code="SEARCH_ERROR",
                details={"query": query, "error": str(e)}
            )
```

**Dependencies**: 
- [ ] Aggiungi `yfinance` a `Pipfile`: `pipenv install yfinance`
- [ ] Aggiungi `pandas` (dependency di yfinance)

**Test**: `backend/test_scripts/test_services/test_asset_providers.py`

**Generic test suite** that iterates over ALL registered asset providers (like FX provider tests):

```python
"""
Generic test suite for all asset pricing providers.

This test file discovers all registered providers via AssetProviderRegistry
and runs the same uniform tests on each one.

Similar to: backend/test_scripts/test_external/test_fx_providers.py
"""

def test_all_providers():
    """
    Iterate over all registered providers and run uniform tests.
    
    For each provider:
    1. Test metadata (provider_code, provider_name)
    2. Test get_current_value (with test_identifier if available)
    3. Test get_history_value (7 days)
    4. Test search (if supported)
    5. Test error handling
    """
    providers = AssetProviderRegistry.list_providers()
    for provider_info in providers:
        code = provider_info["code"]
        provider = AssetProviderRegistry.get_provider(code)
        
        # Run uniform tests
        test_provider_metadata(provider)
        test_provider_current_value(provider)
        test_provider_history(provider)
        test_provider_search(provider)
        test_provider_errors(provider)
```

**Note**: No separate `test_yahoo_finance_provider.py` or `test_synthetic_yield_provider.py`.  
All providers tested by same generic suite.

**Checklist**:
- [ ] @register_provider(AssetProviderRegistry) decorator
- [ ] Provider-specific logic (yfinance: fast_info fallback, css: float parsing, synthetic: ACT/365)
- [ ] Error handling robusto
- [ ] OHLC conversion a PricePoint (where applicable)
- [ ] Search implementation (where supported)
- [ ] Test suite discovers provider automatically
- [ ] All uniform tests pass
- [ ] Auto-discovery works (provider found by registry)

---

### Phase 3: CSS Scraper Provider (1-2 giorni)

**File**: `backend/app/services/asset_source_providers/css_scraper.py`

**Implementa**:
```python
import logging
import re
from datetime import date
from decimal import Decimal, InvalidOperation
import httpx
from bs4 import BeautifulSoup

from backend.app.services.asset_source import (
    AssetSourceProvider,
    ProviderError,
    CurrentValue,
    PricePoint,
    HistoricalData,
)
from backend.app.services.provider_registry import AssetProviderRegistry, register_provider

logger = logging.getLogger(__name__)

@register_provider(AssetProviderRegistry)
class CSSScraperProvider(AssetSourceProvider):
    """Web scraping provider with CSS selectors."""
    
    @property
    def provider_code(self) -> str:
        return "cssscraper"
    
    @property
    def plugin_name(self) -> str:
        return "CSS Web Scraper"
    
    @property
    def test_identifier(self) -> str:
        """Not applicable for CSS scraper (URL-based)."""
        return "https://example.com/price"
    
    @property
    def test_expected_currency(self) -> str:
        """Configured in plugin_params."""
        return "EUR"
    
    def validate_params(self, plugin_params: dict | None) -> dict:
        """
        Validate required parameters.
        
        Required for get_current_value:
        - current_url: str
        - current_css_selector: str
        - currency: str
        
        Optional for get_history_value:
        - history_url: str
        - history_css_selector: str
        """
        if not plugin_params:
            raise PluginError(
                "CSS scraper requires plugin_params",
                error_code="MISSING_PARAMS"
            )
        
        # Check required for current
        required = ['current_url', 'current_css_selector', 'currency']
        missing = [k for k in required if k not in plugin_params]
        if missing:
            raise PluginError(
                f"Missing required params: {', '.join(missing)}",
                error_code="MISSING_PARAMS",
                details={"missing": missing}
            )
        
        return plugin_params
    
    def parse_float(self, text: str) -> Decimal:
        """
        Robust float parsing.
        
        Handles:
        - "1,234.56" (US format)
        - "1.234,56" (EU format)
        - "1 234,56" (space separator)
        - "€1,234.56" (with currency symbol)
        """
        # Remove whitespace and currency symbols
        text = text.strip()
        text = re.sub(r'[€$£¥\s]', '', text)
        
        # Count commas and dots
        comma_count = text.count(',')
        dot_count = text.count('.')
        
        # Determine format
        if comma_count == 0 and dot_count <= 1:
            # Simple: "1234" or "1234.56"
            pass
        elif comma_count == 1 and dot_count == 0:
            # EU format: "1234,56"
            text = text.replace(',', '.')
        elif comma_count > 1 and dot_count == 1:
            # US format with separators: "1,234,567.89"
            text = text.replace(',', '')
        elif dot_count > 1 and comma_count == 1:
            # EU format with separators: "1.234.567,89"
            text = text.replace('.', '').replace(',', '.')
        elif comma_count == 1 and dot_count == 1:
            # Ambiguous: check last separator
            last_comma = text.rfind(',')
            last_dot = text.rfind('.')
            if last_dot > last_comma:
                # US format: "1,234.56"
                text = text.replace(',', '')
            else:
                # EU format: "1.234,56"
                text = text.replace('.', '').replace(',', '.')
        
        try:
            return Decimal(text)
        except InvalidOperation:
            raise PluginError(
                f"Could not parse '{text}' as number",
                error_code="PARSE_ERROR",
                details={"text": text}
            )
    
    async def get_current_value(
        self,
        identifier: str,
        plugin_params: dict | None = None
    ) -> CurrentValue:
        """
        Scrape current value from web page.
        
        identifier: Not used (URL is in plugin_params)
        plugin_params: Must contain current_url, current_css_selector, currency
        """
        params = self.validate_params(plugin_params)
        
        url = params['current_url']
        selector = params['current_css_selector']
        currency = params['currency']
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url)
                response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            element = soup.select_one(selector)
            
            if not element:
                raise PluginError(
                    f"CSS selector '{selector}' not found",
                    error_code="SELECTOR_NOT_FOUND",
                    details={"url": url, "selector": selector}
                )
            
            text = element.get_text(strip=True)
            value = self.parse_float(text)
            
            return CurrentValue(
                value=value,
                currency=currency,
                as_of_date=date.today(),
                source=self.plugin_name
            )
            
        except PluginError:
            raise
        except httpx.HTTPError as e:
            raise PluginError(
                f"HTTP error fetching {url}: {e}",
                error_code="HTTP_ERROR",
                details={"url": url, "error": str(e)}
            )
        except Exception as e:
            raise PluginError(
                f"Error scraping {url}: {e}",
                error_code="SCRAPE_ERROR",
                details={"url": url, "error": str(e)}
            )
    
    async def get_history_value(
        self,
        identifier: str,
        start_date: date,
        end_date: date,
        plugin_params: dict | None = None
    ) -> HistoricalData:
        """
        Scrape historical data (optional, may return empty).
        
        If history_url and history_css_selector provided, attempts scraping.
        Otherwise returns empty list.
        """
        params = self.validate_params(plugin_params)
        currency = params['currency']
        
        # History is optional
        if 'history_url' not in params or 'history_css_selector' not in params:
            logger.info("No history config for CSS scraper, returning empty")
            return HistoricalData(
                prices=[],
                currency=currency,
                source=self.plugin_name
            )
        
        # TODO: Implement history scraping if needed
            # This would require parsing date + value pairs
            # For now, return empty
            return HistoricalData(
                prices=[],
                currency=currency,
                source=self.plugin_name
            )
    
    async def search(self, query: str) -> list[dict]:
        """
        Search not applicable for CSS scraper.
        
        CSS scraper requires full URL configuration, not searchable.
        """
        raise PluginError(
            "Search not supported for CSS scraper plugin",
            error_code="NOT_SUPPORTED",
            details={"message": "CSS scraper requires manual URL configuration"}
        )
```

**Dependencies**:
- [ ] Aggiungi `beautifulsoup4` a `Pipfile`: `pipenv install beautifulsoup4`
- [ ] `httpx` già presente (usato per FX providers)

**Test**: `backend/test_scripts/test_services/test_cssscraper_plugin.py`
- [ ] Test parse_float con vari formati (US, EU, con simboli)
- [ ] Test get_current_value con HTML mock (httpx mock)
- [ ] Test validate_params richiede current_url, selector, currency
- [ ] Test selector not found raises PluginError
- [ ] Test HTTP error raises PluginError
- [ ] Test get_history_value ritorna empty se no history config

**Checklist**:
- [ ] @register_plugin decorator
- [ ] validate_params checks required fields
- [ ] parse_float handles multiple formats
- [ ] httpx async client con timeout
- [ ] BeautifulSoup4 parsing
- [ ] CSS selector error handling
- [ ] History returns empty (optional feature)
- [ ] Test con HTML mock passa

---

### Phase 4: Complete Synthetic Yield Implementation (3-4 giorni) ⚠️ MOST COMPLEX

**Status**: Deferred from Phase 0.2.2  
**Current State**: Only ACT/365 day count helper implemented  
**Remaining Work**: Rate schedules, accrued interest calculation, get_prices() integration

**Note**: Synthetic yield is NOT a separate provider. It's integrated into `asset_source.py` as runtime calculation logic for SCHEDULED_YIELD assets.

**What's Already Done (Phase 0.2.2)**:
- ✅ `calculate_days_between_act365(start, end)` → ACT/365 day fraction

**What Needs Implementation (Phase 4)**:
- [ ] `find_active_rate(schedule, target_date, maturity, late_interest)` → rate lookup from schedule
- [ ] `calculate_accrued_interest(principal, schedule, start, end, maturity, late_interest)` → SIMPLE interest
- [ ] `calculate_synthetic_value(asset, target_date, session)` → full valuation (face_value + accrued interest)
- [ ] Integration in `get_prices()` → auto-detect SCHEDULED_YIELD assets and calculate on-demand
- [ ] Transaction-aware logic → check if loan was repaid/sold

**Implementation Location**: `backend/app/services/asset_source.py` (NOT a separate plugin)

**Code to Add**:
```python
import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Literal

from backend.app.services.plugins.base import (
    DataPlugin,
    PluginError,
    CurrentValue,
    PricePoint,
    HistoricalData,
)
from backend.app.services.plugins.registry import register_plugin
from backend.app.db import Asset

logger = logging.getLogger(__name__)

# Type aliases
DayCountConvention = Literal["ACT/365", "ACT/360", "30/360"]
InterestType = Literal["SIMPLE", "COMPOUND"]
Frequency = Literal["DAILY", "MONTHLY", "QUARTERLY", "ANNUAL"]

@register_plugin
class SyntheticYieldPlugin(DataPlugin):
    """
    Synthetic valuation plugin for scheduled-yield assets (loans, bonds).
    
    Calculates: price = face_value + accrued_interest_per_unit
    
    Uses ACT/365 day-count convention (actual days / 365).
    
    Note: This is an ESTIMATE. True profits = sell_proceeds - buy_cost.
    Accrued interest calculation is for portfolio valuation only.
    
    Supports:
    - Day-count: ACT/365 only (simplicity)
    - Interest type: SIMPLE only
    - Maturity + grace period + late interest
    """
    
    @property
    def plugin_key(self) -> str:
        return "synthetic_yield"
    
    @property
    def plugin_name(self) -> str:
        return "Synthetic Yield Calculator"
    
    @property
    def test_identifier(self) -> str:
        """Asset ID for testing."""
        return "loan-test-001"
    
    @property
    def test_expected_currency(self) -> str:
        """Expected currency from asset."""
        return "EUR"
    
    def validate_params(self, plugin_params: dict | None) -> dict:
        """
        Validate optional parameters.
        
        Note: ACT/365 is always used (hardcoded for simplicity).
        """
        params = plugin_params or {}
        # No validation needed - ACT/365 is hardcoded
        return params
    
    def calculate_days_between(
        self,
        start: date,
        end: date
    ) -> Decimal:
        """
        Calculate day count between two dates using ACT/365.
        
        ACT/365: Actual days / 365
        
        Note: This is an estimate. True profits = sell - buy.
        """
        days = (end - start).days
        return Decimal(days) / Decimal(365)
    
    def find_active_rate(
        self,
        schedule: list[dict],
        target_date: date,
        maturity_date: date,
        late_interest: dict | None
    ) -> Decimal:
        """
        Find active interest rate for a specific date.
        
        Schedule format:
        [
          {"start_date": "2024-01-01", "end_date": "2024-06-30", "rate": "0.05"},
          {"start_date": "2024-07-01", "end_date": null, "rate": "0.06"}
        ]
        
        After maturity + grace period, use late_interest.rate if no repayment.
        """
        # Check if we're past maturity + grace
        if late_interest and target_date > maturity_date:
            grace_days = late_interest.get('grace_period_days', 0)
            grace_end = maturity_date + timedelta(days=grace_days)
            
            if target_date > grace_end:
                # Check if loan was repaid (TODO: check transactions)
                # For now, assume not repaid → apply late rate
                late_rate = late_interest.get('rate', '0')
                return Decimal(late_rate)
        
        # Find matching schedule segment
        for segment in schedule:
            start = date.fromisoformat(segment['start_date'])
            end_str = segment.get('end_date')
            end = date.fromisoformat(end_str) if end_str else maturity_date
            
            if start <= target_date <= end:
                return Decimal(segment['rate'])
        
        # No active rate found → 0
        logger.warning(f"No active rate for {target_date}, returning 0")
        return Decimal('0')
    
    def calculate_accrued_interest(
        self,
        principal: Decimal,
        schedule: list[dict],
        start_date: date,
        end_date: date,
        maturity_date: date,
        late_interest: dict | None
    ) -> Decimal:
        """
        Calculate accrued interest from start_date to end_date.
        
        Uses SIMPLE interest: interest = principal * sum(rate * time_fraction)
        
        Note: This is an ESTIMATE for portfolio valuation.
        True profits = sell_proceeds - buy_cost.
        """
        # Sum daily accruals
        total_interest = Decimal('0')
        current = start_date
        
        while current <= end_date:
            next_day = current + timedelta(days=1)
            
            # Find active rate
            rate = self.find_active_rate(schedule, current, maturity_date, late_interest)
            
            # Calculate days fraction (ACT/365)
            days_fraction = self.calculate_days_between(current, next_day)
            
            # Accrue
            daily_interest = principal * rate * days_fraction
            total_interest += daily_interest
            
            current = next_day
        
        return total_interest
    
    async def get_current_value(
        self,
        identifier: str,
        plugin_params: dict | None = None
    ) -> CurrentValue:
        """
        Calculate current synthetic value.
        
        identifier: asset_id (will fetch asset from DB)
        plugin_params: Optional override for day_count, interest_type, frequency
        """
        # TODO: Fetch asset from DB
        # For now, expect asset to be passed in plugin_params
        raise PluginError(
            "get_current_value requires asset data (to be implemented)",
            error_code="NOT_IMPLEMENTED"
        )
    
    async def get_history_value(
        self,
        identifier: str,
        start_date: date,
        end_date: date,
        plugin_params: dict | None = None
    ) -> HistoricalData:
        """
        Generate daily synthetic price series.
        
        identifier: asset_id
        plugin_params: Should contain asset data or will be fetched
        """
        # TODO: Fetch asset from DB if not in params
        raise PluginError(
            "get_history_value requires asset data (to be implemented)",
            error_code="NOT_IMPLEMENTED"
        )
    
    async def search(self, query: str) -> list[dict]:
        """
        Search not applicable for synthetic yield.
        
        Synthetic yield works on existing assets in DB, not searchable externally.
        """
        raise PluginError(
            "Search not supported for synthetic yield plugin",
            error_code="NOT_SUPPORTED",
            details={"message": "Synthetic yield requires existing asset with schedule data"}
        )
```

**Note**: Questo plugin richiede accesso al database per fetch asset data. Potrebbe essere necessario passare `async_session_maker` o fetch asset prima di chiamare plugin.

**Test**: `backend/test_scripts/test_services/test_synthetic_yield_plugin.py`
- [ ] Test calculate_days_between per ogni convention
- [ ] Test find_active_rate con schedule semplice
- [ ] Test find_active_rate dopo maturity (late interest)
- [ ] Test calculate_accrued_interest SIMPLE
- [ ] Test validate_params
- [ ] Test full series generation con schedule complesso
- [ ] Test edge case: maturity + grace + late rate

**Checklist**:
- [ ] @register_plugin decorator
- [ ] Day-count conventions: ACT/365, ACT/360, 30/360
- [ ] Interest rate schedule parsing
- [ ] Maturity + grace period handling
- [ ] Late interest rate application
- [ ] SIMPLE interest calculation
- [ ] COMPOUND interest (TODO or implement)
- [ ] Test con schedule complesso passa

---

### Phase 5: Service Layer (1-2 giorni)

#### 5.1 Plugin Manager Service

**File**: `backend/app/services/plugins/manager.py`

**Implementa**:
```python
import logging
import json
from datetime import datetime
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db import Asset, AssetPluginAssignment
from backend.app.services.plugins import PluginRegistry, PluginError

logger = logging.getLogger(__name__)

async def get_asset_plugin(
    asset_id: int,
    session: AsyncSession
) -> AssetPluginAssignment | None:
    """Fetch plugin assignment for asset."""
    stmt = select(AssetPluginAssignment).where(
        AssetPluginAssignment.asset_id == asset_id
    )
    result = await session.exec(stmt)
    return result.first()

async def assign_plugin(
    asset_id: int,
    plugin_key: str,
    plugin_params: dict | None,
    session: AsyncSession
) -> AssetPluginAssignment:
    """
    Assign plugin to asset (UPSERT).
    
    Validates plugin exists before assigning.
    """
    # Verify asset exists
    asset = await session.get(Asset, asset_id)
    if not asset:
        raise ValueError(f"Asset {asset_id} not found")
    
    # Verify plugin exists
    try:
        PluginRegistry.get_plugin(plugin_key)
    except PluginError:
        raise ValueError(f"Plugin '{plugin_key}' not found")
    
    # Check existing assignment
    existing = await get_asset_plugin(asset_id, session)
    
    if existing:
        # Update
        existing.plugin_key = plugin_key
        existing.plugin_params = json.dumps(plugin_params) if plugin_params else None
        existing.updated_at = datetime.utcnow()
        assignment = existing
    else:
        # Insert
        assignment = AssetPluginAssignment(
            asset_id=asset_id,
            plugin_key=plugin_key,
            plugin_params=json.dumps(plugin_params) if plugin_params else None
        )
        session.add(assignment)
    
    await session.commit()
    await session.refresh(assignment)
    return assignment

async def remove_plugin(
    asset_id: int,
    session: AsyncSession
) -> bool:
    """
    Remove plugin assignment from asset.
    
    Returns:
        True if removed, False if not found
    """
    assignment = await get_asset_plugin(asset_id, session)
    if not assignment:
        return False
    
    await session.delete(assignment)
    await session.commit()
    return True

async def bulk_assign_plugins(
    assignments: list[dict],
    session: AsyncSession
) -> dict:
    """
    Bulk assign plugins.
    
    Args:
        assignments: [{"asset_id": 1, "plugin_key": "yfinance", "plugin_params": {...}}, ...]
    
    Returns:
        {"success": [...], "errors": [...]}
    """
    results = {"success": [], "errors": []}
    
    for item in assignments:
        try:
            assignment = await assign_plugin(
                asset_id=item['asset_id'],
                plugin_key=item['plugin_key'],
                plugin_params=item.get('plugin_params'),
                session=session
            )
            results['success'].append({
                "asset_id": assignment.asset_id,
                "plugin_key": assignment.plugin_key
            })
        except Exception as e:
            results['errors'].append({
                "asset_id": item.get('asset_id'),
                "error": str(e)
            })
    
    return results
```

**Test**: `backend/test_scripts/test_services/test_plugin_manager.py`
- [ ] Test get_asset_plugin ritorna None se non assegnato
- [ ] Test assign_plugin crea nuovo assignment
- [ ] Test assign_plugin aggiorna esistente (UPSERT)
- [ ] Test assign_plugin valida plugin_key
- [ ] Test remove_plugin rimuove assignment
- [ ] Test remove_plugin ritorna False se non trovato
- [ ] Test bulk_assign_plugins con successi ed errori

---

#### 5.2 Pricing Service

**File**: `backend/app/services/pricing.py`

**Implementa**:
```python
import logging
import json
from datetime import date, datetime
from decimal import Decimal
from sqlmodel import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db import Asset, PriceHistory
from backend.app.services.plugins import PluginRegistry, PluginError
from backend.app.services.plugins.manager import get_asset_plugin

logger = logging.getLogger(__name__)

async def refresh_current_price(
    asset_id: int,
    session: AsyncSession
) -> dict:
    """
    Refresh current price using assigned plugin.
    
    Returns:
        Dict with updated price info
        
    Raises:
        ValueError: If asset not found or no plugin assigned
        PluginError: If plugin fails
    """
    # Fetch asset
    asset = await session.get(Asset, asset_id)
    if not asset:
        raise ValueError(f"Asset {asset_id} not found")
    
    # Get plugin assignment
    assignment = await get_asset_plugin(asset_id, session)
    if not assignment:
        raise ValueError(f"No plugin assigned to asset {asset_id}")
    
    # Get plugin instance
    plugin = PluginRegistry.get_plugin(assignment.plugin_key)
    
    # Parse params
    plugin_params = json.loads(assignment.plugin_params) if assignment.plugin_params else None
    
    # Fetch current value
    current_value = await plugin.get_current_value(
        identifier=asset.identifier,
        plugin_params=plugin_params
    )
    
    # UPSERT price_history
    stmt = select(PriceHistory).where(
        PriceHistory.asset_id == asset_id,
        PriceHistory.date == current_value['as_of_date']
    )
    result = await session.exec(stmt)
    price_record = result.first()
    
    if price_record:
        price_record.close = current_value['value']
        price_record.updated_at = datetime.utcnow()
    else:
        price_record = PriceHistory(
            asset_id=asset_id,
            date=current_value['as_of_date'],
            close=current_value['value']
        )
        session.add(price_record)
    
    await session.commit()
    await session.refresh(price_record)
    
    return {
        "asset_id": asset_id,
        "date": current_value['as_of_date'],
        "value": current_value['value'],
        "currency": current_value['currency'],
        "source": current_value['source']
    }

async def refresh_history(
    asset_id: int,
    start_date: date,
    end_date: date,
    session: AsyncSession
) -> dict:
    """
    Refresh historical prices using assigned plugin.
    
    Returns:
        Dict with statistics (fetched, inserted, updated)
    """
    asset = await session.get(Asset, asset_id)
    if not asset:
        raise ValueError(f"Asset {asset_id} not found")
    
    assignment = await get_asset_plugin(asset_id, session)
    if not assignment:
        raise ValueError(f"No plugin assigned to asset {asset_id}")
    
    plugin = PluginRegistry.get_plugin(assignment.plugin_key)
    plugin_params = json.loads(assignment.plugin_params) if assignment.plugin_params else None
    
    # Fetch history
    history = await plugin.get_history_value(
        identifier=asset.identifier,
        start_date=start_date,
        end_date=end_date,
        plugin_params=plugin_params
    )
    
    # UPSERT each price
    inserted, updated = 0, 0
    for price_point in history['prices']:
        stmt = select(PriceHistory).where(
            PriceHistory.asset_id == asset_id,
            PriceHistory.date == price_point['date']
        )
        result = await session.exec(stmt)
        existing = result.first()
        
        if existing:
            # Update
            existing.open = price_point.get('open')
            existing.high = price_point.get('high')
            existing.low = price_point.get('low')
            existing.close = price_point['close']
            existing.updated_at = datetime.utcnow()
            updated += 1
        else:
            # Insert
            new_price = PriceHistory(
                asset_id=asset_id,
                date=price_point['date'],
                open=price_point.get('open'),
                high=price_point.get('high'),
                low=price_point.get('low'),
                close=price_point['close']
            )
            session.add(new_price)
            inserted += 1
    
    await session.commit()
    
    return {
        "asset_id": asset_id,
        "fetched": len(history['prices']),
        "inserted": inserted,
        "updated": updated,
        "source": history['source']
    }

async def upsert_prices(
    asset_id: int,
    prices: list[dict],
    session: AsyncSession
) -> dict:
    """
    Manual price insert/update (no plugin).
    
    Args:
        prices: [{"date": "2025-01-01", "close": 100.50, "open": 99.0, ...}, ...]
    
    Returns:
        {"inserted": 5, "updated": 3}
    """
    asset = await session.get(Asset, asset_id)
    if not asset:
        raise ValueError(f"Asset {asset_id} not found")
    
    inserted, updated = 0, 0
    
    for price_data in prices:
        price_date = date.fromisoformat(price_data['date'])
        
        stmt = select(PriceHistory).where(
            PriceHistory.asset_id == asset_id,
            PriceHistory.date == price_date
        )
        result = await session.exec(stmt)
        existing = result.first()
        
        if existing:
            # Update
            for field in ['open', 'high', 'low', 'close']:
                if field in price_data:
                    setattr(existing, field, Decimal(str(price_data[field])))
            existing.updated_at = datetime.utcnow()
            updated += 1
        else:
            # Insert
            new_price = PriceHistory(
                asset_id=asset_id,
                date=price_date,
                open=Decimal(str(price_data['open'])) if 'open' in price_data else None,
                high=Decimal(str(price_data['high'])) if 'high' in price_data else None,
                low=Decimal(str(price_data['low'])) if 'low' in price_data else None,
                close=Decimal(str(price_data['close']))
            )
            session.add(new_price)
            inserted += 1
    
    await session.commit()
    
    return {"inserted": inserted, "updated": updated}

async def delete_prices(
    asset_id: int,
    start_date: date,
    end_date: date,
    session: AsyncSession
) -> int:
    """
    Delete price range.
    
    Returns:
        Number of records deleted
    """
    stmt = select(PriceHistory).where(
        and_(
            PriceHistory.asset_id == asset_id,
            PriceHistory.date >= start_date,
            PriceHistory.date <= end_date
        )
    )
    result = await session.exec(stmt)
    records = result.all()
    
    for record in records:
        await session.delete(record)
    
    await session.commit()
    return len(records)
```

**Test**: `backend/test_scripts/test_services/test_pricing_service.py`
- [ ] Test refresh_current_price con plugin mock
- [ ] Test refresh_current_price raises se no plugin assigned
- [ ] Test refresh_history inserts nuovi record
- [ ] Test refresh_history updates record esistenti
- [ ] Test upsert_prices manual insert
- [ ] Test upsert_prices manual update
- [ ] Test delete_prices range completo
- [ ] Test delete_prices single date

**Checklist**:
- [ ] Plugin manager completo e testato
- [ ] Pricing service completo e testato
- [ ] Error handling robusto
- [ ] Tutti i test passano

---

### Phase 6: API Endpoints (1-2 giorni)

#### 6.1 Plugin Discovery Endpoint

**File**: `backend/app/api/v1/asset_providers.py` (nuovo)

**Implementa**:
```python
from fastapi import APIRouter

from backend.app.services.plugins import PluginRegistry

router = APIRouter(prefix="/plugins", tags=["plugins"])

@router.get("")
async def list_plugins():
    """
    List available plugins.
    
    Returns:
        {"plugins": [{"key": "yfinance", "name": "Yahoo Finance"}, ...]}
    """
    plugins = PluginRegistry.list_plugins()
    return {"plugins": plugins, "count": len(plugins)}
```

**Test**: `backend/test_scripts/test_api/test_plugins_api.py`
- [ ] Test GET /plugins ritorna lista plugin
- [ ] Test verifica presenza yfinance, cssscraper, synthetic_yield

---

#### 6.2 Plugin Assignment Endpoints

**File**: `backend/app/api/v1/assets.py` (aggiorna o crea)

**Implementa**:
```python
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date

from backend.app.db import get_async_session
from backend.app.services import pricing
from backend.app.services.plugins import manager as plugin_manager

router = APIRouter(prefix="/assets", tags=["assets"])

# ========== Plugin Assignment CRUD ==========

class PluginAssignmentRequest(BaseModel):
    plugin_key: str
    plugin_params: dict | None = None

class BulkPluginAssignmentRequest(BaseModel):
    assignments: list[dict]  # [{"asset_id": 1, "plugin_key": "yfinance", ...}, ...]

@router.get("/{asset_id}/plugin")
async def get_asset_plugin(
    asset_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """Get plugin assignment for asset."""
    assignment = await plugin_manager.get_asset_plugin(asset_id, session)
    if not assignment:
        raise HTTPException(status_code=404, detail="No plugin assigned")
    
    return {
        "asset_id": assignment.asset_id,
        "plugin_key": assignment.plugin_key,
        "plugin_params": json.loads(assignment.plugin_params) if assignment.plugin_params else None,
        "created_at": assignment.created_at,
        "updated_at": assignment.updated_at
    }

@router.post("/{asset_id}/plugin")
async def assign_asset_plugin(
    asset_id: int,
    request: PluginAssignmentRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """Assign or update plugin for asset."""
    try:
        assignment = await plugin_manager.assign_plugin(
            asset_id=asset_id,
            plugin_key=request.plugin_key,
            plugin_params=request.plugin_params,
            session=session
        )
        return {
            "asset_id": assignment.asset_id,
            "plugin_key": assignment.plugin_key,
            "message": "Plugin assigned successfully"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{asset_id}/plugin")
async def remove_asset_plugin(
    asset_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """Remove plugin assignment from asset."""
    removed = await plugin_manager.remove_plugin(asset_id, session)
    if not removed:
        raise HTTPException(status_code=404, detail="No plugin assigned")
    
    return {"message": "Plugin removed successfully"}

@router.post("/plugin/bulk")
async def bulk_assign_plugins(
    request: BulkPluginAssignmentRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """Bulk assign plugins to multiple assets."""
    results = await plugin_manager.bulk_assign_plugins(request.assignments, session)
    return results

@router.delete("/plugin/bulk")
async def bulk_remove_plugins(
    asset_ids: list[int],
    session: AsyncSession = Depends(get_async_session)
):
    """Bulk remove plugin assignments."""
    results = {"removed": [], "not_found": []}
    
    for asset_id in asset_ids:
        removed = await plugin_manager.remove_plugin(asset_id, session)
        if removed:
            results['removed'].append(asset_id)
        else:
            results['not_found'].append(asset_id)
    
    return results

# ========== Price Refresh (via Plugin) ==========

@router.post("/{asset_id}/refresh-current")
async def refresh_current_price(
    asset_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Refresh current price using assigned plugin.
    
    Requires plugin assignment.
    """
    try:
        result = await pricing.refresh_current_price(asset_id, session)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to refresh: {e}")

@router.post("/{asset_id}/refresh-history")
async def refresh_historical_prices(
    asset_id: int,
    start: date,
    end: date,
    session: AsyncSession = Depends(get_async_session)
):
    """Refresh historical prices using assigned plugin."""
    try:
        result = await pricing.refresh_history(asset_id, start, end, session)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to refresh: {e}")

# ========== Manual Price CRUD ==========

class PriceData(BaseModel):
    date: str  # ISO date
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float

class BulkPricesRequest(BaseModel):
    prices: list[PriceData]

@router.get("/{asset_id}/prices")
async def get_asset_prices(
    asset_id: int,
    start: date,
    end: date,
    session: AsyncSession = Depends(get_async_session)
):
    """Query existing prices for asset."""
    from sqlmodel import select, and_
    from backend.app.db import PriceHistory
    
    stmt = select(PriceHistory).where(
        and_(
            PriceHistory.asset_id == asset_id,
            PriceHistory.date >= start,
            PriceHistory.date <= end
        )
    ).order_by(PriceHistory.date)
    
    result = await session.exec(stmt)
    prices = result.all()
    
    return {
        "asset_id": asset_id,
        "prices": [
            {
                "date": p.date,
                "open": p.open,
                "high": p.high,
                "low": p.low,
                "close": p.close
            }
            for p in prices
        ],
        "count": len(prices)
    }

@router.post("/{asset_id}/prices/bulk")
async def upsert_prices(
    asset_id: int,
    request: BulkPricesRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """Manually insert/update prices (no plugin)."""
    try:
        prices_data = [p.dict() for p in request.prices]
        result = await pricing.upsert_prices(asset_id, prices_data, session)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/{asset_id}/prices/bulk")
async def delete_prices(
    asset_id: int,
    start: date,
    end: date,
    session: AsyncSession = Depends(get_async_session)
):
    """Delete price range."""
    deleted_count = await pricing.delete_prices(asset_id, start, end, session)
    return {"deleted": deleted_count}
```

**Test**: `backend/test_scripts/test_api/test_assets_api.py`

**Plugin Assignment CRUD**:
- [ ] Test GET /assets/{id}/plugin
- [ ] Test GET 404 se no plugin assigned
- [ ] Test POST /assets/{id}/plugin (assign)
- [ ] Test POST /assets/{id}/plugin (update existing)
- [ ] Test POST 400 se plugin_key invalid
- [ ] Test DELETE /assets/{id}/plugin
- [ ] Test DELETE 404 se no assignment
- [ ] Test POST /assets/plugin/bulk (success + errors)
- [ ] Test DELETE /assets/plugin/bulk

**Price Refresh**:
- [ ] Test POST /assets/{id}/refresh-current
- [ ] Test 404 se no plugin assigned
- [ ] Test POST /assets/{id}/refresh-history

**Manual Price CRUD**:
- [ ] Test GET /assets/{id}/prices ritorna lista
- [ ] Test GET vuoto se no prices
- [ ] Test POST /assets/{id}/prices/bulk (insert)
- [ ] Test POST /assets/{id}/prices/bulk (update)
- [ ] Test DELETE /assets/{id}/prices/bulk

**Plugin Discovery**:
- [ ] Test GET /plugins ritorna 3 plugin

**Checklist**:
- [ ] Tutti gli endpoint implementati
- [ ] Error handling completo (404, 400, 500)
- [ ] Pydantic models per validation
- [ ] Tutti i test passano (20+ test)

---

### Phase 7: Documentation (1 giorno)

**File**: `docs/plugins/`

**Crea**:
1. `docs/plugins/overview.md` - Plugin system overview
2. `docs/plugins/yfinance.md` - yfinance plugin guide
3. `docs/plugins/cssscraper.md` - CSS scraper configuration
4. `docs/plugins/synthetic-yield.md` - Synthetic yield calculation

**Aggiorna**:
- `docs/api-reference.md` - Add assets endpoints
- `docs/testing-guide.md` - Add plugin tests

**Checklist**:
- [ ] Overview doc completo
- [ ] Per ogni plugin: usage, config, examples
- [ ] API reference aggiornato
- [ ] Testing guide aggiornato

---

## ✅ Final Checklist

### Database
- [ ] Migration asset_plugin_assignments creata e applicata
- [ ] Model AssetPluginAssignment implementato
- [ ] UNIQUE constraint su asset_id verificato
- [ ] FK CASCADE verso assets verificato
- [ ] Schema validation test aggiornato e passa

### Core System
- [ ] Abstract DataPlugin class
- [ ] Plugin registry con factory
- [ ] TypedDicts per type safety
- [ ] PluginError exception
- [ ] @register_plugin decorator

### Plugins
- [ ] yfinance plugin completo e testato
- [ ] cssscraper plugin completo e testato
- [ ] synthetic_yield plugin completo e testato
- [ ] Tutti i test plugin passano (30+ test)

### Services
- [ ] Plugin manager service (get, assign, remove, bulk)
- [ ] Pricing service (refresh_current, refresh_history)
- [ ] Manual price CRUD (upsert, delete)
- [ ] Tutti i test service passano (15+ test)

### API Endpoints
- [ ] GET /plugins (plugin discovery)
- [ ] Plugin assignment CRUD (GET, POST, DELETE, bulk)
- [ ] Price refresh endpoints (current, history)
- [ ] Manual price CRUD (GET, POST, DELETE bulk)
- [ ] Tutti i test API passano (25+ test)

### Documentation
- [ ] Day-count conventions spiegati
- [ ] Plugin system overview
- [ ] Per-plugin guides (yfinance, cssscraper, synthetic_yield)
- [ ] API reference update (nuovi endpoint)
- [ ] Testing guide update
- [ ] Database schema docs update

### Dependencies
- [ ] yfinance installato
- [ ] beautifulsoup4 installato
- [ ] httpx già presente ✅
- [ ] pandas (dependency yfinance)

---

## 🎯 Success Criteria

### Must Have ✅
1. ✅ Database: asset_plugin_assignments table con UNIQUE constraint
2. ✅ Plugin Discovery: GET /plugins ritorna 3 plugin
3. ✅ Plugin Assignment: GET/POST/DELETE per asset funzionano
4. ✅ Plugin Assignment: Bulk assign/remove funzionano
5. ✅ yfinance: fetches AAPL current price e history (OHLC)
6. ✅ cssscraper: parses HTML con CSS selector, handles EU/US formats
7. ✅ synthetic_yield: calcola SIMPLE interest correttamente
8. ✅ synthetic_yield: supports ACT/365, ACT/360, 30/360
9. ✅ synthetic_yield: applica late rate dopo maturity+grace
10. ✅ Price Refresh: refresh_current e refresh_history funzionano
11. ✅ Manual Price CRUD: GET/POST/DELETE prezzi funzionano
12. ✅ All 70+ tests pass (plugin + service + API)
13. ✅ API endpoints ritornano dati corretti
14. ✅ Documentation completa (day-count conventions spiegati)

### Should Have 🟡
1. 🟡 synthetic_yield supports COMPOUND interest
2. 🟡 cssscraper supports history scraping
3. 🟡 Plugin performance benchmarks
4. 🟡 Async batch price refresh (multiple assets)

### Nice to Have 🔵
1. 🔵 Additional plugins (Bloomberg, Alpha Vantage, justEtf, borsa italiana, etc...)
2. 🔵 Plugin caching layer
3. 🔵 Async batch updates
4. 🔵 Plugin health monitoring

---

## 📊 Estimated Timeline

| Phase | Description | Days | Complexity |
|-------|-------------|------|------------|
| 0 | Database migration (asset_plugin_assignments) | 0.5 | Low |
| 1 | Plugin system base | 2-3 | Medium |
| 2 | yfinance plugin | 1-2 | Low |
| 3 | CSS scraper | 1-2 | Medium |
| 4 | synthetic_yield | 3-4 | **High** |
| 5 | Service layer (plugin manager + pricing) | 1-2 | Medium |
| 6 | API endpoints (plugin CRUD + price CRUD) | 1-2 | Medium |
| 7 | Documentation | 1 | Low |
| **Total** | | **11-17 days** | **Medium-High** |

**Note**: synthetic_yield è il componente più complesso. Day-count conventions e interest calculations richiedono attenzione ai dettagli finanziari.

---

## 🚀 Ready to Start!

### 📋 Ordine di Implementazione Consigliato

**Phase 0 - Database** (inizio obbligatorio):
1. Crea migration `asset_plugin_assignments`
2. Applica migration a test_app.db
3. Verifica schema validation

**Phase 1-4 - Plugins** (core implementation):
4. Plugin system base (abstract class + registry)
5. yfinance plugin (quick win, testabile subito)
6. cssscraper plugin (utility)
7. synthetic_yield plugin (più complesso, lascia per ultimo)

**Phase 5-6 - Services & API** (integrazione):
8. Plugin manager service (assign/remove)
9. Pricing service (refresh + manual CRUD)
10. API endpoints (tutti insieme)

**Phase 7 - Docs** (chiusura):
11. Documentation completa

### 🎯 Note Importanti

**Day-Count Conventions**:
- Default: ACT/365 (standard, accurato)
- ACT/360 produce ~1.4% interesse in più (money market)
- 30/360 è prevedibile ma meno accurato

**Plugin Assignment**:
- 1 asset = max 1 plugin (UNIQUE constraint)
- Nessuna logica priority (diverso da FX pair-sources)
- Configurazione in plugin_params JSON

**Manual Price CRUD**:
- Permette correzioni senza plugin
- UPSERT logic (insert se nuovo, update se esiste)
- Bulk operations dove possibile

**Test Strategy**:
- ~70+ test totali previsti
- Test dopo ogni fase (incrementale)
- Integration test finale (API → Service → Plugin)

### 🔧 Setup Iniziale

```bash
# 1. Crea cartelle
mkdir -p backend/app/services/plugins
mkdir -p backend/test_scripts/test_services
mkdir -p backend/test_scripts/test_api

# 2. Installa dependencies
pipenv install yfinance beautifulsoup4

# 3. Crea migration
./dev.sh db:migrate "add asset_plugin_assignments table"

# 4. Applica migration
./dev.sh db:upgrade backend/data/sqlite/test_app.db
```

### 📚 Riferimenti

**Day-count conventions**:
- Vedi sezione "📐 Day-Count Conventions Explained" sopra
- ACT/365 default, ACT/360 e 30/360 supportati

**Similitudini con FX system**:
- Plugin registry simile a FX provider factory
- @register_plugin simile a provider auto-discovery
- PluginError simile a FXServiceError

**Differenze chiave**:
- ❌ Nessuna priority logic (1 plugin per asset massimo)
- ❌ Nessun fallback (diverso da FX multi-provider)
- ✅ Manual CRUD (diverso da FX che è sempre API-driven)

---

**Buon lavoro su Step 05! 🎉**

**Stima realistica**: 11-17 giorni (synthetic_yield è il pezzo più complesso)  
**Test coverage target**: 70+ test (100% coverage obiettivo)  
**Endpoint totali**: ~15 endpoint nuovi


# Service Tests

Testing backend business logic and service layer.

> 📖 **Back to**: [Testing Guide](./README.md)

---

## Overview

Service tests verify **business logic** and **service layer functionality** with DB integration.

**Run**: `./test_runner.py services all`

---

## Test Suites

### 1. FX Conversion

**File**: `backend/test_scripts/test_services/test_fx_conversion.py`

**What it tests**:
- Currency conversion logic (identity, direct, inverse, roundtrip)
- Forward-fill for missing dates
- Different date ranges
- Multi-currency scenarios

**DB Requirements**: FX rates populated

**Run**: `./test_runner.py services fx`

**See**: [FX Implementation](../fx-implementation.md)

---

### 2. Asset Source

**File**: `backend/test_scripts/test_services/test_asset_source.py`

**Coverage**: 15/15 tests pass

**What it tests**:
- **Helper Functions**:
  - Price column precision validation (18,6)
  - Price truncation to DB precision
  - ACT/365 day count calculation
  - Find active period for synthetic yield schedules
- **Provider Assignment**:
  - Bulk and single provider assignment
  - Bulk and single provider removal
  - Provider metadata validation
- **Price Operations**:
  - Bulk and single price upsert
  - Bulk and single price deletion
  - Price retrieval with date ranges
- **Backward-Fill Logic**:
  - Basic backward-fill with gap filling
  - **Volume propagation** in backward-filled prices (NEW)
  - Edge case: query with no initial data (empty result)
- **Provider Fallback**:
  - Invalid/unregistered provider graceful fallback to DB (NEW)
  - Structured logging of provider failures (NEW)

**DB Requirements**: Clean test database (auto-created)

**Run**: `./test_runner.py services asset-source`

**Key Features Tested**:
- Backward-fill preserves `volume` field from last known price
- Provider fetch failures logged with context (provider_code, asset_id, exception)
- Distinct warnings for "provider not registered" vs "runtime exception"
- Graceful degradation to DB when provider unavailable

**See**: 
- [Asset Source Architecture](../assets/architecture.md)
- [Provider Development](../assets/provider-development.md)

---

### 3. Provider Registry

**File**: `backend/test_scripts/test_services/test_provider_registry.py`

**What it tests**:
- Provider registration and discovery
- Metadata validation
- Provider initialization

**Run**: `./test_runner.py services provider-registry`

---

### 4. Synthetic Yield

**File**: `backend/test_scripts/test_services/test_synthetic_yield.py`

**Coverage**: 9/9 tests pass

**What it tests**:
- Provider param validation (Pydantic)
- `get_current_value()` and `get_history_value()`
- `_calculate_value_for_date()` private method
- Integration with AssetSourceManager
- No DB storage (on-demand calculation)
- Utility functions with Pydantic

**Pattern**: Uses `_transaction_override` for DB-free testing

**Run**: `./test_runner.py services synthetic-yield`

**See**: [Synthetic Yield Provider](../financial-calculations/scheduled-investment-provider.md)

---

### 5. Synthetic Yield Integration E2E

**File**: `backend/test_scripts/test_services/test_synthetic_yield_integration.py`

**Coverage**: 3/3 scenarios pass

**What it tests**:
- **Scenario 1**: P2P loan with two periods + grace + late interest
- **Scenario 2**: Bond with quarterly compound interest
- **Scenario 3**: Mixed SIMPLE/COMPOUND multi-period schedule

**Pattern**: End-to-end realistic scenarios with `_transaction_override`

**Run**: `./test_runner.py services synthetic-yield-integration`

**See**: [Synthetic Yield E2E](./synthetic-yield-e2e.md)

---

## Running Service Tests

```bash
# All service tests (includes DB creation)
./test_runner.py services all

# Specific test
./test_runner.py services synthetic-yield

# With verbose output
./test_runner.py -v services all
```

**Note**: `services all` automatically creates clean test DB before running.

---

## Related Documentation

- **[Synthetic Yield E2E](./synthetic-yield-e2e.md)** - Integration scenarios
- **[Utils Tests](./utils-tests.md)** - Unit-level utility tests
- **[Testing Guide](./README.md)** - Main testing documentation

---

**Last Updated**: November 17, 2025


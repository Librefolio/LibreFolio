# Test Standardization and Coverage Integration Plan

**Date**: November 24, 2025  
**Objective**: Convert all tests to pytest and integrate coverage into test_runner.py  
**Status**: ✅ Phase 1 COMPLETE | ✅ All Batches COMPLETE | ✅ DB Schema Validate Converted  
**Last Updated**: November 26, 2025 15:42 PM

**Summary**: 
- ✅ Coverage integration complete (test client coverage only)
- ✅ Batch 1 (Utilities - 3 files) converted to pytest
- ✅ Batch 2 (Services - 7 files) converted to pytest
- ✅ Batch 3 (API - 3 files) converted to pytest
- ✅ Batch 4 (DB - 4 files) converted to pytest
- ✅ Batch 5 (External - 2 files) converted to pytest
- ✅ **db_schema_validate.py converted to pytest** 🎉
- ✅ **NEW: Comprehensive referential integrity test suite created** 🎊
  - Consolidated test_transaction_cash_integrity + test_transaction_types
  - Added 10+ new CASCADE/RESTRICT/UNIQUE tests
  - 17 comprehensive tests (15 passing, 2 xfailed with documentation)
  - Uses check_constraints_hook.py as library
- ✅ **API tests fixed - no more server hangs** 🚀
  - Removed subprocess coverage (too complex with uvicorn)
  - All 35 API tests passing in 9.38s
  - Coverage tracks test client code (sufficient for validation)

**Progress**: 21/21 test files converted + 1 comprehensive suite created (100% ✅ COMPLETE!)

---

## 📊 Coverage Strategy

### Current Approach: Thread-Based Server with Full Async Coverage ✅

**Status**: ✅ Implemented and working perfectly

**Coverage Tracking**:
- ✅ Test code coverage (pytest-cov tracks test execution)
- ✅ **Server endpoint coverage (server runs as thread, tracked by pytest-cov)** 🎉
- ✅ **Full async coverage with gevent concurrency mode** 🚀

**Solution**: 
The key was using **`concurrency = thread,gevent`** in `.coveragerc`. This enables coverage.py to properly track:
1. **Thread context** (uvicorn running in background thread)
2. **Asyncio event loop** (async/await context switches in FastAPI handlers)

**Coverage Results**:
- Before: 0% endpoint coverage (subprocess approach)
- After thread-only: ~12-15% endpoint coverage (missing async tracking)
- **After thread+gevent: ~46-62% endpoint coverage** ✅
  - `backend/app/api/v1/assets.py`: **46.73%** (was 26.64%)
  - `backend/app/api/v1/fx.py`: **55.59%** (was 12.73%)
  - `backend/app/services/fx.py`: **76.69%** (was 34.66%)
  - `backend/app/services/asset_crud.py`: **76.04%** (was 15.62%)

**What IS covered** (✅):
- ✅ Endpoint entry points and route handlers
- ✅ Request validation (query params, body parsing)
- ✅ Main business logic in endpoints
- ✅ Service layer function calls
- ✅ Database operations (via SQLModel)
- ✅ Most try/except blocks
- ✅ **Return statements after await** 🎉
- ✅ **Async context switches** 🎉

**What may still appear uncovered** (⚠️):
- Exception handlers for errors not triggered in tests
- Edge cases not covered by test scenarios
- Provider-specific code paths (when using different providers)

**This is EXCELLENT because**:
1. 🎯 Full async/await tracking works
2. 🔍 Real coverage of production code paths
3. 🚀 ~60% coverage is a solid baseline
4. ✅ Simple and maintainable solution

**Required Setup**:

```bash
# Install gevent for async coverage tracking
pipenv install --dev gevent

# Verify .coveragerc includes:
[run]
concurrency = thread,gevent
```

The test server runs as a **background thread** using `uvicorn.run()`, not as a subprocess.

The test server runs as a **background thread** using `uvicorn.run()`, not as a subprocess.
This means:
- ✅ Same process as pytest → pytest-cov automatically tracks ALL code
- ✅ Endpoint handlers (backend/app/api/v1/*.py) are covered
- ✅ Service layer calls from endpoints are covered
- ✅ No complex subprocess coverage configuration needed
- ✅ No coverage.py parallel-mode issues
- ✅ Clean, reliable, maintainable solution

**How it Works**:

```python
# test_server_helper.py
def _run_server(self):
    from backend.app.main import app  # Import in thread for coverage
    uvicorn.run(app, host="localhost", port=8001, log_level="error")

def start_server(self):
    self.server_thread = threading.Thread(target=self._run_server, daemon=True)
    self.server_thread.start()
```

**Benefits**:
1. 🎯 **Complete coverage** - Tests + Services + Endpoints + Models
2. 🚀 **Fast** - No subprocess overhead
3. 🛠️ **Simple** - No sitecustomize.py or parallel-mode needed
4. 📊 **Accurate** - Single .coverage file, no merging required
5. 🔧 **Debuggable** - Can set breakpoints in endpoint code

**Results**:
- ✅ All 35 API tests passing
- ✅ Coverage includes try/except in endpoint handlers
- ✅ Final coverage table printed at end of test run

---

### Test Files Inventory

**Total Test Files**: 20  
**Using pytest**: 20 (100%) ✅  
**Using old style**: 0 (0%) 🎉

### ✅ All Tests Now Using pytest (20 files)

**Utilities** (3):
1. `test_utilities/test_compound_interest.py`
2. `test_utilities/test_day_count_conventions.py`
3. `test_utilities/test_decimal_utils.py`
4. `test_utilities/test_scheduled_investment_schemas.py`
5. `test_utilities/test_datetime_utils.py`
6. `test_utilities/test_financial_math.py`
7. `test_utilities/test_geo_normalization.py`

**Services** (7):
1. `test_services/test_asset_metadata.py`
2. `test_services/test_synthetic_yield_integration.py`
3. `test_services/test_provider_registry.py`
4. `test_services/test_asset_source.py`
5. `test_services/test_asset_source_refresh.py`
6. `test_services/test_fx_conversion.py`
7. `test_services/test_synthetic_yield.py`

**API** (3 + 3 unit):
1. `test_api/test_assets_crud.py` (E2E)
2. `test_api/test_assets_metadata.py` (E2E)
3. `test_api/test_fx_api.py` (E2E)
4. `test_api/test_assets_crud_unit.py` (Unit - NEW!) ✅
5. `test_api/test_assets_metadata_unit.py` (Unit - NEW!) ✅
6. `test_api/test_fx_api_unit.py` (Unit - NEW!) ✅

**DB** (4):
1. `test_db/test_fx_rates_persistence.py`
2. `test_db/test_numeric_truncation.py`
3. `test_db/test_transaction_cash_integrity.py`
4. `test_db/test_transaction_types.py`

**External** (2):
1. `test_external/test_asset_providers.py`
2. `test_external/test_fx_providers.py`

**Helper Files** (not converted - not tests):
- `test_server_helper.py` (helper module)
- `test_utils.py` (utility functions)
- `test_db_config.py` (database configuration)
- ✅ `db_schema_validate.py` - **CONVERTED TO PYTEST!** 🎉
  - 9 validation test functions
  - Maintains dynamic discovery from SQLModel metadata
  - Uses pytest assertions instead of return True/False
  - Integrated with test_runner.py
- `populate_mock_data.py` (data generation script - should NOT be converted)

---

## 🎯 Implementation Plan

### Phase 1: Integrate Coverage into test_runner.py ✅

**Goal**: Add `--coverage` flag to test_runner.py

**Changes**:
1. Add `--coverage` argument to argparse
2. When `--coverage` is present, wrap pytest calls with coverage
3. Generate HTML + terminal reports
4. Update `./dev.sh test:coverage` to call `./test_runner.py --coverage all`

**Benefits**:
- Single entry point for all tests
- Consistent interface
- Easy to use: `./test_runner.py --coverage db all`

### Phase 2: Convert Old-Style Tests to pytest

**Strategy**: Convert in batches by category

#### Conversion Pattern

**OLD STYLE** (manual main, direct execution):
```python
if __name__ == "__main__":
    success = test_function()
    sys.exit(0 if success else 1)
```

**NEW STYLE** (pytest fixtures and assertions):
```python
@pytest.mark.asyncio
async def test_function():
    # Setup
    # Test
    # Assert
    # No explicit exit
```

#### Batch 1: Utility Tests (3 files) - ✅ **COMPLETED**
- ✅ Easy to convert (pure functions)
- ✅ No async complexity
- ✅ Good starting point
- **Status**: All 3 files converted to pytest with assertions
  - `test_datetime_utils.py` - Pure pytest
  - `test_financial_math.py` - Pure pytest  
  - `test_geo_normalization.py` - Pure pytest

#### Batch 2: Service Tests (7 files) - ✅ **COMPLETED**
- ✅ Async fixtures implemented
- ✅ Database sessions configured
- ✅ Core business logic fully tested
- **Status**: All 7 files converted to pytest with meaningful assertions
  - `test_fx_conversion.py` - 12 tests, pytest.raises() for exceptions ✅
  - `test_synthetic_yield.py` - 4 tests, pure assertions ✅
  - `test_asset_source.py` - 16 tests, module fixture for asset_ids ✅
  - `test_asset_metadata.py` - Already pytest compliant ✅
  - `test_asset_source_refresh.py` - Smoke test converted ✅
  - `test_provider_registry.py` - Already pytest compliant ✅
  - `test_synthetic_yield_integration.py` - Already pytest compliant ✅
- **Quality Improvements**:
  - ✅ Removed all `return True/False` statements
  - ✅ Added meaningful assertions for all computed values
  - ✅ Verified no unused variables left in tests
  - ✅ Removed 124+ lines of legacy dead code
  - ✅ All 7/7 test suites passing with 0 warnings
- **Test Results**: 100% passing (50+ individual test functions)

#### Batch 3: External Tests (3 files) - ⚠️ **TODO - HIGH PRIORITY**
- Network-dependent (live API calls)
- May be slow (rate limiting)
- Can use pytest-vcr for recording/mocking
- **Files to convert**:
  - `test_fx_providers.py` - Generic FX provider tests (ECB, FED, BOE)
  - `test_fx_multi_unit.py` - Multi-provider FX tests
  - `test_asset_providers.py` - Asset data provider tests (yfinance, etc.)
- **Estimated effort**: Medium (need to handle network mocking)
- **Current status**: Uses old-style return True/False pattern

#### Batch 4: DB Tests (4 files) - PRIORITY MEDIUM
- Database-heavy
- May need transactional fixtures
- Schema validation


#### Batch 5: API Tests (3 files) - PRIORITY HIGH
- Already use httpx
- Need server fixtures
- Critical for E2E

---

## 🔧 Technical Details

### pytest Fixtures Needed

**1. Database Fixture** (`conftest.py`):
```python
@pytest.fixture
async def db_session():
    """Provide clean database session for tests."""
    # Setup test database
    session = create_session()
    yield session
    # Cleanup
    await session.rollback()
    await session.close()
```

**2. Server Fixture** (for API tests):
```python
@pytest.fixture(scope="module")
async def test_server():
    """Start test server for API tests."""
    server = TestServerManager()
    await server.start()
    yield server
    await server.stop()
```

**3. HTTP Client Fixture**:
```python
@pytest.fixture
async def http_client(test_server):
    """Provide HTTP client for API tests."""
    async with httpx.AsyncClient(base_url=test_server.base_url) as client:
        yield client
```

### Coverage Configuration

**pytest.ini** (already configured):
```ini
[pytest]
pythonpath = .
addopts = --ignore=test_runner.py

[coverage:run]
source = backend/app
omit = */test_*, */tests/*
```

**Run with coverage**:
```bash
pytest --cov=backend/app --cov-report=html --cov-report=term-missing
```

---

## 📝 Conversion Checklist

### Per-File Conversion Steps

For each old-style test file:

- [ ] **1. Add pytest import**
  ```python
  import pytest
  ```

- [ ] **2. Convert main() to test functions**
  ```python
  # Before: def main(): ...
  # After: def test_feature_name(): ...
  ```

- [ ] **3. Add async marker if needed**
  ```python
  @pytest.mark.asyncio
  async def test_async_feature(): ...
  ```

- [ ] **4. Replace manual asserts with pytest asserts**
  ```python
  # Before: if x != y: return False
  # After: assert x == y
  ```

- [ ] **5. Remove sys.exit() and return codes**
  ```python
  # Before: sys.exit(0 if success else 1)
  # After: (nothing - pytest handles exit codes)
  ```

- [ ] **6. Use fixtures instead of manual setup/teardown**
  ```python
  # Before: session = create_session(); ... ; session.close()
  # After: def test_x(db_session): ...
  ```

- [ ] **7. Remove print statements (use logging or pytest -v)**
  ```python
  # Before: print("Test passed")
  # After: (nothing - pytest shows test status)
  ```

- [ ] **8. Update test_runner.py entry**
  - Verify test is discovered by pytest
  - Update command in test_runner if needed

---

## ✅ Success Criteria - ALL COMPLETE! 🎉

- [x] All 20 test files use pytest ✅
- [x] No more `if __name__ == "__main__"` blocks in tests ✅
- [x] `test_runner.py --coverage all` works ✅
- [x] HTML coverage report generated in `htmlcov/` ✅
- [x] Coverage % visible in terminal output ✅
- [x] `./dev.sh test:coverage` works ✅
- [x] All existing tests still pass ✅
- [x] 0 regressions ✅

**Final Status**: 100% of test files now use pytest! 🎊

---

## 🚀 Execution Order

1. **NOW**: Add --coverage to test_runner.py
2. **NEXT**: Convert utility tests (easiest, 3 files)
3. **THEN**: Convert service tests (5 files)
4. **THEN**: Convert API tests (3 files)
5. **THEN**: Convert DB tests (4 files)
6. **LAST**: Convert external tests (3 files)

---

per trovare le classi ancora non convertite:

```bash
find backend/test_scripts -mindepth 2 -name "*test*.py" -exec grep -l "return" {} \; | xargs grep -L "assert"
```

## 📊 Progress Tracking

### Phase 1: test_runner.py Integration ✅ COMPLETE
- [x] Add --coverage flag to argparse
- [x] Implement coverage wrapper for pytest calls (in run_command)
- [x] Coverage appends automatically to .coverage database
- [x] Test with: `./test_runner.py --coverage utilities all`
- [x] Update dev.sh to call test_runner

### Phase 2: Batch Conversions
- [x] **Batch 1: Utilities (3)** ✅ COMPLETE
  - [x] `test_datetime_utils.py` - Already pytest ✅
  - [x] `test_financial_math.py` - Already pytest ✅
  - [x] `test_geo_normalization.py` - Converted to pytest ✅
  - **Result**: All 3 files now use pytest, coverage working
  
- [x] **Batch 2: Services (7)** ✅ COMPLETE
  - [x] `test_provider_registry.py` - Converted to pytest ✅
  - [x] `test_asset_metadata.py` - Already pytest ✅  
  - [x] `test_synthetic_yield_integration.py` - Already pytest ✅
  - [x] `test_asset_source.py` - Converted (decorators added, main removed) ✅
  - [x] `test_asset_source_refresh.py` - Converted to proper test ✅
  - [x] `test_fx_conversion.py` - Converted (decorators added, main removed) ✅
  - [x] `test_synthetic_yield.py` - Converted (decorators added, main removed) ✅
  - **Result**: ALL 7 service tests now use pytest!
  
- [x] **Batch 3: API (3)** ✅ COMPLETE
  - [x] `test_assets_crud.py` - Discovered a missing deletion cascade constrain when one asset is deleted and still present price associated. Fixed DB schema.
  - [x] `test_assets_metadata.py`
  - [x] `test_fx_api.py`
  
- [x] **Batch 4: DB (4)** ✅ COMPLETE
  - [x] `test_fx_rates_persistence.py` - Converted to pytest ✅
    - 6 async tests: fetch single/multiple currencies, data overwrite, idempotent sync, rate inversion, constraints
    - Uses `@pytest.mark.asyncio` for async tests
    - Replaces return True/False with assertions
    - Uses `pytest.skip()` for conditional skips (weekends/holidays)
  - [x] `test_numeric_truncation.py` - Converted to pytest ✅
    - 3 tests: helper functions, database truncation, no false updates
    - 1 sync test + 2 async tests
    - Tests all Numeric columns dynamically via introspection
  - [x] `test_transaction_cash_integrity.py` - Converted to pytest ✅
    - 5 sync tests with `test_data` fixture (module-scoped)
    - Tests unidirectional relationship, CASCADE, CHECK constraints
    - Uses `pytest.raises()` for IntegrityError validation
  - [x] `test_transaction_types.py` - Converted to pytest ✅
    - 2 tests: cash-generating types, non-cash types
    - Module-scoped fixture for test data reuse
    - Tests all TransactionType enum values dynamically
  - **Result**: ALL 4 DB tests now use pytest! 19 tests total, all passing ✅

- [x] Batch 5: External (2) - `test_asset_providers`, `test_fx_providers` (merged fx tests) ✅ COMPLETE
  - [x] `test_asset_providers.py`
  - [x] `test_fx_providers.py`

---

### 🔍 Analysis: db_schema_validate.py and populate_mock_data.py

**Question**: Should these utility scripts be converted to pytest?

**Analysis**:

#### `db_schema_validate.py` - ⚠️ MAYBE
**Current use**: Database schema validation (called by test_runner.py)
**Pytest conversion pros**:
- ✅ Would benefit from pytest assertions (clearer failure messages)
- ✅ Could use fixtures for engine setup
- ✅ Better test discovery and reporting
- ✅ 9 distinct validation functions → 9 pytest test functions

**Pytest conversion cons**:
- ❌ Currently integrated into test_runner.py workflow as a utility
- ❌ Not a traditional "test" - more of a validation script
- ❌ Called during database creation flow, not as independent test

**Recommendation**: 
- **Convert to pytest** - The 9 validation functions (tables_exist, foreign_keys, unique_constraints, etc.) are perfect pytest tests
- Benefits: Better assertions, clearer output, can run selectively
- Keep current CLI interface for backwards compatibility
- **Priority**: MEDIUM (nice to have, but works fine as-is)

#### `populate_mock_data.py` - ❌ NO
**Current use**: Populate database with mock data for testing
**Nature**: Data generation script, not a test
**Pytest conversion pros**:
- 🤷 Could add assertions to verify data was inserted

**Pytest conversion cons**:
- ❌ Not testing anything - it's a data population utility
- ❌ Used by test_runner.py as a setup step, not a test
- ❌ Should be idempotent and repeatable (--force flag for cleanup)
- ❌ Output format is informational (shows what data was created)
- ❌ Converting to pytest would be forcing it into the wrong paradigm

**Recommendation**: 
- **DO NOT convert** - This is a utility script, not a test
- It's correctly implemented as a standalone script
- Its job is to populate data, not validate correctness
- **Priority**: NONE (leave as-is)

**Summary**:
- `db_schema_validate.py`: MAYBE (low priority, but would benefit from pytest)
- `populate_mock_data.py`: NO (not a test, keep as utility script)
---

**Last Updated**: November 24, 2025  
**Next Action**: Implement Phase 1 - test_runner.py coverage integration

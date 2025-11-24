# Test Standardization and Coverage Integration Plan

**Date**: November 24, 2025  
**Objective**: Convert all tests to pytest and integrate coverage into test_runner.py  
**Status**: 🚧 IN PROGRESS

---

## 📊 Current State Analysis

### Test Files Inventory

**Total Test Files**: 26  
**Using pytest**: 6 (23%)  
**Using old style**: 20 (77%)

### ✅ Already Using pytest (6 files)

1. `test_services/test_asset_metadata.py`
2. `test_services/test_synthetic_yield_integration.py`
3. `test_utilities/test_compound_interest.py`
4. `test_utilities/test_day_count_conventions.py`
5. `test_utilities/test_decimal_utils.py`
6. `test_utilities/test_scheduled_investment_schemas.py`

### ❌ Need Conversion to pytest (20 files)

**API Tests** (3):
- `test_api/test_assets_crud.py`
- `test_api/test_assets_metadata.py`
- `test_api/test_fx_api.py`

**DB Tests** (4):
- `test_db/test_fx_rates_persistence.py`
- `test_db/test_numeric_truncation.py`
- `test_db/test_transaction_cash_integrity.py`
- `test_db/test_transaction_types.py`

**External Tests** (3):
- `test_external/test_asset_providers.py`
- `test_external/test_fx_multi_unit.py`
- `test_external/test_fx_providers.py`

**Service Tests** (5):
- `test_services/test_asset_source.py`
- `test_services/test_asset_source_refresh.py`
- `test_services/test_fx_conversion.py`
- `test_services/test_provider_registry.py`
- `test_services/test_synthetic_yield.py`

**Utility Tests** (3):
- `test_utilities/test_datetime_utils.py`
- `test_utilities/test_financial_math.py`
- `test_utilities/test_geo_normalization.py`

**Helper Files** (2 - skip):
- `test_server_helper.py` (helper, not a test)
- `test_utils.py` (helper, not a test)

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

#### Batch 1: Utility Tests (3 files) - PRIORITY HIGH
- Easy to convert (pure functions)
- No async complexity
- Good starting point

#### Batch 2: Service Tests (5 files) - PRIORITY HIGH
- May need async fixtures
- Database sessions required
- Core business logic

#### Batch 3: DB Tests (4 files) - PRIORITY MEDIUM
- Database-heavy
- May need transactional fixtures
- Schema validation

#### Batch 4: External Tests (3 files) - PRIORITY LOW
- Network-dependent
- May be slow
- Can use pytest-vcr for recording

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

## ✅ Success Criteria

- [ ] All 26 test files use pytest
- [ ] No more `if __name__ == "__main__"` blocks in tests
- [ ] `test_runner.py --coverage all` works
- [ ] HTML coverage report generated in `htmlcov/`
- [ ] Coverage % visible in terminal output
- [ ] `./dev.sh test:coverage` works
- [ ] All existing tests still pass
- [ ] 0 regressions

---

## 🚀 Execution Order

1. **NOW**: Add --coverage to test_runner.py
2. **NEXT**: Convert utility tests (easiest, 3 files)
3. **THEN**: Convert service tests (5 files)
4. **THEN**: Convert API tests (3 files)
5. **THEN**: Convert DB tests (4 files)
6. **LAST**: Convert external tests (3 files)

---

## 📊 Progress Tracking

### Phase 1: test_runner.py Integration
- [ ] Add --coverage flag to argparse
- [ ] Implement coverage wrapper for pytest calls
- [ ] Update non-pytest tests to use pytest discovery
- [ ] Test with: `./test_runner.py --coverage utilities all`
- [ ] Update dev.sh to call test_runner

### Phase 2: Batch Conversions
- [ ] Batch 1: Utilities (3) - `test_datetime_utils`, `test_financial_math`, `test_geo_normalization`
- [ ] Batch 2: Services (5) - `test_asset_source*`, `test_fx_conversion`, `test_provider_registry`, `test_synthetic_yield`
- [ ] Batch 3: API (3) - `test_assets_crud`, `test_assets_metadata`, `test_fx_api`
- [ ] Batch 4: DB (4) - `test_fx_rates_persistence`, `test_numeric_truncation`, `test_transaction_*`
- [ ] Batch 5: External (3) - `test_asset_providers`, `test_fx_*`

---

**Last Updated**: November 24, 2025  
**Next Action**: Implement Phase 1 - test_runner.py coverage integration


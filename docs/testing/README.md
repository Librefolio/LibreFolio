# Testing Guide

Complete guide to testing in LibreFolio.

> 🎯 **Related**: [Financial Calculations](../financial-calculations/README.md) | [Database Schema](../database-schema.md)

---

## 📚 Table of Contents

### Test Categories

- **[Utility Tests](./utils-tests.md)** - Testing helper functions and utilities
- **[Service Tests](./services-tests.md)** - Testing business logic and services  
- **[Database Tests](./database-tests.md)** - Schema validation and persistence
- **[API Tests](./api-tests.md)** - REST API endpoint testing
- **[Synthetic Yield E2E](./synthetic-yield-e2e.md)** - End-to-end integration scenarios

### Quick Reference

| Category | Test Files | Coverage | Run Command |
|----------|-----------|----------|-------------|
| [Utils](./utils-tests.md) | 6 files | 110+ tests | `./test_runner.py utils all` |
| [Services](./services-tests.md) | 6 files | 25+ tests | `./test_runner.py services all` |
| [Database](./database-tests.md) | 7 files | 100+ tests | `./test_runner.py db all` |
| [API](./api-tests.md) | 1 file | 15+ tests | `./test_runner.py api all` |

---

## 🎯 Testing Philosophy

### Test Pyramid

```
        /\
       /  \      E2E Integration Tests (3-5 scenarios)
      /____\
     /      \    Service/Integration Tests (~20 tests)
    /________\
   /          \  Unit Tests (~100+ tests)
  /____________\
```

**Distribution**:
- **70%** Unit tests (utils, schemas, helpers)
- **20%** Service tests (business logic)
- **10%** E2E tests (full scenarios)

### Principles

1. **Independence** - Tests don't depend on each other
2. **Determinism** - Same input → same output
3. **Fast** - Unit tests < 1s, integration < 10s
4. **Clear failures** - Easy to understand what broke
5. **Exact comparisons** - For math, no tolerance ranges

---

## 🚀 Quick Start

### Run All Tests

```bash
# Complete test suite (~3-5 minutes)
./test_runner.py all

# Specific category
./test_runner.py utils all
./test_runner.py services all
./test_runner.py db all
```

### Run Specific Test

```bash
# Single test file
./test_runner.py utils financial-math
./test_runner.py services synthetic-yield

# With verbose output
./test_runner.py -v services synthetic-yield-integration
```

### Test Structure

```
backend/test_scripts/
├── test_utilities/          # Unit tests for utils
│   ├── test_decimal_utils.py
│   ├── test_datetime_utils.py
│   ├── test_financial_math.py
│   ├── test_day_count_conventions.py
│   ├── test_compound_interest.py
│   └── test_scheduled_investment_schemas.py
├── test_services/           # Service/integration tests
│   ├── test_fx_conversion.py
│   ├── test_asset_source.py
│   ├── test_synthetic_yield.py
│   └── test_synthetic_yield_integration.py
├── test_db/                 # Database tests
│   ├── db_schema_validate.py
│   ├── populate_mock_data.py
│   └── test_*.py
└── test_api/                # API tests
    └── test_fx_api.py
```

---

## 📊 Test Coverage by Feature

### Financial Calculations

**Coverage**: 100% of implemented features

| Feature | Tests | Status |
|---------|-------|--------|
| Day Count Conventions | 20 | ✅ All pass |
| Simple Interest | 10 | ✅ All pass |
| Compound Interest | 28 | ✅ All pass |
| Scheduled Investment | 9 | ✅ All pass |
| E2E Scenarios | 3 | ✅ All pass |

**See**: [Synthetic Yield E2E](./synthetic-yield-e2e.md)

### Database

**Coverage**: All tables, constraints, relationships

| Feature | Tests | Status |
|---------|-------|--------|
| Schema Validation | 9 | ✅ All pass |
| Constraints | 12 | ✅ All pass |
| Transactions | 7 | ✅ All pass |
| Mock Data | 1 | ✅ Pass |

**See**: [Database Tests](./database-tests.md)

### Services

**Coverage**: Core business logic

| Service | Tests | Status |
|---------|-------|--------|
| FX Conversion | 8 | ✅ All pass |
| Asset Source | 5 | ✅ All pass |
| Synthetic Yield | 12 | ✅ All pass |

**See**: [Service Tests](./services-tests.md)

---

## 🧪 Test Runner

### Architecture

**Central orchestrator**: `test_runner.py`

**Features**:
- ✅ Organized test categories
- ✅ Verbose/quiet modes
- ✅ Automatic test database setup
- ✅ Summary reports
- ✅ Exit codes for CI/CD

### Commands

```bash
# Utils
./test_runner.py utils decimal-precision
./test_runner.py utils datetime
./test_runner.py utils financial-math
./test_runner.py utils day-count
./test_runner.py utils compound-interest
./test_runner.py utils scheduled-investment-schemas
./test_runner.py utils all

# Services
./test_runner.py services fx
./test_runner.py services asset-source
./test_runner.py services synthetic-yield
./test_runner.py services synthetic-yield-integration
./test_runner.py services all

# Database
./test_runner.py db create
./test_runner.py db validate
./test_runner.py db populate
./test_runner.py db all

# API
./test_runner.py api fx
./test_runner.py api all

# Everything
./test_runner.py all
```

---

## 📝 Writing Tests

### Unit Test Example

```python
"""Test day count conventions."""
from datetime import date
from decimal import Decimal
from backend.app.utils.financial_math import calculate_day_count_fraction
from backend.app.schemas.assets import DayCountConvention

def test_act_365_thirty_days():
    """Test ACT/365 for 30 days."""
    result = calculate_day_count_fraction(
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 31),
        convention=DayCountConvention.ACT_365
    )
    expected = Decimal("30") / Decimal("365")
    assert result == expected  # Exact comparison
```

### Integration Test Example

```python
"""Test E2E P2P loan scenario."""
import pytest
from backend.app.services.asset_source_providers.scheduled_investment import ScheduledInvestmentProvider

@pytest.mark.asyncio
async def test_p2p_loan_with_grace_and_late():
    """Test loan with grace period and late interest."""
    provider = ScheduledInvestmentProvider()
    
    params = {
        "schedule": [...],
        "late_interest": {...},
        "_transaction_override": [
            {"type": "BUY", "quantity": 1, "price": "10000", "trade_date": "2025-01-01"}
        ]
    }
    
    result = await provider.get_current_value("1", params)
    assert result.value > Decimal("10000")  # Has accrued interest
```

---

## 🔍 Test Database

### Configuration

**Test database**: `backend/data/sqlite/test_app.db`

**Automatic setup**:
- Test runner creates fresh DB if needed
- Uses Alembic migrations
- Isolated from production data

### Commands

```bash
# Create fresh test DB
./test_runner.py db create

# Populate with mock data
./test_runner.py db populate

# Validate schema
./test_runner.py db validate
```

---

## 📖 Detailed Guides

1. **[Utility Tests](./utils-tests.md)**
   - Day count conventions (ACT/365, ACT/360, ACT/ACT, 30/360)
   - Compound interest (all frequencies)
   - Financial math helpers (find_active_period, etc.)
   - Pydantic schema validation (InterestRatePeriod, ScheduledInvestmentSchedule)
   - Decimal precision and datetime utilities

2. **[Service Tests](./services-tests.md)**
   - FX conversion logic (identity, direct, inverse, roundtrip)
   - Asset source providers (assignment, retrieval)
   - Synthetic yield calculation (provider-based)
   - Provider registry (registration and discovery)

3. **[Database Tests](./database-tests.md)**
   - Schema validation (tables, constraints, indexes)
   - Transaction-CashMovement integrity (CASCADE, CHECK constraints)
   - Transaction types validation
   - Numeric truncation (Decimal precision)
   - Mock data population
   - FX rates persistence

4. **[API Tests](./api-tests.md)**
   - REST endpoint testing (FX conversion API)
   - Validation and error handling
   - Auto-start test server

5. **[Synthetic Yield E2E](./synthetic-yield-e2e.md)**
   - P2P loan scenarios (grace + late interest)
   - Bond with compound interest
   - Mixed SIMPLE/COMPOUND schedules

---

## 🐛 Debugging Failed Tests

### Common Issues

**Import errors**:
```bash
# Ensure you're in project root
cd /path/to/LibreFolio

# Check virtual env
pipenv shell
```

**Database errors**:
```bash
# Recreate test database
./test_runner.py db create

# Check database exists
ls -la backend/data/sqlite/test_app.db
```

**Async errors**:
```python
# Use pytest.mark.asyncio for async tests
@pytest.mark.asyncio
async def test_something():
    result = await async_function()
```

### Verbose Mode

```bash
# Show full output
./test_runner.py -v services synthetic-yield

# Run test file directly
pipenv run python -m pytest backend/test_scripts/test_utilities/test_financial_math.py -v
```

---

## 🔗 Related Documentation

- **[Financial Calculations](../financial-calculations/README.md)** - Math functions being tested
- **[Database Schema](../database-schema.md)** - DB structure
- **[Testing Environment](../testing-environment.md)** - Setup and configuration
- **[API Development](../api-development-guide.md)** - API testing context

---

**Last Updated**: November 17, 2025


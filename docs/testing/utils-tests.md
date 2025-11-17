# Utility Tests

Testing utility modules and helper functions.

> 📖 **Back to**: [Testing Guide](./README.md)

---

## Overview

Utility tests verify **pure functions** and **helper modules** used across LibreFolio.

**Characteristics**:
- ✅ Fast (< 1s total)
- ✅ No external dependencies
- ✅ Exact comparisons (mathematical functions)
- ✅ High coverage (70% of test suite)

---

## Test Suites

### 1. Day Count Conventions

**File**: `backend/test_scripts/test_utilities/test_day_count_conventions.py`

**Coverage**: 20/20 tests pass

**Tested functions**:
```python
from backend.app.utils.financial_math import (
    calculate_day_count_fraction,
    _calculate_act_365,
    _calculate_act_360,
    _calculate_act_act,
    _calculate_thirty_360,
)
```

**Test cases**:
- ACT/365: 30 days, 1 year, multi-year ranges
- ACT/360: 30/90/360 days
- ACT/ACT: Non-leap, leap year, cross-leap years
- 30/360: Same month, consecutive months, end-of-month

**Run**:
```bash
./test_runner.py utils day-count
```

**See**: [Day Count Conventions](../financial-calculations/day-count-conventions.md)

---

### 2. Compound Interest

**File**: `backend/test_scripts/test_utilities/test_compound_interest.py`

**Coverage**: 28/28 tests pass

**Tested functions**:
```python
from backend.app.utils.financial_math import (
    calculate_simple_interest,
    calculate_compound_interest,
)
```

**Test cases**:
- Simple interest (baseline)
- All frequencies: ANNUAL, SEMIANNUAL, QUARTERLY, MONTHLY, DAILY, CONTINUOUS
- Edge cases: 0% rate, 0 time, 0 principal
- Exact decimal comparisons

**Run**:
```bash
./test_runner.py utils compound-interest
```

**See**: [Interest Types](../financial-calculations/interest-types.md), [Compounding Frequencies](../financial-calculations/compounding-frequencies.md)

---

### 3. Financial Math Integration

**File**: `backend/test_scripts/test_utilities/test_financial_math.py`

**Coverage**: 23/23 tests pass

**Tested functions**:
```python
from backend.app.utils.financial_math import (
    find_active_period,
    calculate_accrued_interest,
    parse_decimal_value,
)
```

**Test scenarios**:
- `find_active_period()`: Within schedule, grace period, after grace, before schedule, no late interest
- `find_active_rate()`: Backward compatibility
- Preserves period attributes (compounding, day_count, etc.)

**Run**:
```bash
./test_runner.py utils financial-math
```

---

### 4. Scheduled Investment Schemas

**File**: `backend/test_scripts/test_utilities/test_scheduled_investment_schemas.py`

**Coverage**: 23/25 tests pass (2 skipped due to validator limitation)

**Tested models**:
```python
from backend.app.schemas.assets import (
    InterestRatePeriod,
    LateInterestConfig,
    ScheduledInvestmentSchedule,
)
```

**Test cases**:
- InterestRatePeriod: Date validation, rate validation, compounding logic
- LateInterestConfig: Rate/grace period validation
- ScheduledInvestmentSchedule: Overlaps, gaps, auto-sorting, continuity

**Run**:
```bash
./test_runner.py utils scheduled-investment-schemas
```

**See**: [Scheduled Investment Provider](../financial-calculations/scheduled-investment-provider.md)

---

### 5. Decimal Precision

**File**: `backend/test_scripts/test_utilities/test_decimal_utils.py`

**Coverage**: 14/14 tests pass

**Tested functions**:

```python
from backend.app.utils.decimal_utils import (
    get_model_column_precision,
    truncate_to_db_precision,
    truncate_priceHistory,
    truncate_fx_rate,
    )
```

**Test cases**:
- Precision extraction from DB models
- Truncation for prices, FX rates
- Edge cases: Zero, negative, large values
- No false update detection

**Run**:
```bash
./test_runner.py utils decimal-precision
```

---

### 6. Datetime Utilities

**File**: `backend/test_scripts/test_utilities/test_datetime_utils.py`

**Coverage**: 5/5 tests pass

**Tested functions**:
```python
from backend.app.utils.datetime_utils import utcnow
```

**Test cases**:
- Returns datetime with timezone info
- Timezone is UTC
- Returns current time (within reason)
- Multiple calls work correctly

**Run**:
```bash
./test_runner.py utils datetime
```

---

## Running All Utility Tests

```bash
# All utils tests
./test_runner.py utils all

# With verbose output
./test_runner.py -v utils all
```

**Expected output**:
```
Results: 6/6 tests passed
✅ Decimal Precision
✅ Datetime Utils
✅ Financial Math
✅ Day Count Conventions
✅ Compound Interest
✅ Scheduled Investment Schemas
```

---

## Test Patterns

### Exact Comparisons (Math Functions)

```python
def test_calculation():
    """Math functions use exact Decimal comparisons."""
    result = calculate_simple_interest(
        Decimal("10000"),
        Decimal("0.05"),
        Decimal("1")
    )
    expected = Decimal("500")
    assert result == expected  # Exact, no tolerance
```

### Pydantic Validation

```python
def test_schema_validation():
    """Pydantic raises ValidationError for invalid data."""
    with pytest.raises(ValidationError, match="end_date must be"):
        InterestRatePeriod(
            start_date=date(2025, 12, 31),
            end_date=date(2025, 1, 1),  # Invalid: before start
            annual_rate=Decimal("0.05")
        )
```

### Edge Cases

```python
@pytest.mark.parametrize("principal,rate,time,expected", [
    (Decimal("0"), Decimal("0.05"), Decimal("1"), Decimal("0")),  # Zero principal
    (Decimal("10000"), Decimal("0"), Decimal("1"), Decimal("0")),  # Zero rate
    (Decimal("10000"), Decimal("0.05"), Decimal("0"), Decimal("0")),  # Zero time
])
def test_edge_cases(principal, rate, time, expected):
    """Test edge cases return expected zero."""
    result = calculate_simple_interest(principal, rate, time)
    assert result == expected
```

---

## Related Documentation

- **[Financial Calculations](../financial-calculations/README.md)** - Functions being tested
- **[Service Tests](./services-tests.md)** - Integration-level tests
- **[Testing Guide](./README.md)** - Main testing documentation

---

**Last Updated**: November 17, 2025


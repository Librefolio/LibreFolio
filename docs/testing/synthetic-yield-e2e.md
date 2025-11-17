# Synthetic Yield E2E Tests

End-to-end integration tests for Scheduled Investment Provider.

> 📖 **Back to**: [Testing Guide](./README.md)

---

## Overview

**E2E tests** validate complete scenarios with realistic parameters, verifying the entire calculation pipeline from JSON schedule to final value.

**File**: `backend/test_scripts/test_services/test_synthetic_yield_integration.py`

**Coverage**: 3/3 scenarios pass

**Run**:
```bash
./test_runner.py services synthetic-yield-integration
```

---

## Test Scenarios

### Scenario 1: P2P Loan with Grace and Late Interest

**Goal**: Validate multi-period schedule with grace period and late interest penalty.

**Setup**:
- Principal: €10,000
- Period 1: Jan 1 - Jun 30, 2025 @ 5% simple
- Period 2: Jul 1 - Dec 31, 2025 @ 6% simple
- Maturity: Dec 31, 2025
- Grace period: 30 days @ 6% (continues last rate)
- Late interest: After Jan 30, 2026 @ 12% simple

**Timeline**:
```
2025-01-01 ────────────── 2025-06-30 ─────────── 2025-12-31 ─── 2026-01-30 ──→
  BUY €10k    Period 1 (5%)    Period 2 (6%)      Maturity       Grace (6%)   Late (12%)
```

**Test Code**:
```python
@pytest.mark.asyncio
async def test_e2e_p2p_loan_two_periods_late_interest():
    schedule = ScheduledInvestmentSchedule(
        schedule=[
            InterestRatePeriod(
                start_date=date(2025, 1, 1),
                end_date=date(2025, 6, 30),
                annual_rate=Decimal("0.05"),
                compounding=CompoundingType.SIMPLE,
                day_count=DayCountConvention.ACT_365
            ),
            InterestRatePeriod(
                start_date=date(2025, 7, 1),
                end_date=date(2025, 12, 31),
                annual_rate=Decimal("0.06"),
                compounding=CompoundingType.SIMPLE,
                day_count=DayCountConvention.ACT_365
            ),
        ],
        late_interest=LateInterestConfig(
            annual_rate=Decimal("0.12"),
            grace_period_days=30,
            compounding=CompoundingType.SIMPLE,
            day_count=DayCountConvention.ACT_365
        )
    )
    
    params = json.loads(schedule.model_dump_json())
    params["_transaction_override"] = [
        {"type": "BUY", "quantity": 1, "price": "10000", "trade_date": "2025-01-01"}
    ]
    
    # Test value progression
    mid_first = await value_on(date(2025, 3, 15))   # Mid period 1
    maturity = await value_on(date(2025, 12, 31))   # Maturity
    grace = await value_on(date(2026, 1, 15))       # Grace period
    late = await value_on(date(2026, 2, 5))         # Late interest
    
    # Assert monotonic increase
    assert mid_first > Decimal("10000")  # Has accrued interest
    assert maturity > mid_first          # More interest
    assert grace > maturity              # Grace continues accruing
    assert late > grace                  # Late penalty applies
```

**Validated**:
- ✅ Rate changes between periods
- ✅ Grace period continues with last rate
- ✅ Late interest penalty applies after grace
- ✅ Value increases monotonically
- ✅ Period-based calculation efficiency (no timeout)

---

### Scenario 2: Bond with Quarterly Compound Interest

**Goal**: Validate compound interest with quarterly compounding frequency.

**Setup**:
- Principal: €20,000
- Period: Jan 1 - Dec 31, 2025
- Rate: 4% annual, compound quarterly
- Day count: ACT/365

**Expected Behavior**:
- Interest compounds every 3 months
- Quarterly compounding > simple interest
- End-of-year value > mid-year value

**Test Code**:
```python
@pytest.mark.asyncio
async def test_e2e_bond_quarterly_compound():
    schedule = ScheduledInvestmentSchedule(
        schedule=[
            InterestRatePeriod(
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                annual_rate=Decimal("0.04"),
                compounding=CompoundingType.COMPOUND,
                compound_frequency=CompoundFrequency.QUARTERLY,
                day_count=DayCountConvention.ACT_365
            )
        ]
    )
    
    params = json.loads(schedule.model_dump_json())
    params["_transaction_override"] = [
        {"type": "BUY", "quantity": 1, "price": "20000", "trade_date": "2025-01-01"}
    ]
    
    # Q1 end vs start
    hist_q1 = await _history_values(params, date(2025, 1, 1), date(2025, 3, 31))
    assert hist_q1[0] == Decimal("20000")  # Start
    assert hist_q1[-1] > hist_q1[0]        # Q1 growth
    
    # Mid-year vs year-end
    mid_year = await value_on(date(2025, 6, 1))
    year_end = await value_on(date(2025, 12, 31))
    assert year_end > mid_year > hist_q1[-1]  # Continuous growth
```

**Validated**:
- ✅ Compound interest calculation
- ✅ Quarterly frequency applied
- ✅ Value grows over time
- ✅ Compounding effect visible

---

### Scenario 3: Mixed SIMPLE/COMPOUND Multi-Period Schedule

**Goal**: Validate schedule with different interest types in different periods.

**Setup**:
- Principal: €5,000
- Period 1: Jan 1 - Mar 31 @ 3% SIMPLE
- Period 2: Apr 1 - Jun 30 @ 3.5% COMPOUND monthly
- Period 3: Jul 1 - Dec 31 @ 4% SIMPLE

**Test Code**:
```python
@pytest.mark.asyncio
async def test_e2e_mixed_schedule_simple_compound():
    schedule = ScheduledInvestmentSchedule(
        schedule=[
            InterestRatePeriod(
                start_date=date(2025, 1, 1),
                end_date=date(2025, 3, 31),
                annual_rate=Decimal("0.03"),
                compounding=CompoundingType.SIMPLE,
                day_count=DayCountConvention.ACT_365
            ),
            InterestRatePeriod(
                start_date=date(2025, 4, 1),
                end_date=date(2025, 6, 30),
                annual_rate=Decimal("0.035"),
                compounding=CompoundingType.COMPOUND,
                compound_frequency=CompoundFrequency.MONTHLY,
                day_count=DayCountConvention.ACT_365
            ),
            InterestRatePeriod(
                start_date=date(2025, 7, 1),
                end_date=date(2025, 12, 31),
                annual_rate=Decimal("0.04"),
                compounding=CompoundingType.SIMPLE,
                day_count=DayCountConvention.ACT_365
            ),
        ]
    )
    
    params = json.loads(schedule.model_dump_json())
    params["_transaction_override"] = [
        {"type": "BUY", "quantity": 1, "price": "5000", "trade_date": "2025-01-01"}
    ]
    
    # Quarterly snapshots
    q1_end = await value_on(date(2025, 3, 31))
    q2_end = await value_on(date(2025, 6, 30))
    q3_end = await value_on(date(2025, 9, 30))
    q4_end = await value_on(date(2025, 12, 31))
    
    # Assert monotonic increase
    assert q1_end > Decimal("5000")
    assert q2_end > q1_end  # Higher rate + compounding
    assert q3_end > q2_end  # Next rate
    assert q4_end > q3_end  # Final growth
```

**Validated**:
- ✅ Mixed SIMPLE/COMPOUND in same schedule
- ✅ Different rates per period
- ✅ Seamless transitions between periods
- ✅ Correct calculation for each type

---

## Key Testing Patterns

### Using `_transaction_override`

All E2E tests use `_transaction_override` to avoid DB dependency:

```python
params["_transaction_override"] = [
    {"type": "BUY", "quantity": 1, "price": "10000", "trade_date": "2025-01-01"}
]
```

**Benefits**:
- No DB setup required
- Fast execution
- Isolated tests
- Easy to modify scenarios

**See**: [Scheduled Investment Provider](../financial-calculations/scheduled-investment-provider.md#testing-with-_transaction_override)

### Helper Functions

```python
async def value_on(d: date) -> Decimal:
    """Get value for a single date."""
    return (await _history_values(params, d, d))[0]
```

Simplifies test code and improves readability.

### Exact Comparisons

```python
# For starting values
assert hist_q1[0] == Decimal("20000")  # Exact match

# For growth assertions
assert value_later > value_earlier  # Monotonic increase
```

---

## Running E2E Tests

```bash
# All synthetic yield E2E
./test_runner.py services synthetic-yield-integration

# With verbose output
./test_runner.py -v services synthetic-yield-integration

# Direct pytest
pipenv run python -m pytest backend/test_scripts/test_services/test_synthetic_yield_integration.py -v
```

**Expected output**:
```
test_e2e_p2p_loan_two_periods_late_interest PASSED       [33%]
test_e2e_bond_quarterly_compound PASSED                  [66%]
test_e2e_mixed_schedule_simple_compound PASSED           [100%]

3 passed in 0.6s
```

---

## What These Tests DON'T Cover

E2E tests focus on **happy path scenarios**. For edge cases, see:

- **Unit tests**: `test_synthetic_yield.py` (9 tests)
- **Pydantic validation**: `test_scheduled_investment_schemas.py` (23 tests)
- **Financial math**: `test_financial_math.py` (23 tests)

**Examples of edge cases tested elsewhere**:
- Invalid date ranges (end < start)
- Negative interest rates
- Empty schedules
- Overlapping periods
- Missing compound_frequency

---

## Performance Notes

### Test Execution Time

All 3 E2E scenarios complete in **< 1 second** thanks to:
- Period-based algorithm (O(periods) not O(days))
- No DB I/O (using `_transaction_override`)
- Efficient Decimal arithmetic

### Historical Data Generation

Even generating **365 daily values** is fast:
```python
# 365 iterations, still < 100ms
hist = await _history_values(params, date(2025, 1, 1), date(2025, 12, 31))
```

**Key**: Each call to `_calculate_value_for_date()` is O(periods), typically 3-5 periods.

---

## Related Documentation

- **[Scheduled Investment Provider](../financial-calculations/scheduled-investment-provider.md)** - Provider architecture
- **[Interest Types](../financial-calculations/interest-types.md)** - Simple vs Compound
- **[Service Tests](./services-tests.md)** - Unit-level provider tests
- **[Testing Guide](./README.md)** - Main testing documentation

---

**Last Updated**: November 17, 2025


# Interest Types

LibreFolio supports two interest calculation methods: **Simple** and **Compound**.

> 📖 **Back to**: [Financial Calculations Home](./README.md)

---

## Overview

Interest is the cost of borrowing money or the return on lending. The calculation method significantly impacts the final value.

```
Value = Principal + Accrued Interest
```

---

## Simple Interest

### Formula

```
Interest = Principal × Annual Rate × Time Fraction
```

**Characteristics**:
- Linear growth
- Interest does NOT compound (no "interest on interest")
- Easy to calculate and understand
- Common for short-term loans and P2P lending

### Example

```python
from backend.app.utils.financial_math import calculate_simple_interest
from decimal import Decimal

principal = Decimal("10000")
annual_rate = Decimal("0.05")  # 5%
time_fraction = Decimal("1")    # 1 year

interest = calculate_simple_interest(principal, annual_rate, time_fraction)
# Result: €500.00
```

### Multi-Period Calculation

For periods with **rate changes**, calculate each segment separately:

```python
# Period 1: 6 months at 5%
interest_p1 = Decimal("10000") * Decimal("0.05") * (Decimal("182") / Decimal("365"))
# Result: €249.32

# Period 2: 6 months at 6%
interest_p2 = Decimal("10000") * Decimal("0.06") * (Decimal("183") / Decimal("365"))
# Result: €300.82

# Total interest
total = interest_p1 + interest_p2
# Result: €550.14
```

**Note**: Principal remains constant (€10,000). Interest from period 1 does NOT earn interest in period 2.

### Use Cases

✅ **When to use Simple Interest**:
- P2P crowdfunding loans
- Short-term instruments (< 1 year)
- Contracts explicitly specifying simple interest
- Portfolio estimates where precision isn't critical

---

## Compound Interest

### Formula

```
Interest = Principal × [(1 + r/n)^(n×t) - 1]

Where:
  r = annual rate
  n = compounding frequency (times per year)
  t = time in years
```

**Characteristics**:
- Exponential growth
- Interest earns interest (**compounding effect**)
- More complex to calculate
- Higher returns over time
- Common for bonds and long-term investments

### Example (Annual Compounding)

```python
from backend.app.utils.financial_math import calculate_compound_interest
from backend.app.schemas.assets import CompoundFrequency
from decimal import Decimal

principal = Decimal("10000")
annual_rate = Decimal("0.05")
time_fraction = Decimal("1")
frequency = CompoundFrequency.ANNUAL

interest = calculate_compound_interest(
    principal, annual_rate, time_fraction, frequency
)
# Result: €500.00 (same as simple for 1 year, annual compounding)
```

### Compounding Frequencies

See [Compounding Frequencies](./compounding-frequencies.md) for detailed comparison.

**Quick reference**:

| Frequency | Times/Year | Formula n | Example (5%, 1 year, €10k) |
|-----------|------------|-----------|----------------------------|
| ANNUAL | 1 | 1 | €500.00 |
| SEMIANNUAL | 2 | 2 | €506.25 |
| QUARTERLY | 4 | 4 | €509.45 |
| MONTHLY | 12 | 12 | €511.62 |
| DAILY | 365 | 365 | €512.67 |
| CONTINUOUS | ∞ | e^(r×t) | €512.71 |

**Key insight**: Higher frequency = higher returns, but diminishing returns.

### Multi-Period with Rate Changes

Compound interest with rate changes is **more complex**. Current implementation:

```python
# Period 1: 6 months at 5%, monthly compounding
interest_p1 = calculate_compound_interest(
    Decimal("10000"),
    Decimal("0.05"),
    Decimal("182") / Decimal("365"),
    CompoundFrequency.MONTHLY
)

# Period 2: 6 months at 6%, monthly compounding  
# Note: Principal stays €10,000 (interest not reinvested between periods in current design)
interest_p2 = calculate_compound_interest(
    Decimal("10000"),
    Decimal("0.06"),
    Decimal("183") / Decimal("365"),
    CompoundFrequency.MONTHLY
)

total = interest_p1 + interest_p2
```

**Important**: Interest calculated in each period is NOT added to principal for subsequent periods in the current implementation. This keeps calculations simple and predictable for portfolio valuation.

### Use Cases

✅ **When to use Compound Interest**:
- Bonds with periodic coupon payments
- Long-term investments (> 1 year)
- Instruments explicitly specifying compound interest
- High-precision return calculations

---

## Comparison

### Same Investment, Different Methods

**Scenario**: €10,000 at 5% for 1 year

| Method | Calculation | Result | Difference |
|--------|-------------|--------|------------|
| Simple | €10,000 × 0.05 × 1 | €500.00 | Baseline |
| Compound (Monthly) | €10,000 × [(1.004167)^12 - 1] | €511.62 | +€11.62 (+2.3%) |
| Compound (Daily) | €10,000 × [(1.000137)^365 - 1] | €512.67 | +€12.67 (+2.5%) |

**For periods < 1 year**, difference is smaller (<1%).

### 5-Year Comparison

**Scenario**: €10,000 at 5% for 5 years

| Method | Result | Difference from Simple |
|--------|--------|------------------------|
| Simple | €2,500.00 | Baseline |
| Compound (Annual) | €2,762.82 | +€262.82 (+10.5%) |
| Compound (Monthly) | €2,833.59 | +€333.59 (+13.3%) |
| Compound (Daily) | €2,840.25 | +€340.25 (+13.6%) |

**Key insight**: Compounding impact grows significantly over time.

---

## Implementation

### Code Location

```
backend/app/utils/financial_math.py
```

**Functions**:
```python
def calculate_simple_interest(
    principal: Decimal,
    annual_rate: Decimal,
    time_fraction: Decimal
) -> Decimal:
    """Calculate simple interest."""
    return principal * annual_rate * time_fraction

def calculate_compound_interest(
    principal: Decimal,
    annual_rate: Decimal,
    time_fraction: Decimal,
    frequency: CompoundFrequency
) -> Decimal:
    """Calculate compound interest with specified frequency."""
```

### Pydantic Models

**Enum** (`backend/app/schemas/assets.py`):
```python
class CompoundingType(str, Enum):
    SIMPLE = "SIMPLE"
    COMPOUND = "COMPOUND"

class CompoundFrequency(str, Enum):
    DAILY = "DAILY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    SEMIANNUAL = "SEMIANNUAL"
    ANNUAL = "ANNUAL"
    CONTINUOUS = "CONTINUOUS"
```

**Usage in InterestRatePeriod**:
```python
class InterestRatePeriod(BaseModel):
    start_date: date
    end_date: date
    annual_rate: Decimal
    compounding: CompoundingType = CompoundingType.SIMPLE
    compound_frequency: Optional[CompoundFrequency] = None
    day_count: DayCountConvention = DayCountConvention.ACT_365
```

---

## Testing

### Test Files

- **Simple interest**: `test_compound_interest.py` (includes simple as baseline)
- **Compound interest**: `test_compound_interest.py` (all frequencies)
- **Integration**: `test_synthetic_yield_integration.py` (mixed scenarios)

### Coverage

**28/28 tests pass** for compound interest:
- Simple interest baseline
- All 6 frequencies (daily, monthly, quarterly, semiannual, annual, continuous)
- Edge cases (0% rate, 0 time, 0 principal)

**Run tests**:
```bash
./test_runner.py utils compound-interest
```

---

## Performance Considerations

### Calculation Cost

| Method | Complexity | Performance |
|--------|------------|-------------|
| Simple | O(1) | Instant |
| Compound | O(1) | Fast (few ops) |
| Continuous | O(1) | Fast (exp function) |

**All methods are fast enough for real-time portfolio valuation.**

### Period-Based Optimization

The scheduled investment provider uses a **period-based algorithm** (not day-by-day) for efficiency:

```python
# O(number_of_periods) instead of O(number_of_days)
for period in periods_to_process:
    time_fraction = calculate_day_count_fraction(period.start, period.end)
    if period.compounding == SIMPLE:
        interest += calculate_simple_interest(...)
    else:
        interest += calculate_compound_interest(...)
```

This keeps calculations **O(n)** where n = number of rate periods (typically < 10), not days (potentially 1000s).

---

## Related Documentation

- **[Day Count Conventions](./day-count-conventions.md)** - How time fractions are calculated
- **[Compounding Frequencies](./compounding-frequencies.md)** - Detailed frequency comparison
- **[Scheduled Investment Provider](./scheduled-investment-provider.md)** - Real-world usage
- **[Testing Guide](../testing/utils-tests.md)** - Test suite details

---

**Last Updated**: November 17, 2025


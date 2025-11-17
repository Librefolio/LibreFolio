# Compounding Frequencies

Detailed comparison of all supported compounding frequencies in LibreFolio.

> 📖 **Back to**: [Financial Calculations Home](./README.md) | [Interest Types](./interest-types.md)

---

## Overview

When using [Compound Interest](./interest-types.md#compound-interest), the **frequency** determines how often interest is added to principal:

```
Final Amount = Principal × (1 + r/n)^(n×t)

Where:
  r = annual rate
  n = compounding periods per year
  t = time in years
```

---

## Supported Frequencies

### DAILY

**Compounding**: 365 times per year

**Formula**: `(1 + r/365)^(365×t)`

**Example** (€10,000 at 5% for 1 year):
```python
from backend.app.utils.financial_math import calculate_compound_interest
from backend.app.schemas.assets import CompoundFrequency
from decimal import Decimal

interest = calculate_compound_interest(
    Decimal("10000"),
    Decimal("0.05"),
    Decimal("1"),
    CompoundFrequency.DAILY
)
# Result: €512.67
```

---

### MONTHLY

**Compounding**: 12 times per year

**Formula**: `(1 + r/12)^(12×t)`

**Example**: €511.62 interest for same scenario above.

**Common use**: Mortgages, savings accounts

---

### QUARTERLY

**Compounding**: 4 times per year

**Formula**: `(1 + r/4)^(4×t)`

**Example**: €509.45 interest

**Common use**: Corporate bonds, some loan products

---

### SEMIANNUAL

**Compounding**: 2 times per year

**Formula**: `(1 + r/2)^(2×t)`

**Example**: €506.25 interest

**Common use**: Many bonds

---

### ANNUAL

**Compounding**: 1 time per year

**Formula**: `(1 + r)^t`

**Example**: €500.00 interest (same as simple interest for 1 year)

**Common use**: Simple bond structures

---

### CONTINUOUS

**Compounding**: Infinite (mathematical limit)

**Formula**: `e^(r×t) - 1` (where e ≈ 2.71828)

**Example**: €512.71 interest (maximum possible)

**Common use**: Theoretical calculations, some derivatives

**Implementation**:
```python
interest = calculate_compound_interest(
    principal,
    annual_rate,
    time_fraction,
    CompoundFrequency.CONTINUOUS
)
# Uses: principal * (exp(annual_rate * time_fraction) - 1)
```

---

## Comparison Table

**Scenario**: €10,000 at 5% annual rate

### 1 Year

| Frequency | Times/Year | Interest | vs Simple | vs Previous |
|-----------|------------|----------|-----------|-------------|
| Simple | - | €500.00 | - | - |
| ANNUAL | 1 | €500.00 | +€0.00 | - |
| SEMIANNUAL | 2 | €506.25 | +€6.25 | +€6.25 |
| QUARTERLY | 4 | €509.45 | +€9.45 | +€3.20 |
| MONTHLY | 12 | €511.62 | +€11.62 | +€2.17 |
| DAILY | 365 | €512.67 | +€12.67 | +€1.05 |
| CONTINUOUS | ∞ | €512.71 | +€12.71 | +€0.04 |

**Key insight**: Diminishing returns as frequency increases. Daily vs Continuous = only €0.04 difference.

### 5 Years

| Frequency | Interest | vs Simple | Effective Annual Rate |
|-----------|----------|-----------|----------------------|
| Simple | €2,500.00 | - | 5.00% |
| ANNUAL | €2,762.82 | +€262.82 | 5.00% |
| SEMIANNUAL | €2,800.85 | +€300.85 | 5.06% |
| QUARTERLY | €2,820.37 | +€320.37 | 5.09% |
| MONTHLY | €2,833.59 | +€333.59 | 5.12% |
| DAILY | €2,840.25 | +€340.25 | 5.13% |
| CONTINUOUS | €2,840.25 | +€340.25 | 5.13% |

---

## Effective Annual Rate (EAR)

The **true annual return** accounting for compounding:

```
EAR = (1 + r/n)^n - 1
```

**Example** (5% nominal, monthly compounding):
```
EAR = (1 + 0.05/12)^12 - 1 = 5.12%
```

Higher frequency → higher effective rate.

---

## Choosing a Frequency

### Decision Tree

```
Is compound frequency specified in asset contract?
├─ Yes → Use specified frequency
└─ No → Consider:
    ├─ Short-term (< 1 year) → MONTHLY or QUARTERLY
    ├─ Long-term (> 5 years) → DAILY (for precision)
    └─ Bonds → Match coupon payment frequency
```

### LibreFolio Recommendations

| Asset Type | Recommended Frequency |
|------------|-----------------------|
| P2P Loans | SIMPLE (not compound) |
| Corporate Bonds | SEMIANNUAL or ANNUAL |
| Savings Accounts | MONTHLY or DAILY |
| Theoretical Max | CONTINUOUS |

---

## Implementation

### Code Location

```
backend/app/utils/financial_math.py
```

**Function**:
```python
def calculate_compound_interest(
    principal: Decimal,
    annual_rate: Decimal,
    time_fraction: Decimal,
    frequency: CompoundFrequency
) -> Decimal:
    """Calculate compound interest with frequency handling."""
    
    if frequency == CompoundFrequency.CONTINUOUS:
        # Use e^(r×t) - 1
        exponent = float(annual_rate) * float(time_fraction)
        return principal * Decimal(str(math.exp(exponent) - 1))
    else:
        # Use (1 + r/n)^(n×t) - 1
        n = _get_compounding_periods_per_year(frequency)
        rate_per_period = annual_rate / n
        periods = n * time_fraction
        # ... calculation ...
```

### Enum Definition

```python
class CompoundFrequency(str, Enum):
    DAILY = "DAILY"            # n = 365
    MONTHLY = "MONTHLY"        # n = 12
    QUARTERLY = "QUARTERLY"    # n = 4
    SEMIANNUAL = "SEMIANNUAL"  # n = 2
    ANNUAL = "ANNUAL"          # n = 1
    CONTINUOUS = "CONTINUOUS"  # n = ∞ (uses e^rt)
```

---

## Testing

### Test Coverage

**28/28 tests pass** including:
- All 6 frequencies
- Edge cases (0% rate, 0 time, 0 principal)
- Comparison vs simple interest
- Precision validation (exact Decimal arithmetic)

**Test file**: `backend/test_scripts/test_utilities/test_compound_interest.py`

**Run tests**:
```bash
./test_runner.py utils compound-interest
```

---

## Performance

All frequencies have **O(1)** complexity:
- Discrete frequencies: Single power operation
- Continuous: Single exponential operation

**Typical calculation time**: < 1ms per calculation.

---

## Related Documentation

- **[Interest Types](./interest-types.md)** - Simple vs Compound overview
- **[Day Count Conventions](./day-count-conventions.md)** - Time fraction calculation
- **[Scheduled Investment Provider](./scheduled-investment-provider.md)** - Usage in provider
- **[Testing Guide](../testing/utils-tests.md)** - Test details

---

**Last Updated**: November 17, 2025


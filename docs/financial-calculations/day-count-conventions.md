# Day Count Conventions

Day count conventions define how to calculate time fractions for interest calculations.

> 📖 **Back to**: [Financial Calculations Home](./README.md)

---

## Overview

When calculating interest, we need to convert a date range into a **time fraction** (years):

```
Interest = Principal × Annual Rate × Time Fraction
```

Different conventions calculate time fractions differently, leading to small variations in results.

---

## Supported Conventions

### ACT/365 (Actual/365)

**Formula**: `time_fraction = actual_days / 365`

**Used for**: Most LibreFolio calculations (default for scheduled investments)

**Characteristics**:
- Simple and intuitive
- Fair to both parties (no bias)
- Standard in European markets
- Sufficient accuracy for portfolio valuation

**Example**:
```
Period: January 1 to March 31 = 90 actual days
Time fraction = 90 / 365 = 0.246575...

Principal: €10,000
Annual rate: 5%
Interest = €10,000 × 0.05 × 0.246575 = €123.29
```

**Implementation**:
```python
from backend.app.utils.financial_math import calculate_day_count_fraction
from backend.app.schemas.assets import DayCountConvention
from datetime import date

fraction = calculate_day_count_fraction(
    start_date=date(2025, 1, 1),
    end_date=date(2025, 3, 31),
    convention=DayCountConvention.ACT_365
)
# Result: Decimal('0.246575342465753424657534246575')
```

---

### ACT/360 (Actual/360)

**Formula**: `time_fraction = actual_days / 360`

**Used for**: US Treasury Bills, commercial paper

**Characteristics**:
- Results in ~1.4% MORE interest than ACT/365
- Favors lenders (360 < 365)
- Common in US money markets

**Example**:
```
Period: 90 days
ACT/365: 90 / 365 = 0.2466 → Interest: €123.29
ACT/360: 90 / 360 = 0.2500 → Interest: €125.00
Difference: +€1.71 (+1.4%)
```

**When to use**: Only if explicitly required by instrument specifications (e.g., specific bonds).

---

### ACT/ACT (Actual/Actual)

**Formula**: Sum of `actual_days_in_year / days_in_year` for each calendar year

**Used for**: US Treasury bonds, precise calculations spanning multiple years

**Characteristics**:
- Most accurate for multi-year periods
- Accounts for leap years correctly
- More complex to calculate

**Example**:
```
Period: January 1, 2024 to January 1, 2025

2024 (leap year): 366 days
Days in period: 366
Time fraction: 366 / 366 = 1.0000

Total: 1.0000 years
```

**Multi-year example**:
```
Period: January 1, 2023 to January 1, 2025

2023 (365 days): 365 / 365 = 1.0000
2024 (366 days): 366 / 366 = 1.0000
Total: 2.0000 years (exact)
```

**Implementation**:
```python
fraction = calculate_day_count_fraction(
    start_date=date(2023, 1, 1),
    end_date=date(2025, 1, 1),
    convention=DayCountConvention.ACT_ACT
)
# Result: Decimal('2.0') (exact 2 years)
```

---

### 30/360 (Thirty/360)

**Formula**: Assumes 30 days per month and 360 days per year

```python
days = 360 * (year2 - year1) + 30 * (month2 - month1) + (day2 - day1)
time_fraction = days / 360
```

**Used for**: Corporate bonds, mortgages

**Characteristics**:
- Predictable and simple
- Ignores actual calendar differences
- Can be less accurate for specific dates

**Example**:
```
Period: January 31 to February 28 (28 actual days)

30/360 calculation:
  Days = 30 * (2 - 1) + (28 - 31) = 30 - 3 = 27 days
  Time fraction = 27 / 360 = 0.0750

ACT/365 calculation:
  Days = 28
  Time fraction = 28 / 365 = 0.0767

Difference: -2.3%
```

**When to use**: Only for specific bond instruments that require this convention.

---

## Choosing a Convention

### Decision Tree

```
Are you valuing a scheduled investment (loan/bond)?
├─ Yes → Check asset specifications
│  ├─ Specified in contract → Use specified convention
│  └─ Not specified → Use ACT/365 (default)
└─ No → Use ACT/365 (LibreFolio default)

Is it a US Treasury security?
├─ Bill → ACT/360
└─ Bond → ACT/ACT

Is it a corporate bond?
└─ Often 30/360 (check prospectus)
```

### LibreFolio Default

**We use ACT/365 as the default** because:
1. ✅ Simple and intuitive
2. ✅ Fair (no bias towards lender or borrower)
3. ✅ Standard in European markets
4. ✅ Sufficient accuracy (<2% difference vs alternatives)

---

## Implementation Details

### Code Location

```
backend/app/utils/financial_math.py
```

**Main function**:
```python
def calculate_day_count_fraction(
    start_date: date,
    end_date: date,
    convention: DayCountConvention
) -> Decimal:
    """Calculate time fraction between two dates."""
```

**Enum definition** (`backend/app/schemas/assets.py`):
```python
class DayCountConvention(str, Enum):
    ACT_365 = "ACT/365"
    ACT_360 = "ACT/360"
    ACT_ACT = "ACT/ACT"
    THIRTY_360 = "30/360"
```

### Testing

**Test file**: `backend/test_scripts/test_utilities/test_day_count_conventions.py`

**Coverage**: 20/20 tests pass
- ACT/365: 30 days, 1 year, multi-year
- ACT/360: 30 days, 90 days, 360 days
- ACT/ACT: non-leap, leap, cross-leap years
- 30/360: same month, consecutive months, end-of-month cases

**Run tests**:
```bash
./test_runner.py utils day-count
```

---

## Edge Cases

### Leap Years

**ACT/ACT** handles leap years correctly:
```python
# 2024 is leap year (366 days)
fraction = calculate_day_count_fraction(
    date(2024, 1, 1),
    date(2024, 12, 31),
    DayCountConvention.ACT_ACT
)
# Result: 365 / 366 = 0.997268...
```

**ACT/365** ignores leap years:
```python
# Always divides by 365
fraction = calculate_day_count_fraction(
    date(2024, 1, 1),
    date(2024, 12, 31),
    DayCountConvention.ACT_365
)
# Result: 365 / 365 = 1.0
```

### Same Day

All conventions return 0 for same-day periods:
```python
fraction = calculate_day_count_fraction(
    date(2025, 1, 1),
    date(2025, 1, 1),
    convention  # Any convention
)
# Result: Decimal('0')
```

### End-of-Month (30/360)

**30/360** has special handling for month-end dates:
```python
# January 31 to February 28
# Treats as: day 30 to day 28 = -2 days? No, special rules apply
# LibreFolio uses standard 30/360 US (NASD) convention
```

---

## Performance Impact

All conventions are **O(1)** except ACT/ACT which is **O(years)** due to year-by-year iteration.

**For typical portfolio use cases** (< 10 years), performance difference is negligible.

---

## Related Documentation

- **[Interest Types](./interest-types.md)** - How time fractions are used in interest calculations
- **[Scheduled Investment Provider](./scheduled-investment-provider.md)** - Real-world usage in provider
- **[Testing Guide](../testing/utils-tests.md)** - Day count test suite details

---

**Last Updated**: November 17, 2025


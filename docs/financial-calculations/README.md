# Financial Calculations

Complete guide to financial calculations and mathematical reasoning in LibreFolio.

> 🎯 **Related Documentation**: [Testing Guide](../testing/README.md) | [Database Schema](../database-schema.md) | [Asset Providers](../assets/README.md)

---

## 📚 Table of Contents

This section documents all financial mathematics used in LibreFolio for portfolio valuation and analytics.

### Core Concepts

- **[Day Count Conventions](./day-count-conventions.md)** - How we measure time fractions for interest calculations
- **[Interest Types](./interest-types.md)** - Simple vs Compound interest models
- **[Compounding Frequencies](./compounding-frequencies.md)** - Daily, Monthly, Quarterly, etc.
- **[Scheduled Investment Provider](./scheduled-investment-provider.md)** - Synthetic yield calculation for loans and bonds

### Quick Reference

| Topic | What It Does | When To Use |
|-------|--------------|-------------|
| [Day Count](./day-count-conventions.md) | Calculates time fractions (e.g., 90 days = 0.2466 years) | All interest calculations |
| [Simple Interest](./interest-types.md#simple-interest) | Linear interest accrual | P2P loans, short-term instruments |
| [Compound Interest](./interest-types.md#compound-interest) | Exponential growth with reinvestment | Bonds, long-term investments |
| [Scheduled Investment](./scheduled-investment-provider.md) | Runtime valuation without DB storage | Crowdfunding loans, fixed-income assets |

---

## 🎯 Design Philosophy

### Estimates vs Reality

**Portfolio valuations are estimates**. They help you track performance and make decisions, but:

```
True Profit = Sell Proceeds - Buy Cost
```

Everything else (accrued interest, market value, unrealized P/L) is **estimative**.

### Simplicity Over Precision

> **Don't split hairs for estimates**

We prioritize:
1. **Simplicity** - Easy to understand and verify
2. **Sufficient accuracy** - Good enough for decision-making  
3. **No over-engineering** - Sub-percent differences don't matter

**Example**: Using ACT/365 vs ACT/360 gives ~1.4% difference. Not worth the complexity for portfolio valuation.

---

## 📊 Implementation Overview

### Supported Features

✅ **Day Count Conventions**
- ACT/365 (actual days / 365)
- ACT/360 (actual days / 360)
- ACT/ACT (actual days / actual year days)
- 30/360 (30 days per month, 360 days per year)

✅ **Interest Types**
- Simple interest (linear)
- Compound interest (exponential)

✅ **Compounding Frequencies**
- DAILY, MONTHLY, QUARTERLY, SEMIANNUAL, ANNUAL, CONTINUOUS

✅ **Scheduled Investments**
- Multi-period schedules with rate changes
- Grace periods after maturity
- Late interest penalties
- On-demand calculation (no DB storage)

### Code Structure

```
backend/app/
├── utils/
│   └── financial_math.py          # Core calculation functions
├── schemas/
│   └── assets.py                   # Pydantic models (InterestRatePeriod, etc.)
└── services/asset_source_providers/
    └── scheduled_investment.py     # Provider implementation
```

**Tests**: See [Testing Guide](../testing/README.md)

---

## 🔢 Example Calculations

### Simple Interest (90 days at 5%)

```python
from backend.app.utils.financial_math import calculate_simple_interest
from decimal import Decimal

principal = Decimal("10000")
annual_rate = Decimal("0.05")
time_fraction = Decimal("90") / Decimal("365")  # ACT/365

interest = calculate_simple_interest(principal, annual_rate, time_fraction)
# Result: €123.29
```

### Compound Interest (1 year at 5%, monthly)

```python
from backend.app.utils.financial_math import calculate_compound_interest
from backend.app.schemas.assets import CompoundFrequency

interest = calculate_compound_interest(
    principal=Decimal("10000"),
    annual_rate=Decimal("0.05"),
    time_fraction=Decimal("1"),
    frequency=CompoundFrequency.MONTHLY
)
# Result: €511.62
```

### Scheduled Investment Valuation

See [Scheduled Investment Provider](./scheduled-investment-provider.md) for complete examples.

---

## 📖 Deep Dive Documentation

1. **[Day Count Conventions](./day-count-conventions.md)**
   - ACT/365, ACT/360, ACT/ACT, 30/360
   - When to use each convention
   - Implementation details and edge cases

2. **[Interest Types](./interest-types.md)**
   - Simple vs Compound interest
   - Mathematical formulas
   - Performance comparison

3. **[Compounding Frequencies](./compounding-frequencies.md)**
   - All supported frequencies
   - Continuous compounding
   - Impact on returns

4. **[Scheduled Investment Provider](./scheduled-investment-provider.md)**
   - Provider architecture
   - JSON schedule format
   - Grace periods and late interest
   - Period-based calculation algorithm
   - Testing with `_transaction_override`

---

## 🧪 Testing

All financial math functions have comprehensive test coverage. See:

- [Testing Guide](../testing/README.md)
- [Utility Tests](../testing/utils-tests.md) - Day count, compound interest
- [Synthetic Yield E2E](../testing/synthetic-yield-e2e.md) - Integration scenarios

**Run tests**:
```bash
./test_runner.py utils financial-math
./test_runner.py services synthetic-yield
./test_runner.py services synthetic-yield-integration
```

---

## 🔗 Related Documentation

- **[Database Schema](../database-schema.md)** - Asset and Transaction models
- **[Asset Providers](../assets/README.md)** - Provider system architecture
- **[Testing Guide](../testing/README.md)** - How to test financial calculations
- **[API Development](../api-development-guide.md)** - REST API integration

---

**Last Updated**: November 17, 2025


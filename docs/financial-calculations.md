# Financial Calculations

Complete guide to financial calculations and mathematical reasoning in LibreFolio.

> 🎯 **Quick Links**: [FX System](./fx-implementation.md) | [Asset Sources](./asset-sources/overview.md) | [Database Schema](./database-schema.md)

---

## 📋 What Are Financial Calculations?

LibreFolio performs various **financial calculations** for portfolio management:

- 💰 **Accrued interest** - Calculate interest on loans and bonds
- 💱 **Currency conversion** - Multi-currency portfolio support
- 📊 **Performance metrics** - ROI, P/L, duration-weighted returns
- 🔢 **Precision handling** - Numeric truncation and rounding

All calculations prioritize **simplicity** and **sufficient accuracy** for portfolio valuation.

---

## ⚠️ Important: Estimates vs Reality

### Fundamental Principle

**Portfolio valuations are estimates**. They help you:
- ✅ Track portfolio performance over time
- ✅ Make informed investment decisions
- ✅ Compare assets and strategies

**True profits**:
```
True Profit = Sell Proceeds - Buy Cost
```

Everything else (accrued interest, market value, unrealized P/L) is **estimative**.

### Design Philosophy

> **Don't split hairs for estimates**

We prioritize:
1. **Simplicity** - Easy to understand and verify
2. **Sufficient accuracy** - Good enough for decision-making
3. **No over-engineering** - Sub-percent differences don't matter

For example: Using ACT/365 vs ACT/360 day-count gives ~1.4% difference. Not worth the complexity for portfolio valuation.

---

## 📐 Day-Count Conventions

### ACT/365 (Implemented)

**Formula**: `time_fraction = actual_days / 365`

**Used for**: Interest accrual calculations in [Synthetic Yield Source](./asset-sources/synthetic-yield.md)

#### Why ACT/365?

| Reason | Description |
|--------|-------------|
| **Simplicity** | Intuitive: just count actual days |
| **Accuracy** | Sufficient for portfolio valuation |
| **Standard** | Used in Europe and many markets |
| **Fair** | Doesn't favor lender or borrower |

#### Example Calculation

```
Period: January 1 to March 31 = 90 actual days
Year fraction = 90 / 365 = 0.2466

Principal: €10,000
Annual rate: 5%
Interest = €10,000 × 0.05 × 0.2466 = €123.29
```

---

### Other Conventions (Not Implemented)

We **do not implement** ACT/360 or 30/360. Here's why:

#### ACT/360 (US Treasury Bills)

- **Formula**: `actual_days / 360`
- **Effect**: ~1.4% more interest than ACT/365
- **Example**: 90 days, 5%, €10,000
  - ACT/365: €123.29
  - ACT/360: €125.00 ← **+€1.71 (1.4% more)**

#### 30/360 (Corporate Bonds)

- **Formula**: Assumes 30 days/month, 360 days/year
- **Effect**: Predictable but less accurate
- **Example**: 31 actual days
  - ACT/365: 0.0849 years
  - 30/360: 0.0833 years ← **-1.9% less**

#### Why Not Implement?

**Differences <2% don't justify the complexity** for portfolio valuation.

Remember: **True profits = sell - buy**. Day-count only affects estimated valuations.

📖 **Learn more**: [Asset Sources Development](./asset-sources/development.md)

---

## 💰 Accrued Interest (Loans & Bonds)

### What is Accrued Interest?

For **SCHEDULED_YIELD** assets (P2P loans, bonds), the value grows over time as interest accrues:

```
Asset Value = Face Value + Accrued Interest
```

**Implementation**: [Synthetic Yield Source](./asset-sources/synthetic-yield.md)  
**Code**: `backend/app/services/asset_sources/synthetic_yield_source.py`

---

### SIMPLE Interest (Implemented)

**Formula**:
```
Accrued Interest = Principal × Σ(Rate × Time Fraction)
```

#### Calculation Method

We calculate **day by day** using ACT/365:

```python
total_interest = 0
for each_day in period:
    active_rate = find_rate_for_day(each_day, schedule)
    days_fraction = 1 / 365
    daily_interest = principal × active_rate × days_fraction
    total_interest += daily_interest
```

#### Example

| Parameter | Value |
|-----------|-------|
| Principal | €10,000 |
| Annual Rate | 5% |
| Period | 90 days |

**Calculation**:
```
Daily rate = 0.05 / 365 = 0.0001370
Daily interest = €10,000 × 0.0001370 = €1.37
Total (90 days) = €1.37 × 90 = €123.29
```

---

### COMPOUND Interest (Not Implemented)

**Why we don't implement compound interest**:

| Reason | Impact |
|--------|--------|
| **Complexity** | Requires frequency management (daily/monthly/quarterly) |
| **Rare** | Most P2P loans use simple interest |
| **Minimal difference** | <1% for periods <1 year |

#### Comparison

**Example**: €10,000, 5% rate, 1 year

| Method | Calculation | Result | Difference |
|--------|-------------|--------|------------|
| **SIMPLE** | €10,000 × 0.05 | €500.00 | Baseline |
| **COMPOUND** (daily) | €10,000 × (1 + 0.05/365)^365 - €10,000 | €512.67 | +€12.67 (+2.5%) |

For periods <1 year: **Difference is negligible** (<1%).

📖 **See also**: [Multi-Rate Schedules](#interest-schedule-handling) below

---

## 📅 Interest Schedule Handling

### Multi-Rate Schedules

Assets can have **different rates in different periods**.

**Related**: [Database Schema](./database-schema.md) - Asset model `interest_schedule` field

#### Example Schedule

```json
{
  "interest_schedule": [
    {"start_date": "2024-01-01", "end_date": "2024-06-30", "rate": "0.05"},
    {"start_date": "2024-07-01", "end_date": "2024-12-31", "rate": "0.06"},
    {"start_date": "2025-01-01", "end_date": null, "rate": "0.055"}
  ]
}
```

#### Calculation Logic

1. For each day, find the **active rate** from schedule
2. Calculate interest with that rate
3. Sum day by day

---

### Maturity + Grace Period + Late Interest

**Loan lifecycle**:

| Phase | Duration | Rate Used |
|-------|----------|-----------|
| **Active** | Until maturity date | Rate from schedule |
| **Grace** | maturity_date + grace_period_days | Rate from schedule |
| **Late** | After grace, if not repaid | `late_interest.rate` |

#### Example Timeline

```
Maturity date: 2024-12-31
Grace period: 30 days
Normal rate: 5%
Late rate: 10%

Timeline:
├─ 2024-01-01 to 2024-12-31: Active (5% rate)
├─ 2025-01-01 to 2025-01-30: Grace period (still 5%)
└─ 2025-01-31 onwards: Late (10% rate if not repaid)
```

**Note**: System assumes late rate after grace for prudence (doesn't check if loan was actually repaid).

---

## 💱 Currency Conversion

### FX Integration

**Principle**: All asset values must be converted to **portfolio base currency** for aggregations.

**Related documentation**:
- 📖 [FX Implementation](./fx-implementation.md) - Multi-provider system
- 📖 [FX Architecture](./fx/architecture.md) - Design details
- 📖 [FX API Reference](./fx/api-reference.md) - Conversion endpoints

### Conversion Flow

```python
# Step 1: Calculate value in asset's native currency
value_native = calculate_asset_value(asset)  # e.g., $1,234 USD

# Step 2: Convert to portfolio base currency
value_base = fx_convert(
    amount=value_native,
    from_currency=asset.currency,      # USD
    to_currency=portfolio.base_currency,  # EUR
    date=valuation_date
)
# Result: €1,132 EUR (at 0.918 EUR/USD rate)
```

### Backward-Fill Strategy

**What if FX rate is missing for valuation_date?**

✅ **Solution**: Use most recent available rate (backward-fill)

| Feature | Description |
|---------|-------------|
| **Support** | Unlimited backward-fill |
| **Warning** | Logged if rate is > N days old |
| **Use case** | Weekends, holidays, new currencies |

**Example**:
```
Valuation date: Saturday 2025-01-04
Last FX rate: Friday 2025-01-03
→ Use Friday's rate (1 day back)
```

📖 **Learn more**: [FX Implementation Guide](./fx-implementation.md)

---

## 📊 Performance Metrics

**Implementation**: See Step 06 (Runtime Analysis) for FIFO-based calculations

### Simple ROI

**Return on Investment** measures total gain/loss relative to investment.

**Formula**:
```
ROI = (Current Value + Realized Cashflows - Total Invested) / Total Invested × 100%
```

#### Example

| Item | Amount |
|------|--------|
| Total Invested | €10,000 |
| Current Value (unrealized) | €11,500 |
| Sold Assets (realized) | €1,000 |

**Calculation**:
```
ROI = (11,500 + 1,000 - 10,000) / 10,000 = 0.25 = 25%
```

---

### Duration-Weighted ROI (DW-ROI)

**Purpose**: Account for investment duration (time-weighted returns).

**Why it matters**: 25% ROI in 1 month is **much better** than 25% in 1 year.

#### Formula (Simplified)

```
DW-ROI = weighted_average(per_lot_ROI)

For each investment lot:
  lot_ROI = (exit_value - entry_value) / entry_value
  lot_weight = time_held / total_time
```

**Implementation**: Step 06 uses FIFO lot tracking for accurate time-weighting.

---

### Unrealized vs Realized P/L

**Profit & Loss** can be split into two categories:

| Type | Formula | When Recognized |
|------|---------|-----------------|
| **Unrealized** | Market Value - Purchase Cost | Asset still held |
| **Realized** | Sell Proceeds - Purchase Cost | Asset sold |
| **Total** | Unrealized + Realized | Overall performance |

#### Example

```
Bought 100 shares at €50 = €5,000 (cost basis)
Current price: €60 per share = €6,000 (market value)
Sold 30 shares at €65 = €1,950 (proceeds)

Unrealized P/L (70 shares): (70 × €60) - (70 × €50) = €700
Realized P/L (30 shares): €1,950 - (30 × €50) = €450
Total P/L: €700 + €450 = €1,150
```

---

## 🔢 Numeric Precision

**Related**: [Database Schema](./database-schema.md) - Column definitions

### Database Column Precision

Different data types require different precision levels:

| Column Type | Precision | Example | Why? |
|-------------|-----------|---------|------|
| **FX Rates** | `Numeric(24, 10)` | 1.0644252000 | Cross-rate precision |
| **Prices** | `Numeric(18, 6)` | 123456.789012 | Sufficient for stocks |
| **Amounts** | `Numeric(18, 6)` | 10000.50 | Standard currency |

#### Why These Precisions?

**FX Rates (24, 10)**:
- 10 decimals needed for cross-currency calculations
- Prevents compounding rounding errors
- Example: EUR → USD → GBP requires high precision

**Asset Prices (18, 6)**:
- 6 decimals sufficient (stocks rarely < $0.01)
- Handles high-value assets (up to 12 digits before decimal)
- Balance between accuracy and storage

---

### Truncation Strategy

**Problem**: API returns 1.012345678901234, DB stores 1.0123456789 (10 decimals)

**Solution**: Truncate **before** comparing to avoid false updates

```python
# Step 1: Fetch from API
api_value = 1.012345678901234

# Step 2: Truncate to DB precision
new_value = truncate(api_value, precision=10)  # → 1.0123456789

# Step 3: Compare with existing DB value
db_value = 1.0123456789
if new_value == db_value:
    skip_update()  # ✅ No DB write (values are identical)
```

**Benefits**:
- ✅ Prevents spurious updates
- ✅ Reduces DB writes
- ✅ Maintains data consistency

**Testing**: `backend/test_scripts/test_db/test_numeric_truncation.py`  
**Related**: [Testing Guide](./testing-guide.md) - Numeric precision tests

---

## 🧮 Future: More Complex Calculations

### FIFO Cost Basis (Step 6)

**Purpose**: Calculate realized P/L for tax reporting.

**Algorithm**:
1. Each BUY creates a lot (qty, price, date)
2. Each SELL consumes oldest lots first (FIFO)
3. Compute P/L per consumed lot
4. Track remaining inventory

**Implementation**: See Step 06 (Runtime Analysis) for details

### Tax Lot Optimization (Future)

**Methods**: FIFO, LIFO, Highest Cost First, Specific ID

**Not implemented**: Only FIFO is supported (Step 6).

**Why**: FIFO is required in many jurisdictions, other methods are nice-to-have.

---

## 📚 References

### Standards
- Day-count conventions: [ISDA documentation](https://www.isda.org/)
- ACT/365 vs ACT/360: Finance industry standards
- FIFO accounting: [IRS Publication 550](https://www.irs.gov/publications/p550)

### LibreFolio Documentation
- **FX System**:
  - [FX Implementation](./fx-implementation.md) - Multi-provider architecture
  - [FX Architecture](./fx/architecture.md) - System design
  - [FX API Reference](./fx/api-reference.md) - Endpoints and examples
  - [FX Providers](./fx/providers.md) - Available providers (ECB, FED, BOE, SNB)
- **Asset Sources**:
  - [Asset Sources Overview](./asset-sources/overview.md) - Plugin system
  - [Development Guide](./asset-sources/development.md) - Creating new sources
  - [Synthetic Yield](./asset-sources/synthetic-yield.md) - Loan valuation
- **Database**:
  - [Database Schema](./database-schema.md) - Table definitions and constraints
  - [Alembic Guide](./alembic-guide.md) - Migration management
- **Testing**:
  - [Testing Guide](./testing-guide.md) - Test organization and execution
  - [Testing Environment](./testing-environment.md) - Setup and isolation

### Related Code
- `backend/app/services/asset_sources/synthetic_yield_source.py` - Interest calculation
- `backend/app/services/fx.py` - Currency conversion
- `backend/app/db/models.py` - Numeric column definitions
- `backend/test_scripts/test_db/test_numeric_truncation.py` - Precision tests

---

## 📝 Contributing

**When adding new financial calculations**:
1. ✅ **Document reasoning** in this file
2. ✅ **Explain simplifications** - Why is this approach acceptable?
3. ✅ **Provide examples** with actual numbers
4. ✅ **Cite standards** if applicable (ISDA, IRS, etc.)
5. ✅ **Add tests** with known good values
6. ✅ **Link related docs** - Cross-reference relevant guides

**Remember**: **Estimates are estimates**. True profits = sell - buy.

Don't over-engineer for sub-percent accuracy in portfolio valuation.

---

**Last Updated**: 5 November 2025  
**Maintainer**: LibreFolio Team


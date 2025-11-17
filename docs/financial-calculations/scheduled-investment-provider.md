# Scheduled Investment Provider

Complete guide to the `ScheduledInvestmentProvider` - synthetic yield calculation for loans and bonds.

> 📖 **Back to**: [Financial Calculations Home](./README.md)

---

## Overview

The **Scheduled Investment Provider** calculates synthetic valuations for fixed-income assets **at runtime**, without storing prices in the database.

**Use cases**:
- P2P crowdfunding loans
- Corporate bonds with fixed coupons
- Any asset with predictable interest schedules

**Key features**:
- ✅ Multi-period schedules with rate changes
- ✅ Simple and Compound interest
- ✅ All day count conventions ([ACT/365, ACT/360, ACT/ACT, 30/360](./day-count-conventions.md))
- ✅ Grace periods after maturity
- ✅ Late interest penalties
- ✅ On-demand calculation (no DB storage)
- ✅ Transaction-based principal calculation

---

## Architecture

### Provider Code

**Location**: `backend/app/services/asset_source_providers/scheduled_investment.py`

**Registration**:
```python
@register_provider(AssetProviderRegistry)
class ScheduledInvestmentProvider(AssetSourceProvider):
    provider_code = "scheduled_investment"
    provider_name = "Scheduled Investment Calculator"
```

### Calculation Flow

```
1. Get Asset + Transactions from DB
   ↓
2. Calculate Principal (face_value) from Transactions
   - BUY: +amount
   - SELL: -amount
   - INTEREST (negative price): principal repayment
   ↓
3. Load Interest Schedule (JSON from Asset.interest_schedule)
   ↓
4. Calculate Value = Principal + Accrued Interest
   - Period-based algorithm (not day-by-day)
   - Handles rate changes, grace, late interest
   ↓
5. Return CurrentValueModel or HistoricalDataModel
```

---

## JSON Schedule Format

### Basic Schedule (Simple Interest)

```json
{
  "schedule": [
    {
      "start_date": "2025-01-01",
      "end_date": "2025-12-31",
      "annual_rate": 0.05,
      "compounding": "SIMPLE",
      "day_count": "ACT/365"
    }
  ]
}
```

### Multi-Period Schedule with Rate Changes

```json
{
  "schedule": [
    {
      "start_date": "2025-01-01",
      "end_date": "2025-06-30",
      "annual_rate": 0.05,
      "compounding": "SIMPLE",
      "day_count": "ACT/365"
    },
    {
      "start_date": "2025-07-01",
      "end_date": "2025-12-31",
      "annual_rate": 0.06,
      "compounding": "SIMPLE",
      "day_count": "ACT/365"
    }
  ]
}
```

### With Late Interest

```json
{
  "schedule": [
    {
      "start_date": "2025-01-01",
      "end_date": "2025-12-31",
      "annual_rate": 0.05,
      "compounding": "SIMPLE",
      "day_count": "ACT/365"
    }
  ],
  "late_interest": {
    "annual_rate": 0.12,
    "grace_period_days": 30,
    "compounding": "SIMPLE",
    "day_count": "ACT/365"
  }
}
```

### Compound Interest (Quarterly)

```json
{
  "schedule": [
    {
      "start_date": "2025-01-01",
      "end_date": "2025-12-31",
      "annual_rate": 0.04,
      "compounding": "COMPOUND",
      "compound_frequency": "QUARTERLY",
      "day_count": "ACT/365"
    }
  ]
}
```

---

## Pydantic Models

### InterestRatePeriod

```python
class InterestRatePeriod(BaseModel):
    start_date: date
    end_date: date
    annual_rate: Decimal
    compounding: CompoundingType = CompoundingType.SIMPLE
    compound_frequency: Optional[CompoundFrequency] = None
    day_count: DayCountConvention = DayCountConvention.ACT_365
```

**Validation**:
- `end_date >= start_date`
- `compound_frequency` required if `compounding == COMPOUND`
- `compound_frequency` must be None if `compounding == SIMPLE`

### LateInterestConfig

```python
class LateInterestConfig(BaseModel):
    annual_rate: Decimal
    grace_period_days: int = 0
    compounding: CompoundingType = CompoundingType.SIMPLE
    compound_frequency: Optional[CompoundFrequency] = None
    day_count: DayCountConvention = DayCountConvention.ACT_365
```

### ScheduledInvestmentSchedule

```python
class ScheduledInvestmentSchedule(BaseModel):
    schedule: List[InterestRatePeriod]
    late_interest: Optional[LateInterestConfig] = None
```

**Validation**:
- At least one period required
- Periods must be contiguous (no gaps > 1 day)
- No overlapping periods
- Auto-sorted by start_date

---

## Period-Based Calculation Algorithm

### Key Innovation

**Before** (v1 - slow):
- Iterated day-by-day from start to target_date
- O(days) complexity → 400+ days = slow + risk of infinite loops

**After** (v2 - fast):
- Processes **periods**, not days
- O(number_of_periods) complexity → typically < 10 periods = instant
- No infinite loop risk

### Algorithm Steps

```python
def _calculate_value_for_date(schedule, face_value, target_date):
    """Period-based synthetic value calculation."""
    
    # 1. Collect real scheduled periods (truncate to target_date)
    periods_to_process = []
    for period in schedule.schedule:
        if period.start_date > target_date:
            break
        eff_start = period.start_date
        eff_end = min(period.end_date, target_date)
        periods_to_process.append(period[eff_start:eff_end])
    
    # 2. Add synthetic grace period (if applicable)
    if target_date > maturity_date and schedule.late_interest:
        grace_end = maturity_date + grace_period_days
        if target_date <= grace_end:
            # Use last scheduled rate
            periods_to_process.append(
                GracePeriod(maturity+1, min(grace_end, target_date))
            )
    
    # 3. Add synthetic late period (if applicable)
    if target_date > grace_end:
        periods_to_process.append(
            LatePeriod(grace_end+1, target_date, late_rate)
        )
    
    # 4. Calculate interest for each period
    total_interest = 0
    for period in periods_to_process:
        time_fraction = calculate_day_count_fraction(
            period.start_date, period.end_date, period.day_count
        )
        if period.compounding == SIMPLE:
            interest = calculate_simple_interest(...)
        else:
            interest = calculate_compound_interest(...)
        total_interest += interest
    
    # 5. Return principal + interest
    return face_value + total_interest
```

### Grace and Late Interest Timeline

```
Timeline:
  |-------------- Schedule Period --------------|  Grace  |  Late Interest  →
  2025-01-01                          2025-12-31  +30 days  2026-01-31+

Rates:
  Period: 5% (scheduled rate)
  Grace:  5% (continues with last scheduled rate)
  Late:   12% (penalty rate from late_interest config)

Example for 2026-02-05 (36 days after maturity):
  1. Jan 1 - Dec 31: 365 days @ 5%
  2. Jan 1 - Jan 30: 30 days @ 5% (grace)
  3. Jan 31 - Feb 5: 6 days @ 12% (late)
```

---

## Principal Calculation from Transactions

The provider calculates **face_value** (current principal) from transaction history:

```python
def _calculate_face_value_from_transactions(transactions):
    face_value = Decimal("0")
    for txn in transactions:
        if txn.type == TransactionType.BUY:
            face_value += txn.quantity * txn.price
        elif txn.type == TransactionType.SELL:
            face_value -= txn.quantity * txn.price
        elif txn.type == TransactionType.INTEREST:
            if txn.price < 0:  # Principal repayment
                face_value += txn.price  # Negative reduces principal
    return face_value
```

**Examples**:
- BUY €10,000 → face_value = €10,000
- BUY €10,000, then SELL €3,000 → face_value = €7,000
- BUY €10,000, then INTEREST -€1,000 (repayment) → face_value = €9,000

---

## Testing with `_transaction_override`

For **unit tests** without DB dependency, use `_transaction_override`:

```python
params = {
    "schedule": [
        {
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
            "annual_rate": 0.05,
            "compounding": "SIMPLE",
            "day_count": "ACT/365"
        }
    ],
    "_transaction_override": [
        {
            "type": "BUY",
            "quantity": 1,
            "price": "10000",
            "trade_date": "2025-01-01"
        }
    ]
}

provider = ScheduledInvestmentProvider()
result = await provider.get_current_value("1", params)
# Result: CurrentValueModel with calculated value
```

**How it works**:
1. Provider checks for `_transaction_override` in params
2. If present, uses override transactions instead of querying DB
3. Calculates face_value from override
4. Proceeds with normal calculation

**Use cases**:
- Unit tests
- Integration tests (see `test_synthetic_yield_integration.py`)
- Pre-transaction simulations

---

## Usage Examples

### Basic Usage (from DB)

```python
from backend.app.services.asset_source_providers.scheduled_investment import ScheduledInvestmentProvider

provider = ScheduledInvestmentProvider()

# Get current value
result = await provider.get_current_value(
    identifier="123",  # asset_id
    provider_params={}  # Empty - will load from Asset.interest_schedule
)
# Returns: CurrentValueModel(value=Decimal("10547.39"), currency="EUR", ...)

# Get historical values
history = await provider.get_history_value(
    identifier="123",
    provider_params={},
    start_date=date(2025, 1, 1),
    end_date=date(2025, 12, 31)
)
# Returns: HistoricalDataModel with 365 daily prices
```

### With Override (testing)

```python
# Simulate loan without DB
params = {
    "schedule": [...],
    "_transaction_override": [
        {"type": "BUY", "quantity": 1, "price": "10000", "trade_date": "2025-01-01"}
    ]
}

value = await provider.get_current_value("1", params)
```

---

## Integration with Asset Source Manager

The provider integrates with the **AssetSourceManager**:

```python
from backend.app.services.asset_source import AssetSourceManager

# Assign provider to asset
await AssetSourceManager.assign_provider(
    asset_id=123,
    provider_code="scheduled_investment",
    provider_params=json.dumps({
        "schedule": [...],
        "late_interest": {...}
    }),
    session=session
)

# Get prices (calls provider automatically)
prices = await AssetSourceManager.get_prices(
    asset_id=123,
    start_date=date(2025, 1, 1),
    end_date=date(2025, 1, 7),
    session=session
)
# Returns 7 daily calculated values (not stored in DB)
```

---

## Testing

### Test Suites

**Unit tests** (`test_synthetic_yield.py`): 9/9 pass
- Provider param validation
- get_current_value() / get_history_value()
- _calculate_value_for_date() (private method)
- Integration with AssetSourceManager
- Verify no DB storage

**E2E Integration** (`test_synthetic_yield_integration.py`): 3/3 pass
1. **P2P Loan scenario**: Two periods + grace + late interest
2. **Bond scenario**: Quarterly compound interest
3. **Mixed scenario**: Multiple periods with SIMPLE/COMPOUND mix

**Utility tests**:
- Day count conventions: 20/20 pass
- Compound interest: 28/28 pass
- Financial math: 23/23 pass
- Pydantic schemas: 23/25 pass (2 skipped)

**Run tests**:
```bash
# All synthetic yield tests
./test_runner.py services synthetic-yield
./test_runner.py services synthetic-yield-integration

# Supporting tests
./test_runner.py utils day-count
./test_runner.py utils compound-interest
./test_runner.py utils financial-math
./test_runner.py utils scheduled-investment-schemas
```

---

## Performance

### Benchmarks

| Scenario | Periods | Days | Calculation Time |
|----------|---------|------|------------------|
| Single period | 1 | 365 | < 1ms |
| Multi-period (3 periods) | 3 | 365 | < 1ms |
| With grace + late | 3 | 400 | < 1ms |
| Historical (365 days) | 1 | 365 | < 100ms |

**Key**: Period-based algorithm is **O(periods)** not **O(days)**, making it efficient even for long date ranges.

---

## Limitations

### Current Design Choices

1. **Principal stays constant per period**
   - Interest from previous periods NOT reinvested
   - Simplifies calculations and keeps valuations predictable
   - Sufficient for portfolio valuation estimates

2. **No intra-period principal changes**
   - Partial repayments within a period not supported
   - Workaround: Split periods at repayment dates

3. **Grace period uses last scheduled rate**
   - Not a separate configurable rate
   - Design choice: grace = payment extension, not penalty yet

### Future Enhancements

Potential improvements (not currently planned):
- Intra-period principal adjustments
- Configurable grace period rate (separate from late)
- Capitalization of interest between periods (optional mode)

---

## Related Documentation

- **[Day Count Conventions](./day-count-conventions.md)** - Time fraction calculation
- **[Interest Types](./interest-types.md)** - Simple vs Compound
- **[Compounding Frequencies](./compounding-frequencies.md)** - Frequency details
- **[Testing Guide](../testing/synthetic-yield-e2e.md)** - E2E test scenarios
- **[Database Schema](../database-schema.md)** - Asset and Transaction models

---

## Code References

**Provider**: `backend/app/services/asset_source_providers/scheduled_investment.py`  
**Schemas**: `backend/app/schemas/assets.py`  
**Utils**: `backend/app/utils/financial_math.py`  
**Tests**: `backend/test_scripts/test_services/test_synthetic_yield*.py`

---

**Last Updated**: November 17, 2025


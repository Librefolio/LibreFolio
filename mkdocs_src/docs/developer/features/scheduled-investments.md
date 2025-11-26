# Scheduled Investment Provider

Complete guide to the `ScheduledInvestmentProvider` - synthetic yield calculation for loans and bonds.

> 📖 **Back to**: [Feature Guides](./index.md)

---

## Overview

The **Scheduled Investment Provider** calculates synthetic valuations for fixed-income assets with predictable cash flows, such as:

- **Crowdfunding loans** (e.g., Recrowd, Mintos, etc.)
- **Bonds** with fixed interest schedules
- **Structured investments** with tiered interest rates
- **P2P lending** products

Unlike market-based providers (e.g., yfinance), this provider **calculates values at runtime** based on:
- Face value (principal)
- Interest rate schedule
- Maturity date
- Grace period and late interest terms

**Key Feature**: Values are calculated on-demand and **NOT stored in the database**, ensuring they always reflect the latest schedule parameters.

---

## Use Cases

### 1. Crowdfunding Loans
Track investments from platforms like Recrowd, Mintos, or Bondora with:
- Variable interest rates over time
- Late payment penalties
- Grace periods after maturity

### 2. Fixed-Rate Bonds
Value bonds with:
- Fixed coupon rates
- Known maturity dates
- Simple interest calculations

### 3. Structured Products
Handle investments with:
- Tiered interest schedules
- Rate changes based on time periods
- Maturity-dependent returns

---

## Technical Details

### Day Count Convention
**ACT/365** (Actual/365 Fixed)
- Formula: `(actual_days) / 365`
- Standard in many European markets
- Simple and intuitive calculation

### Interest Type
**SIMPLE Interest** (not compound)
- Formula: `interest = principal × rate × time_fraction`
- Day-by-day accrual for accurate rate change handling
- Matches most P2P lending platforms

### Calculation Method
Values are calculated using:
```
value = face_value + accrued_interest
```

Where:
- `face_value`: Original principal amount
- `accrued_interest`: Calculated from schedule start to target date

**Note**: This is an **estimate for portfolio valuation**. True profits = sell_proceeds - buy_cost.

---

## Provider Parameters

The provider requires a `provider_params` JSON object with the following structure:

### Required Fields

```json
{
  "face_value": "10000",
  "currency": "EUR",
  "interest_schedule": [
    {
      "start_date": "2025-01-01",
      "end_date": "2025-12-31",
      "rate": "0.05"
    }
  ],
  "maturity_date": "2025-12-31"
}
```

### Optional Fields

```json
{
  "late_interest": {
    "rate": "0.12",
    "grace_period_days": 30
  }
}
```

### Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `face_value` | string/number | ✅ | Principal amount (face value of investment) |
| `currency` | string | ✅ | ISO 4217 currency code (e.g., "EUR", "USD") |
| `interest_schedule` | array | ✅ | List of interest rate periods (see below) |
| `maturity_date` | string | ✅ | Investment maturity date (ISO format: "YYYY-MM-DD") |
| `late_interest` | object | ⬜ | Late payment terms (see below) |

### Interest Schedule Format

Each period in the schedule:

```json
{
  "start_date": "2025-01-01",  // Period start (ISO format)
  "end_date": "2025-12-31",    // Period end (ISO format)
  "rate": "0.05"               // Annual rate as decimal (0.05 = 5%)
}
```

**Rules**:
- Periods should be consecutive (no gaps)
- Rates are annual (e.g., 0.05 = 5% per year)
- Dates can overlap (last matching period wins)

### Late Interest Format

```json
{
  "rate": "0.12",              // Late interest annual rate (0.12 = 12%)
  "grace_period_days": 30      // Days after maturity before late interest applies
}
```

**Behavior**:
- After maturity + grace period: applies late interest rate
- During grace period: continues with last schedule rate
- If `null`: no late interest (rate becomes 0% after maturity)

---

## Usage Examples

### Example 1: Simple Single-Rate Loan

```json
{
  "face_value": "5000",
  "currency": "EUR",
  "interest_schedule": [
    {
      "start_date": "2025-01-01",
      "end_date": "2025-12-31",
      "rate": "0.06"
    }
  ],
  "maturity_date": "2025-12-31",
  "late_interest": null
}
```

**Expected behavior**:
- Daily accrual at 6% annual rate
- After 1 month: €5,000 × 0.06 × (30/365) ≈ €5,024.66
- After 1 year: €5,000 × 0.06 = €5,300.00
- After maturity: value remains at €5,300.00 (no late interest)

### Example 2: Tiered Interest Schedule

```json
{
  "face_value": "10000",
  "currency": "EUR",
  "interest_schedule": [
    {
      "start_date": "2025-01-01",
      "end_date": "2025-06-30",
      "rate": "0.05"
    },
    {
      "start_date": "2025-07-01",
      "end_date": "2025-12-31",
      "rate": "0.07"
    }
  ],
  "maturity_date": "2025-12-31",
  "late_interest": null
}
```

**Expected behavior**:
- First 6 months: 5% annual rate
- Last 6 months: 7% annual rate (higher rate in second half)
- After 1 year: €10,000 + (€250 + €350) = €10,600

### Example 3: Loan with Late Interest Penalty

```json
{
  "face_value": "8000",
  "currency": "EUR",
  "interest_schedule": [
    {
      "start_date": "2025-01-01",
      "end_date": "2025-12-31",
      "rate": "0.055"
    }
  ],
  "maturity_date": "2025-12-31",
  "late_interest": {
    "rate": "0.15",
    "grace_period_days": 30
  }
}
```

**Expected behavior**:
- Until 2025-12-31: 5.5% annual rate
- 2026-01-01 to 2026-01-30 (grace): continues at 5.5%
- After 2026-01-31: 15% annual rate (late interest)

---

## API Integration

### Assign Provider to Asset

```http
POST /api/v1/assets/{asset_id}/provider
Content-Type: application/json

{
  "provider_code": "scheduled_investment",
  "provider_params": {
    "face_value": "10000",
    "currency": "EUR",
    "interest_schedule": [
      {
        "start_date": "2025-01-01",
        "end_date": "2025-12-31",
        "rate": "0.05"
      }
    ],
    "maturity_date": "2025-12-31",
    "late_interest": {
      "rate": "0.12",
      "grace_period_days": 30
    }
  }
}
```

### Get Current Value

```http
GET /api/v1/assets/{asset_id}/prices/current
```

Response:
```json
{
  "value": "10041.10",
  "currency": "EUR",
  "as_of_date": "2025-01-30",
  "source": "Scheduled Investment Calculator"
}
```

### Get Historical Values

```http
GET /api/v1/assets/{asset_id}/prices?start=2025-01-01&end=2025-01-07
```

Response:
```json
{
  "prices": [
    {
      "date": "2025-01-01",
      "close": "10000.00",
      "currency": "EUR"
    },
    {
      "date": "2025-01-02",
      "close": "10001.37",
      "currency": "EUR"
    },
    ...
  ],
  "currency": "EUR",
  "source": "Scheduled Investment Calculator"
}
```

---

## Automatic Calculation (SCHEDULED_YIELD Assets)

### When to Use

If your asset has `valuation_model = SCHEDULED_YIELD` in the database, you **don't need to assign a provider manually**. The system will automatically assign the `scheduled_investment` provider with the correct parameters when you first query prices.

### Asset Model Fields

```python
asset = Asset(
    display_name="Recrowd Loan 12345",
    valuation_model=ValuationModel.SCHEDULED_YIELD,
    face_value=Decimal("10000"),
    currency="EUR",
    maturity_date=date(2026, 12, 31),
    interest_schedule=json.dumps([
        {"start_date": "2025-01-01", "end_date": "2025-12-31", "rate": "0.05"}
    ]),
    late_interest=json.dumps({"rate": "0.12", "grace_period_days": 30})
)
```

### Automatic Provider Assignment

When you query prices for the first time:
```python
prices = await AssetSourceManager.get_prices(
    asset_id=asset.id,
    start_date=date(2025, 1, 1),
    end_date=date(2025, 1, 7),
    session=session
)
```

The system automatically:
1. Detects `valuation_model == SCHEDULED_YIELD`
2. Auto-assigns `scheduled_investment` provider with asset parameters
3. Delegates to the provider for calculation
4. Returns prices with `backward_fill_info = None` (always exact)

**Note**: The provider assignment persists in the database for future queries.

---

## Implementation Details

### Core Functions

Located in `backend/app/utils/financial_math.py`:

#### `calculate_daily_factor_between_act365(start_date, end_date)`
- Calculates day fraction using ACT/365 convention
- Returns: `Decimal(days) / Decimal(365)`

#### `find_active_rate(schedule, target_date, maturity_date, late_interest)`
- Finds applicable interest rate for specific date
- Handles: schedule periods, grace period, late interest
- Returns: Annual rate as Decimal

#### `calculate_accrued_interest(face_value, start_date, end_date, schedule, maturity_date, late_interest)`
- Calculates accrued SIMPLE interest from start to end
- Day-by-day iteration for accurate rate change handling
- Returns: Total accrued interest as Decimal

### Provider Class

Located in `backend/app/services/asset_source_providers/scheduled_investment.py`:

```python
@register_provider(AssetProviderRegistry)
class ScheduledInvestmentProvider(AssetSourceProvider):
    provider_code = "scheduled_investment"
    provider_name = "Scheduled Investment Calculator"
    
    async def get_current_value(self, provider_params, session):
        # Calculates: face_value + accrued_interest
        ...
    
    async def get_history_value(self, provider_params, start_date, end_date, session):
        # Generates daily values for date range
        ...
```

---

## Validation & Error Handling

### Parameter Validation

The provider validates:
- ✅ `face_value` is positive Decimal
- ✅ `currency` is present
- ✅ `interest_schedule` is non-empty array
- ✅ `maturity_date` is valid ISO date
- ✅ Schedule periods have valid date ranges

### Common Errors

| Error Code | Message | Solution |
|------------|---------|----------|
| `MISSING_PARAMS` | Required params missing | Check required fields (face_value, currency, schedule, maturity_date) |
| `INVALID_PARAMS` | Invalid face_value | face_value must be positive number |
| `INVALID_PARAMS` | Invalid maturity_date | Use ISO format: "YYYY-MM-DD" |
| `INVALID_PARAMS` | Empty interest_schedule | Provide at least one schedule period |
| `NOT_SUPPORTED` | Search not supported | This provider doesn't support search (manual configuration) |

---

## Testing

### Unit Tests

Located in `backend/test_scripts/test_services/test_synthetic_yield.py`:

```bash
# Run synthetic yield tests
python test_runner.py services synthetic-yield

# Results: 7/7 tests passing
✅ find_active_rate - Simple Schedule
✅ find_active_rate - No Late Interest
✅ calculate_accrued_interest - Single Rate
✅ calculate_accrued_interest - Rate Change
✅ calculate_synthetic_value - Full Calculation
✅ get_prices - Synthetic Yield Integration
✅ Synthetic Values Not Written to DB
```

### Manual Testing

```python
from backend.app.services.provider_registry import AssetProviderRegistry

# Get provider instance
provider = AssetProviderRegistry.get_provider("scheduled_investment")

# Define test parameters
params = {
    "face_value": "10000",
    "currency": "EUR",
    "interest_schedule": [
        {"start_date": "2025-01-01", "end_date": "2025-12-31", "rate": "0.05"}
    ],
    "maturity_date": "2025-12-31"
}

# Calculate current value
result = await provider.get_current_value(params, session)
print(f"Current value: {result['value']} {result['currency']}")
```

---

## Limitations & Future Enhancements

### Current Limitations

1. **SIMPLE Interest Only**: No compound interest support
2. **No Dividend Tracking**: Dividend payments not yet subtracted from value
3. **No Transaction Integration**: Doesn't check if loan was repaid early
4. **Manual Configuration**: No search/discovery (must configure manually)

### Planned Enhancements (Step 03)

- [ ] **Transaction Integration**: Check if loan repaid via transactions
- [ ] **Dividend Support**: Subtract dividend payments from value
- [ ] **First BUY Date**: Use actual purchase date instead of schedule start
- [ ] **Compound Interest**: Add support for compound interest calculation
- [ ] **Multiple Schedules**: Support for different schedules per asset

---

## Comparison with Other Providers

| Feature | scheduled_investment | yfinance | cssscraper |
|---------|---------------------|----------|------------|
| **Data Source** | Calculation (local) | Yahoo Finance API | Web scraping |
| **External API** | ❌ No | ✅ Yes | ✅ Yes |
| **Historical Data** | ✅ Yes (calculated) | ✅ Yes (market) | ⬜ Optional |
| **Real-time Prices** | ✅ Yes (calculated) | ✅ Yes (market) | ✅ Yes (scraped) |
| **Search Support** | ❌ No | ✅ Yes | ❌ No |
| **Configuration** | Manual | Ticker symbol | URL + CSS selector |
| **Use Case** | Fixed-income | Public stocks/ETFs | Private assets |
| **DB Storage** | ❌ No (on-demand) | ✅ Yes | ✅ Yes |

---

## Best Practices

### 1. Use for Appropriate Assets
✅ **Good**:
- Crowdfunding loans
- Fixed-rate bonds
- Structured products with known schedules

❌ **Not Recommended**:
- Public stocks (use yfinance)
- Volatile assets (use market data)
- Assets without fixed schedules

### 2. Keep Schedules Up-to-Date
- Update `provider_params` when terms change
- Review late interest settings periodically
- Adjust rates after amendments

### 3. Validate Face Value
- Face value should match actual investment
- Don't include fees in face value
- Use same currency as returns

### 4. Monitor Maturity Dates
- Check if loans are repaid on time
- Update late interest params if needed
- Consider grace period settings

### 5. Use with Transaction Tracking
- Track actual cash flows separately
- Compare synthetic value with realized returns
- Use for portfolio valuation, not P&L

---

## Troubleshooting

### Issue: Value doesn't match expected
**Solution**: Check:
- Schedule dates are correct
- Rates are in decimal format (0.05 not 5)
- Face value matches investment amount
- Currency is correct

### Issue: Late interest not applying
**Solution**: Check:
- Maturity date has passed
- Grace period has expired
- `late_interest` object is present in params

### Issue: Values not increasing
**Solution**: Check:
- Target date is after schedule start
- Interest schedule covers the date range
- Rates are positive values

### Issue: Provider not found
**Solution**:
- Verify provider is registered: `AssetProviderRegistry.list_providers()`
- Check auto-discovery ran on import
- Look for import errors in logs

---

## Additional Resources

- [Asset Pricing Architecture](../architecture/overview.md)
- [Provider Development Guide](../contributing/new-asset-provider.md)
- [This Guide](./scheduled-investments.md)
- [API Reference](../../api/index.md)
- [Testing Guide](../backend/testing.md)

---

## Support & Contribution

For issues, questions, or contributions:
- GitHub Issues: [LibreFolio/issues](https://github.com/LibreFolio/issues)
- Documentation: [docs/README.md](../README.md)
- Provider Registry: `backend/app/services/provider_registry.py`

---

**Last Updated**: 2025-11-11
**Provider Version**: 1.0.0
**Status**: ✅ Production Ready

## 🕵️ How to get information about the Scheduled Investment provider

To get information about the Scheduled Investment provider an Agent can:

1.  Read this file.
2.  Inspect the file `backend/app/services/asset_source_providers/scheduled_investment.py` to see the provider implementation.
3.  Read the `backend/app/utils/financial_math.py` file to understand the calculation logic.
4.  Run the tests for the synthetic yield feature to see it in action:
    - `./test_runner.py services synthetic-yield`
    - `./test_runner.py services synthetic-yield-integration`

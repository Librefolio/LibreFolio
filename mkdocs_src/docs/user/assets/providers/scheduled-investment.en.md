# <img src="/LibreFolio/static/icons/scheduled_investment.png" alt=""> Scheduled Investment

The Scheduled Investment provider is designed for fixed-income instruments where the value is calculated from an interest rate schedule rather than market prices. Examples include savings accounts, fixed deposits, and government bonds with known coupon rates.

## 📊 Capabilities

- ✅ **Current Price**: Calculated deterministically from initial value + interest schedule + asset events
- ✅ **History**: Full historical value curve based on interest accrual
- ✅ **Asset Events**: Generates INTEREST and PRICE_ADJUSTMENT events
- ❌ **Search**: Not applicable

## 🔧 Configuration

- **Identifier**: Auto-generated (no manual identifier needed)
- **Identifier Type**: `AUTO_GENERATED`
- **Parameters**: Configured via the **Interest Schedule Editor** (custom UI component)

### Required Fields

| Field | Description |
|-------|-------------|
| **Initial Value** | The principal / face value of the investment (e.g., 10000) |
| **Currency** | ISO 4217 currency code (e.g., EUR, USD) |

## 📋 Interest Schedule Editor

The editor allows you to define multiple interest rate periods:

| Field | Description |
|-------|-------------|
| **Period** | Start and end date (both inclusive) |
| **Rate %** | Annual interest rate as percentage (e.g., 5.00 = 5%) |
| **Compounding** | Simple or Compound interest |
| **Comp. Freq.** | Compounding frequency (Annual, Semi-annual, Quarterly, Monthly, Daily) |
| **Day Count** | Day count convention (ACT/365, ACT/360, 30/360, ACT/ACT) |

### ⚡ Late Interest

You can enable **Late Interest** to define a penalty rate applied after the last scheduled period ends. The late interest has a configurable **grace period** (in days) before it starts accruing.

## 📋 Asset Events

Asset events describe things that happen to the asset globally (not portfolio-level transactions):

| Event Type | Effect on Price | Description |
|-----------|----------------|-------------|
| **INTEREST** | Price drops by event value | Interest payout — the user received cash, so the asset value decreases |
| **PRICE_ADJUSTMENT** | Algebraic change | Write-down (negative) or write-up (positive) of the asset value |

Events are configured in the editor and affect the calculated price from their date onwards.

## 🧮 How Value is Calculated

1. Start with `initial_value` as the base principal
2. For each interest period, calculate accrued interest based on the rate, compounding type, and day count convention
3. Apply asset events: INTEREST events reduce the price, PRICE_ADJUSTMENT events modify it algebraically
4. The current value = `initial_value` + accrued interest - Σ(INTEREST events) + Σ(PRICE_ADJUSTMENT events)

!!! note "Pure Deterministic Engine"

    The provider is completely deterministic — given the same configuration, it always produces the same prices. It does NOT access the database or read transactions. All inputs come from `provider_params`.

## 🎯 Use Cases

- **Savings accounts** with fixed or variable interest rates
- **Term deposits** (CD/Depositi vincolati)
- **Government bonds** where you want to track accrued interest rather than market price
- **Crowdfunding loans** (P2P lending) with known interest schedules
- **Any instrument** with a known interest rate schedule


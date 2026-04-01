# 🧮 Scheduled Investment Provider

The Scheduled Investment provider is designed for fixed-income instruments where the value is calculated from an interest rate schedule rather than market prices. Examples include savings accounts, fixed deposits, and government bonds with known coupon rates.

## 📊 Capabilities

- ✅ **Current Price**: Calculated from the interest schedule and transactions
- ✅ **History**: Full historical value curve based on interest accrual
- ❌ **Search**: Not applicable

## 🔧 Configuration

- **Identifier**: Auto-generated (no manual identifier needed)
- **Identifier Type**: `AUTO_GENERATED`
- **Parameters**: Configured via the **Interest Schedule Editor** (custom UI component)

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

You can enable **Late Interest** to define a penalty rate applied after the last scheduled period ends. The late interest has a configurable **grace period** (in years, months, and days) before it starts accruing.

## 🧮 How Value is Calculated

1. The provider looks at all **BUY** transactions to determine the principal
2. For each interest period, it calculates accrued interest based on the rate, compounding type, and day count convention
3. The current value = principal + total accrued interest

## 🎯 Use Cases

- **Savings accounts** with fixed or variable interest rates
- **Term deposits** (CD/Depositi vincolati)
- **Government bonds** where you want to track accrued interest rather than market price
- **Any instrument** with a known interest rate schedule


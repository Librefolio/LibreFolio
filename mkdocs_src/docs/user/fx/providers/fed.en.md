# <img src="https://fred.stlouisfed.org/favicon.ico" alt=""> Federal Reserve (FED)

The **Federal Reserve (FRED)** provider retrieves exchange rate data from the Federal Reserve Economic Data (FRED) database. It is the ideal primary or fallback source for portfolios centered around the US Dollar.

## 📊 Capabilities

- ✅ **Current Price**: Reference rate updated daily
- ✅ **History**: Deep historical rates (depends on the currency series)
- ❌ **Search**: No asset search (FX rates only)

## 🔧 Specifications

- **Base Currency**: USD 🇺🇸
- **Update Frequency**: Daily on US business days
- **API Key**: Not required (retrieved via public CSV download)

## 💰 Supported Currencies

FRED provides rates for approximately 20 major currencies, including:

- **G10 Currencies**: EUR 🇪🇺, GBP 🇬🇧, JPY 🇯🇵, CAD 🇨🇦, CHF 🇨🇭, AUD 🇦🇺, NZD 🇳🇿, SEK 🇸🇪, NOK 🇳🇴, DKK 🇩🇰
- **Emerging & Regional**: CNY 🇨🇳, HKD 🇭🇰, SGD 🇸🇬, KRW 🇰🇷, INR 🇮🇳, BRL 🇧🇷, MXN 🇲🇽, ZAR 🇿🇦, TWD 🇹🇼, THB 🇹🇭

## 📝 Important Notes

- **Quotes format**: FRED quotes some currencies as "USD per unit of foreign currency" (e.g., EUR, GBP) and others as "foreign currency per USD" (e.g., JPY, CAD). LibreFolio automatically inverts and normalizes these rates to guarantee consistency in your database.
- **Holidays**: No rates are published on US federal holidays (such as Thanksgiving, Independence Day, etc.) or weekends.

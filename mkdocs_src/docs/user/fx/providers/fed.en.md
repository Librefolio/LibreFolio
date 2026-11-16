# <img src="https://fred.stlouisfed.org/favicon.ico" alt=""> Federal Reserve (FED)

The **Federal Reserve (FRED)** provider retrieves exchange rate data from the Federal Reserve Economic Data (FRED) database. It is the ideal primary or fallback source for portfolios centered around the US Dollar.

## 📊 Capabilities

- ✅ **Current Price**: Reference rate updated daily
- ✅ **History**: Deep historical rates (depends on the currency series)
- ❌ **Search**: No asset search (FX rates only)

## 🔧 Specifications

- **Base Currency**: USD 🇺🇸
- **Update Frequency**: one rate per US business day, published once a week (see below)
- **API Key**: Not required (retrieved via public CSV download)

## 💰 Supported Currencies

FRED provides rates for 23 currencies:

- **G10 Currencies**: EUR 🇪🇺, GBP 🇬🇧, JPY 🇯🇵, CAD 🇨🇦, CHF 🇨🇭, AUD 🇦🇺, NZD 🇳🇿, SEK 🇸🇪, NOK 🇳🇴, DKK 🇩🇰
- **Emerging & Regional**: CNY 🇨🇳, HKD 🇭🇰, SGD 🇸🇬, KRW 🇰🇷, INR 🇮🇳, BRL 🇧🇷, MXN 🇲🇽, ZAR 🇿🇦, TWD 🇹🇼, THB 🇹🇭, MYR 🇲🇾, LKR 🇱🇰, VES 🇻🇪

## 📝 Important Notes

- **Quotes format**: FRED quotes some currencies as "USD per unit of foreign currency" (e.g., EUR, GBP) and others as "foreign currency per USD" (e.g., JPY, CAD). LibreFolio reads each series in its own direction and normalizes it to guarantee consistency in your database.
- **Weekly publication**: FED rates are daily, one value per US business day, but the Federal Reserve publishes them once a week, on Mondays, with the days of the previous week. The latest FED rate can therefore be up to about 10 days old, and a conversion chain with a FED leg has no rate for the most recent days until the next release. The routes that use FED show this as an ℹ️ note.
- **VES (Venezuelan Bolívar)**: available from 4 October 2021, the day of the last redenomination. Earlier FRED values are in older bolívar units and are not used.
- **Holidays**: No rates are published on US federal holidays (such as Thanksgiving, Independence Day, etc.) or weekends.

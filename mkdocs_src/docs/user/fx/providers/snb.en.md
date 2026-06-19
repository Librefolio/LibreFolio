# <img src="https://data.snb.ch/favicon.ico" alt=""> Swiss National Bank (SNB)

The **Swiss National Bank (SNB)** provider publishes daily exchange rates for the Swiss Franc (CHF). It is highly stable and precise, making it a valuable source for CHF-based assets.

## 📊 Capabilities

- ✅ **Current Price**: Reference rate updated daily
- ✅ **History**: Historical daily rates
- ❌ **Search**: No asset search (FX rates only)

## 🔧 Specifications

- **Base Currency**: CHF 🇨🇭
- **Update Frequency**: Daily on Swiss business days
- **API Key**: Not required (public SNB Data Portal API)

## 💰 Supported Currencies

The SNB provides exchange rates for a select list of major currencies:

- **Supported Currencies**: USD 🇺🇸, EUR 🇪🇺, GBP 🇬🇧, JPY 🇯🇵, CAD 🇨🇦, AUD 🇦🇺, SEK 🇸🇪, NOK 🇳🇴, DKK 🇩🇰, CNY 🇨🇳

## 📝 Important Notes

- **Multi-Unit Currency Quotation**: The SNB quotes some currencies per **100 units** (e.g. Japanese Yen, Swedish Krona, Norwegian Krone, Danish Krone) instead of 1 unit. For example, the rate is shown as `100 JPY = 0.58 CHF`. **LibreFolio automatically detects and normalizes these rates** to per-unit values to ensure your transactions are calculated correctly.
- **Holidays**: Rates are not published on Swiss bank holidays or weekends.

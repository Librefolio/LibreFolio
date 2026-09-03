# <img src="https://data.snb.ch/favicon.ico" alt=""> Swiss National Bank (SNB)

The **Swiss National Bank (SNB)** provider publishes **monthly average** exchange rates for the Swiss Franc (CHF), fetched from the public SNB Data Portal. It is a stable and authoritative source for CHF-based assets.

!!! warning "Monthly data only — no daily rates"

    The SNB does **not** offer a daily-rate dataset: each value is the **average of a calendar month**, stored on the **1st of that month**. In conversion chains a rate is computed only on dates where **all** involved providers have data, so chaining through SNB yields one point per month. If you need day-by-day CHF rates, use another provider (e.g. ECB or FED) for the pair.

## 📊 Capabilities

- ✅ **Current Price**: Latest available monthly average
- ✅ **History**: Historical monthly averages
- ❌ **Search**: No asset search (FX rates only)

## 🔧 Specifications

- **Base Currency**: CHF 🇨🇭
- **Update Frequency**: Monthly — new averages are published around the 2nd business day of the following month
- **API Key**: Not required (public SNB Data Portal API)

## 💰 Supported Currencies

The SNB covers about **25 currencies** against CHF; LibreFolio loads the exact list dynamically from the SNB Data Portal. It includes:

- **Major**: USD 🇺🇸, EUR 🇪🇺, GBP 🇬🇧, JPY 🇯🇵, CNY 🇨🇳
- **Global**: CAD 🇨🇦, AUD 🇦🇺, and other world currencies

## 📝 Important Notes

- **Multi-Unit Currency Quotation**: The SNB quotes some currencies per **100 units** instead of 1 unit (e.g. `100 JPY = x CHF`). **LibreFolio automatically detects and normalizes these rates** to per-unit values to ensure your transactions are calculated correctly.
- **One point per month**: rates are dated the 1st of each month. Conversions on dates between two monthly points use the most recent available rate (backward-fill).

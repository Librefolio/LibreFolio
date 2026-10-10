# <img src="https://www.ecb.europa.eu/favicon-32.png" alt=""> European Central Bank (ECB)

The **European Central Bank (ECB)** is the primary reference rate provider for European portfolios. It publishes daily reference rates for the euro against about 30 currencies.

## 📊 Capabilities

- ✅ **Current Price**: Reference rate updated once daily
- ✅ **History**: Historical rates available back to 1999
- ❌ **Search**: No asset search (FX rates only)

## 🔧 Specifications

- **Base Currency**: EUR 🇪🇺
- **Update Frequency**: Monday to Friday (excluding ECB holidays), around 16:00 CET
- **API Key**: Not required (public endpoint)

## 💰 Supported Currencies

The ECB publishes a rate every business day for about 30 currencies, including:

- **Major**: USD 🇺🇸, GBP 🇬🇧, JPY 🇯🇵, CHF 🇨🇭, CAD 🇨🇦, AUD 🇦🇺, NZD 🇳🇿
- **European/Regional**: SEK 🇸🇪, NOK 🇳🇴, DKK 🇩🇰, ISK 🇮🇸, PLN 🇵🇱, CZK 🇨🇿, HUF 🇭🇺, RON 🇷🇴, TRY 🇹🇷
- **Global / Emerging**: CNY 🇨🇳, HKD 🇭🇰, SGD 🇸🇬, KRW 🇰🇷, INR 🇮🇳, BRL 🇧🇷, MXN 🇲🇽, ZAR 🇿🇦

Currencies the ECB no longer publishes, such as the Bulgarian lev (BGN, replaced by the euro in 2026), the Croatian kuna (HRK) or the Russian rouble (RUB), keep their past rates: a sync still downloads their history, and no new rates arrive.

## 📝 Important Notes

- **Quotes format**: Rates are expressed as the amount of foreign currency per 1 EUR (e.g., 1 EUR = 1.08 USD). LibreFolio automatically normalizes this rate depending on your portfolio base currency.
- **No Weekend Data**: The ECB does not publish rates on Saturdays, Sundays, or official ECB holidays (e.g., Good Friday, Easter Monday, Christmas). LibreFolio will retain the last available business day rate for weekend valuations.

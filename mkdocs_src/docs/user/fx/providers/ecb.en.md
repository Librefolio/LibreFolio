# 🇪🇺 European Central Bank (ECB)

The **European Central Bank (ECB)** is the primary reference rate provider for European portfolios. It publishes daily exchange rates for the Euro against approximately 45 major and emerging currencies.

## 📊 Capabilities

- ✅ **Current Price**: Reference rate updated once daily
- ✅ **History**: Historical rates available back to 1999
- ❌ **Search**: No asset search (FX rates only)

## 🔧 Specifications

- **Base Currency**: EUR 🇪🇺
- **Update Frequency**: Monday to Friday (excluding ECB holidays), around 16:00 CET
- **API Key**: Not required (public endpoint)

## 💰 Supported Currencies

The ECB supports a wide range of currencies, including:

- **Major**: USD 🇺🇸, GBP 🇬🇧, JPY 🇯🇵, CHF 🇨🇭, CAD 🇨🇦, AUD 🇦🇺, NZD 🇳🇿
- **European/Regional**: SEK 🇸🇪, NOK 🇳🇴, DKK 🇩🇰, PLN 🇵🇱, CZK 🇨🇿, HUF 🇭🇺, RON 🇷🇴, BGN 🇧🇬, TRY 🇹🇷
- **Global / Emerging**: CNY 🇨🇳, HKD 🇭🇰, SGD 🇸🇬, KRW 🇰🇷, INR 🇮🇳, BRL 🇧🇷, MXN 🇲🇽, ZAR 🇿🇦

## 📝 Important Notes

- **Quotes format**: Rates are expressed as the amount of foreign currency per 1 EUR (e.g., 1 EUR = 1.08 USD). LibreFolio automatically normalizes this rate depending on your portfolio base currency.
- **No Weekend Data**: The ECB does not publish rates on Saturdays, Sundays, or official ECB holidays (e.g., Good Friday, Easter Monday, Christmas). LibreFolio will retain the last available business day rate for weekend valuations.

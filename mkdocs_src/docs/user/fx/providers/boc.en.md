# <img src="https://www.bankofcanada.ca/wp-content/themes/ews-build-2024/img/favicon/favicon-32x32.png" alt=""> Bank of Canada (BOC)

The **Bank of Canada (BOC)** provider retrieves the daily average exchange rates of the Bank of Canada, quoted against the Canadian dollar (CAD). Besides the major currencies, it is a useful second source for Latin American and Asian currencies such as the Mexican peso, the Brazilian real, the Indian rupee and the New Taiwan dollar, and it covers the Peruvian sol, which the ECB does not publish.

## 📊 Capabilities

- ✅ **Current Price**: Daily average rate, updated every Canadian business day
- ✅ **History**: from 3 January 2017
- ❌ **Search**: No asset search (FX rates only)

## 🔧 Specifications

- **Base Currency**: CAD 🇨🇦
- **Update Frequency**: every Canadian business day, by 16:30 ET
- **API Key**: Not required (public open data)

## 💰 Supported Currencies

The Bank of Canada publishes rates for about 24 currencies. LibreFolio reads the list from the bank, so it follows what the bank publishes. Among them:

- **Major**: USD 🇺🇸, EUR 🇪🇺, GBP 🇬🇧, JPY 🇯🇵, CHF 🇨🇭, AUD 🇦🇺, NZD 🇳🇿
- **European/Regional**: SEK 🇸🇪, NOK 🇳🇴, PLN 🇵🇱, TRY 🇹🇷
- **Global / Emerging**: CNY 🇨🇳, HKD 🇭🇰, SGD 🇸🇬, KRW 🇰🇷, INR 🇮🇳, IDR 🇮🇩, TWD 🇹🇼, MYR 🇲🇾, THB 🇹🇭, BRL 🇧🇷, MXN 🇲🇽, ZAR 🇿🇦
- **Not published by the ECB**: PEN 🇵🇪 (Peruvian sol)

Currencies the bank no longer publishes (such as the Vietnamese dong, the Russian rouble and the Saudi riyal) are not offered.

## 📝 Important Notes

- **Quotes format**: rates are expressed as CAD per one unit of the foreign currency (e.g. 1 USD = 1.4257 CAD on 13 November 2026). LibreFolio normalizes the rate behind the scenes.
- **Indicative rates**: the Bank of Canada publishes daily averages as an indication, not as a benchmark for transactions. The routes that use BOC show this, with the rounding of IDR and KRW below, as a ⚠️ note.
- **Few digits for some currencies**: the bank publishes the Indonesian rupiah and the South Korean won with few digits (1 IDR = 0.000078 CAD). Their BOC rates are therefore rounded, by up to about 1% for the rupiah.
- **Holidays**: no rates are published at weekends or on Canadian holidays (for example 11 November, Remembrance Day).
- **History**: rates start on 3 January 2017. The bank's older noon rates are a different series, computed another way, and are not downloaded.
- **Source**: the bank's terms of use ask to name the Bank of Canada as the source of its data. The provider's description does: «Source: Bank of Canada».

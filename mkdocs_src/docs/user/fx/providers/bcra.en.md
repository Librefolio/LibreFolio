# <img src="https://www.bcra.gob.ar/wp-content/uploads/cropped-favicon-bcra-192x192.png" alt="" width="32"> Banco Central de la República Argentina (BCRA)

The **Banco Central de la República Argentina (BCRA)** provider retrieves the daily exchange rates published by Argentina's central bank, quoted against the Argentine peso (ARS), with a history back to 2002. For the US dollar it uses the official reference rate of «Comunicación A 3500».

## 📊 Capabilities

- ✅ **Current Price**: daily rate, Argentine business days
- ✅ **History**: from 4 March 2002 (some currencies start later)
- ❌ **Search**: No asset search (FX rates only)

## 🔧 Specifications

- **Base Currency**: ARS 🇦🇷
- **Update Frequency**: every Argentine business day
- **API Key**: Not required

## 💰 Supported Currencies

A fixed list of 32 currencies, all against ARS:

- **Americas**: USD 🇺🇸, BRL 🇧🇷, CLP 🇨🇱, UYU 🇺🇾, PYG 🇵🇾, BOB 🇧🇴, PEN 🇵🇪, COP 🇨🇴, MXN 🇲🇽, CAD 🇨🇦, NIO 🇳🇮, AWG 🇦🇼
- **Europe**: EUR 🇪🇺, GBP 🇬🇧, CHF 🇨🇭, SEK 🇸🇪, NOK 🇳🇴, DKK 🇩🇰, CZK 🇨🇿, RSD 🇷🇸, RUB 🇷🇺, TRY 🇹🇷
- **Asia and Oceania**: JPY 🇯🇵, CNY 🇨🇳, HKD 🇭🇰, SGD 🇸🇬, INR 🇮🇳, VND 🇻🇳, ILS 🇮🇱, AUD 🇦🇺, NZD 🇳🇿
- **Africa**: ZAR 🇿🇦

## 📝 Important Notes

- **Quotes format**: pesos per one unit of the foreign currency (e.g. 1 USD = 1562.99 ARS on 19 November 2026). LibreFolio normalizes the rate behind the scenes.
- **The US dollar** is the reference rate of «Comunicación A 3500», whose method changed on 1 January 2026 (weighted averages of actual trades).
- **The other currencies** are the bank's own rates, built on another dollar rate the bank publishes. In most years the two dollar rates are within 1%, but they can differ by a few percent (up to 15% in 2002, 6% in 2018).
- **Terms**: the BCRA allows its data for informative, educational or academic use, citing the bank, and not for commercial use without permission. The provider is meant for your own instance: LibreFolio downloads the rates for you only. The provider's description cites the source: «Source: Banco Central de la República Argentina».
- **Russian rouble**: the RUB rate is the one the BCRA publishes, not the Central Bank of Russia's.
- **Uneven data**: on a few days the bank lists a currency twice with two different rates. LibreFolio leaves that day out for that currency instead of guessing.
- **The full history takes about 12 seconds per currency** to download the first time.

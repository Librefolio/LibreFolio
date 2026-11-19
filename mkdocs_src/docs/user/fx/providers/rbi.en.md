# <img src="https://www.rbi.org.in/favicon.ico" alt="" width="32"> Reserve Bank of India (RBI)

The **Reserve Bank of India (RBI)** provider retrieves the reference rate of the Indian rupee (INR) from the RBI's archive. Since July 2018 the reference rate is computed by FBIL (Financial Benchmarks India), and it is the rate Indian accounts and tax returns use.

## 📊 Capabilities

- ✅ **Current Price**: daily reference rate, Mumbai business days
- ✅ **History**: from 25 August 1998, with a gap from July 2018 to April 2022
- ❌ **Search**: No asset search (FX rates only)

## 🔧 Specifications

- **Base Currency**: INR 🇮🇳
- **Update Frequency**: every Mumbai business day, around 1:30 p.m. India time
- **API Key**: Not required

## 💰 Supported Currencies

7 currencies, all against INR:

- USD 🇺🇸, GBP 🇬🇧, EUR 🇪🇺 (from January 1999), JPY 🇯🇵
- AED 🇦🇪 and IDR 🇮🇩 (from January 2026), RUB 🇷🇺 (from September 2026)

## 📝 Important Notes

- **Quotes format**: rupees per one unit of the foreign currency (e.g. 1 USD = 93.3461 INR on 19 November 2026); the yen is quoted per 100 yen and the rupiah per 10 000 rupiah. LibreFolio normalizes the rate behind the scenes.
- **The gap**: the RBI's archive has no rates from 25 July 2018 to 11 April 2022, nor from 10 to 23 July 2018. RBI has no rate for those days: another provider on the same pair can cover them.
- **Web page form**: the rates are read from a form on the RBI's website, which can change without notice. If it changes, the update fails with a clear error instead of storing wrong values. The routes that use RBI show this as a ⚠️ note.
- **Terms**: FBIL does not allow commercial use of its data without written permission. The provider is meant for your own instance: LibreFolio downloads the rates for you only. The provider's description names the source: «Source: Reserve Bank of India (FBIL reference rate)».
- **Russian rouble**: the RUB rate is the one the RBI publishes, not the Central Bank of Russia's.
- **The full history takes about a minute** to download the first time (one request per year).

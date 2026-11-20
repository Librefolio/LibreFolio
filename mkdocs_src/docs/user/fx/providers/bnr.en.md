# <img src="https://www.bnr.ro/favicon.ico" alt="" width="32"> National Bank of Romania (BNR)

The **National Bank of Romania (BNR)** provider retrieves the daily reference rates published by Romania's central bank, quoted against the Romanian leu (RON), with a history back to 2005. Besides the major currencies, it gives several currencies of Eastern Europe and the Middle East: the Moldovan leu, the Ukrainian hryvnia, the Serbian dinar, the Egyptian pound and the UAE dirham.

## 📊 Capabilities

- ✅ **Current Price**: daily reference rate, Romanian business days
- ✅ **History**: from January 2005 (some currencies start later)
- ❌ **Search**: No asset search (FX rates only)

## 🔧 Specifications

- **Base Currency**: RON 🇷🇴
- **Update Frequency**: every Romanian business day
- **API Key**: Not required

## 💰 Supported Currencies

39 currencies, all against RON:

- **Major**: EUR 🇪🇺, USD 🇺🇸, GBP 🇬🇧, CHF 🇨🇭, JPY 🇯🇵, CAD 🇨🇦, AUD 🇦🇺, NZD 🇳🇿
- **Europe**: PLN 🇵🇱, HUF 🇭🇺, CZK 🇨🇿, DKK 🇩🇰, SEK 🇸🇪, NOK 🇳🇴, ISK 🇮🇸, RSD 🇷🇸, MDL 🇲🇩, UAH 🇺🇦, TRY 🇹🇷, RUB 🇷🇺
- **Former currencies**: BGN 🇧🇬 (until 2025), HRK 🇭🇷 (until 2022), SKK 🇸🇰 (2007–2008)
- **Asia, Middle East and Africa**: CNY 🇨🇳, HKD 🇭🇰, SGD 🇸🇬, INR 🇮🇳, IDR 🇮🇩, KRW 🇰🇷, MYR 🇲🇾, PHP 🇵🇭, THB 🇹🇭, ILS 🇮🇱, AED 🇦🇪, EGP 🇪🇬, ZAR 🇿🇦
- **Americas**: BRL 🇧🇷, MXN 🇲🇽

## 📝 Important Notes

- **Quotes format**: lei per one unit of the foreign currency (e.g. 1 EUR = 5.3442 RON on 19 November 2026); the forint, the yen, the won, the rupiah and the króna are quoted per 100 units. LibreFolio normalizes the rate behind the scenes.
- **Later starts**: AED, BRL, CNY, INR, KRW, MXN, NZD, RSD, UAH and ZAR start in March 2009; THB in 2017; HKD, IDR, ILS, ISK, MYR, PHP and SGD in September 2024.
- **Russian rouble**: the RUB rate is the one the National Bank of Romania publishes, not the Central Bank of Russia's.
- **The IMF's special drawing right (XDR)**: served like a currency. It is the IMF's unit of account, a basket of USD, EUR, CNY, JPY and GBP.
- **Not served**: gold (XAU).
- **Source and terms**: no terms of use could be read on the bank's site. LibreFolio downloads the rates for your own instance only. The provider's description names the source: «Source: National Bank of Romania».

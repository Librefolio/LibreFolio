# <img src="https://nbp.pl/favicon.ico" alt="" width="32"> Narodowy Bank Polski (NBP)

The **Narodowy Bank Polski (NBP)** provider retrieves the average exchange rates published by Poland's central bank, quoted against the złoty (PLN), with a history back to 2002. It covers 147 currencies: 31 every business day, and 116 rarer ones once a week, among them most currencies of Africa, Asia and Latin America.

## 📊 Capabilities

- ✅ **Current Price**: daily average rate for 31 currencies, weekly for 116
- ✅ **History**: from 2 January 2002
- ❌ **Search**: No asset search (FX rates only)

## 🔧 Specifications

- **Base Currency**: PLN 🇵🇱
- **Update Frequency**: every Polish business day (table A); once a week, usually on Wednesday (table B)
- **API Key**: Not required

## 💰 Supported Currencies

- **Daily (table A, 31)**: USD, EUR, GBP, CHF, JPY, CAD, AUD, NZD, SEK, NOK, DKK, ISK, CZK, HUF, RON, TRY, UAH, ILS, ZAR, BRL, MXN, CLP, CNY, HKD, SGD, INR, IDR, KRW, MYR, PHP, THB
- **Weekly (table B, 116)**: almost every other currency of the world, for example NGN, KES, EGP, MAD, SAR, AED, KZT, VND, PKR, ARS, COP, PEN, RUB

## 📝 Important Notes

- **Quotes format**: złoty per one unit of the foreign currency (e.g. 1 USD = 4.0176 PLN on 19 November 2026). LibreFolio normalizes the rate behind the scenes.
- **Weekly currencies**: the 116 currencies of table B have one rate a week. Between two publications, the last rate is the only one. Some currencies that are daily today (CNY, BRL, INR and others) were weekly before 2008 or 2011.
- **Jumps that are real**: a few rates jump when the NBP moved from an official parity to a market rate (the Liberian dollar and the Iraqi dinar in 2004, the Iranian rial in 2026).
- **Currency changes**: the Venezuelan bolívar before October 2021 is converted to the new bolívar (1 new = 1 000 000 old); the Syrian pound starts in January 2026, when its scale changed.
- **Russian rouble**: the RUB rate is the one the NBP publishes, not the Central Bank of Russia's.
- **Not served**: the IMF's special drawing right (XDR).
- **Source and terms**: the NBP's API documentation says «All rights reserved». LibreFolio downloads the rates for your own instance only. The provider's description names the source: «Source: Narodowy Bank Polski».
- **The full history takes about 40 seconds** to download the first time.

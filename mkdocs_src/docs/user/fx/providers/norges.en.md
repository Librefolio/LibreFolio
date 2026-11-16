# <img src="https://www.norges-bank.no/Static/Favicons/favicon-32x32.png" alt=""> Norges Bank (NORGES)

The **Norges Bank (NORGES)** provider retrieves the daily exchange rates of Norges Bank, the central bank of Norway, quoted against the Norwegian krone (NOK). Besides the major currencies, it covers several Asian and emerging-market currencies that the ECB does not publish.

## 📊 Capabilities

- ✅ **Current Price**: Reference rate updated daily
- ✅ **History**: from 1980 for the oldest currencies (such as USD and JPY), from 1999 for the euro, later for others
- ❌ **Search**: No asset search (FX rates only)

## 🔧 Specifications

- **Base Currency**: NOK 🇳🇴
- **Update Frequency**: every Norwegian business day, around 16:00 CET
- **API Key**: Not required (public open data)

## 💰 Supported Currencies

Norges Bank publishes rates for about 35 currencies. LibreFolio reads the list from the bank, so it follows what the bank publishes. Among them:

- **Major**: USD 🇺🇸, EUR 🇪🇺, GBP 🇬🇧, JPY 🇯🇵, CHF 🇨🇭, CAD 🇨🇦, AUD 🇦🇺, NZD 🇳🇿
- **European/Regional**: SEK 🇸🇪, DKK 🇩🇰, ISK 🇮🇸, PLN 🇵🇱, CZK 🇨🇿, HUF 🇭🇺, RON 🇷🇴, TRY 🇹🇷
- **Global / Emerging**: CNY 🇨🇳, HKD 🇭🇰, SGD 🇸🇬, KRW 🇰🇷, INR 🇮🇳, IDR 🇮🇩, ILS 🇮🇱, MYR 🇲🇾, PHP 🇵🇭, THB 🇹🇭, BRL 🇧🇷, MXN 🇲🇽, ZAR 🇿🇦
- **Not published by the ECB**: BDT 🇧🇩 (Bangladeshi taka), BYN 🇧🇾 (Belarusian rouble), MMK 🇲🇲 (Myanmar kyat), PKR 🇵🇰 (Pakistani rupee), TWD 🇹🇼 (New Taiwan dollar), VND 🇻🇳 (Vietnamese dong)

Currencies the bank no longer publishes (such as the Russian rouble, the Croatian kuna and the Bulgarian lev) are not offered.

## 📝 Important Notes

- **Quotes format**: rates are expressed as NOK per unit of the foreign currency. For some currencies the bank quotes 100 units (e.g. 100 JPY = 5.98 NOK): LibreFolio converts them to one unit and normalizes the rate behind the scenes.
- **Indicative rates**: Norges Bank publishes mid rates only as an indication. The routes that use NORGES show this as an ℹ️ note.
- **Licence**: Norges Bank publishes its open data under the Norwegian Licence for Open Government Data (NLOD 2.0), which allows free reuse with attribution.
- **Holidays**: no rates are published at weekends or on Norwegian holidays.

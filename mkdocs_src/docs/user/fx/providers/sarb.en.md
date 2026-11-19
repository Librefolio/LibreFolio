# <img src="https://www.resbank.co.za/favicon.ico" alt="" width="32"> South African Reserve Bank (SARB)

The **South African Reserve Bank (SARB)** provider retrieves the daily exchange rates of South Africa's central bank, quoted against the South African rand (ZAR). Besides the major currencies, it is a daily source for currencies of southern and eastern Africa, such as the Botswana pula, the Kenyan shilling, the Malawian and Zambian kwacha and the Mozambican metical.

## 📊 Capabilities

- ✅ **Current Price**: daily rate, updated every South African business day
- ✅ **History**: from 2010
- ❌ **Search**: No asset search (FX rates only)

## 🔧 Specifications

- **Base Currency**: ZAR 🇿🇦
- **Update Frequency**: every South African business day, after about 10:30 South African time
- **API Key**: Not required

## 💰 Supported Currencies

A fixed list of 24 currencies, all against ZAR:

- **Major**: USD 🇺🇸, EUR 🇪🇺, GBP 🇬🇧, JPY 🇯🇵, CHF 🇨🇭, AUD 🇦🇺, CAD 🇨🇦, NZD 🇳🇿
- **European**: DKK 🇩🇰, NOK 🇳🇴, SEK 🇸🇪
- **Asia and Middle East**: CNY 🇨🇳, HKD 🇭🇰, INR 🇮🇳, ILS 🇮🇱, KRW 🇰🇷, TWD 🇹🇼, THB 🇹🇭
- **Africa and Latin America**: BWP 🇧🇼, KES 🇰🇪, MWK 🇲🇼, MZN 🇲🇿, ZMW 🇿🇲, BRL 🇧🇷

## 📝 Important Notes

- **Quotes format**: the bank publishes USD, GBP and EUR as rands per one unit (1 USD = 17.2532 ZAR on 19 November 2026), and the other currencies as units per one rand (1 ZAR = 0.0488 CHF). LibreFolio normalizes the rate behind the scenes.
- **Rounding**: the bank publishes four decimals, so the small «per rand» values are rounded, by up to about 0.1% for the Swiss franc. The routes that use SARB show this as a ⚠️ note.
- **Type of rate**: the weighted average of the banks' rates at about 10:30 South African time, one per business day. No rate at weekends and on South African holidays.
- **History**: LibreFolio downloads the rates from 2010, so that a first update of many currencies stays within its time limit. Older rand history is available from the ECB and Banca d'Italia providers.
- **Source and terms**: the bank's terms do not allow copying or redistributing its material without its written consent. LibreFolio downloads the rates for your own instance only. The provider's description names the source: «Source: South African Reserve Bank».

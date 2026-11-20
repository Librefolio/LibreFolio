# <img src="https://bank.gov.ua/frontend/icon/favicon-32x32.png" alt=""> National Bank of Ukraine (NBU)

The **National Bank of Ukraine (NBU)** provider retrieves the official daily exchange rates of the National Bank of Ukraine, quoted against the Ukrainian hryvnia (UAH). Besides the major currencies, it covers several currencies of Central Asia, the Caucasus, Eastern Europe, the Middle East and North Africa that the ECB does not publish.

## 📊 Capabilities

- ✅ **Current Price**: Official rate updated daily
- ✅ **History**: from 2 September 1996, the first day of the hryvnia
- ❌ **Search**: No asset search (FX rates only)

## 🔧 Specifications

- **Base Currency**: UAH 🇺🇦
- **Update Frequency**: every day, weekends and holidays included (see below)
- **API Key**: Not required (public open data)

## 💰 Supported Currencies

The National Bank of Ukraine publishes rates for about 41 currencies. LibreFolio reads the list from the bank, so it follows what the bank publishes. Among them:

- **Major**: USD 🇺🇸, EUR 🇪🇺, GBP 🇬🇧, JPY 🇯🇵, CHF 🇨🇭, CAD 🇨🇦, AUD 🇦🇺, NZD 🇳🇿
- **European/Regional**: SEK 🇸🇪, NOK 🇳🇴, DKK 🇩🇰, PLN 🇵🇱, CZK 🇨🇿, HUF 🇭🇺, RON 🇷🇴, TRY 🇹🇷
- **Global / Emerging**: CNY 🇨🇳, HKD 🇭🇰, SGD 🇸🇬, KRW 🇰🇷, INR 🇮🇳, IDR 🇮🇩, ILS 🇮🇱, MYR 🇲🇾, THB 🇹🇭, MXN 🇲🇽, ZAR 🇿🇦, DZD 🇩🇿
- **Not published by the ECB**: KZT 🇰🇿 (Kazakhstani tenge), GEL 🇬🇪 (Georgian lari), AZN 🇦🇿 (Azerbaijani manat), MDL 🇲🇩 (Moldovan leu), RSD 🇷🇸 (Serbian dinar), EGP 🇪🇬 (Egyptian pound), LBP 🇱🇧 (Lebanese pound), TND 🇹🇳 (Tunisian dinar), SAR 🇸🇦 (Saudi riyal), AED 🇦🇪 (UAE dirham), BDT 🇧🇩 (Bangladeshi taka), VND 🇻🇳 (Vietnamese dong)

The IMF's SDR (XDR), the IMF's unit of account (a basket of USD, EUR, CNY, JPY and GBP), is offered like any other currency. Gold, silver, platinum and palladium, which the bank also lists, are not offered: they are not currencies.

## 📅 One Rate for Every Day

The bank sets its rates on business days, and each rate is valid **from the next day**. So the rate LibreFolio shows for a Monday is the one the bank set on the Friday before. LibreFolio stores every rate under the day it is valid, just as the bank does.

At weekends and on holidays the bank does not set a new rate: it repeats the last one. The rate set on Friday is therefore valid on Saturday, on Sunday and on Monday:

| Day the rate is valid | Day the bank set it |
|-----------------------|---------------------|
| Friday | Thursday |
| Saturday | Friday |
| Sunday | Friday |
| Monday | Friday |
| Tuesday | Monday |

The bank publishes tomorrow's rate already in the afternoon. LibreFolio does not store it yet: a synchronization on or after that day reads it from the bank.

## 📝 Important Notes

- **Quotes format**: rates are expressed as UAH per unit of the foreign currency. For some currencies the bank quotes more than one unit (e.g. 10 JPY = 2.84 UAH): LibreFolio converts them to one unit and normalizes the rate behind the scenes.
- **Valid day**: the routes that use NBU show the rule of the day above as an ℹ️ note.
- **Source**: the bank's terms of use ask to name the source of its data. The provider's description does: «Source: National Bank of Ukraine (bank.gov.ua)».
- **History**: rates start on 2 September 1996. Earlier values were in karbovanets, the currency before the hryvnia, and are not downloaded.

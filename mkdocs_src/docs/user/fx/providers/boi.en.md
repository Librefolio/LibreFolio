# <img src="https://www.boi.org.il/favicon.ico" alt="" width="32"> Bank of Israel (BOI)

The **Bank of Israel (BOI)** provider retrieves the representative exchange rates published by Israel's central bank, quoted against the new shekel (ILS), with a history back to 1986. Besides the major currencies, it gives the Jordanian dinar and the Egyptian pound.

## 📊 Capabilities

- ✅ **Current Price**: daily representative rate, Israeli business days
- ✅ **History**: from January 1986 (EUR from January 1999)
- ❌ **Search**: No asset search (FX rates only)

## 🔧 Specifications

- **Base Currency**: ILS 🇮🇱
- **Update Frequency**: every Israeli business day, in the afternoon (Israel time)
- **API Key**: Not required

## 💰 Supported Currencies

13 currencies, all against ILS:

- **Major**: USD 🇺🇸, EUR 🇪🇺, GBP 🇬🇧, JPY 🇯🇵, CHF 🇨🇭, CAD 🇨🇦, AUD 🇦🇺
- **Nordic**: SEK 🇸🇪, NOK 🇳🇴, DKK 🇩🇰
- **Region**: JOD 🇯🇴, EGP 🇪🇬
- **Africa**: ZAR 🇿🇦

## 📝 Important Notes

- **Quotes format**: shekels per one unit of the foreign currency (e.g. 1 USD = 3.282 ILS on 19 November 2026); the yen is quoted per 100 yen. LibreFolio normalizes the rate behind the scenes.
- **History from 1986**: the bank's series go back further, but between 1980 and 1985 they hold values in old shekels on many days, so LibreFolio starts in January 1986. A few single wrong days can still appear (JOD on 4 March 1991 and 7 October 2002).
- **The Lebanese pound is not served**: the bank publishes it per 10 pounds with four decimals, so its rate jumps by about 30% at each step.
- **Terms**: the Bank of Israel does not allow copying or publishing its data without its written consent. The provider is meant for your own instance: LibreFolio downloads the rates for you only. The provider's description names the source: «Source: Bank of Israel».

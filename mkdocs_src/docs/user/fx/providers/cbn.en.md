# <img src="https://www.cbn.gov.ng/favicon.ico" alt="" width="32"> Central Bank of Nigeria (CBN)

The **Central Bank of Nigeria (CBN)** provider retrieves the central exchange rates published by Nigeria's central bank, quoted against the naira (NGN), with a history back to 2001. It gives the official naira rate of the US dollar, the major currencies and the West African CFA franc.

## 📊 Capabilities

- ✅ **Current Price**: daily central rate, Nigerian business days
- ✅ **History**: from 10 December 2001
- ❌ **Search**: No asset search (FX rates only)

## 🔧 Specifications

- **Base Currency**: NGN 🇳🇬
- **Update Frequency**: every Nigerian business day
- **API Key**: Not required

## 💰 Supported Currencies

A fixed list of 12 currencies, all against NGN:

- **Major**: USD 🇺🇸, EUR 🇪🇺, GBP 🇬🇧, JPY 🇯🇵, CHF 🇨🇭, DKK 🇩🇰
- **Other**: CNY 🇨🇳, ZAR 🇿🇦, SAR 🇸🇦, AED 🇦🇪 (from January 2026), XOF (West African CFA franc), XDR (the IMF's special drawing right, which the bank calls SDR: a unit of account built on a basket of USD, EUR, CNY, JPY and GBP)

## 📝 Important Notes

- **Quotes format**: rates are expressed as naira per one unit of the foreign currency (e.g. 1 USD = 1353.4741 NGN on 13 November 2026). LibreFolio normalizes the rate behind the scenes.
- **Which rate**: the central rate, between the bank's buying and selling rates.
- **Undocumented source**: the rates come from the data behind the bank's web page, which is not documented and can change without notice. If it changes, the update fails with a clear error instead of storing wrong values. The routes that use CBN show this as a ⚠️ note.
- **Uneven data**: on some days the bank lists a currency twice with two different rates. LibreFolio leaves that day out for that currency instead of guessing.
- **Source and terms**: no terms of use were found on the bank's site. LibreFolio downloads the rates for your own instance only. The provider's description names the source: «Source: Central Bank of Nigeria».

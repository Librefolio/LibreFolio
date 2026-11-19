# <img src="https://www.centralbank.go.ke/wp-content/uploads/2016/09/NewLogoCBK-150x150.png" alt="" width="32"> Central Bank of Kenya (CBK)

The **Central Bank of Kenya (CBK)** provider retrieves the daily exchange rates published by Kenya's central bank, quoted against the Kenyan shilling (KES), with a history back to 2004. Besides the major currencies, it gives the shillings of Uganda and Tanzania and the francs of Rwanda and Burundi.

## 📊 Capabilities

- ✅ **Current Price**: daily rate, Kenyan business days
- ✅ **History**: daily from 2 November 2004
- ❌ **Search**: No asset search (FX rates only)

## 🔧 Specifications

- **Base Currency**: KES 🇰🇪
- **Update Frequency**: every Kenyan business day
- **API Key**: Not required

## 💰 Supported Currencies

A fixed list of 21 currencies, all against KES:

- **Major**: USD 🇺🇸, EUR 🇪🇺, GBP 🇬🇧, JPY 🇯🇵, CHF 🇨🇭, CAD 🇨🇦, AUD 🇦🇺
- **Nordic**: SEK 🇸🇪, NOK 🇳🇴, DKK 🇩🇰
- **Asia and Middle East**: CNY 🇨🇳, HKD 🇭🇰, SGD 🇸🇬, INR 🇮🇳, SAR 🇸🇦, AED 🇦🇪
- **Africa**: ZAR 🇿🇦, UGX 🇺🇬, TZS 🇹🇿, RWF 🇷🇼, BIF 🇧🇮

## 📝 Important Notes

- **Quotes format**: most rates are shillings per one unit of the foreign currency (e.g. 1 USD = 129.99 KES on 19 November 2026); the yen is quoted per 100 yen; the Ugandan and Tanzanian shillings and the Rwandan and Burundian francs are quoted the other way round, units per one Kenyan shilling (1 KES = 32.27 UGX). LibreFolio normalizes the rate behind the scenes.
- **The method changed in January 2024**: since 5 January 2024 the rate is a weighted average of the trades between banks; before, it was the average of the main dealers' buying and selling rates at the opening. A chart over that date can show a small jump.
- **Two decimals**: since 2026 the bank publishes two decimals. For a currency worth little against the shilling this is coarse: the Indian rupee is 1.39 KES, so each step is about 0.7%.
- **Undocumented source**: the rates come from the data behind the bank's web pages, which is not documented and can change without notice. If it changes, the update fails with a clear error instead of storing wrong values. The routes that use CBK show this as a ⚠️ note.
- **Uneven data**: on some days the bank lists a currency twice with two different rates. LibreFolio leaves that day out for that currency instead of guessing. A few old rows carry the rates of another day (two before November 2004, one on a Sunday in 2015): LibreFolio leaves them out too.
- **Source and terms**: no terms of use were found on the bank's site. LibreFolio downloads the rates for your own instance only. The provider's description names the source: «Source: Central Bank of Kenya».

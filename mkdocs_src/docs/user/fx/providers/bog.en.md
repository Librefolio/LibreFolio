# <img src="https://www.bog.gov.gh/wp-content/uploads/2020/08/logo-150x150.png" alt="" width="32"> Bank of Ghana (BOG)

The **Bank of Ghana (BOG)** provider retrieves the daily interbank exchange rates published by Ghana's central bank, quoted against the cedi (GHS). Besides the major currencies, it gives the currencies of Ghana's West African neighbours: the naira, the West African CFA franc, the dalasi and the leone.

## 📊 Capabilities

- ✅ **Current Price**: daily mid rate, Ghanaian business days
- ✅ **History**: from January 2020
- ❌ **Search**: No asset search (FX rates only)

## 🔧 Specifications

- **Base Currency**: GHS 🇬🇭
- **Update Frequency**: every Ghanaian business day
- **API Key**: Not required

## 💰 Supported Currencies

A fixed list of 17 currencies, all against GHS:

- **Major**: USD 🇺🇸, EUR 🇪🇺, GBP 🇬🇧, JPY 🇯🇵, CHF 🇨🇭, CAD 🇨🇦, AUD 🇦🇺, NZD 🇳🇿
- **Nordic**: SEK 🇸🇪, NOK 🇳🇴, DKK 🇩🇰
- **Other**: CNY 🇨🇳, ZAR 🇿🇦
- **West Africa**: NGN 🇳🇬, XOF (West African CFA franc), GMD 🇬🇲, SLE 🇸🇱

## 📝 Important Notes

- **Quotes format**: most rates are cedis per one unit of the foreign currency (e.g. 1 USD = 11.77 GHS on 19 November 2026); the naira, the CFA franc, the dalasi and the leone are quoted the other way round, units per one cedi (1 GHS = 117.50 NGN). LibreFolio normalizes the rate behind the scenes.
- **Which rate**: the mid rate, between the bank's buying and selling rates.
- **History from 2020**: the bank's table goes back to 1996, but its earlier years hold old cedis (before the 2007 redenomination) and many days with the value of another currency. LibreFolio starts in January 2020. A single wrong day can still appear (CNY on 28 February 2025).
- **The leone**: until 10 September 2026 the bank quotes old leones; LibreFolio converts them to new leones (SLE, 1 SLE = 1 000 old leones).
- **The yen** has four decimals (0.0736 GHS), so its rate moves in steps of about 0.14%.
- **Not served**: the Mauritanian ouguiya, whose rate in the bank's table is a fixed parity rather than a market rate, and the ECOWAS unit of account.
- **Undocumented source**: the rates come from the data behind the bank's web page, which is not documented and can change without notice. If it changes, the update fails with a clear error instead of storing wrong values. The routes that use BOG show this as a ⚠️ note.
- **Source and terms**: the bank gives the information for general reference. LibreFolio downloads the rates for your own instance only. The provider's description names the source: «Source: Bank of Ghana».

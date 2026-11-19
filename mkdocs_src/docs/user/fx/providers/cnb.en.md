# <img src="https://www.cnb.cz/export/system/modules/org.opencms.apollo/resources/img/favicon_120.png" alt="" width="32"> Czech National Bank (CNB)

The **Czech National Bank (CNB)** provider retrieves the central bank exchange rate fixing of the Czech National Bank, quoted against the Czech koruna (CZK). Besides the major currencies, it is a daily source for the currencies of central Europe, such as the Hungarian forint, the Polish zloty and the Romanian leu, with a history back to 1991.

## 📊 Capabilities

- ✅ **Current Price**: daily fixing, updated every Czech working day
- ✅ **History**: from 1991
- ❌ **Search**: No asset search (FX rates only)

## 🔧 Specifications

- **Base Currency**: CZK 🇨🇿
- **Update Frequency**: every Czech working day, at around 2.30 p.m. Prague time
- **API Key**: Not required (public files)

## 💰 Supported Currencies

The CNB fixes about 30 currencies. LibreFolio reads the list from the bank, so it follows what the bank publishes. Among them:

- **Major**: USD 🇺🇸, EUR 🇪🇺, GBP 🇬🇧, JPY 🇯🇵, CHF 🇨🇭, AUD 🇦🇺, CAD 🇨🇦, NZD 🇳🇿
- **European/Regional**: HUF 🇭🇺, PLN 🇵🇱, RON 🇷🇴, DKK 🇩🇰, SEK 🇸🇪, NOK 🇳🇴, ISK 🇮🇸, TRY 🇹🇷
- **Global / Emerging**: CNY 🇨🇳, HKD 🇭🇰, SGD 🇸🇬, KRW 🇰🇷, INR 🇮🇳, IDR 🇮🇩, MYR 🇲🇾, PHP 🇵🇭, THB 🇹🇭, ILS 🇮🇱, BRL 🇧🇷, MXN 🇲🇽, ZAR 🇿🇦
- **Other**: XDR (the IMF's Special Drawing Right)

The bank's «other currencies», published once a month, are not offered: Banca d'Italia (BDI) publishes them every day.

## 📝 Important Notes

- **Quotes format**: rates are expressed as CZK per one unit of the foreign currency (e.g. 1 USD = 22.219 CZK on 19 November 2026). The bank quotes some currencies per 100 or 1000 units; LibreFolio divides them for you.
- **Fixing days only**: the fixing is declared on Czech working days and stays valid until the next one. LibreFolio stores the fixing days only, as the bank lists them. The routes that use CNB show this as an ℹ️ note.
- **Small units**: some currencies have three decimals per 100 or 1000 units (1000 IDR = 1.218 CZK), so their rates move in steps of up to about 0.1%.
- **Before 1993**: until 8 February 1993 the rates are those of the Czechoslovak koruna, which the Czech koruna replaced at par: the history runs on without a break.
- **History per currency**: each currency starts when the CNB began to fix it (for example the forint in 1997).
- **Source**: the bank's terms of use allow reusing its data and ask to state the CNB as the source. The provider's description does: «Source: the CNB».

# ![](../../../static/icons/fx/bdi.png) Banca d'Italia (BDI)

The **Banca d'Italia (BDI)** provider retrieves the daily exchange rates the Banca d'Italia publishes for about 150 currencies, quoted against the euro (EUR). It covers almost every currency in the world, so a currency no other provider in LibreFolio offers, such as the Nigerian naira or the Kenyan shilling, reaches the euro in one step.

## 📊 Capabilities

- ✅ **Current Price**: Daily rate, updated every Italian business day
- ✅ **History**: from 4 January 1999, the first day of the euro series
- ❌ **Search**: No asset search (FX rates only)

## 🔧 Specifications

- **Base Currency**: EUR 🇪🇺
- **Update Frequency**: every Italian business day
- **API Key**: Not required (public data)

## 💰 Supported Currencies

The Banca d'Italia publishes rates for about 150 currencies. LibreFolio reads the list from the bank, so it follows what the bank publishes. Among them:

- **Major**: USD 🇺🇸, GBP 🇬🇧, JPY 🇯🇵, CHF 🇨🇭, CAD 🇨🇦, AUD 🇦🇺, NZD 🇳🇿, CNY 🇨🇳
- **Africa**: NGN 🇳🇬 (Nigerian naira), KES 🇰🇪 (Kenyan shilling), GHS 🇬🇭 (Ghanaian cedi), EGP 🇪🇬 (Egyptian pound), UGX 🇺🇬 (Ugandan shilling), MAD 🇲🇦, ZAR 🇿🇦, XOF and XAF (CFA francs)
- **Asia and Middle East**: VND 🇻🇳 (Vietnamese dong), PKR 🇵🇰 (Pakistani rupee), BDT 🇧🇩, LKR 🇱🇰, AED 🇦🇪, SAR 🇸🇦, INR 🇮🇳, IDR 🇮🇩
- **Latin America and the Caribbean**: DOP 🇩🇴 (Dominican peso), PEN 🇵🇪, COP 🇨🇴, CLP 🇨🇱, ARS 🇦🇷, BRL 🇧🇷, MXN 🇲🇽

The naira, the shillings, the cedi, the dong, the Pakistani rupee and the Dominican peso, among many others, are not published by the ECB.

Currencies whose rate the bank has suspended (on 16 November 2026: the Belarusian rouble, the Iranian rial, the North Korean won and the Russian rouble) are not offered. The IMF's SDR (XDR), which the bank also lists, is offered like any other currency: it is the IMF's unit of account, a basket of USD, EUR, CNY, JPY and GBP, not a commodity.

## 📝 Important Notes

- **Quotes format**: rates are expressed as units of the foreign currency per one euro (e.g. 1 EUR = 1498.5186 NGN on 13 November 2026). LibreFolio normalizes the rate behind the scenes.
- **Indicative rates**: the Banca d'Italia publishes these rates as an indication, not as a benchmark. For the major currencies they are the ECB's reference rates; for the others the bank computes them, and for some currencies whose rate is set by their government the value can reflect the official rate of the day before. The routes that use BDI show this as a ⚠️ note.
- **For your own use**: the rates are downloaded by your LibreFolio instance and kept for you.
- **Holidays**: no rates are published at weekends or on Italian holidays.
- **History**: rates start on 4 January 1999. A first synchronization of the whole history takes a couple of seconds per currency.
- **Source**: the provider's description names the Banca d'Italia as the source of its rates: «Source: Banca d'Italia».

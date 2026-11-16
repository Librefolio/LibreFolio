# <img src="https://www.bcb.gov.br/favicon.ico" alt=""> Banco Central do Brasil (BCB)

The **Banco Central do Brasil (BCB)** provider retrieves the PTAX closing bulletin the Banco Central do Brasil publishes every Brazilian business day: about 150 currencies quoted against the US dollar (USD), and the Brazilian real (BRL). Like the Banca d'Italia, it covers almost every currency in the world, so a currency such as the Nigerian naira or the Kenyan shilling reaches the dollar in one step.

## 📊 Capabilities

- ✅ **Current Price**: Daily closing rate, every Brazilian business day
- ✅ **History**: from 1 February 1999
- ❌ **Search**: No asset search (FX rates only)

## 🔧 Specifications

- **Base Currency**: USD 🇺🇸
- **Update Frequency**: every Brazilian business day; the closing bulletin comes out around 13:10 Brasília time
- **API Key**: Not required (public open data)

## 💰 Supported Currencies

LibreFolio offers 152 currencies from the BCB bulletin, plus the US dollar and the Brazilian real. Among them:

- **Major**: EUR 🇪🇺, GBP 🇬🇧, JPY 🇯🇵, CHF 🇨🇭, CAD 🇨🇦, AUD 🇦🇺, NZD 🇳🇿, CNY 🇨🇳
- **Latin America and the Caribbean**: BRL 🇧🇷 (Brazilian real), ARS 🇦🇷, CLP 🇨🇱, COP 🇨🇴, PEN 🇵🇪, MXN 🇲🇽, DOP 🇩🇴 (Dominican peso), VES 🇻🇪 (Venezuelan bolívar)
- **Africa**: NGN 🇳🇬 (Nigerian naira), KES 🇰🇪 (Kenyan shilling), UGX 🇺🇬 (Ugandan shilling), GHS 🇬🇭 (Ghanaian cedi), EGP 🇪🇬 (Egyptian pound), MAD 🇲🇦, ZAR 🇿🇦, XOF and XAF (CFA francs)
- **Asia and Middle East**: VND 🇻🇳 (Vietnamese dong), PKR 🇵🇰 (Pakistani rupee), BDT 🇧🇩, LKR 🇱🇰, AED 🇦🇪, SAR 🇸🇦, INR 🇮🇳, IDR 🇮🇩

The naira, the shillings, the cedi, the dong, the Pakistani rupee and the Dominican peso, among many others, are not published by the ECB.

## 📝 Important Notes

- **Quotes format**: the bank quotes most currencies as units per one US dollar (e.g. 1 USD = 1348.365 NGN on 16 November 2026), and a few, such as the euro and the pound, as dollars per one unit (1 EUR = 1.1007 USD). LibreFolio reads each the right way and normalizes the rate behind the scenes.
- **Buying and selling**: the bank publishes a buying and a selling rate; LibreFolio stores their mean.
- **Through the dollar**: every BCB rate is against the US dollar, so every route that uses BCB goes through USD. The Brazilian real comes from the bank's own dollar rate.
- **The Sierra Leone leone**: the bank publishes it in old leones (SLL). LibreFolio stores it as the current leone, SLE, divided by 1000.
- **Note in the routes**: the routes that use BCB show these facts as an ℹ️ note.
- **Holidays**: no rates are published at weekends or on Brazilian holidays.
- **History**: rates start on 1 February 1999; for the Venezuelan bolívar (VES), from 4 October 2021, after its redenomination. A first synchronization of the whole history takes about three seconds per currency. If you synchronize many BCB currencies for the first time at once (more than about 35), some routes may not finish in time: synchronize again a few minutes later, and the rates already downloaded are reused.
- **Source and licence**: the rates come from the bank's PTAX dataset, published under the [Open Data Commons Open Database License (ODbL)](https://dadosabertos.bcb.gov.br/dataset/taxas-de-cambio-todos-os-boletins-diarios). The provider's description, shown in the route picker, names the source: «Source: Banco Central do Brasil, PTAX, ODbL». Parities other than USD/BRL come from Refinitiv and are not guaranteed by the bank.

# <img src="https://www.superfinanciera.gov.co/info/superfinancierav8/web/portal/img/favicon.png" alt="" width="32"> TRM Colombia (TRM)

The **TRM** provider retrieves the «Tasa de Cambio Representativa del Mercado», Colombia's official exchange rate of the US dollar against the Colombian peso (COP), certified by the Superintendencia Financiera de Colombia, with a history back to 1991.

## 📊 Capabilities

- ✅ **Current Price**: a value for every day, published the day before
- ✅ **History**: from 2 December 1991
- ❌ **Search**: No asset search (FX rates only)

## 🔧 Specifications

- **Base Currency**: COP 🇨🇴
- **Update Frequency**: every Colombian banking day, for the next day
- **API Key**: Not required

## 💰 Supported Currencies

- **USD** 🇺🇸 only

## 📝 Important Notes

- **Quotes format**: rates are expressed as pesos per one US dollar (e.g. 1 USD = 3316.70 COP on 14 November 2026). LibreFolio normalizes the rate behind the scenes.
- **How it is computed**: the TRM valid on a day comes from the spot trades of the previous Colombian banking day, and is published the day before.
- **Every day has a value**: weekends and holidays carry the TRM the Superintendencia declares valid for them, the one computed on the last banking day before. LibreFolio stores it on each of those days. The routes that use TRM show this as an ℹ️ note.
- **Source and licence**: the data come from Colombia's open-data portal (datos.gov.co) under the Creative Commons Attribution-ShareAlike 4.0 licence. The provider's description names the source: «Source: Superintendencia Financiera de Colombia».

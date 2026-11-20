# <img src="https://estadisticas.bcrp.gob.pe/favicon.ico" alt="" width="32"> Banco Central de Reserva del Perú (BCRP)

The **Banco Central de Reserva del Perú (BCRP)** provider retrieves the interbank exchange rate of the US dollar published by Peru's central bank, quoted against the Peruvian sol (PEN), with a history back to 1997.

## 📊 Capabilities

- ✅ **Current Price**: daily rate, published one to three days late
- ✅ **History**: from 2 January 1997
- ❌ **Search**: No asset search (FX rates only)

## 🔧 Specifications

- **Base Currency**: PEN 🇵🇪
- **Update Frequency**: every Peruvian business day, published one to three days later
- **API Key**: Not required

## 💰 Supported Currencies

- **USD** 🇺🇸 only: the interbank rate, sell side

The bank also publishes a euro rate, which LibreFolio does not use: it does not follow the reference rates (between 5 and 12 November 2026 it was 2% to 6% above US dollar × EUR/USD).

## 📝 Important Notes

- **Quotes format**: rates are expressed as soles per one US dollar (e.g. 1 USD = 3.4162 PEN on 10 November 2026). LibreFolio normalizes the rate behind the scenes.
- **Which rate**: the average of the day's interbank sells of US dollars. The routes that use BCRP show this as an ℹ️ note.
- **Delay**: the bank publishes each day one to three days later. Until then the day has no value; it arrives at a later update.
- **Holidays**: no rate on Peruvian holidays.
- **Source**: the bank's conditions of use allow reusing its statistics if the source is cited. The provider's description does: «Source: BCRP (BCRPData)».

# <img src="https://cpx.cbc.gov.tw/favicon.ico" alt="" width="32"> Central Bank of the Republic of China (Taiwan) (CBC)

The **Central Bank of the Republic of China (Taiwan) (CBC)** provider retrieves the interbank closing rate of the US dollar against the New Taiwan dollar (TWD), published by Taiwan's central bank on the same day, with a history back to 2008.

## 📊 Capabilities

- ✅ **Current Price**: daily rate, published the same afternoon
- ✅ **History**: from 2 January 2008
- ❌ **Search**: No asset search (FX rates only)

## 🔧 Specifications

- **Base Currency**: TWD 🇹🇼
- **Update Frequency**: every Taiwanese business day, between 16:00 and 17:00 Taiwan time
- **API Key**: Not required (public open data)

## 💰 Supported Currencies

- **USD** 🇺🇸 only

The bank's table of other currencies is published about two weeks late, so LibreFolio does not use it: Banca d'Italia (BDI) publishes those currencies every day.

## 📝 Important Notes

- **Quotes format**: rates are expressed as New Taiwan dollars per one US dollar (e.g. 1 USD = 32.942 TWD on 19 November 2026). LibreFolio normalizes the rate behind the scenes.
- **Which rate**: the interbank closing rate of the day, from Taipei Forex Inc. The routes that use CBC show this as an ℹ️ note.
- **Holidays**: no rate at weekends and on Taiwanese holidays.
- **Source and licence**: the data are open, under Taiwan's Open Government Data License, which asks to name the source. The provider's description does: «Source: Central Bank of the Republic of China (Taiwan)».

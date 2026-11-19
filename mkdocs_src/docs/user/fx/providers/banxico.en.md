# <img src="https://www.banxico.org.mx/favicon.ico" alt=""> Banco de México (BANXICO)

The **Banco de México (BANXICO)** provider retrieves the official exchange rates of Mexico's central bank, quoted against the Mexican peso (MXN). Its main value is the **FIX**, the official US dollar / peso rate used in Mexico, with a history back to 1991. It needs a free API token from the bank: [see below](#token).

## 📊 Capabilities

- ✅ **Current Price**: daily rate, updated every Mexican banking day
- ✅ **History**: USD from 12 November 1991; EUR, JPY, GBP, CNY and the SDR from 31 July 2018
- ❌ **Search**: No asset search (FX rates only)

## 🔧 Specifications

- **Base Currency**: MXN 🇲🇽
- **Update Frequency**: every Mexican banking day; the FIX is determined at 12:00 Mexico City time
- **API Key**: Required (free): [Getting the API token](#token)

## 💰 Supported Currencies

A fixed list of six currencies, all quoted against MXN:

- **USD** 🇺🇸: the official **FIX**, from 1991
- **EUR** 🇪🇺, **JPY** 🇯🇵, **GBP** 🇬🇧, **CNY** 🇨🇳 and **XDR** (the IMF's Special Drawing Right): daily quotes, from 2018

## 📝 Important Notes

- **Quotes format**: rates are expressed as MXN per one unit of the foreign currency. LibreFolio normalizes the rate behind the scenes.
- **Which dollar rate**: USD is the FIX, determined at 12:00 Mexico City time on each banking day and dated that day, not the day the Diario Oficial (DOF) publishes it. The routes that use BANXICO show this as an ℹ️ note.
- **JPY steps**: the yen is published with four decimals (for example 0.1160 MXN), so its rate moves in steps of about 0.1%.
- **Holidays**: no rate on Mexican bank holidays.
- **Source**: the bank's terms of use («Salvedad de uso») allow reusing its data if the source and the bank's web address are cited. The provider's description does: «Source: Banco de México (banxico.org.mx)».

## 🔑 Getting the API token {: #token }

The bank's data service asks for a token, and it is free.

1. Open the bank's token page: [banxico.org.mx/SieAPIRest/service/v1/token](https://www.banxico.org.mx/SieAPIRest/service/v1/token).
2. Under «Solicitar token», type the security code of the image and ask for the token: the page shows it, a string of 64 characters. Keep it private: it is yours.
3. An **administrator** of your LibreFolio sets it, in either way:
    - in the instance's plugin settings, for the FX provider **BANXICO**, the field **API token**;
    - or with the environment variable `LIBREFOLIO_PLUGIN_FX_BANXICO_TOKEN`, which then **locks** the field.

   How plugin settings and variables work: [Plugin Settings](../../settings/plugins.md) (user manual) and [Plugin Settings](../../../admin/configuration_secrets.md#plugin-settings) (administrator). The token is a [secret](../../settings/plugins.md#secrets).

Until the token is set, BANXICO is [to configure](../../settings/plugins.md#configured): in the route window of a pair
(for example MXN → USD) its route is greyed out, and clicking it says that the Banxico API token is missing; an
administrator's **Configure** button there opens the same **API token** field. The sync does not call the bank.

The bank limits each token to 200 requests every 5 minutes and 10 000 a day; LibreFolio makes one request per update, far below it.

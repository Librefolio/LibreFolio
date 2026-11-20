# <img src="https://ecos.bok.or.kr/favicon.ico" alt="" width="32"> Bank of Korea (BOK)

The **Bank of Korea (BOK)** provider retrieves the daily exchange rates published by Korea's central bank, quoted against the won (KRW): the basic rates of the US dollar and the yuan, and the rates of 41 more currencies, many of Asia and the Middle East. It needs a free API key from the bank: [see below](#key).

## 📊 Capabilities

- ✅ **Current Price**: daily rate, Korean business days
- ✅ **History**: USD from 1964; most major currencies from the 1970s–1990s; 22 currencies from 2015; CNY from 2016
- ❌ **Search**: No asset search (FX rates only)

## 🔧 Specifications

- **Base Currency**: KRW 🇰🇷
- **Update Frequency**: every Korean business day
- **API Key**: Required (free): [Getting the API key](#key)

## 💰 Supported Currencies

43 currencies, all against KRW:

- **Major**: USD 🇺🇸, EUR 🇪🇺, JPY 🇯🇵, GBP 🇬🇧, CHF 🇨🇭, CAD 🇨🇦, AUD 🇦🇺, NZD 🇳🇿, CNY 🇨🇳, HKD 🇭🇰
- **Asia**: TWD 🇹🇼, SGD 🇸🇬, THB 🇹🇭, MYR 🇲🇾, IDR 🇮🇩, PHP 🇵🇭, VND 🇻🇳, BND 🇧🇳, INR 🇮🇳, PKR 🇵🇰, BDT 🇧🇩, MNT 🇲🇳, KZT 🇰🇿
- **Europe**: SEK 🇸🇪, NOK 🇳🇴, DKK 🇩🇰, HUF 🇭🇺, PLN 🇵🇱, CZK 🇨🇿, RUB 🇷🇺, TRY 🇹🇷
- **Middle East and Africa**: SAR 🇸🇦, QAR 🇶🇦, AED 🇦🇪, KWD 🇰🇼, BHD 🇧🇭, JOD 🇯🇴, ILS 🇮🇱, EGP 🇪🇬, ZAR 🇿🇦
- **Americas**: MXN 🇲🇽, BRL 🇧🇷, ARS 🇦🇷

## 📝 Important Notes

- **Quotes format**: won per one unit of the foreign currency (e.g. 1 USD = 1331.1 KRW on 19 November 2026); the yen, the rupiah and the dong are quoted per 100 units. LibreFolio normalizes the rate behind the scenes.
- **Which rates**: USD and CNY are the bank's basic rates; the others are arbitraged rates the bank builds from them.
- **Two decimals**: small currencies move in coarse steps: the Mongolian tögrög (0.37 KRW) by about 3%, the Argentine peso by about 1%.
- **Russian rouble**: the RUB rate is the one the Bank of Korea publishes, not the Central Bank of Russia's.
- **Source and terms**: the terms of use are accepted when the key is requested and could not be read beforehand. LibreFolio downloads the rates for your own instance only. The provider's description names the source: «Source: Bank of Korea (ECOS)».

## 🔑 Getting the API key {: #key }

The bank's data service, ECOS, asks for a key, and it is free.

1. Open the ECOS Open API site: [ecos.bok.or.kr/api](https://ecos.bok.or.kr/api/), and register to apply for an authentication key. Keep it private: it is yours.
2. An **administrator** of your LibreFolio sets it, in either way:
    - in the instance's plugin settings, for the FX provider **BOK**, the field **API key**;
    - or with the environment variable `LIBREFOLIO_PLUGIN_FX_BOK_API_KEY`, which then **locks** the field.

   How plugin settings and variables work: [Plugin Settings](../../settings/plugins.md) (user manual) and [Plugin Settings](../../../admin/configuration_secrets.md#plugin-settings) (administrator). The key is a [secret](../../settings/plugins.md#secrets).

Until the key is set, BOK is [to configure](../../settings/plugins.md#configured): in the route window of a pair
(for example KRW → USD) its route is greyed out, and clicking it says that the Bank of Korea ECOS API key is missing;
an administrator's **Configure** button there opens the same **API key** field. The sync does not call the bank.

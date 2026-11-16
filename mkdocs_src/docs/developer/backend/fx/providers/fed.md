# 🇺🇸 FED — Federal Reserve (FRED)

| Property | Value |
|----------|-------|
| **Code** | `FED` |
| **Base Currency** | USD |
| **API Endpoint** | `https://fred.stlouisfed.org/graph/fredgraph.csv` |
| **API Format** | CSV (public download, no API key) |
| **API Key** | Not required |
| **Currencies** | 23 (`CURRENCY_SERIES`) |
| **Update Frequency** | One value per US business day, **released once a week** (H.10, Mondays 4:15 p.m. ET) |
| **API Docs** | [FRED Economic Data](https://fred.stlouisfed.org/) |

### ⚙️ How It Works

The Federal Reserve provides exchange rate data through FRED (Federal Reserve Economic Data). The provider downloads one CSV per currency series.

- **Series and direction**: `CURRENCY_SERIES` maps each currency to a `FredSeries(series_id, quote, first_day)`.
  `quote` is a `FredQuote` and says how FRED publishes the series, as its title reads:
    - `USD_PER_UNIT` — the four `DEXUS..` series («U.S. Dollars to One Euro»): `DEXUSEU` 1.08 → `(d, 'EUR', 'USD', 1.08)`;
    - `UNITS_PER_USD` — every `DEX..US` series («Japanese Yen to One U.S. Dollar»): `DEXJPUS` 158.2 → `(d, 'USD', 'JPY', 158.2)`.

  The rate is returned as published, «1 base = rate quote»; the FX service normalizes the pair (alphabetical order,
  inverted when needed). Nothing is inverted in the plugin. Every series declares its direction: a new series without
  one cannot be added by mistake, and `test_fx_fed_quotes.py` pins all 23 against a table written by hand.
- **`first_day`**: the first day a series is in the currency's present unit. Only VES has one (see below): the request
  starts there and earlier lines are dropped; a range ending before it makes no request.
- **Multi-unit currencies**: none (FRED quotes every currency per 1 unit, JPY included).
- **Too many requests**: an HTTP 429 on any currency's request refuses the whole call. After the parallel fetch, `raise_longest_refusal()` raises the `FXRateLimitedError` with the longest `Retry-After`, and the core pauses the provider ([Paused Providers](../configuration.md#paused-providers)).

### 💰 Supported Currencies

EUR 🇪🇺, GBP 🇬🇧, JPY 🇯🇵, CAD 🇨🇦, CHF 🇨🇭, AUD 🇦🇺, INR 🇮🇳, BRL 🇧🇷, MXN 🇲🇽, ZAR 🇿🇦, SGD 🇸🇬, HKD 🇭🇰, KRW 🇰🇷, TWD 🇹🇼, NZD 🇳🇿, THB 🇹🇭, SEK 🇸🇪, NOK 🇳🇴, DKK 🇩🇰, CNY 🇨🇳, MYR 🇲🇾, LKR 🇱🇰, VES 🇻🇪.

### 🗺️ Series ID Mapping

| Currency | FRED Series | Direction (`FredQuote`) | Returned tuple |
|----------|-------------|-------------------------|----------------|
| EUR 🇪🇺 | `DEXUSEU` | USD per 1 EUR (`USD_PER_UNIT`) | `(d, EUR, USD, v)` |
| GBP 🇬🇧 | `DEXUSUK` | USD per 1 GBP (`USD_PER_UNIT`) | `(d, GBP, USD, v)` |
| AUD 🇦🇺 | `DEXUSAL` | USD per 1 AUD (`USD_PER_UNIT`) | `(d, AUD, USD, v)` |
| NZD 🇳🇿 | `DEXUSNZ` | USD per 1 NZD (`USD_PER_UNIT`) | `(d, NZD, USD, v)` |
| JPY 🇯🇵 | `DEXJPUS` | JPY per 1 USD (`UNITS_PER_USD`) | `(d, USD, JPY, v)` |
| CAD 🇨🇦 | `DEXCAUS` | CAD per 1 USD | `(d, USD, CAD, v)` |
| CHF 🇨🇭 | `DEXSZUS` | CHF per 1 USD | `(d, USD, CHF, v)` |
| SEK 🇸🇪 | `DEXSDUS` | SEK per 1 USD | `(d, USD, SEK, v)` |
| DKK 🇩🇰 | `DEXDNUS` | DKK per 1 USD | `(d, USD, DKK, v)` |
| NOK 🇳🇴 | `DEXNOUS` | NOK per 1 USD | `(d, USD, NOK, v)` |
| CNY 🇨🇳 | `DEXCHUS` | CNY per 1 USD | `(d, USD, CNY, v)` |
| INR 🇮🇳 | `DEXINUS` | INR per 1 USD | `(d, USD, INR, v)` |
| BRL 🇧🇷 | `DEXBZUS` | BRL per 1 USD | `(d, USD, BRL, v)` |
| MXN 🇲🇽 | `DEXMXUS` | MXN per 1 USD | `(d, USD, MXN, v)` |
| ZAR 🇿🇦 | `DEXSFUS` | ZAR per 1 USD | `(d, USD, ZAR, v)` |
| SGD 🇸🇬 | `DEXSIUS` | SGD per 1 USD | `(d, USD, SGD, v)` |
| HKD 🇭🇰 | `DEXHKUS` | HKD per 1 USD | `(d, USD, HKD, v)` |
| KRW 🇰🇷 | `DEXKOUS` | KRW per 1 USD | `(d, USD, KRW, v)` |
| TWD 🇹🇼 | `DEXTAUS` | TWD per 1 USD | `(d, USD, TWD, v)` |
| THB 🇹🇭 | `DEXTHUS` | THB per 1 USD | `(d, USD, THB, v)` |
| MYR 🇲🇾 | `DEXMAUS` | MYR per 1 USD | `(d, USD, MYR, v)` |
| LKR 🇱🇰 | `DEXSLUS` | LKR per 1 USD | `(d, USD, LKR, v)` |
| VES 🇻🇪 | `DEXVZUS` | VES per 1 USD, from 2021-10-04 (`first_day`) | `(d, USD, VES, v)` |

!!! warning "Before 1.4 the sixteen `DEX..US` series came back inverted"

    Up to 1.3 the plugin read every series as «USD per 1 unit» and returned `(d, JPY, USD, 158.23)`: «1 JPY = 158.23 USD».
    Rates stored from FED for those currencies are wrong until the user syncs them again: a sync upserts on
    `(date, base, quote)` and overwrites them. No migration rewrites them.

### 🇻🇪 VES and the redenominations

`DEXVZUS` joins three units in one column: VEF until 2018-08-17, the 2018 bolívar (VEF / 10⁵) until 2021-10-01, and
today's bolívar (2018 bolívar / 10⁶) since 2021-10-04. Only the last one is today's VES, so `first_day` cuts the series
there: an older value would be stored as a VES rate a million times too large.

### 📅 Release schedule

**Release schedule**: the H.10 series hold one value per US business day (the noon buying rates in New York, certified by the Federal Reserve Bank of New York), but they are released once a week, on Mondays at 4:15 p.m. ET, with the previous week's days. The latest value is therefore 3 to about 10 days old. In a chain route, a FED leg has no rate for the days after the last release, so those days get no chain rate until the next Monday. Source: [H.10 — About](https://www.federalreserve.gov/releases/h10/about.htm).

The provider says it in the four languages with the same mechanism as SNB's monthly note (`warning_i18n`), at
**info** level (`warning_level = "info"`): ℹ️ on every route that uses FED, not ⚠️, because the rates are complete and
daily, only released late. The English text:

> FED rates are daily: one value per US business day. The Federal Reserve publishes them once a week, on Mondays, with
> the days of the previous week, so the latest FED rate can be up to about 10 days old.

### ⚠️ Limitations

- One HTTP request per currency, sent in parallel (`asyncio.gather`).
- No data on US holidays and weekends.
- Some series may have occasional gaps.

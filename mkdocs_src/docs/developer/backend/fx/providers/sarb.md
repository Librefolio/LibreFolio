# 🇿🇦 SARB — South African Reserve Bank

| Property | Value |
|----------|-------|
| **Code** | `SARB` |
| **Base Currency** | ZAR |
| **API Endpoint** | `https://custom.resbank.co.za/SarbWebApi/WebIndicators/Shared/GetTimeseriesObservations/{CODE}/{yyyy-MM-dd}/{yyyy-MM-dd}` |
| **API Format** | JSON list, one series per request, newest first |
| **API Key** | Not required |
| **Terms** | [Disclaimer](https://www.resbank.co.za/en/home/quick-links/disclaimer): no copy, reproduction or distribution without the bank's written consent. Developer decision D1: offered for a self-hosted instance that stores the rates for its owner |
| **Currencies** | A fixed table of 25 plus ZAR (`SERIES` in the plugin), RUB included since the developer's answer to Q3 |
| **Update Frequency** | Every South African business day, after about 10:30 SAST |
| **Historical Data** | From 2010-01-01 in LibreFolio (`FIRST_DAY`); the series themselves start in 1970–1990 |
| **Series List** | `…/WebIndicators/HistoricalExchangeRatesDaily/`, behind the bank's [Selected Historical Rates](https://www.resbank.co.za/en/home/what-we-do/statistics/key-statistics/selected-historical-rates) page |

### ⚙️ How It Works

The South African Reserve Bank publishes its daily rates through the service API behind its web pages
(`custom.resbank.co.za`). The provider (`backend/app/services/fx_providers/sarb/plugin.py`) asks one series per
currency.

- **No API documentation**: the API's help page, `/SarbWebApi/Help`, answered 404 on 16 and 19 November 2026. The
  series codes come from `…/WebIndicators/HistoricalExchangeRatesDaily/`, the list the bank's «Selected Historical
  Rates» page reads: each entry has a `TimeseriesCode` and a `Name` such as «Rand per US Dollar» or «Switzerland: Franc
  per Rand». The name gives the direction.
- **One request per currency**: `fetch_rates()` asks the series of each asked currency in sorted order, with a pause of
  `PAUSE_SECONDS` (0.3 s) between two requests (D9). An unknown code, or a range without data (a weekend), answers 200
  with `[]`.
- **Values read as `Decimal`**: the answer is parsed with `json.loads(…, parse_float=Decimal)`, so `0.0488` stays
  `Decimal("0.0488")`; no value passes through a float. Rows come back newest first and are returned oldest first.
- **Start date**: `"min"`, and any start before 2010-01-01, asks from `FIRST_DAY` (see the budget below). ZAR alone
  makes no request; an asked currency the table does not hold (PLN…) gets an empty list.
- **Base currency**: `fetch_rates()` with a `base_currency` other than ZAR (or None) raises `ValueError`.

### ↔️ Direction and Unit

The direction is the series', and it is mixed:

| Series | Currencies | The plugin returns |
|--------|-----------|--------------------|
| «Rand per X» (`EXCX135D`, `EXCZ001D`, `EXCZ002D`) | USD, GBP, EUR | `(d, CUR, 'ZAR', ZAR per 1 CUR)` |
| «X per Rand» (`EXCB…D`) | AUD BWP BRL CAD CNY DKK HKD INR ILS JPY KES MWK MZN NZD NOK KRW SEK CHF TWD THB ZMW RUB | `(d, 'ZAR', CUR, CUR per 1 ZAR)` |

Worked example, 19 November 2026: «Rand per US Dollar» `17.2532` gives `(d, 'USD', 'ZAR', Decimal('17.2532'))`, «1 USD =
17.2532 ZAR»; «Switzerland: Franc per Rand» `0.0488` gives `(d, 'ZAR', 'CHF', Decimal('0.0488'))`, «1 ZAR = 0.0488
CHF». The FX service normalizes the pair; nothing is inverted in the plugin. JPY uses «Yen per Rand» (`EXCB120D`,
9.2609), never the «Rand per Yen» form (0.1064 with four decimals).

**Four decimals**: every value has four decimals (`FormatNumber 0.0000`). A small «X per Rand» value is rounded: CHF
0.0488 by up to about 0.1%, CAD 0.0830 and AUD 0.0865 by about 0.06%. The provider says so in its note, at **warning**
level, as BOC does for IDR.

### 📅 The Day of a Rate (D2)

The rate is the «weighted average of the banks' daily rates at approximately 10:30 am», one per South African business
day. The value of the day is published that morning, under that day. Weekends and South African holidays have no row;
the plugin returns every row under its `Period`, and fills nothing.

### 💰 Supported Currencies

`get_supported_currencies()` returns the fixed table plus ZAR, without a request: the direction of each series is fixed
in the table anyway. The list also holds the four USD cross rates and the effective exchange rate index, which are no
rate against ZAR.

**RUB** («Russia: Rouble per Rand», `EXCB110D`) is served since the developer's answer to Q3 (19 November 2026): the
rouble published by a bank other than the Central Bank of Russia (CBR, suspended by decision D4) is a route like the
others. The note says, in a neutral way, that the rate is the one the SARB publishes (roubles per rand), not the Central
Bank of Russia's.

### 📦 Request Budget

One request per currency. Measured on 2026-11-19 on the real API:

| Range | Requests | Time |
|-------|----------|------|
| one series from 1970 | 1 | ~7 s, ~4 MB |
| one series from 2010 | 1 | ~1.5 s, ~1.2 MB |
| 14 days, 2 currencies | 2 | 2.0 s |
| `"min"` (from 2010), 24 currencies (before RUB) | 24 | 68.9 s, pause included (25 with RUB: about 72 s, estimated) |

With the history from 1970, 25 currencies would take about 3 minutes, over the 120 s the core gives one leg
(`fx/sync.py`): hence `FIRST_DAY` 2010-01-01. A route usually asks one to three SARB currencies. The ECB and BDI hold the
older ZAR history.

!!! warning "The bank's API is not always that fast"

    The times above were measured on the afternoon of 19 November 2026. The same evening every request took 20–35 s,
    whatever its range (14 days of USD: 22.6 s; RUB from 2010: 29–35 s). At such times a sync that asks several SARB
    currencies can exceed the 120 s of a leg, and the sync tries the next route.

### 🚨 Errors

| Answer | Result |
|--------|--------|
| HTTP 429 on any currency | `FXRateLimitedError` (its `Retry-After`, through `raise_if_fx_rate_limited()`); no further currency is asked |
| Another HTTP error, a network failure, an HTML page, non-JSON text, or JSON that is not a list, for one currency | That currency gets an empty list, with a warning; the others are asked and returned (XRL-H09) |
| The same for **every** asked currency | `FXServiceError` («SARB API error for every asked series: …»): the sync tries the next route |
| A row whose `Value` is null, zero, negative or not a number, or whose `Period` cannot be read (X-R50) | That day only is skipped |

The endpoint is a service API of the bank's site, not a documented product: a change of its shape fails the call with
a clear error instead of reading wrong values.

### ⚖️ Terms and robots.txt

The bank's disclaimer says its material «may not be copied, reproduced, adapted, published or distributed in any form
whatsoever without the prior written consent» of the bank. Developer decision D1 (lane 75): a self-hosted instance that
downloads the rates for its owner is not a redistribution; nothing downloaded from the bank is committed, and the tests
use synthetic answers only. The description names the source («Source: South African Reserve Bank»). `robots.txt` of
`www.resbank.co.za` disallows only `/content/dam/`; `custom.resbank.co.za` has none.

### ⚠️ Limitations

- History from 2010 only, to fit the core's time for a leg.
- Small «X per Rand» values are rounded by up to about 0.1%.
- No rate on South African non-business days.
- No documentation of the API: its shape can change without notice.

### 🧪 Tests

`backend/test_scripts/test_services/test_fx_sarb.py` pins the direction of both kinds of series (USD; CHF and JPY), the
exact decimals, one request per currency in sorted order with a pause, the start from 2010, the skipped rows, RUB served as
roubles per rand, the 429 that stops the series, one failed series that leaves the others, every series failed as an error and the
static catalogue, all with synthetic answers written by hand (no network, no DB, no server). It is registered among the
provider error paths:

```bash
./dev.py test services provider-errors
```

The external test reads the real API:

```bash
./dev.py test external fx-providers --providers SARB
```

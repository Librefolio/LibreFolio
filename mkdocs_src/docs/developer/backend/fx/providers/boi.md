# 🇮🇱 BOI — Bank of Israel

| Property | Value |
|----------|-------|
| **Code** | `BOI` |
| **Base Currency** | ILS |
| **API Endpoint** | `https://edge.boi.gov.il/FusionEdgeServer/sdmx/v2/data/dataflow/BOI.STATISTICS/EXR/1.0/{keys}?startperiod=…&endperiod=…&format=csv` |
| **API Format** | SDMX REST, CSV (the endpoint of the bank's own [guide](https://www.boi.org.il/media/upqgqpuv/extracting-representative-exchange-rates-from-the-new-series-database.pdf)) |
| **API Key** | Not required |
| **Terms** | [Terms of use](https://www.boi.org.il/en/terms-of-use/): no copying, publishing or disseminating without written consent. Developer decision D1: offered for a self-hosted instance; the paid cloud turns it off |
| **Currencies** | A fixed list: 13 currencies plus ILS |
| **Update Frequency** | Israeli business days |
| **Historical Data** | From 1986-01-01 (`FIRST_DAY`); EUR from 1999-01-04 |

### ⚙️ How It Works

The provider (`backend/app/services/fx_providers/boi/plugin.py`) reads the representative rates from the bank's SDMX
server: one series per currency, `RER_{CUR}_ILS`, **every asked series in one request** (the keys joined by `+`),
as CSV. The columns are read by name.

- **The dataflow mixes other series** (basket indices, volatilities, implied rates such as `RER_USD_ILS_GLBLIMP`):
  only the asked `RER_{CUR}_ILS` rows are read.
- **An empty range** (a weekend, a holiday) answers, about half the time each, **200 with an empty body** (labelled
  `text/html`) **or 404 with an HTML error page**; a range with rates always answers 200 CSV (20 requests, 19 November
  2026). So a 404 or no rate at all is an empty range when it spans at most `EMPTY_SPAN_DAYS` (10 days); over a longer
  range it is an error («no rate … the API may have moved»): the longest gap since 1986 is 7 days (Passover).
- **Validation**: a body that starts with `<` (a block page, or the API changed) or a CSV without `SERIES_CODE`,
  `TIME_PERIOD`, `OBS_VALUE`, `UNIT_MULT` is an error.
- **Start date**: `"min"`, and any start before 1986-01-01, keeps from `FIRST_DAY`. ILS alone, or only currencies
  outside the list, makes no request.
- **Base currency**: `fetch_rates()` with a `base_currency` other than ILS (or None) raises `ValueError`.

### ↔️ Direction and Unit

Every value is ILS per `10**UNIT_MULT` units: `UNIT_MULT` is 2 for JPY (per 100 yen), 0 for the others. The provider
returns `(d, CUR, 'ILS', OBS_VALUE / 10**UNIT_MULT)`, «1 CUR = v ILS»: USD 3.282, JPY 2.0519 per 100 → 0.020519
(19 November 2026).

### 📅 The Day of a Rate (D2) and Why the History Starts in 1986

Each value is returned under its `TIME_PERIOD`, in ascending order. The bank publishes its history already rescaled to
the new shekel, from 1948 (USD 0.000025), daily from 1977. Measured on 2026-11-19 (175 338 rows, 14 series):

- **1980 to September 1985** (the old shekel): the non-USD series carry **×1000 values on most Sundays** (about
  3 000 days in all: AUD 0.0039429, 3.9429, 0.003983 in January 1980). USD has none.
- **September to December 1985**: JOD and LBP carry ÷10 values on Sundays (JOD 3.8123, 0.3812, 3.801).
- **So `FIRST_DAY` is 1986-01-01.** Since then a few single days remain, which the provider does not detect: JOD
  2.5575 on 1991-03-04 (between 2.89 and 2.93), JOD 6.2303 on 2002-10-07 (between 6.83 and 6.84), and some moves of
  EGP in 1989–1992 and ZAR in December 2001 that may be real. **To be reviewed with the developer** (lane 75, L35).
- **Sundays** until 2025 are Israeli business days, not errors.
- **No conflicting duplicate**; a day with two different values would be dropped (X-R50).

**LBP is not served**: the bank quotes it per 10 pounds (`UNIT_MULT` 1) with four decimals, 0.0003 or 0.0004 since the
pound's collapse, steps of about 30%.

### 📦 Request Budget

Measured on 2026-11-19:

| Range | Requests | Answer | Time |
|-------|----------|--------|------|
| 14 days, the 13 currencies | 1 | 9 KB, 143 rates | 0.4 s |
| A weekend | 1 | no rate (empty or 404) | 0.4 s |
| `"min"`, the 13 currencies | 1 | 9.1 MB, 133 849 rates | 3.3 s |

### 🚨 Errors

| Answer | Result |
|--------|--------|
| HTTP 429 | `FXRateLimitedError` (its `Retry-After`, through `raise_if_fx_rate_limited()`) |
| HTTP 404, an empty body or a header-only CSV over at most 10 days | No rows |
| The same over more than 10 days | `FXServiceError` («no rate … the API may have moved») |
| Any other HTTP error, or a network failure | `FXServiceError` («BOI API error …»), logged as a warning |
| A body starting with `<`, or a CSV without the four columns | `FXServiceError` |
| A row of another series, an unreadable day, unit or value, a value not positive | That row is skipped |

### ⚖️ Terms

The [terms of use](https://www.boi.org.il/en/terms-of-use/) (read on 19 November 2026; the page was behind a Radware
check during the research) say the site's information is «the exclusive property of the Bank of Israel», and the user
«may not copy, publish, disseminate, transmit or sell» it «without the prior written consent of the BOI». Developer
decision D1 (lane 75), as for SARB and BDI: the provider is offered for a self-hosted instance that stores the rates
for its owner; the paid cloud turns it off (`LIBREFOLIO_FX_PROVIDERS_ENABLED`). Nothing downloaded from the bank is
committed; the tests use synthetic answers only. The description names the source («Source: Bank of Israel»).

The note (`warning_i18n`) is at **warning** level: restrictive terms, a history cut to 1986 and residual wrong days are
limits that can mislead.

### ⚠️ Limitations

- A wrong value on a business day is not detected (JOD on 1991-03-04 and 2002-10-07).
- No history before 1986, and no LBP.
- An asked currency with no rate over a long range fails the call (EUR alone before 1999, for example).

### 🧪 Tests

`backend/test_scripts/test_services/test_fx_boi.py` pins the one request and its keys, the columns read by name, the
unit, the series left out, the skipped rows, the duplicates, the empty range (404, empty body, header only) and its
10-day limit, every answer that is not the series' CSV, the 429, the HTTP errors and the network failures, all with
synthetic answers written by hand (no network, no DB, no server). It is registered among the provider error paths:

```bash
./dev.py test services provider-errors
```

The external test reads the real API:

```bash
./dev.py test external fx-providers --providers BOI
```

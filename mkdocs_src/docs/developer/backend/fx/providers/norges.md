# 🇳🇴 NORGES — Norges Bank

| Property | Value |
|----------|-------|
| **Code** | `NORGES` |
| **Base Currency** | NOK |
| **API Endpoint** | `https://data.norges-bank.no/api/data/EXR/B.<c1>+<c2>+….NOK.SP` |
| **API Format** | CSV (SDMX, `format=csv`, `;`-separated), every asked currency in one request |
| **API Key** | Not required |
| **Licence** | Norwegian Licence for Open Government Data, NLOD 2.0 ([national data catalogue](https://data.norge.no/en/datasets/23076ce8-b442-407c-817f-0d4ec3cbe744)): free reuse with attribution |
| **Currencies** | Discovered at runtime by `get_supported_currencies()`: on 2026-11-16, 35 plus NOK. `GET /fx/providers` caches the list for 24 h (`backend/app/services/fx/catalog.py`) |
| **Update Frequency** | Daily, Norwegian business days, around 16:00 CET |
| **Historical Data** | From 1980-12-10 for the oldest series (USD, JPY…), from 1999-01-04 for EUR, later for others (VND from 2021-01-04) |
| **API Docs** | [Norges Bank open data](https://www.norges-bank.no/en/topics/statistics/open-data/), [query builder](https://app.norges-bank.no/query/index.html#/en/) |

### ⚙️ How It Works

Norges Bank, the central bank of Norway, publishes its daily exchange rates through an SDMX REST API. The provider
(`backend/app/services/fx_providers/norges/plugin.py`) reads the dataflow `EXR`, business-day spot series
`B.<CUR>.NOK.SP`, as CSV.

- **One request for every currency**: `fetch_rates()` joins the asked currencies in one key, `B.USD+JPY+….NOK.SP`, with
  `format=csv`, `startPeriod` and `endPeriod`. The answer holds one row per series and business day. NOK alone makes no
  request; a currency the bank does not know is ignored by the API.
- **No `locale` parameter**: with `locale=en` a value carries a thousands separator (CHF `1,140.68`), with `locale=no` a
  decimal comma. Without it the values are plain (`1140.68`), and the plugin never sends it.
- **Columns read**: `BASE_CUR` (the foreign currency), `QUOTE_CUR` (NOK), `UNIT_MULT`, `TIME_PERIOD`, `OBS_VALUE`. A row
  of a currency that was not asked, or not against NOK, is skipped.
- **Start date**: `"min"` asks from 1900-01-01 (`FX_HISTORY_MIN_FALLBACK`); the API answers each series from its own
  first day.
- **Dates**: every value keeps the day the bank gives it. The plugin filters no day: the sync, not the plugin, drops the
  days after the sync's end.
- **Base currency**: `fetch_rates()` with a `base_currency` other than NOK (or None) raises `ValueError`.

### ↔️ Direction and Unit

Every series is «NOK per 10<sup>UNIT_MULT</sup> units of the foreign currency». `UNIT_MULT` is 0 for USD, 2 for JPY,
SEK, DKK, CHF and others: the plugin reads it from each row, never from a table of its own. `_parse_row()` divides `OBS_VALUE` by 10<sup>UNIT_MULT</sup> and returns the rate
per one unit, in the bank's direction: `(d, CUR, 'NOK', NOK per 1 CUR)`, «1 CUR = v NOK». The FX service normalizes the
pair (alphabetical order, inverted when needed); nothing is inverted in the plugin.

Worked example, the JPY row of one day:

| `BASE_CUR` | `QUOTE_CUR` | `UNIT_MULT` | `TIME_PERIOD` | `OBS_VALUE` | Meaning |
|------------|-------------|-------------|---------------|-------------|---------|
| JPY | NOK | 2 | 2026-01-05 | 5.9772 | 100 JPY = 5.9772 NOK |

5.9772 / 10² = 0.059772, so the plugin returns `(date(2026, 1, 5), 'JPY', 'NOK', Decimal('0.059772'))`. A USD row with
`UNIT_MULT` 0 and `OBS_VALUE` 9.5000 is returned as published: `(d, 'USD', 'NOK', Decimal('9.5000'))`.

### 💰 Supported Currencies

On 2026-11-16, 35 currencies plus NOK: AUD 🇦🇺, BDT 🇧🇩, BRL 🇧🇷, BYN 🇧🇾, CAD 🇨🇦, CHF 🇨🇭, CNY 🇨🇳, CZK 🇨🇿, DKK 🇩🇰,
EUR 🇪🇺, GBP 🇬🇧, HKD 🇭🇰, HUF 🇭🇺, IDR 🇮🇩, ILS 🇮🇱, INR 🇮🇳, ISK 🇮🇸, JPY 🇯🇵, KRW 🇰🇷, MMK 🇲🇲, MXN 🇲🇽, MYR 🇲🇾, NZD 🇳🇿,
PHP 🇵🇭, PKR 🇵🇰, PLN 🇵🇱, RON 🇷🇴, SEK 🇸🇪, SGD 🇸🇬, THB 🇹🇭, TRY 🇹🇷, TWD 🇹🇼, USD 🇺🇸, VND 🇻🇳, ZAR 🇿🇦.

Beyond the ECB's list, Norges Bank quotes BDT, BYN, MMK, PKR, TWD and VND.

#### 📋 The catalogue rule

`get_supported_currencies()` asks `EXR/B..NOK.SP?format=csv&lastNObservations=1`: the last observation of every series.
On 2026-11-16 the answer listed 41 series, and the plugin keeps the live currencies only:

- **Not currencies** (`NOT_CURRENCIES`): the two NOK exchange-rate indices `I44` and `TWI`, and the IMF's SDR `XDR`.
- **Closed series** (`CLOSED_AFTER`, 31 days): a series whose last value is more than 31 days older than the newest value
  of the answer. On 2026-11-16: RUB (last value 2022-03-01), HRK (2022-12-30), BGN (2025-12-31).
- **NOK**, the base, is always added.

An answer with no currency against NOK raises `FXServiceError`. Right after a restart, while the first discovery is slow
or fails, the catalogue lists `FALLBACK_CURRENCIES` (the same 35 plus NOK); the live list replaces it as soon as one
arrives.

### 🚨 Errors

The call is one request for every currency, so its outcome is the whole call's: there is no per-currency skip as in the
parallel providers (FED, BOE).

| Answer | Result |
|--------|--------|
| HTTP 404 with the SDMX error code 100 («No data»): a range with no business day, a weekend, a range before a series starts | No row, no error: every asked currency gets an empty list |
| HTTP 429 | `FXRateLimitedError` (`raise_if_fx_rate_limited()`) with the response's `Retry-After`; the core pauses the provider ([Paused Providers](../configuration.md#paused-providers)) |
| Any other HTTP error (a 404 without code 100, a 500, a timeout after 60 s) | `FXServiceError` («Norges Bank API error: …»), logged as a warning |
| A 200 that is not the CSV: an HTML page, an empty body, a CSV without one of the columns read | `FXServiceError` naming what is wrong («…is an HTML page…», «…columns [...] missing…»): nothing is parsed or stored |
| One value that is no number (empty, `NaN`) or not positive | That day only is skipped (debug log); the rest of the series is kept |

The same checks apply to the catalogue request: an HTML answer to `get_supported_currencies()` is an `FXServiceError`.

### ⚖️ Licence and robots.txt

- **Licence**: the national data catalogue lists the bank's open data API under NLOD 2.0: free reuse, with attribution
  («Source: Norges Bank», as the provider's description says in the four languages).
- **Indicative rates**: the bank says its rates are only intended as an indication
  ([exchange rates page](https://www.norges-bank.no/en/topics/statistics/exchange_rates/)). The provider says it in its
  `warning_i18n` text, at **info** level (`warning_level = "info"`): ℹ️ on every route that uses NORGES in the route
  picker, not ⚠️. The English text:

    > Norges Bank's rates are mid rates the bank publishes only as an indication. One value per Norwegian business day:
    > none at weekends and on Norwegian holidays.

- **robots.txt** (checked 2026-11-16): `Allow: /` for every user agent not named, with `Content-Signal: use=reference`.
- **Reference implementation**: the open-source Frankfurter project (MIT) reads the same API; it served as the reference
  for the request shape.

### ⚠️ Limitations

- No data at weekends and on Norwegian holidays.
- Mid rates, published only as an indication.
- One request for all currencies: one failing answer fails the whole call, for every currency.
- History depth varies by currency (see the table above); a range before a series' first day returns nothing for it.

### 🧪 Tests

`backend/test_scripts/test_services/test_fx_norges.py` pins the direction and unit (the JPY example above), the single
request without `locale`, `"min"`, the dates kept as given, the skipped values, the «No data» 404, every non-CSV answer,
the 429 and the catalogue rule, with synthetic answers written by hand (no network, no DB, no server). It is registered
among the provider error paths:

```bash
./dev.py test services provider-errors
```

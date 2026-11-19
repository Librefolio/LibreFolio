# 🇨🇿 CNB — Czech National Bank

| Property | Value |
|----------|-------|
| **Code** | `CNB` |
| **Base Currency** | CZK |
| **API Endpoint** | `…/central-bank-exchange-rate-fixing/year.txt?year=YYYY` (history), `…/daily.txt` (the catalogue) |
| **API Format** | Plain text, `|`-separated, one file per year |
| **API Key** | Not required |
| **Terms** | [Disclaimer & Copyright](https://www.cnb.cz/en/privacy-statement-and-disclaimer/disclaimer-copyright/index.html): «You may store, distribute and reproduce all our Internet information»; the CNB must always be stated as the source («Source: the CNB») |
| **Currencies** | Discovered at runtime from the last fixing: on 2026-11-19, 30 plus CZK. `GET /fx/providers` caches the list for 24 h (`backend/app/services/fx/catalog.py`) |
| **Update Frequency** | Every Czech working day, at around 2.30 p.m. Prague time |
| **Historical Data** | From 1991 (the first yearly file) |
| **Data Page** | [Central bank exchange rate fixing](https://www.cnb.cz/en/financial-markets/foreign-exchange-market/central-bank-exchange-rate-fixing/central-bank-exchange-rate-fixing/) |

The two files live under
`https://www.cnb.cz/en/financial-markets/foreign-exchange-market/central-bank-exchange-rate-fixing/central-bank-exchange-rate-fixing/`.

### ⚙️ How It Works

The Czech National Bank declares the central bank exchange rate fixing every working day and publishes it as plain-text
files. The provider (`backend/app/services/fx_providers/cnb/plugin.py`) reads one file per year of the asked range.

- **One request per year**: `fetch_rates()` asks `year.txt?year=YYYY` for every year from the start to the end of the
  range, in ascending order, with a pause of `PAUSE_SECONDS` (0.3 s) between two requests (D9). The current year's
  file ends with today's fixing, so no daily file is needed for the last day.
- **Blocks with their own columns**: a file starts with a header `Date|1 AUD|100 HUF|1000 IDR|…` (amount, space, ISO
  code), then one row per fixing day, `dd.mm.yyyy|v1|v2|…`. A year can hold several blocks with different columns: 1993
  has three headers, as currencies entered and left. The parser reads every header and reads each row with the columns
  of its own block; a currency absent from a block has no value there.
- **A year without a file**: the CNB answers `year=1990` (any year without a file) with **the current year's file**,
  not with an error. A row is kept only when its year is the asked one; the others are skipped with a warning.
- **Values read as `Decimal`**: no value passes through a float.
- **Start date**: `"min"`, and any start before 1991-01-01, asks from `FIRST_DAY` (1991-01-01). CZK alone makes no
  request; an asked currency the files do not hold gets an empty list.
- **Base currency**: `fetch_rates()` with a `base_currency` other than CZK (or None) raises `ValueError`.

### ↔️ Direction and Unit

Every value is «CZK per `amount` units» of the currency in its column, where `amount` (1, 100 or 1000) is in the
header. The plugin divides by the amount and returns the bank's direction: `(d, CUR, 'CZK', CZK per 1 CUR)`, «1 CUR = v
CZK». The FX service normalizes the pair; nothing is inverted in the plugin.

Worked example, one row:

| Header | Row | Meaning |
|--------|-----|---------|
| `Date|1 USD|100 HUF|1000 IDR` | `02.01.2025|24.398|6.097|1.507` | 1 USD = 24.398 CZK, 1 HUF = 0.06097 CZK, 1 IDR = 0.001507 CZK |

**Three decimals per amount**: IDR is `1.218` CZK per 1000 (19/11/2026), so a step of about 0.08%; KRW `1.674` per 100,
about 0.06%. The provider says so in its note.

### 📅 The Day of a Rate (D2)

The fixing is declared at around 2.30 p.m. on Czech working days and is valid for that day and the following non-working
days (the CNB's page: a rate declared on Tuesday 23 December is valid until Sunday 28 December). The files list the
fixing days only, and **the provider returns them as they are** (D2): it never fills a weekend or a holiday. A day the
bank lists on a holiday (the file of 1991 starts on 1 January) is kept.

### 💰 Supported Currencies

`get_supported_currencies()` reads `daily.txt` without a date: a first line with the date and the number of the fixing
(`19 Nov 2026 #222`), the header `Country|Currency|Amount|Code|Rate`, then one row per currency. The catalogue is the
`Code` column plus CZK: on 2026-11-19, AUD BRL CAD CHF CNY DKK EUR GBP HKD HUF IDR ILS INR ISK JPY KRW MXN MYR NOK NZD
PHP PLN RON SEK SGD THB TRY USD XDR ZAR. BGN left at the end of 2025. While the first discovery after a restart is slow
or fails, `fallback_currencies` lists the same 31 codes.

The **other currencies** of the CNB (124, one value a month) are left out: BDI publishes them daily.

The history of a currency starts when the CNB began to fix it: on 2026-11-19, USD and JPY from 1991-01-01, HUF from
1997-01-29, TRY from 2005-01-03 (the new lira), IDR from 2005-04-01. Before 8 February 1993 the rates are those of the
Czechoslovak koruna, which the Czech koruna replaced at par: the series runs on without a break.

### 📦 Request Budget

Measured on 2026-11-19 on the real files (five currencies):

| Range | Requests | Time |
|-------|----------|------|
| 14 days | 1 (2 across New Year) | 0.15 s |
| `"min"` (1991 onward) | 36 | 25.6 s, pause included |

Both stay well under the 120 s the core gives one leg (`fx/sync.py`). The CNB documents no request limit.

### 🚨 Errors

The years of one call make one dataset: a year that fails fails the call. A history with a silent hole is never
returned.

| Answer | Result |
|--------|--------|
| HTTP 429 on any year | `FXRateLimitedError` (its `Retry-After`, through `raise_if_fx_rate_limited()`); no further year is asked |
| Any other HTTP error, or a network failure | `FXServiceError` («CNB API error for year …»), logged as a warning |
| A yearly answer whose first non-empty line does not start with `Date|` (an HTML page, an error text) | `FXServiceError` («… is not a yearly file … (format changed)») |
| A daily file without the header `Country|Currency|Amount|Code|Rate`, or without a row | `FXServiceError` from `get_supported_currencies()`; the catalogue falls back to the last list or `fallback_currencies` |
| A row of another year than the asked one | Skipped, one warning per file |
| A line whose day cannot be read | Skipped (debug log) |
| An empty cell, a value that is no number, zero or negative (X-R50) | That currency loses that day only |

### ⚖️ Terms and robots.txt

The CNB's Disclaimer & Copyright page allows storing, distributing and reproducing its Internet information, and asks
that the CNB always be stated as the source. The provider's description ends with «Source: the CNB» in the four
languages. `robots.txt` (19/11/2026) disallows nothing under these files.

The note (`warning_i18n`) is at **info** level: the fixing days, the units with three decimals and the koruna of 1993
are facts worth knowing, not a limit of the data that misleads.

### ⚠️ Limitations

- Only fixing days: no rate on Czech non-working days, though the bank declares each fixing valid for them.
- Small units are rounded: up to about 0.1% for IDR.
- One request per year: a full history is 36 requests, about 26 s.
- A file whose structure changes (no `Date|` header) fails the call with a clear error instead of reading wrong
  columns.

### 🧪 Tests

`backend/test_scripts/test_services/test_fx_cnb.py` pins the direction (CZK per 1 unit, divided by the amount), the one
request per year in ascending order, the blocks with different columns, the rows of another year, the fixing days kept
as they are, the skipped cells and lines, the pause between years, the 429 that stops the years, the failure of one
year that fails the call, every answer that is not a yearly file and the catalogue from the daily file, all with
synthetic answers written by hand (no network, no DB, no server). It is registered among the provider error paths:

```bash
./dev.py test services provider-errors
```

The external test reads the real files:

```bash
./dev.py test external fx-providers --providers CNB
```

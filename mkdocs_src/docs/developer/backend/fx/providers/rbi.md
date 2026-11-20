# 🇮🇳 RBI — Reserve Bank of India

| Property | Value |
|----------|-------|
| **Code** | `RBI` |
| **Base Currency** | INR |
| **API Endpoint** | `https://www.rbi.org.in/Scripts/ReferenceRateArchive.aspx`: a GET, then one POST of the form per window |
| **API Format** | ASP.NET page, HTML table read with CSS selectors (BeautifulSoup, `html.parser`) |
| **API Key** | Not required |
| **Terms** | FBIL: no commercial use without written permission; RBI: «All Rights Reserved». Developer decision Q2 (b): kept for a self-hosted instance, with a note; the paid cloud turns it off (`LIBREFOLIO_FX_PROVIDERS_ENABLED`) |
| **Currencies** | USD, GBP, EUR, JPY, AED, IDR, RUB |
| **Update Frequency** | Mumbai business days (FBIL publishes at 13:30 IST) |
| **Historical Data** | From 1998-08-25, **without** 2018-07-10..2018-07-23 and 2018-07-25..2022-04-11 |
| **Data Page** | [Reference Rate Archive](https://www.rbi.org.in/Scripts/ReferenceRateArchive.aspx) |

### ⚙️ How It Works

The RBI's archive is an ASP.NET form. The provider (`backend/app/services/fx_providers/rbi/plugin.py`) does what a
browser does (developer decision Q4 (a)): no headless browser, no rotation, a real block stays an error.

- **One session**: one `httpx.AsyncClient` for the whole call, so the session cookies the GET receives go with every
  POST.
- **The GET** reads the page's hidden fields (`input[type=hidden][name]`: `__VIEWSTATE`, `__EVENTVALIDATION`…). A page
  without the form, or without `__VIEWSTATE`, is an error.
- **One POST per window**: the hidden fields of the **previous** answer, plus `chkAll=on`, `txtFromDate` and
  `txtToDate` (`dd/mm/yyyy`) and `btnSubmit= GO `. A window is at most `WINDOW_DAYS` (365) days, counted from the
  start of the range: a 14-day sync across New Year is one POST. A pause of `PAUSE_SECONDS` (1 s) separates two POSTs
  (D9).
- **Why windows**: the server's time grows faster than the range. One year answers in about 1.7 s, two years in 5 s,
  ten years in 78 s.
- **The table**: the `table.tablebg` whose first row has `td.tableheader` cells (the page has other `tablebg` layout
  tables). Rows come newest first.
- **An empty range** (before 1998, inside the gap, a holiday) answers the page with the form and without the result
  table: no rows for that window, and the next POST goes on with that page's hidden fields.
- **Start date**: `"min"`, and any start before 1998-08-25 (`FIRST_DAY`), keeps from `FIRST_DAY`. INR alone, or only
  currencies outside the 7, makes no request.
- **Base currency**: `fetch_rates()` with a `base_currency` other than INR (or None) raises `ValueError`.

### ↔️ Direction and Unit

The header gives each column's unit: `USD (INR / 1 USD)`, `JPY (INR / 100 JPY)`, `IDR (INR / 10000 IDR)`. The provider
reads it with `HEADER_PATTERN` and returns `(d, CUR, 'INR', value / unit)`, «1 CUR = v INR»: on 19 November 2026 USD
93.3461, JPY 58.52 per 100 → 0.5852, IDR 51.1244 per 10 000 → 0.00511244. The first header cell must be `Date`; a
header cell of another shape, or a missing column of the 7, is an error («the page changed»).

### 📅 The Day of a Rate (D2) and the Archive's Holes

Each value is returned under its date, in ascending order. Measured on 2026-11-19 (5 923 days):

| Currency | First day | Note |
|----------|-----------|------|
| USD, GBP, JPY | 1998-08-25 | GBP and JPY are 0.0000 on 1999-01-01 |
| EUR | 1999-01-04 | 0.0000 before |
| AED, IDR | 2026-01-22 | empty cells before |
| RUB | 2026-09-15 | one empty day, 2026-09-23 |

- **The gap**: nothing from 2018-07-10 to 2018-07-23 (FBIL's first two weeks) and from 2018-07-25 to 2022-04-11. The
  archive shows the RBI's own rate until 2018-07-09, one FBIL day (2018-07-24), then FBIL's rate from 2022-04-12. On
  11 and 12 November 2026 the archive and FBIL's own values are equal.
- **FBIL has the gap's rates** (an undocumented JSON endpoint, `fbil.org.in/wasdm/refrates/fetchfiltered`: 4
  currencies in January 2019), but it is another source with another owner, and its anonymous answers lag about a week
  (on 19 November the last day was 12 November). It is not used: a question for the developer (lane 75, L32).
- **Cells**: an empty cell, `0.0000` or text loses only that currency of the row.
- **Sundays**: the bank does not publish on Sundays. The one Sunday row, 1998-10-11, copies 1998-11-10 (day and month
  swapped): Sunday rows are skipped. The one Saturday, 2000-09-23, looks like a real rate and is kept.
- **Duplicates**: none in the archive; a day with two different values for one currency would be dropped (X-R50).

### 📦 Request Budget

Measured on 2026-11-19:

| Range | Requests | Answer | Time |
|-------|----------|--------|------|
| 14 days, the 7 currencies | 1 GET + 1 POST | 164 KB, 10 days | 1.5 s |
| 2020, inside the gap | 1 GET + 2 POSTs (a leap year is 366 days) | no rows | 2.7 s |
| `"min"`, the 7 currencies | 1 GET + 29 POSTs | 6.7 MB, 24 048 rates | 72 s |

The full history stays under the ~100 s a sync can take before the interface stops waiting.

### 🚨 Errors

| Answer | Result |
|--------|--------|
| HTTP 429 on the GET or on a POST | `FXRateLimitedError` (its `Retry-After`, through `raise_if_fx_rate_limited()`) |
| Any other HTTP error, or a network failure | `FXServiceError` («RBI API error (GET/POST) …»), logged as a warning |
| A page without the form (a block page, a new layout), or a GET without `__VIEWSTATE` | `FXServiceError` («… the page changed, or the request was refused») |
| A result table without `Date` first, with an unknown column, or without one of the 7 | `FXServiceError` («… the page changed») |
| A row whose date cannot be read, or dated Sunday | That row is skipped |
| An empty cell, 0.0000 or text | That currency of the row is skipped |

### ⚖️ Terms

FBIL: «does not authorize commercial use of the data available in its website without written permission»; the RBI's
site is «© Reserve Bank of India. All Rights Reserved.» and may block addresses that abuse it. Developer decision Q2
(b), 19/11/2026: the provider stays for a self-hosted instance, the note says so, and the paid cloud turns it off with
`LIBREFOLIO_FX_PROVIDERS_ENABLED`. Nothing downloaded from the bank is committed; the tests use synthetic pages only.
The RUB column is the RBI's own (Q3 (b)), not the Central Bank of Russia's: the note says so.

The note (`warning_i18n`) is at **warning** level: a web form, restrictive terms and a four-year gap are limits that
can mislead.

### ⚠️ Limitations

- The form and its layout can change without notice.
- The archive has no rates from 2018-07-25 to 2022-04-11 (and 2018-07-10..23).
- Single wrong values on a business day are not detected: on 2005-07-11 JPY reads 36.91 between 38.85 and 39.10.

### 🧪 Tests

`backend/test_scripts/test_services/test_fx_rbi.py` pins the GET and the POSTs in one session, the hidden fields
echoed from the previous answer, the windows and the pauses, the unit read from the header, the skipped cells and
rows, Sundays, the empty answer, every page that is not the archive's form or table, the 429, the HTTP errors and the
network failures, all with synthetic pages written by hand (no network, no DB, no server). It is registered among the
provider error paths:

```bash
./dev.py test services provider-errors
```

The external test reads the real archive:

```bash
./dev.py test external fx-providers --providers RBI
```

# 🇵🇱 NBP — Narodowy Bank Polski

| Property | Value |
|----------|-------|
| **Code** | `NBP` |
| **Base Currency** | PLN |
| **API Endpoint** | `https://api.nbp.pl/api/exchangerates/tables/{table}/{from}/{to}/?format=json`, table `A` or `B` |
| **API Format** | JSON, **documented** ([NBP Web API](https://api.nbp.pl/en.html)) |
| **API Key** | Not required |
| **Terms** | The API documentation reads «All rights reserved»; the instructions page is behind an anti-bot wall. Developer decision D1: offered for a self-hosted instance |
| **Currencies** | 148: table A, 32 daily; table B, 116 weekly (D3) |
| **Update Frequency** | Polish business days (A); weekly, usually Wednesday (B) |
| **Historical Data** | From 2002-01-02 |

### ⚙️ How It Works

The provider (`backend/app/services/fx_providers/nbp/plugin.py`) reads whole tables of average rates (`mid`):

- **Table A** (`A_CURRENCIES`, 31) is daily; **table B** (`B_CURRENCIES`, 116) is weekly: developer decision D3 accepts
  a weekly source with a note, as for SNB's monthly averages.
- **Windows**: at most `WINDOW_DAYS` (93) days per request (the API answers 400 «Limit of 93 days has been exceeded»
  beyond), oldest first, `PAUSE_SECONDS` (0.3 s) between two requests of a table. **The two tables are read at once**.
- **Which tables**: A when an asked currency is in A; B when one is in B. Many table-A currencies were in table B
  before moving to A (on 2003-01-07, 2008-01-02 and 2011-07-27/2011-08-31). So for A currencies the provider also reads
  table B **up to `B_HISTORY_UNTIL`** (2011-08-31): their history is weekly before the move. Table B goes on to the end
  of the range only when a B currency is asked.
- **Values** are read as `Decimal` straight from the JSON text; only `code` and `mid` are read (old tables have
  `country` and `symbol` instead of `currency`).
- **No table in a window** answers 404 «Brak danych» (no data): no rows, the next window goes on. Any other 404 is an
  error.
- **Start date**: `"min"`, and any start before 2002-01-02, keeps from `FIRST_DAY`. PLN alone, or only currencies
  outside the 148, makes no request.
- **Base currency**: `fetch_rates()` with a `base_currency` other than PLN (or None) raises `ValueError`.

### ↔️ Direction and Unit

Every `mid` is PLN per 1 unit, small currencies included (IRR 0.00000208): `(d, CUR, 'PLN', mid)`, «1 CUR = v PLN»,
with `d` the table's `effectiveDate`. USD 4.0176 on 2026-11-19.

### 📅 The Day of a Rate (D2), Scale Changes and Jumps

Each rate is returned under its table's `effectiveDate`. Measured on 2026-11-19: 6 287 A tables and 1 240 B tables
since 2002, no conflicting duplicate, and A and B never disagree on a day both publish (2002–2011); equal values are
kept once. Table B was published every two weeks in 2002, then weekly.

- **XDR** (the IMF's special drawing right, a basket of USD, EUR, CNY, JPY and GBP) is in table A and is served: 5.4103 PLN per 1 XDR.
- **VES**: the bolívar was redenominated (÷10⁶) on 2021-10-01; the NBP published the new scale from 2021-10-13
  (`VES_NEW_FROM`). Older values are multiplied by `VES_FACTOR` (10⁶), as BCB does: 0.95 on 2021-10-06, 0.9538 on
  2021-10-13.
- **SYP** changed scale on 2026-01-07 (11 048 → 116 per USD, about 1:100 with a market move; the exact factor is not
  certain): it is served from that day (`SERIES_FROM`).
- **Jumps that are real** (not corrected): LRD and IQD in 2004 and IRR in 2026, when the NBP moved from an official
  parity (1 LRD = 1 USD; 0.31 IQD per USD; 42 000 IRR per USD) to a market rate. MMK in 2012, SDG in 2021 and LBP in
  2023 and 2024 are devaluations.
- **The RUB rate** is the NBP's own (Q3 (b)), not the Central Bank of Russia's: the note says so.

### 📦 Request Budget

Measured on 2026-11-19:

| Range | Requests | Answer | Time |
|-------|----------|--------|------|
| 14 days, USD and EUR | 1 (A) | 19 KB | 0.3 s |
| 14 days, the 147 currencies | 2 (A and B) | 32 KB | 0.2 s |
| A weekend | 1 (404 «Brak danych») | no rate | 0.1 s |
| `"min"`, USD | 136 (A to 2026, B to 2011) | 6 287 rates | 36 s |
| `"min"`, the 147 currencies | 196 (98 per table, at once) | 21 MB, 307 209 rates | 43 s |

### 🚨 Errors

| Answer | Result |
|--------|--------|
| HTTP 429 | `FXRateLimitedError` (its `Retry-After`, through `raise_if_fx_rate_limited()`) |
| HTTP 404 «Brak danych» | No table in that window: no rows |
| Any other 404, a 400 (its text in the message), any other HTTP error, or a network failure | `FXServiceError`, logged as a warning |
| An HTML page, text that is not JSON, or JSON that is not a list | `FXServiceError` |
| A rate not a positive number, or a table whose date cannot be read | Skipped |
| Two different values for one currency on one day | That day is dropped for that currency |

A failure in either table fails the whole call.

### ⚖️ Terms

The [API documentation](https://api.nbp.pl/en.html) reads only «All rights reserved»; the instructions page on nbp.pl
is behind an anti-bot wall, so no reuse terms could be read. Developer decision D1 (lane 75): the provider is offered
for a self-hosted instance that stores the rates for its owner; nothing downloaded from the bank is committed, and the
tests use synthetic answers only. The description names the source («Source: Narodowy Bank Polski»).

The note (`warning_i18n`) is at **warning** level: weekly rates for 116 currencies, and jumps where the source changed,
are limits that can mislead.

### ⚠️ Limitations

- 116 currencies have one rate a week.
- A wrong value is not detected; the scale changes known on 2026-11-19 are handled one by one.
- A full history takes about 40 seconds.

### 🧪 Tests

`backend/test_scripts/test_services/test_fx_nbp.py` pins the choice of tables and the B history of the A currencies,
the 93-day windows and the pauses, the `Decimal` values, old and new table fields, the skipped rates, the duplicates
across tables, VES and SYP, the «no data» 404, every other error, all with synthetic answers written by hand (no
network, no DB, no server). It is registered among the provider error paths:

```bash
./dev.py test services provider-errors
```

The external test reads the real API:

```bash
./dev.py test external fx-providers --providers NBP
```

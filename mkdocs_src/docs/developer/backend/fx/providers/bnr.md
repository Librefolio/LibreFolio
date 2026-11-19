# 🇷🇴 BNR — National Bank of Romania

| Property | Value |
|----------|-------|
| **Code** | `BNR` |
| **Base Currency** | RON |
| **API Endpoint** | `https://curs.bnr.ro/nbrfxrates10days.xml` (the last ten business days), `https://curs.bnr.ro/files/xml/years/nbrfxrates{YYYY}.xml` (one year) |
| **API Format** | XML (`DataSet` → `Body` → `Cube date=…` → `Rate currency=… multiplier=…`) |
| **API Key** | Not required |
| **Terms** | ❔ The «Disclaimer & Copyright» page renders its text with a script: no terms could be read. Developer decision D1: offered for a self-hosted instance |
| **Currencies** | A fixed list: 38 currencies plus RON |
| **Update Frequency** | Romanian business days |
| **Historical Data** | From 2005-01-03 (`FIRST_DAY` 2005-01-01: the first year file) |

### ⚙️ How It Works

The BNR publishes its reference rates as XML files. The provider (`backend/app/services/fx_providers/bnr/plugin.py`)
reads them with the standard library's parser, by **local tag names**: the namespace changes between files
(`https://www.bnr.ro/xsd` in the recent ones, `http://www.bnr.ro/xsd` in older years).

- **The host moved in 2026**: `www.bnr.ro/files/xml/…` now answers 302 to the home page; the files are on
  `curs.bnr.ro` (19 November 2026).
- **A short range** (at most `RECENT_SPAN_DAYS`, 14 days) asks the ten-day file first, and uses it when its earliest
  day is on or before the start of the range: a daily sync is one request of 13 KB.
- **Otherwise** one year file per year of the range, oldest first, `PAUSE_SECONDS` (0.3 s) apart. The year files hold
  every day up to today and **replace** the ten-day file (its rows are not merged).
- **A missing year** (before 2005, or after the current year) answers **502** with an nginx page: an error naming the
  year.
- **Validation**: a body that is not XML, or whose root is not `DataSet` (the old host's home page, for example), is
  an error.
- **Start date**: `"min"`, and any start before 2005-01-01, keeps from `FIRST_DAY`. RON alone, or only currencies
  outside the list, makes no request.
- **Base currency**: `fetch_rates()` with a `base_currency` other than RON (or None) raises `ValueError`.

### ↔️ Direction and Unit

Every rate is RON per `multiplier` units (`multiplier="100"` for HUF, IDR, ISK, JPY, KRW; 1 when absent). The provider
returns `(d, CUR, 'RON', value / multiplier)`, «1 CUR = v RON»: EUR 5.3442, HUF 1.4501 per 100 → 0.014501
(19 November 2026). 2005 is already in RON (USD 2.9027 on 2005-01-03): the 2005 redenomination does not show.

### 📅 The Day of a Rate (D2) and the Currencies

Each rate is returned under its `Cube` date. Measured on 2026-11-19: 5 524 business days from 2005-01-03, no weekend
date, no conflicting duplicate (a day with two different values would be dropped, X-R50).

| Currencies | From |
|------------|------|
| AUD CAD CHF CZK DKK EGP EUR GBP HUF JPY MDL NOK PLN SEK TRY USD | 2005-01-03 |
| RUB | 2007-11-12 |
| BGN (until 2025-12-31), SKK (until 2008-12-31) | 2007-12-03 |
| AED BRL CNY INR KRW MXN NZD RSD UAH ZAR | 2009-03-02 |
| HRK (until 2022-12-30) | 2015-08-21 |
| THB | 2017-06-19 |
| HKD IDR ILS ISK MYR PHP SGD | 2024-09-23 |

- **Former currencies** are served for their history, as ECB does: BGN, HRK, SKK.
- **Not served**: XAU (gold, RON per gram) and XDR (an open question of lane 75, Q7).
- **Missing values** are written `-` (1 093 cells, mostly BGN, RUB and SKK in 2007): skipped.
- **The RUB rate** is the BNR's own (Q3 (b)), not the Central Bank of Russia's: the note says so.
- **Jumps above 10%** are real market moves: CHF on 2015-01-15, EGP in 2016, RUB in 2014 and 2022, TRY in 2018 and
  2021, UAH in 2014.

### 📦 Request Budget

Measured on 2026-11-19:

| Range | Requests | Answer | Time |
|-------|----------|--------|------|
| 10 days, the 38 currencies | 1 (the ten-day file) | 13 KB | 0.3 s |
| 14 days (the ten-day file does not reach back) | 2 (ten-day file + 2026) | 313 KB | 0.8 s |
| `"min"`, the 38 currencies | 22 (2005–2026) | 6.7 MB, 150 667 rates | 10.9 s |

### 🚨 Errors

| Answer | Result |
|--------|--------|
| HTTP 429 | `FXRateLimitedError` (its `Retry-After`, through `raise_if_fx_rate_limited()`) |
| HTTP 502 on a year file (a missing year), any other HTTP error, or a network failure | `FXServiceError` («BNR API error for the YYYY file …»), logged as a warning |
| A body that is not XML, or whose root is not `DataSet` | `FXServiceError` («… the host or the format changed») |
| A `Cube` whose date cannot be read | That day is skipped |
| A rate `-`, empty, not a number, zero or negative | That currency is skipped for that day |

### ⚖️ Terms

The bank's [Disclaimer & Copyright](https://www.bnr.ro/en/2573-disclaimer-copyright) page renders its text with a
script, so no terms could be read (19 November 2026): the terms stay ❔. Developer decision D1 (lane 75): the provider is
offered for a self-hosted instance that stores the rates for its owner; nothing downloaded from the bank is committed,
and the tests use synthetic files only. The description names the source («Source: National Bank of Romania»).

The note (`warning_i18n`) is at **info** level: later starts, euro adoptions and the BNR's RUB are facts worth
knowing, not limits that mislead.

### ⚠️ Limitations

- The host changed once without a working redirect; a new move would fail with a clear error until the URLs change.
- The full history is one file per year: 22 files today.

### 🧪 Tests

`backend/test_scripts/test_services/test_fx_bnr.py` pins the ten-day file and when it is enough, the year files that
replace it, the pauses, the multiplier, the three namespaces, XAU and XDR left out, the skipped values, the duplicates,
the missing year, every answer that is not the BNR's XML, the 429, the HTTP errors and the network failures, all with
synthetic files written by hand (no network, no DB, no server). It is registered among the provider error paths:

```bash
./dev.py test services provider-errors
```

The external test reads the real files:

```bash
./dev.py test external fx-providers --providers BNR
```

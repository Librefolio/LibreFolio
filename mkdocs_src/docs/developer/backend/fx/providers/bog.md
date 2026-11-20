# 🇬🇭 BOG — Bank of Ghana

| Property | Value |
|----------|-------|
| **Code** | `BOG` |
| **Base Currency** | GHS |
| **API Endpoint** | `GET` of the [historical rates page](https://www.bog.gov.gh/treasury-and-the-markets/historical-interbank-fx-rates/) for the nonce, then `POST https://www.bog.gov.gh/wp-admin/admin-ajax.php?action=get_wdtable&table_id=40` |
| **API Format** | wpDataTables server-side JSON (sent as `text/html`); **undocumented** |
| **API Key** | Not required (the page's public nonce) |
| **Terms** | Disclaimer: information «for general reference purposes only», no clause against reproduction; «© Bank of Ghana. All rights reserved.». Developer decision D1: offered for a self-hosted instance |
| **Currencies** | A fixed pair map: 17 currencies plus GHS |
| **Update Frequency** | Ghanaian business days |
| **Historical Data** | From 2020-01-01 (`FIRST_DAY`); the table goes back to 1996 |

### ⚙️ How It Works

The Bank of Ghana shows its historical rates in a WordPress «wpDataTables» table (`table_id=40`), served through
`admin-ajax.php` with the DataTables server-side protocol, the same as [CBK](cbk.md). Unlike CBK, the table asks for
the **nonce** the page gives every visitor (`wdtNonceFrontendServerSide_40`): without it the server answers an empty
body. The provider (`backend/app/services/fx_providers/bog/plugin.py`) reads the page, then sends the nonce with the
form, as a browser does (developer decision Q4 (a)).

- **One session**: one `httpx.AsyncClient` for the GET and the POST, so the page's cookies go with the POST.
- **One POST for any range**: `length=PAGE_LENGTH` (100 000), the order on the date, the six columns, `wdtNonce`, and
  the date filter `columns[0][search][value]=dd Mon yyyy|dd Mon yyyy`. The server honours both bounds. Month names are
  read and written with a fixed English table, never the process locale.
- **A cut answer** (`recordsFiltered` above the rows returned) is an error: rows come newest first, so a cut would lose
  the oldest days silently. From 2020 the table has about 32 000 rows and grows by about 4 800 a year.
- **Rows**: `["19 Nov 2026", "US Dollar", "USDGHS", "11.7641", "11.7759", "11.7700"]`: date, name, pair, buying,
  selling, **mid**. The mid is used. Values can carry thousands separators (`"2,906.6300"`).
- **Start date**: `"min"`, and any start before `FIRST_DAY`, keeps from `FIRST_DAY`. GHS alone, or only currencies
  outside the map, makes no request.
- **Base currency**: `fetch_rates()` with a `base_currency` other than GHS (or None) raises `ValueError`.
- **Not used**: the static «Daily Interbank FX Rates» page the plan named for the last day: table 40 already holds the
  day's rows (checked on 19 November 2026).

### ↔️ Direction and Unit

The pair code gives the direction (`PAIRS`):

| Pairs | Bank's quote | Returned tuple |
|-------|--------------|----------------|
| `AUDGHS` `CADGHS` `CHFGHS` `CNYGHS` `DKKGHS` `EURGHS` `GBPGHS` `JPYGHS` `NOKGHS` `NZDGHS` `SEKGHS` `USDGHS` `ZARGHS` | GHS per 1 unit (USD 11.77) | `(d, CUR, 'GHS', mid)` |
| `GHSGMD` `GHSNGN` `GHSXOF` `GHSSLL` | units per 1 GHS (NGN 117.50) | `(d, 'GHS', CUR, mid)` |

**The leone**: `GHSSLL` is in old leones until 2026-09-10 (2 109.39) and in new leones from 2026-09-11 (2.1082).
The ISO list has only SLE, so old leones are served as SLE ÷ 1 000 (`SLL_PER_SLE`), as BCB does; the two sides join
(2.1094 and 2.1082).

**Dropped pairs**: `WAUGHS` (the ECOWAS unit of account) and `GHSMRO`. The ouguiya is always USDGHS × 357.5, a parity
of 2017, while the market says about 40 MRU (400 old MRO) per USD; MRO is no longer an ISO code either.

### 📅 The Day of a Rate (D2) and Why the History Starts in 2020

Each mid is returned under its date, in ascending order. The whole table (146 034 rows, 1996–2026, measured on
2026-11-19) has no conflicting duplicate. But its earlier years are not usable as they are:

- **Old cedis** until 2007-06-27; the redenomination (10 000:1) leaves a gap until 2007-07-09.
- **One-day values of another currency or another scale**, from 2007 to 2019: 110 days in the 17 pairs served
  where a pair's mid moves by more than 10% and comes back the next day, 16 of them ten-fold or more, among them
  USD 9 539.94 on 2012-06-19 (between 1.88 and 1.89) and GBP 25 798.58 on 2014-10-22.
- **The buying and selling columns do not separate them**: a rule on the row (a side not positive, buying above
  selling, a wide spread, the mid not the average) catches the thousand-fold rows but would also drop more than 1 000
  normal rows, mostly the yen's four-decimal rounding.

So `FIRST_DAY` is 2020-01-01. Since then one such day is left: **CNY 2.3951 on 2025-02-28**, between 2.1325 and
2.1314. Above 5%, three more days are left, all NGN (2021-02-17, 2023-11-06, 2023-11-23), perhaps real: the
naira moved a lot in those years. **To be reviewed with the developer** (lane 75, L33): the alternatives are history from 2007-07-09 with all
those days, or a filter for one-day values, a policy the other providers do not have.

**Precision**: four decimals; the yen (0.0736 GHS) moves in steps of about 0.14%.

### 📦 Request Budget

Measured on 2026-11-19:

| Range | Requests | Answer | Time |
|-------|----------|--------|------|
| 14 days, the 17 currencies | GET (240 KB) + POST | 14 KB, 11 days | 5.6 s |
| `"min"`, the 17 currencies | GET + POST | 2.2 MB, 1 707 days per currency | 8.5 s |

The GET takes about 4 s on its own (a WordPress page). The whole table since 1996 in one POST is 10 MB in 12 s.

### 🚨 Errors

| Answer | Result |
|--------|--------|
| HTTP 429 on the GET or the POST | `FXRateLimitedError` (its `Retry-After`, through `raise_if_fx_rate_limited()`) |
| Any other HTTP error, or a network failure | `FXServiceError` («BOG API error (GET/POST) …»), logged as a warning |
| A page without the nonce | `FXServiceError`, and no POST |
| An empty body, an HTML page, text that is not JSON, or JSON without a `data` list | `FXServiceError` (the message names the cause) |
| `recordsFiltered` above the rows returned | `FXServiceError` («… was cut at …») |
| A row with an unknown pair, an unreadable date or a mid that is no positive number | That row is skipped |
| Two different mids for one currency on one day | That day is dropped for that currency, one warning per call |

### ⚖️ Terms

The bank's [disclaimer](https://www.bog.gov.gh/disclaimer/) gives the information «for general reference purposes
only», with no clause against reproduction; the footer reads «© Bank of Ghana. All rights reserved.». Developer
decision D1 (lane 75): the provider is offered for a self-hosted instance that stores the rates for its owner; nothing
downloaded from the bank is committed, and the tests use synthetic answers only. The description names the source
(«Source: Bank of Ghana»).

The note (`warning_i18n`) is at **warning** level: an undocumented source, a history cut to 2020 and a residual wrong
day are limits that can mislead.

### ⚠️ Limitations

- The endpoint and its nonce are undocumented and can change without notice.
- No history before 2020.
- A wrong value on a business day is not detected (CNY on 2025-02-28).

### 🧪 Tests

`backend/test_scripts/test_services/test_fx_bog.py` pins the GET and the POST in one session, the nonce, the form and
its date filter, the mid, the thousands separators, the English dates, both directions, the leone's two scales, the
dropped pairs, the skipped rows, the duplicates, the cut answer, every answer that is not the table's JSON, the 429,
the HTTP errors and the network failures, all with synthetic answers written by hand (no network, no DB, no server).
It is registered among the provider error paths:

```bash
./dev.py test services provider-errors
```

The external test reads the real endpoint:

```bash
./dev.py test external fx-providers --providers BOG
```

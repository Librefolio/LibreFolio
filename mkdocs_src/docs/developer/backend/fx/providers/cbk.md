# 🇰🇪 CBK — Central Bank of Kenya

| Property | Value |
|----------|-------|
| **Code** | `CBK` |
| **Base Currency** | KES |
| **API Endpoint** | `POST https://www.centralbank.go.ke/wp-admin/admin-ajax.php?action=get_wdtable&table_id=<id>`: table `193` (from 2024-01-05), table `32` (up to 2024-01-04) |
| **API Format** | wpDataTables server-side JSON (sent as `text/html`); **undocumented** (the endpoint the bank's rate pages read) |
| **API Key** | Not required |
| **Terms** | ❔ No terms of use found (`/disclaimer/` and `/terms-of-use/` answer 404). Developer decision D1: offered for a self-hosted instance that stores the rates for its owner |
| **Currencies** | A fixed name map: 21 currencies plus KES |
| **Update Frequency** | Kenyan business days |
| **Historical Data** | From 2004-11-02, the start of the daily series (each currency from its own first day) |
| **Data Pages** | [Forex](https://www.centralbank.go.ke/forex/), [Forex exchange rates](https://www.centralbank.go.ke/rates/forex-exchange-rates/) |

### ⚙️ How It Works

The Central Bank of Kenya shows its rates in two WordPress «wpDataTables» tables. Their data come from
`admin-ajax.php` through the DataTables server-side protocol: a POST with the same form fields the page sends. The
endpoint is not documented (decision D10 c, lane 75): the provider (`backend/app/services/fx_providers/cbk/plugin.py`)
says so in its note and fails with a clear error when an answer changes shape. No nonce is needed (19 November 2026).

- **Two tables, two periods**: table `193` (`CURRENT_TABLE`) from `CURRENT_FIRST_DAY` (2024-01-05), 3 columns (date,
  name, rate); table `32` (`OLD_TABLE`) up to 2024-01-04, 5 columns (date, name, mean, buy, sell). Each table owns only
  its own period: a row of one table outside it is ignored. From the old table the **mean** is used.
- **Which tables**: the old one when the range starts on or before 2024-01-04, the current one when it ends on or after
  2024-01-05; old first, then a pause of `PAUSE_SECONDS` (0.3 s) before the current one (D9).
- **The form**: `draw=1`, `start=0`, `length=PAGE_LENGTH` (100 000, every row in one answer), the order on column 0
  descending, and for each column `columns[i][data]=i`, `searchable` and `orderable` `true`, an empty search. The date
  column carries a lower bound, `columns[0][search][value]=dd/mm/yyyy|` (the start of the range, or 2024-01-05 for
  the current table). The server honours the lower bound and ignores an upper one, so the end is cut by the plugin.
  One page is enough today: the old table holds 97 606 rows, the current one grows by about 5 000 a year.
- **Rows**: `["19/11/2026", "US DOLLAR", "129.9900"]` (current) or `[date, name, mean, buy, sell]` (old). Names are
  stripped, then looked up in `CURRENCY_NAMES`; values are read as `Decimal`.
- **Start date**: `"min"`, and any start before 2004-11-02 (`FIRST_DAY`, the start of the daily series), keeps from
  `FIRST_DAY`. KES alone, or only currencies the bank does not publish, makes no request.
- **Base currency**: `fetch_rates()` with a `base_currency` other than KES (or None) raises `ValueError`.

### ↔️ Direction and Unit

The bank quotes in three ways; `CURRENCY_NAMES` gives each name its kind:

| Kind | Bank's quote | Returned tuple |
|------|--------------|----------------|
| `per_unit` | KES per 1 unit («US DOLLAR» 129.99) | `(d, CUR, 'KES', v)` |
| `per_100` | KES per 100 yen («JPY (100)» 81.62) | `(d, 'JPY', 'KES', v / 100)` |
| `inverse` | units per 1 KES («KES / USHS» 32.27) | `(d, 'KES', CUR, v)` |

The values are those of 19 November 2026.

### 🏷️ Currency Names

| Bank's names | ISO |
|--------------|-----|
| US DOLLAR, STG POUND, EURO, SA RAND, AE DIRHAM | USD, GBP, EUR, ZAR, AED |
| CAN $, S FRANC, AUSTRALIAN $ | CAD, CHF, AUD |
| SW KRONER, NOR KRONER, DAN KRONER | SEK, NOK, DKK |
| IND RUPEE, SAUDI RIYAL, CHINESE YUAN | INR, SAR, CNY |
| HONGKONG DOLLAR, HONGKONG $ | HKD |
| SINGAPORE DOLLAR, SINGAPORE $ | SGD |
| JPY (100), JPY(100) | JPY (per 100) |
| KES / USHS, KES / TSHS, KES / RWF, KES / BIF (with or without spaces) | UGX, TZS, RWF, BIF (inverse) |

Every other name is discarded.

### 📅 The Day of a Rate (D2), the Method and the Duplicates

Each value is returned under its own date, in ascending order.

**The method changed on 2024-01-05**, with the table: since then a weighted average of the registered interbank spot
trades; before, the average of the main dealers' buying and selling rates at the opening. The series has a break there.
**Precision**: four decimals until 2025, two in 2026 (INR 1.39 KES: steps of about 0.7%).

**Junk rows in the old table** (19 November 2026): besides 21 rows dated 01/01/1970, three days are not what their date says: two
before the daily series (one of them a Sunday) and a Sunday in 2015. 2003-09-12 repeats the rates of 2012-03-09, and 2004-09-12 (a Sunday)
looks like 2012 too, both with values under the wrong names (INR 14.19 KES against 1.79 at the start of the series);
2015-04-12 (a Sunday) copies 2015-12-03 and 2015-12-04 (HKD 13.18 against 11.99 the next Monday). A value that cannot sit
under its own day is dropped (D2), so `FIRST_DAY` is the start of the daily series and the **old table's Saturday and
Sunday rows are skipped**. The current table has no weekend rows; it keeps any it may get, since the rule was checked on
the old table's data only. To be reviewed with the developer (lane 75, L31).

**Duplicates**: table `193` has 21 duplicate day-and-name keys, all identical; in table `32`, from 2004-11-02 and
without the weekends, 59 day-and-name keys carry two different values. A day with two different values for one currency is **dropped for that
currency** (X-R50), with one warning per call; the provider never picks one. Equal values are kept once. Name variants
count as the same currency, so a day can also conflict across two spellings: over the whole history, 61 days are
dropped.

### 📦 Request Budget

Measured on 2026-11-19:

| Range | Requests | Answer | Time |
|-------|----------|--------|------|
| 14 days, USD and EUR | 1 (table `193` from the start of the range) | 9 KB, 11 days | 0.9 s |
| `"min"`, the 21 currencies | 2 (table `32`, then `193`) | 5.8 MB + 0.6 MB, 111 734 rates, 61 conflicting days dropped | 20–24 s |

The whole history takes seconds, not minutes, within the httpx timeout of 60 s per request.

### 🚨 Errors

| Answer | Result |
|--------|--------|
| HTTP 429 on either table | `FXRateLimitedError` (its `Retry-After`, through `raise_if_fx_rate_limited()`) |
| Any other HTTP error, or a network failure | `FXServiceError` («CBK API error for table …»), logged as a warning |
| An empty body, an HTML page, text that is not JSON, or JSON without a `data` list | `FXServiceError` (the message names the undocumented endpoint) |
| `recordsFiltered` larger than the rows returned (the answer was cut at `PAGE_LENGTH`) | `FXServiceError` («… was cut at …»): the oldest days are never lost silently |
| A row with an unknown name | Discarded |
| A row whose date cannot be read, or whose value is no positive number | That row is skipped |
| Two different values for one currency on one day | That day is dropped for that currency, one warning per call |

The two tables make one dataset: a table that fails fails the whole call.

### ⚖️ Terms

No terms of use were found on the bank's site (`/disclaimer/` and `/terms-of-use/` answer 404, 19 November 2026): the
terms stay ❔. Developer decision D1 (lane 75): the provider is offered for a self-hosted instance that stores the rates
for its owner; nothing downloaded from the bank is committed, and the tests use synthetic answers only. The description
names the source («Source: Central Bank of Kenya»).

The note (`warning_i18n`) is at **warning** level: an undocumented source, a method break, two decimals and conflicting
rows are limits of the data that can mislead.

### ⚠️ Limitations

- The endpoint is undocumented and can change without notice (a nonce, other columns).
- The series breaks on 2024-01-05 (another method).
- Two decimals since 2026 are coarse for INR.
- A day with conflicting values is missing for that currency.
- Junk rows are recognised only by their date (before the daily series, on a weekend in the old table); a wrong row
  dated on a business day is not detected.

### 🧪 Tests

`backend/test_scripts/test_services/test_fx_cbk.py` pins the three directions, the name map and its variants, the
choice of tables and the pause between them, the form fields and the date bound, each table's period, the first day
of the daily series, the old table's weekend rows, the ascending order, the conflicting and the repeated duplicates,
the skipped rows, the 429, an answer cut at `PAGE_LENGTH` and every answer that is not the table's JSON, all with
synthetic answers written by hand (no network, no DB, no server). It is registered among the provider error paths:

```bash
./dev.py test services provider-errors
```

The external test reads the real endpoint:

```bash
./dev.py test external fx-providers --providers CBK
```

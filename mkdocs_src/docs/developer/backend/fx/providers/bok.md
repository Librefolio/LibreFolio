# 🇰🇷 BOK — Bank of Korea

| Property | Value |
|----------|-------|
| **Code** | `BOK` |
| **Base Currency** | KRW |
| **API Endpoint** | `https://ecos.bok.or.kr/api/StatisticSearch/{KEY}/json/en/{from_row}/{to_row}/731Y001/D/{YYYYMMDD}/{YYYYMMDD}/{item}` |
| **API Format** | JSON ([ECOS Open API](https://ecos.bok.or.kr/api/)), one series per request |
| **API Key** | Required: a free key, setting `api_key` (secret, instance-wide), **in the URL path** (the API's format) |
| **Terms** | ❔ Accepted at registration, not readable before. A secondary source (data.go.kr) lists the ECOS API without restrictions. Developer decision D1: offered for a self-hosted instance |
| **Currencies** | A static table: 43 currencies plus KRW (`ITEMS`). No request and no key: `get_supported_currencies()` returns the table |
| **Update Frequency** | Korean business days |
| **Historical Data** | USD from 1964-05-04 (`FIRST_DAY`); the others from their own first day |

### ⚙️ How It Works

The provider (`backend/app/services/fx_providers/bok/plugin.py`) reads table `731Y001` «Arbitraged Rates of Major
Currencies Against Won», one series (item) per currency.

- **The key is in the URL path**: it is the API's format, not a choice. So the provider never logs a URL and never puts
  one in an error of its own (its messages name the item and the HTTP status only), and the core masks the key in the
  errors and the log lines of the call (`utils/runtime/secret_masking.py`). The tests check that no error text carries
  the key.
- **Without the key** the provider raises `FXNotConfiguredError`, and the core shows it as «to configure». A call that
  asks nothing (KRW alone, currencies outside the table, an empty range) does not read the key.
- **One series per currency**, at most `MAX_PARALLEL` (3) at once, `PAUSE_SECONDS` (0.3 s) between two request starts
  of the call: the [SARB](sarb.md) pattern.
- **Pages**: rows `1..PAGE_ROWS` (10 000), then the next page while `list_total_count` is larger. The largest page the
  API accepts with a real key is not measured (❔, developer decision Q1: the key comes later).
- **Answers**: `{"StatisticSearch": {"list_total_count": N, "row": [{"ITEM_CODE1", "TIME": "20261118",
  "DATA_VALUE": "1338.8"}]}}`. Errors come with HTTP 200 as `{"RESULT": {"CODE", "MESSAGE"}}`.
- **Start date**: `"min"`, and any start before 1964-05-04, keeps from `FIRST_DAY`.
- **Base currency**: `fetch_rates()` with a `base_currency` other than KRW (or None) raises `ValueError`.

### ↔️ Direction, Unit and Items

Every value is KRW per unit: `(d, CUR, 'KRW', DATA_VALUE / units)`. **JPY, IDR and VND are per 100** (the item names
say so for JPY only: IDR 7.32 and VND 5.21 KRW on 2026-11-18); the others per 1.

- **43 items served** (`ITEMS`): USD `0000001` and CNY `0000053` are the basic exchange rates; the others are
  arbitraged rates the bank builds from them.
- **Not served**: the eight pre-euro currencies (DEM, FRF, ITL, BEF, ATS, NLG, ESP, FIM, ended 2001–2002), and the two
  older CNY series (`0000027`, 1994–2016; `0000030`, the offshore yuan, 2015–2016).
- **First days**: USD, GBP, HKD 1964; CAD, CHF 1964; SEK 1967; AUD, DKK, NOK 1970; SAR 1976; JPY, KWD, BHD, AED
  1977; SGD, MYR 1983; NZD 1988; EUR, THB, IDR 1994; 22 currencies (TWD, MNT, KZT, PHP, VND, BND, INR, PKR, BDT, MXN,
  BRL, ARS, RUB, HUF, PLN, CZK, QAR, ILS, JOD, TRY, ZAR, EGP) 2015-01-02; CNY 2016-01-04.
- **Two decimals**: MNT (0.37 KRW) moves in steps of about 3%, ARS (0.86) of about 1%, KZT (3.02) of 0.3%. The note
  says so.

### 📅 The Day of a Rate (D2)

Each value is returned under its `TIME`, in ascending order. A row of another item, with an unreadable day or a value
that is not positive is skipped (X-R50); a day with two different values is dropped. The full series could not be
scanned with the public `sample` key (10 rows at most): the scan for wrong values waits for a real key.

### 📦 Request Budget

Measured on 2026-11-19 with the public `sample` key (pages of 10 rows):

| Range | Requests | Time |
|-------|----------|------|
| 10 days, USD, JPY, IDR, MNT | 4 (one per currency) | 2.3 s |

With a real key: a 14-day sync is one request per currency. A full history is one or two pages per currency (USD has
about 15 000 rows since 1964), three currencies at once. Not measured (❔ until the key).

### 🚨 Errors

| Answer | Result |
|--------|--------|
| No `api_key` set | `FXNotConfiguredError` (the route shows «to configure»); no request |
| `RESULT` `INFO-200` (no data) | That currency has no rows |
| `RESULT` `INFO-100` (the key is refused) | `FXServiceError` «refused the API key: check the BOK api_key…» for the whole call |
| `RESULT` `ERROR-602` (too many calls), or HTTP 429 | `FXRateLimitedError` for the whole call; currencies not started yet are never asked |
| Any other `RESULT` code, an HTTP error, a network failure, HTML or text that is not JSON | That currency is skipped with a warning; when every asked currency fails, `FXServiceError` naming each failure |
| A row of another item, an unreadable day, a value not positive | That row is skipped |

### ⚖️ Terms

The ECOS terms are accepted when the key is requested and could not be read beforehand: they stay ❔. The public data
portal data.go.kr lists the ECOS API without use restrictions (a secondary source). Developer decision D1 (lane 75): the
provider is offered for a self-hosted instance that stores the rates for its owner; nothing downloaded from the bank is
committed, and the tests use synthetic answers only. The description names the source («Source: Bank of Korea
(ECOS)»). Registering for a key from outside Korea is not verified (❔).

The note (`warning_i18n`) is at **warning** level: two decimals make small currencies coarse.

### ⚠️ Limitations

- Needs a key (free, from the bank).
- The largest page, the time of a full history and the quality of the old series are measured only with a real key.
- Small currencies are coarse (two decimals).

### 🧪 Tests

`backend/test_scripts/test_services/test_fx_bok.py` pins the key (missing, refused, never in an error's text), the
item table and the units, the requests and the pages, the parallel limit and the pauses, the `RESULT` codes, the
skipped rows and the duplicates, all with synthetic answers written by hand (no network, no DB, no server). It is
registered among the provider error paths:

```bash
./dev.py test services provider-errors
```

The external test reads the real API, and is skipped without `LIBREFOLIO_PLUGIN_FX_BOK_API_KEY`:

```bash
./dev.py test external fx-providers --providers BOK
```

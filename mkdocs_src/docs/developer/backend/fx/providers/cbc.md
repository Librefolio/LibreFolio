# 🇹🇼 CBC — Central Bank of the Republic of China (Taiwan)

| Property | Value |
|----------|-------|
| **Code** | `CBC` |
| **Base Currency** | TWD |
| **API Endpoint** | `https://cpx.cbc.gov.tw/api/OpenData/FTDOpenData_Day` |
| **API Format** | JSON list, the whole series in one answer, no date filter |
| **API Key** | Not required |
| **Terms** | [Open Government Data License, version 1](https://data.gov.tw/license) (政府資料開放授權條款-第1版): open, with attribution |
| **Currencies** | USD only |
| **Update Frequency** | Every Taiwanese business day, between 16:00 and 17:00 Taiwan time (UTC+8) |
| **Historical Data** | From 2008-01-02 |
| **Dataset** | [銀行間市場新臺幣對美元收盤匯率](https://data.gov.tw/dataset/7232) (data.gov.tw 7232) |

### ⚙️ How It Works

The Central Bank of the Republic of China (Taiwan) publishes, as open data, the interbank closing rate of the New Taiwan
dollar against the US dollar, from Taipei Forex Inc. The provider (`backend/app/services/fx_providers/cbc/plugin.py`)
reads the daily file.

- **One request, the whole series**: the endpoint has no date filter. `fetch_rates()` asks it once (about 190 KB, 4 691
  rows from 2008, about 1.4 s) and keeps the days of the asked range itself.
- **Rows**: `{"日期": "20261119", "NTD_USD": "32.942"}`. `日期` means «date» (`yyyyMMdd`); the value is a string, read as
  `Decimal`. The rows come oldest first; the provider sorts them anyway.
- **Start date**: `"min"`, and any start before 2008-01-02, keeps from `FIRST_DAY`. A range that ends before it makes no
  request. TWD alone makes no request; any currency other than USD gets an empty list.
- **Base currency**: `fetch_rates()` with a `base_currency` other than TWD (or None) raises `ValueError`.

### ↔️ Direction and Unit

The series is «NTD/USD», TWD per 1 USD. The plugin returns `(d, 'USD', 'TWD', TWD per 1 USD)`, «1 USD = v TWD»: on
2026-11-19, `(date(2026, 11, 19), 'USD', 'TWD', Decimal('32.942'))`.

### 📅 The Day of a Rate (D2)

The rate of the day is published between 16:00 and 17:00 Taiwan time, on the day itself, as the note of the bank's
[rate page](https://www.cbc.gov.tw/tw/lp-645-1.html) says:
«每一日工作日下午4:00至5:00，提供本日銀行間成交收盤匯率». On 2026-11-19, the value of 19 November was already there. Each value is returned under its own day; weekends and Taiwanese holidays have
no row. A day listed twice would be skipped with a warning, never picked at random (the series has none).

### 💰 Supported Currencies

`get_supported_currencies()` returns TWD and USD, without a request. The CBC also publishes a table of 18 currencies
against USD (`BP01D01`): it is left out, because it arrives about two weeks late (on 2026-11-16 its last day was 30
October) and BDI publishes those currencies every day.

### 📦 Request Budget

Measured on 2026-11-19: one request for 14 days (0.94 s) and one for `"min"` (1.4 s, 4 691 days). No limit is
documented.

### 🚨 Errors

| Answer | Result |
|--------|--------|
| HTTP 429 | `FXRateLimitedError` (its `Retry-After`, through `raise_if_fx_rate_limited()`) |
| Any other HTTP error, or a network failure | `FXServiceError` («CBC open data API error: …»), logged as a warning |
| An HTML page, text that is not JSON, or JSON that is not a list | `FXServiceError` |
| `[]` | An empty list, no error |
| A row whose day cannot be read, or whose value is missing or no positive number (X-R50) | That row is skipped |

### ⚖️ Terms

The dataset is published under the Open Government Data License, version 1, an open licence that asks for attribution.
The provider's description names the source («Source: Central Bank of the Republic of China (Taiwan), Open Government
Data License») in the four languages.

The note (`warning_i18n`) is at **info** level: the source of the rate, its time and the other currencies left out are
facts worth knowing.

### ⚠️ Limitations

- USD only.
- No rate on Taiwanese non-business days.
- The whole series is downloaded at every call (about 190 KB).

### 🧪 Tests

`backend/test_scripts/test_services/test_fx_cbc.py` pins the direction, the days kept from the whole series, the
ascending order, the single request without a query, the start from 2008, the skipped rows, the 429 and every answer
that is not a JSON list, all with synthetic answers written by hand (no network, no DB, no server). It is registered
among the provider error paths:

```bash
./dev.py test services provider-errors
```

The external test reads the real file:

```bash
./dev.py test external fx-providers --providers CBC
```

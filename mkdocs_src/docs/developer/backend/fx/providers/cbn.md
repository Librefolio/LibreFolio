# 🇳🇬 CBN — Central Bank of Nigeria

| Property | Value |
|----------|-------|
| **Code** | `CBN` |
| **Base Currency** | NGN |
| **API Endpoint** | `https://www.cbn.gov.ng/api/GetAllExchangeRatesGRAPH` (about the last month), `https://www.cbn.gov.ng/api/GetAllExchangeRates` (the whole history) |
| **API Format** | JSON list, newest first; **undocumented** (the endpoints the bank's rate page reads) |
| **API Key** | Not required |
| **Terms** | ❔ No terms of use or disclaimer page found. Developer decision D1: offered for a self-hosted instance that stores the rates for its owner |
| **Currencies** | A fixed name map: 12 currencies plus NGN |
| **Update Frequency** | Nigerian business days |
| **Historical Data** | From 2001-12-10 (each currency from its own first day) |
| **Data Page** | [Exchange Rates by Currency](https://www.cbn.gov.ng/rates/ExchRateByCurrency.html) |

### ⚙️ How It Works

The Central Bank of Nigeria shows its exchange rates on a page that reads two JSON endpoints. They are not documented
(decision D10 c, lane 75): the provider (`backend/app/services/fx_providers/cbn/plugin.py`) reads them as they are, says
so in its note, and fails with a clear error when an answer changes shape.

- **Two endpoints**: `GetAllExchangeRates` answers the whole history in one go (62 696 rows from 2001, about 8 MB in
  about 4 s); `GetAllExchangeRatesGRAPH` answers about the last month (240 rows, about 32 KB). Neither takes a date
  filter. The site is behind Cloudflare; GET only.
- **Which one**: a range of at most `RECENT_SPAN_DAYS` (20) days asks the recent endpoint first, and uses it when its
  earliest day is on or before the start of the range. Otherwise (a longer range, an older one, an empty recent answer)
  it asks the whole history. A daily sync downloads 32 KB, not 8 MB.
- **Rows**: `{"id": 65444, "currency": "US DOLLAR", "ratedate": "2026-11-13", "buyingrate": "1352.9741",
  "centralrate": "1353.4741", "sellingrate": "1353.9741"}`. The **central** rate is used, never the buying or the
  selling one. Values are read as `Decimal`.
- **Start date**: `"min"`, and any start before 2001-12-10, keeps from `FIRST_DAY`. NGN alone, or only currencies the
  bank does not publish, makes no request.
- **Base currency**: `fetch_rates()` with a `base_currency` other than NGN (or None) raises `ValueError`.

### ↔️ Direction and Unit

Every central rate is NGN per 1 unit of the currency, JPY and the CFA franc included («YEN» 8.4608, «CFA» 2.2796 on
13 November 2026). The plugin returns `(d, CUR, 'NGN', NGN per 1 CUR)`, «1 CUR = v NGN».

### 🏷️ Currency Names

The bank's names are dirty: trailing spaces and tabs (`"EURO\t"`, `"YEN "`), variants and noise. The names are
stripped, then looked up in `CURRENCY_NAMES`:

| Bank's name | ISO |
|-------------|-----|
| US DOLLAR | USD |
| POUNDS STERLING, POUND STERLING | GBP |
| EURO | EUR |
| YEN, JAPANESE YEN | JPY |
| CFA | XOF (the West African CFA franc) |
| RIYAL | SAR |
| SWISS FRANC | CHF |
| YUAN/RENMINBI | CNY |
| DANISH KRONA, DANISH KRONER | DKK |
| SOUTH AFRICAN RAND | ZAR |
| UAE DIRHAM | AED (from 2026-01-22) |

The bank's name `SDR` (the IMF's special drawing right, a basket of USD, EUR, CNY, JPY and GBP) maps to `XDR` and is served: 1848.9020 NGN per 1 XDR on 2026-11-19.

Every other row is discarded and counted in the log: WAUA (the African Development Bank's unit of account), and
eleven rows named NAIRA or POESO with values of other currencies.

### 📅 The Day of a Rate (D2) and the Duplicates

Each central rate is returned under its `ratedate`. The rates are published on Nigerian business days (four weekend
dates in 25 years); some business days are missing (for example 2023-06-13).

**Conflicting duplicates**: 97 day-and-currency keys appear twice in the history, 64 of them with two different central
rates, sometimes far apart (JPY on 2017-10-09: 2.7072 and 46.0795; DKK on 2019-01-22: 46.5813 and 426.7372). Such a
day is **dropped for that currency** (X-R50), with one warning: the provider never picks one of the two. Two rows with
the same central rate are kept once. Name variants count as the same currency here.

### 📦 Request Budget

Measured on 2026-11-19: 14 days of USD and EUR, one request to the recent endpoint (0.26 s); `"min"` for the 11
currencies, one request to the whole history (1.0 s for the 8 MB at that moment; 3.9 s at the first probe the same
day).
64 conflicting days dropped.

### 🚨 Errors

| Answer | Result |
|--------|--------|
| HTTP 429 | `FXRateLimitedError` (its `Retry-After`, through `raise_if_fx_rate_limited()`) |
| Any other HTTP error, or a network failure | `FXServiceError` («CBN API error for …»), logged as a warning |
| An HTML page (a Cloudflare page), text that is not JSON, or JSON that is not a list | `FXServiceError` («… undocumented endpoint changed …») |
| A row with an unknown name | Discarded, counted in the debug log |
| A row whose day cannot be read, or whose central rate is no positive number | That row is skipped |
| Two different central rates for one currency on one day | That day is dropped for that currency, one warning per call |

### ⚖️ Terms

No terms of use or disclaimer page was found on the bank's site (searched on 16 and 19 November 2026): the terms stay
❔. Developer decision D1 (lane 75): the provider is offered for a self-hosted instance that stores the rates for its
owner; nothing downloaded from the bank is committed, and the tests use synthetic answers only. The description names
the source («Source: Central Bank of Nigeria»).

The note (`warning_i18n`) is at **warning** level: an undocumented source and conflicting rows are a limit of the data
that can mislead.

### ⚠️ Limitations

- The endpoints are undocumented and can change without notice.
- A day with conflicting rates is missing for that currency.
- Single wrong values that are not duplicated are not detected (the provider protects only what it can detect).

### 🧪 Tests

`backend/test_scripts/test_services/test_fx_cbn.py` pins the central rate and its direction, the name map (spaces,
variants, noise), the ascending order, the conflicting and the repeated duplicates, the choice between the two
endpoints, the start from 2001, the skipped rows, the 429 and every answer that is not a JSON list, all with synthetic
answers written by hand (no network, no DB, no server). It is registered among the provider error paths:

```bash
./dev.py test services provider-errors
```

The external test reads the real endpoints:

```bash
./dev.py test external fx-providers --providers CBN
```

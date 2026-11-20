# 🇺🇦 NBU — National Bank of Ukraine

| Property | Value |
|----------|-------|
| **Code** | `NBU` |
| **Base Currency** | UAH |
| **API Endpoint** | `https://bank.gov.ua/NBU_Exchange/exchange_site?start=YYYYMMDD&end=YYYYMMDD&valcode=<cur>&sort=exchangedate&order=asc&json` |
| **API Format** | JSON list, one object per day, one request per currency |
| **API Key** | Not required |
| **Terms** | [bank.gov.ua/en/useterms](https://bank.gov.ua/en/useterms): further use of the bank's materials needs a reference to the source |
| **Currencies** | Discovered at runtime by `get_supported_currencies()`: on 2026-11-16, 40 plus UAH; with the SDR (`XDR`) served since 2026-11-20, 41 plus UAH. `GET /fx/providers` caches the list for 24 h (`backend/app/services/fx/catalog.py`) |
| **Update Frequency** | Daily: a rate set on a business day is valid from the next day; weekends and holidays have rows too |
| **Historical Data** | From 1996-09-02, the first day of the hryvnia |
| **API Docs** | [NBU open data API](https://bank.gov.ua/en/open-data/api-dev) |

### ⚙️ How It Works

The National Bank of Ukraine publishes the official exchange rates of the hryvnia through an open-data API. The
provider (`backend/app/services/fx_providers/nbu/plugin.py`) reads the range endpoint `NBU_Exchange/exchange_site`, one
currency at a time.

- **One request per currency, in series**: `fetch_rates()` sorts the asked currencies and sends one request for each,
  with `start`, `end`, the lower-case `valcode`, `sort=exchangedate`, `order=asc` and `json`. Between two requests it
  waits `PAUSE_SECONDS` (0.3 s): a slow, explicit pace. One currency's whole history (USD from 1996) is about 2 MB and
  arrives in about a second. UAH alone makes no request.
- **Numbers read as `Decimal`**: the answer is parsed with `json.loads(..., parse_float=Decimal, parse_int=Decimal)`, so
  no value passes through a float.
- **Rows read**: `exchangedate`, `cc`, `rate_per_unit` (or `rate` and `units`), `group`. A row of another currency, or a
  row with `group` "3" (a metal), is skipped.
- **Start date**: `"min"`, and any start before 1996-09-02, asks from `FIRST_DAY` (1996-09-02). Before that day the
  values are in karbovanets, 100 000 times larger (USD 176100 on 01.09.1996, 1.761 on 02.09.1996). A range that ends
  before `FIRST_DAY` makes no request.
- **Base currency**: `fetch_rates()` with a `base_currency` other than UAH (or None) raises `ValueError`.

### ↔️ Direction and Unit

Every row is «UAH per `units` units of the foreign currency», and the bank also gives `rate_per_unit`, the rate for one
unit. `_parse_row()` reads `rate_per_unit`; when it is missing, it divides `rate` by `units`. It returns the rate in the
bank's direction: `(exchangedate, CUR, 'UAH', UAH per 1 CUR)`, «1 CUR = v UAH». The FX service normalizes the pair
(alphabetical order, inverted when needed); nothing is inverted in the plugin.

Worked example, the JPY row of one day:

| `exchangedate` | `cc` | `units` | `rate` | `rate_per_unit` | Meaning |
|----------------|------|---------|--------|-----------------|---------|
| 05.01.2026 | JPY | 10 | 2.8423 | 0.28423 | 10 JPY = 2.8423 UAH |

The plugin returns `(date(2026, 1, 5), 'JPY', 'UAH', Decimal('0.28423'))`. A KRW row with `rate` 2.9, `units` 100 and
no `rate_per_unit` is returned as 2.9 / 100: `Decimal('0.029')`.

### 📅 The Day of a Rate (D2)

Each row carries two dates:

- `exchangedate`: the day the rate is **valid**;
- `calcdate`: the business day the bank **set** it.

A rate set on a business day is valid from the next day. Saturdays, Sundays and holidays have rows of their own, copies
of the rate set on the last business day (same `calcdate`). The rows of one week, as pinned by the tests:

| `exchangedate` (valid) | `calcdate` (set) | USD rate |
|------------------------|------------------|----------|
| Fri 09.01.2026 | Thu 08.01.2026 | 41.1 |
| Sat 10.01.2026 | Fri 09.01.2026 | 41.2 |
| Sun 11.01.2026 | Fri 09.01.2026 | 41.2 |
| Mon 12.01.2026 | Fri 09.01.2026 | 41.2 |
| Tue 13.01.2026 | Mon 12.01.2026 | 41.3 |

The rule (D2, developer decision, lane 75): **every row is returned under its `exchangedate`**, weekend and holiday
copies included, with no dedup on `calcdate`. The plugin filters no day.

Tomorrow's row is published the afternoon before (asked on 2026-11-16, the answer already held 17.11 with `calcdate`
16.11). The plugin returns it too; the sync, not the plugin, drops every day after the sync's end
(`_is_date_within_sync_range()` in `backend/app/services/fx/sync.py`), and the next sync reads that row again once its
day has come.

### 💰 Supported Currencies

On 2026-11-16, 40 currencies plus UAH, and since 2026-11-20 the SDR as well (`XDR`, the IMF's unit of account, a basket of USD, EUR, CNY, JPY and GBP: 60.7444 UAH per 1 XDR on 2026-11-19): AED 🇦🇪, AUD 🇦🇺, AZN 🇦🇿, BDT 🇧🇩, CAD 🇨🇦, CHF 🇨🇭, CNY 🇨🇳, CZK 🇨🇿, DKK 🇩🇰,
DZD 🇩🇿, EGP 🇪🇬, EUR 🇪🇺, GBP 🇬🇧, GEL 🇬🇪, HKD 🇭🇰, HUF 🇭🇺, IDR 🇮🇩, ILS 🇮🇱, INR 🇮🇳, JPY 🇯🇵, KRW 🇰🇷, KZT 🇰🇿, LBP 🇱🇧,
MDL 🇲🇩, MXN 🇲🇽, MYR 🇲🇾, NOK 🇳🇴, NZD 🇳🇿, PLN 🇵🇱, RON 🇷🇴, RSD 🇷🇸, SAR 🇸🇦, SEK 🇸🇪, SGD 🇸🇬, THB 🇹🇭, TND 🇹🇳, TRY 🇹🇷,
USD 🇺🇸, VND 🇻🇳, ZAR 🇿🇦.

Beyond the ECB provider's list, NBU quotes AED, AZN, BDT, EGP, GEL, KZT, LBP, MDL, RSD, SAR, TND and VND.

#### 📋 The catalogue rule

`get_supported_currencies()` asks `NBUStatService/v1/statdirectory/exchange?json`, the day's rates. On 2026-11-16 the
answer listed 45 entries, and the plugin keeps the currencies only:

- **Not currencies** (`NOT_CURRENCIES`): the four metals `XAU`, `XAG`, `XPT`, `XPD`. The IMF's SDR `XDR` is served.
- **UAH**, the base, is always added.

An answer with no currency left raises `FXServiceError`. Right after a restart, while the first discovery is slow or
fails, the catalogue lists `FALLBACK_CURRENCIES` (the same 40 plus UAH); the live list replaces it as soon as one
arrives.

### 🚨 Errors

The requests are one per currency, so most failures cost one currency only (XRL-H09). Two answers refuse the client
itself and stop the whole call.

| Answer | Result |
|--------|--------|
| `[]`: an unknown `valcode`, a range with no row | No row, no error: the currency gets an empty list |
| HTTP 403 (Cloudflare is in front of bank.gov.ua) | `FXServiceError` («NBU refused the request (HTTP 403; bank.gov.ua is behind Cloudflare): not retried, no other currency asked»). The call stops: no other currency is asked, nothing is retried, nothing works around it |
| HTTP 429 | `FXRateLimitedError` (`raise_if_fx_rate_limited()`) with the response's `Retry-After`; the call stops and the core pauses the provider ([Paused Providers](../configuration.md#paused-providers)) |
| Any other HTTP error (a 500, a timeout after 60 s) | `FXServiceError` for that currency: it is skipped with one warning («NBU fetch failed for USD, skipping: …»), the others arrive |
| A 200 that is not the JSON list: an HTML page, the bank's «Wrong date format/period» body, an object, an empty body | `FXServiceError` («NBU answer for USD is not the JSON list: …»): that currency is skipped with one warning, the others arrive |
| One row with no number, an unreadable day, a zero or negative value (X-R50) | That day only is skipped (debug log); the rest of the currency is kept |

The catalogue request has its own messages: an HTTP error is «NBU catalogue request failed: …» (a 429 is still
`FXRateLimitedError`), a body that is not the JSON list is the same «not the JSON list» `FXServiceError`.

### ⚖️ Terms and robots.txt

- **Terms**: the bank's [terms of use](https://bank.gov.ua/en/useterms) ask for a reference to the source for any
  further use of its materials. The provider's description names it in the four languages («Source: National Bank of
  Ukraine (bank.gov.ua)»).
- **Valid day**: the provider explains the rule of the day in its `warning_i18n` text, at **info** level
  (`warning_level = "info"`): ℹ️ on every route that uses NBU in the route picker, not ⚠️. The English text:

    > NBU rates are the bank's official rates. Each is set on a business day and valid from the next day, so it is
    > stored under the day it is valid. At weekends and on holidays the bank repeats the last business day's rate.

- **robots.txt** (checked 2026-11-16): `Disallow:` empty for every user agent.
- **Cloudflare**: bank.gov.ua sits behind Cloudflare. A 403 is reported as a refusal and never retried or worked around.

### ⚠️ Limitations

- One request per currency: N currencies cost N requests in series, with 0.3 s between two of them.
- History starts on 1996-09-02; earlier days are never asked.
- Tomorrow's rate is already published, but it is stored only once its day falls inside a sync's range.

### 🧪 Tests

`backend/test_scripts/test_services/test_fx_nbu.py` pins the direction and unit (the JPY and KRW examples above), one
request per currency on the range endpoint, the D2 rows (weekend and tomorrow kept under their `exchangedate`), the
start from 1996-09-02, the skipped rows, rows of another currency or of a metal, every answer that is not the JSON list,
the 403, the 429 and the catalogue rule, with synthetic answers written by hand (no network, no DB, no server). It is
registered among the provider error paths:

```bash
./dev.py test services provider-errors
```

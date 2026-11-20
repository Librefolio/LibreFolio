# 🇮🇹 BDI — Banca d'Italia

| Property | Value |
|----------|-------|
| **Code** | `BDI` |
| **Base Currency** | EUR |
| **API Endpoint** | `https://tassidicambio.bancaditalia.it/terzevalute-wf-web/rest/v1.0/dailyTimeSeries?startDate=YYYY-MM-DD&endDate=YYYY-MM-DD&baseCurrencyIsoCode=<CUR>&currencyIsoCode=EUR&lang=en` |
| **API Format** | JSON (`Accept: application/json`), one time series per request, one request per currency |
| **API Key** | Not required |
| **Terms** | Site © Banca d'Italia ([copyright](https://www.bancaditalia.it/footer/copyright/index.html)); the rates are indicative, not a benchmark under Regulation (EU) 2016/1011 |
| **Currencies** | Discovered at runtime by `get_supported_currencies()`: on 2026-11-16, 149 plus EUR; with the SDR (`XDR`) served since 2026-11-20, 150 plus EUR. `GET /fx/providers` caches the list for 24 h (`backend/app/services/fx/catalog.py`) |
| **Update Frequency** | Daily, Italian business days |
| **Historical Data** | From 1999-01-04, the first day of the euro series |
| **API Docs** | [Operating instructions (PDF)](https://tassidicambio.bancaditalia.it/terzevalute-wf-ui-web/assets/files/Operating_Instructions.pdf), [exchange rates portal](https://www.bancaditalia.it/compiti/operazioni-cambi/portale-tassi/index.html) |

### ⚙️ How It Works

The Banca d'Italia publishes daily exchange rates for about 150 currencies against the euro on its «terze valute»
portal, with a REST API behind it. The provider (`backend/app/services/fx_providers/bdi/plugin.py`) reads the endpoint
`dailyTimeSeries`, one currency at a time.

- **One request per currency, in series**: `fetch_rates()` sorts the asked currencies and sends one request for each,
  with `startDate`, `endDate`, the foreign currency in `baseCurrencyIsoCode`, `EUR` in `currencyIsoCode` and `lang=en`.
  Between two requests it waits `PAUSE_SECONDS` (0.3 s, D9): a slow, explicit pace. One currency's whole history (USD
  from 1999) is about 0.8 MB and arrives in about 1.8 s. EUR alone makes no request.
- **The parameters are not symmetric**: `baseCurrencyIsoCode` is the foreign currency. The other way round
  (`currencyIsoCode=NGN`) the API answers HTTP 400 with a plain-text body, «WARNING! Parameter currencyIsoCode can take
  the value of: EUR, USD or ITL».
- **JSON by the header**: the request sends `Accept: application/json`; the answer holds `resultsInfo` (with
  `exchangeConventionCode`) and `rates`, one object per day with `referenceDate`, `avgRate` (a string) and
  `exchangeConvention`.
- **Values read as `Decimal`**: `_rate()` turns the `avgRate` string into a `Decimal`: no value passes through a float.
- **Start date**: `"min"`, and any start before 1999-01-04, asks from `FIRST_DAY` (1999-01-04). A range that ends
  before `FIRST_DAY` makes no request.
- **Base currency**: `fetch_rates()` with a `base_currency` other than EUR (or None) raises `ValueError`.
- **Reference specification**: the open-source Frankfurter project (MIT) reads the same API; it served as the
  reference for the request shape (D6).

### ↔️ Direction and Unit

Every series is «Foreign currency amount for 1 Euro.»: convention code `C` in `resultsInfo.exchangeConventionCode`,
the same sentence in each row's `exchangeConvention`. The plugin returns the rate in the bank's direction:
`(referenceDate, 'EUR', CUR, CUR per 1 EUR)`, «1 EUR = v CUR». The FX service normalizes the pair (alphabetical order,
inverted when needed); nothing is inverted in the plugin.

Worked example, one row of two series:

| `referenceDate` | Currency | `avgRate` | Meaning |
|-----------------|----------|-----------|---------|
| 2026-11-13 | NGN | `"1498.5186"` | 1 EUR = 1498.5186 NGN |
| 2026-11-13 | USD | `"1.1052"` | 1 EUR = 1.1052 USD |

The plugin returns `(date(2026, 11, 13), 'EUR', 'NGN', Decimal('1498.5186'))` and
`(date(2026, 11, 13), 'EUR', 'USD', Decimal('1.1052'))`.

**The convention guard**: on 2026-11-16 all 171 currencies of a day had convention `C`, but the plugin does not take
it for granted. `_check_convention()` refuses a series whose `exchangeConventionCode` is not `C`, or whose rows name
another convention (such as «Euro amount for 1 foreign currency.»): stored as «CUR per 1 EUR», such a series would be
upside down, the mistake the FED provider made in wave 0. The refused currency is skipped with one warning; the others
arrive.

### 📅 The Day of a Rate (D2)

Each row carries one date, `referenceDate`: the Italian business day the rate belongs to. Weekends and holidays have no
row; a range that holds none answers 200 with `"totalRecords": 0`. An empty or absent `rates` list is read as no rate,
not as an error.

The rule (D2, developer decision, lane 75): **every value is returned under its `referenceDate`**. The plugin filters
no day; the sync, not the plugin, drops every day after the sync's end (`_is_date_within_sync_range()` in
`backend/app/services/fx/sync.py`).

**Suspended currencies**: the bank keeps their rows with `avgRate` «N.A.». RUB has «N.A.» from 2022-03-02; on
2026-11-16 BYN, IRR, KPW and RUB were all «N.A.». Each such row loses its day only (X-R50): the earlier days of the
series are kept.

### 💰 Supported Currencies

On 2026-11-16, 149 currencies plus EUR; since 2026-11-20 `FALLBACK_CURRENCIES` also holds `XDR`, 150 plus EUR:

AED, AFN, ALL, AMD, AOA, ARS, AUD, AWG, AZN, BAM, BBD, BDT, BHD, BIF, BMD, BND, BOB, BRL, BSD, BTN, BWP, BZD, CAD, CDF,
CHF, CLP, CNY, COP, CRC, CUP, CVE, CZK, DJF, DKK, DOP, DZD, EGP, ERN, ETB, EUR, FJD, FKP, GBP, GEL, GHS, GIP, GMD, GNF,
GTQ, GYD, HKD, HNL, HTG, HUF, IDR, ILS, INR, IQD, ISK, JMD, JOD, JPY, KES, KGS, KHR, KMF, KRW, KWD, KYD, KZT, LAK, LBP,
LKR, LRD, LSL, LYD, MAD, MDL, MGA, MKD, MMK, MNT, MOP, MRU, MUR, MVR, MWK, MXN, MYR, MZN, NAD, NGN, NIO, NOK, NPR, NZD,
OMR, PAB, PEN, PGK, PHP, PKR, PLN, PYG, QAR, RON, RSD, RWF, SAR, SBD, SCR, SDG, SEK, SGD, SHP, SLE, SOS, SRD, SSP, STN,
SVC, SYP, SZL, THB, TJS, TMT, TND, TOP, TRY, TTD, TWD, TZS, UAH, UGX, USD, UYU, UZS, VES, VND, VUV, WST, XAF, XCD, XCG,
XDR, XOF, XPF, YER, ZAR, ZMW, ZWG.

`XDR` is the IMF's special drawing right (SDR): the IMF's unit of account, a basket of USD, EUR, CNY, JPY and GBP, not a
commodity. It has the same convention `C` as the other currencies: 0.817625 XDR per 1 EUR on 2026-11-19.

117 of them are not in the ECB provider's list (`FALLBACK_CURRENCIES` in `backend/app/services/fx_providers/ecb/plugin.py`),
among them NGN, KES, GHS, EGP, VND, PKR, DOP and UGX: BDI reaches them in one step to the euro, with no chain of routes.

#### 📋 The catalogue rule

`get_supported_currencies()` asks `latestRates?lang=en`: the last day's rate of every country's currency, one row per
country, so a currency shared by several countries (XOF, XAF, USD…) repeats. On 2026-11-16 the answer held 172 rows.
The plugin keeps:

- **Rows with a rate**: a row whose `eurRate` is «N.A.» (a suspended currency), empty or no positive number is dropped.
- **The SDR is served**: `XDR` stays in the catalogue, in the bank's convention and unit like any other currency.
- **EUR**, the base, is always added.

A `latestRates` answer without the list raises `FXServiceError` («Banca d'Italia catalogue has no latestRates list
(endpoint changed)»), one with no currency left raises «Banca d'Italia catalogue lists no currency». Right after a
restart, while the first discovery is slow or fails, the catalogue lists `FALLBACK_CURRENCIES` (on 2026-11-16 the live
list and the fallback matched, 150 entries); the live list replaces it as soon as one arrives.

### 🚨 Errors

The requests are one per currency, so a failure costs one currency only (XRL-H09); a 429 stops the whole call.

| Answer | Result |
|--------|--------|
| HTTP 200 with `"totalRecords": 0` (an empty or absent `rates` list): a weekend, a holiday, a range with no business day | No row, no error: the currency gets an empty list |
| HTTP 429 | `FXRateLimitedError` (`raise_if_fx_rate_limited()`) with the response's `Retry-After`; the call stops and the core pauses the provider ([Paused Providers](../configuration.md#paused-providers)) |
| Any other HTTP error (the 400 of reversed parameters, a 404, a 500, a timeout after 60 s) | `FXServiceError` («Banca d'Italia API error for NGN: …»): that currency is skipped with one warning («BDI fetch failed for NGN, skipping: …»), the others arrive |
| A 200 that is not JSON: an HTML page, a CSV, an empty body | `FXServiceError` («Banca d'Italia answer for NGN is not JSON: an HTML page», or «first bytes …»): that currency is skipped with one warning |
| A JSON answer that is not an object, or an object without a `rates` list (and not `totalRecords: 0`) | `FXServiceError` («… is not a JSON object», «… has no rates list (endpoint changed)»): that currency is skipped with one warning |
| A series in another convention (code not `C`, or a row naming another convention) | `FXServiceError` («Banca d'Italia quotes NGN in another convention …»): that currency is skipped with one warning |
| One value «N.A.», empty, no number, zero or negative, or one `referenceDate` that is no ISO date (X-R50) | That day only is skipped (debug log); the rest of the currency is kept |

The catalogue request goes through the same reader (`_get_json()`): an HTTP error, an HTML page or a body that is no
JSON object is an `FXServiceError` naming «the catalogue», and a 429 is still `FXRateLimitedError`.

### ⚖️ Terms

- **Terms**: the site is © Banca d'Italia ([copyright](https://www.bancaditalia.it/footer/copyright/index.html)). The
  bank calls the rates indicative, not a financial benchmark under Regulation (EU) 2016/1011.
- **Developer decision D1** (lane 75, 2026-11-16): the provider is offered for a self-hosted instance, which stores the
  rates for its owner. Nothing downloaded from the bank is in the repository: the tests use synthetic answers written
  by hand. The provider's description names the source in the four languages («Source: Banca d'Italia»).
- **robots.txt** (checked 2026-11-16): the API host `tassidicambio.bancaditalia.it` has none (HTTP 404).
- **Indicative rates**: the provider says it in its `warning_i18n` text, at **warning** level
  (`warning_level = "warning"`): ⚠️ on every route that uses BDI in the route picker, because a value of the day before
  for some currencies is a limit of the data that can mislead, not only a fact worth knowing. On 2026-11-13 the NGN
  rate was 0.04% from the Central Bank of Nigeria's rate of 12/11 and 0.18% from that of 13/11. The English text:

    > Banca d'Italia's rates are indicative, not a financial benchmark. For the major currencies they are the ECB
    > reference rates; for the others the bank computes them, and for some administered currencies the value can
    > reflect the official rate of the day before.

### ⚠️ Limitations

- No data at weekends and on Italian holidays.
- Indicative rates, not a benchmark; for some administered currencies the value can reflect the official rate of the
  day before.
- One request per currency: N currencies cost N requests in series, with 0.3 s between two of them.
- **A first full-history sync of many currencies is long**: the sync waits for the provider's whole answer. Its 120 s
  wait on a route's legs (`asyncio.wait_for(..., timeout=120.0)` in `backend/app/services/fx/sync.py`) starts only after
  every provider of the sync has answered, so it never cuts a slow fetch and never switches route because of time
  (lane 75, L25c). One currency's whole history takes about 1.8 s plus the 0.3 s pause, so roughly 50 BDI currencies
  from 1999 fit the 120 s a sync started from the interface waits for its answer (`FX_SYNC_TIMEOUT_MS`, or a sync
  window's longer **Timeout**; see [Architecture](../architecture.md)); beyond that the interface stops waiting first.
- Suspended currencies (BYN, IRR, KPW, RUB on 2026-11-16) are not offered, and their «N.A.» days are never stored.
- History starts on 1999-01-04; earlier days are never asked.

### 🧪 Tests

`backend/test_scripts/test_services/test_fx_bdi.py` pins the direction (NGN and JPY, euro first), one request per
currency against the euro in JSON, the start from 1999-01-04, the days kept as given, the skipped «N.A.» and unreadable
values, every answer that is not the currency's euro series (the 400 of reversed parameters, an HTML page, a CSV, no
`rates` list, an inverted or dollar convention, a 500), the 429 and the catalogue rule, with synthetic answers written
by hand (no network, no DB, no server). It is registered among the provider error paths:

```bash
./dev.py test services provider-errors
```

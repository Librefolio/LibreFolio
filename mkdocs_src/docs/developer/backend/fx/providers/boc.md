# 🇨🇦 BOC — Bank of Canada

| Property | Value |
|----------|-------|
| **Code** | `BOC` |
| **Base Currency** | CAD |
| **API Endpoint** | `https://www.bankofcanada.ca/valet/observations/group/FX_RATES_DAILY/json?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD` |
| **API Format** | JSON (Valet), every series of the group in one request |
| **API Key** | Not required |
| **Terms** | [bankofcanada.ca/terms](https://www.bankofcanada.ca/terms/), linked in every Valet answer: reuse with attribution; the rates are indicative, not a benchmark for transactions |
| **Currencies** | Discovered at runtime by `get_supported_currencies()`: on 2026-11-16, 24 plus CAD. `GET /fx/providers` caches the list for 24 h (`backend/app/services/fx/catalog.py`) |
| **Update Frequency** | Daily, Canadian business days, by 16:30 ET |
| **Historical Data** | From 2017-01-03, the first day of the `FX_RATES_DAILY` group |
| **API Docs** | [Valet API](https://www.bankofcanada.ca/valet/docs) |

### ⚙️ How It Works

The Bank of Canada publishes its daily average exchange rates through Valet, its open-data API. The provider
(`backend/app/services/fx_providers/boc/plugin.py`) reads the group `FX_RATES_DAILY`, which holds one series
`FX<CUR>CAD` per currency.

- **One request for every currency**: `fetch_rates()` asks the group once, with `start_date` and `end_date`, and picks
  the series of the asked currencies from the answer. The whole history (2017 onward, 24 live series) is about 4 MB and
  arrives in about 1.6 s. CAD alone makes no request; an asked currency the group does not hold gets an empty list.
- **Never a series request**: Valet also answers `observations/FXUSDCAD,FXEURCAD/json`, but a request naming one
  series it does not know is HTTP 404 for every series asked. A series the bank removes would then break every currency,
  so the provider always asks the group.
- **Values read as `Decimal`**: each observation is `{"d": "YYYY-MM-DD", "FX<CUR>CAD": {"v": "1.4181"}, …}`, with the
  values as strings. `_value()` turns the string into a `Decimal`: no value passes through a float.
- **Start date**: `"min"`, and any start before 2017-01-03, asks from `FIRST_DAY` (2017-01-03). The noon rates before
  that day are another group, `LEGACY_NOON_RATES`, with another methodology: they are never mixed in. A range that ends
  before `FIRST_DAY` makes no request.
- **Base currency**: `fetch_rates()` with a `base_currency` other than CAD (or None) raises `ValueError`.

### ↔️ Direction and Unit

Every series `FX<CUR>CAD` is «CAD per 1 unit of the foreign currency», for every currency: there is no unit multiplier
to read. The plugin returns the rate in the bank's direction: `(d, CUR, 'CAD', CAD per 1 CUR)`, «1 CUR = v CAD». The FX
service normalizes the pair (alphabetical order, inverted when needed); nothing is inverted in the plugin.

Worked example, one observation:

| `d` | `FXUSDCAD` | `FXJPYCAD` | Meaning |
|-----|------------|------------|---------|
| 2026-01-05 | `{"v": "1.4181"}` | `{"v": "0.008940"}` | 1 USD = 1.4181 CAD, 1 JPY = 0.008940 CAD |

The plugin returns `(date(2026, 1, 5), 'USD', 'CAD', Decimal('1.4181'))` and
`(date(2026, 1, 5), 'JPY', 'CAD', Decimal('0.008940'))`.

**Few digits for small units**: the bank publishes the value with few decimals whatever its size. On 2026-11-13 IDR was
`0.000078` CAD (two significant digits) and KRW `0.001067`. A rate of IDR read from BOC is therefore rounded by up to
about 1%; the provider says so in its `warning_i18n` (quoted below, under Terms and robots.txt).

### 📅 The Day of a Rate (D2)

Each observation carries one date, `d`: the Canadian business day the average belongs to. Weekends and Canadian
holidays have no observation at all; a range that holds none answers 200 with `"observations": []`. Asked on
2026-11-16 for 10–13 November, the answer held 10, 12 and 13 November: the 11th, Remembrance Day, is absent.

The rule (D2, developer decision, lane 75): **every value is returned under its `d`**. The plugin filters no day; the
sync, not the plugin, drops every day after the sync's end (`_is_date_within_sync_range()` in
`backend/app/services/fx/sync.py`).

### 💰 Supported Currencies

On 2026-11-16, 24 currencies plus CAD: AUD 🇦🇺, BRL 🇧🇷, CHF 🇨🇭, CNY 🇨🇳, EUR 🇪🇺, GBP 🇬🇧, HKD 🇭🇰, IDR 🇮🇩, INR 🇮🇳,
JPY 🇯🇵, KRW 🇰🇷, MXN 🇲🇽, MYR 🇲🇾, NOK 🇳🇴, NZD 🇳🇿, PEN 🇵🇪, PLN 🇵🇱, SEK 🇸🇪, SGD 🇸🇬, THB 🇹🇭, TRY 🇹🇷, TWD 🇹🇼, USD 🇺🇸,
ZAR 🇿🇦.

Beyond the ECB provider's catalogue, BOC quotes PEN. It is also a second source for MXN, BRL, INR and TWD, which the
ECB provider lists too.

#### 📋 The catalogue rule

`get_supported_currencies()` asks the same group with `recent=1`: the last observation of every series. The plugin
keeps the live currencies only:

- **Series keys**: a key of the form `FX<CUR>CAD` names the currency `<CUR>`; any other key is ignored.
- **Closed series** (`CLOSED_AFTER`, 31 days): a series whose last value is more than 31 days older than the newest
  value of the answer. On 2026-11-16: VND (last value 2019-12-31), RUB and SAR (2026-04-30).
- **CAD**, the base, is always added.

An answer with no currency raises `FXServiceError` («Bank of Canada catalogue lists no currency»). Right after a
restart, while the first discovery is slow or fails, the catalogue lists `FALLBACK_CURRENCIES` (the same 24 plus CAD;
on 2026-11-16 the live list and the fallback matched, 25 entries); the live list replaces it as soon as one arrives.

### 🚨 Errors

The call is one request for every currency, so its outcome is the whole call's: there is no per-currency skip as in the
parallel providers (FED, BOE).

| Answer | Result |
|--------|--------|
| HTTP 200 with `"observations": []`: a weekend, a holiday, a range with no business day | No row, no error: every asked currency gets an empty list |
| HTTP 429 | `FXRateLimitedError` (`raise_if_fx_rate_limited()`) with the response's `Retry-After`; the core pauses the provider ([Paused Providers](../configuration.md#paused-providers)) |
| Any other HTTP error (a 400 for a malformed date, a 404, a 500, a timeout after 60 s) | `FXServiceError` («Bank of Canada API error: …»), logged as a warning |
| A 200 that is an HTML page | `FXServiceError` («Bank of Canada answer is an HTML page, not the Valet JSON (endpoint changed or request refused)») |
| A 200 that is not JSON, such as an empty body | `FXServiceError` («Bank of Canada answer is not JSON: first bytes …») |
| A JSON answer without an `observations` list (an object without it, a list) | `FXServiceError` («Bank of Canada answer has no observations list (endpoint changed)») |
| One value that is empty, no number, zero or negative, or not a `{"v": …}` object (X-R50) | That day only is skipped for that currency (debug log); the rest is kept |
| One observation whose `d` is no ISO date | That observation is skipped (debug log); the other days are kept |

The same checks apply to the catalogue request: an HTML answer to `get_supported_currencies()` is an `FXServiceError`.

### ⚖️ Terms and robots.txt

- **Terms**: the bank's [terms](https://www.bankofcanada.ca/terms/), linked in every Valet answer, allow reuse with
  attribution to the Bank of Canada. The provider's description names the source in the four languages («Source: Bank
  of Canada»). The terms also ask not to work around the limits the bank imposes on Valet requests: the provider makes
  one request per call and, after a 429, waits for the pause.
- **Indicative rates**: the bank calls these rates indicative, not a benchmark for transactions. The provider says it in
  its `warning_i18n` text, at **info** level (`warning_level = "info"`): ℹ️ on every route that uses BOC in the route
  picker, not ⚠️. The English text:

    > Bank of Canada rates are indicative daily averages, one per Canadian business day: none at weekends and on
    > Canadian holidays. IDR and KRW are published with few digits (IDR 0.000079 CAD), so their BOC rates are rounded,
    > by up to about 1% for IDR.

- **robots.txt** (checked 2026-11-16): nothing is disallowed under `/valet/`.

### ⚠️ Limitations

- No data at weekends and on Canadian holidays.
- Indicative daily averages, not a benchmark for transactions.
- IDR and KRW are published with few digits: IDR is rounded by up to about 1%.
- One request for all currencies: one failing answer fails the whole call, for every currency.
- History starts on 2017-01-03; earlier days are never asked.

### 🧪 Tests

`backend/test_scripts/test_services/test_fx_boc.py` pins the direction (the USD and JPY example above), the single
request on the group with the asked range, no request for CAD alone, the start from 2017-01-03, the days kept as given,
the skipped values, the empty answer, every answer that is not the group's JSON, the 429 and the catalogue rule, with
synthetic answers written by hand (no network, no DB, no server). It is registered among the provider error paths:

```bash
./dev.py test services provider-errors
```

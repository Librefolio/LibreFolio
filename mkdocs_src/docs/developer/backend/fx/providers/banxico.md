# 🇲🇽 BANXICO — Banco de México

| Property | Value |
|----------|-------|
| **Code** | `BANXICO` |
| **Base Currency** | MXN |
| **API Endpoint** | `https://www.banxico.org.mx/SieAPIRest/service/v1/series/{id1,id2,…}/datos/{yyyy-MM-dd}/{yyyy-MM-dd}` |
| **API Format** | JSON (SIE API), every series in one request |
| **API Key** | Required: a free token of 64 characters, setting `token` (secret, instance-wide), sent in the `Bmx-Token` header |
| **Terms** | «Salvedad de uso» ([banxico.org.mx](https://www.banxico.org.mx/footer-es/salvedad-politicas-uso-banco-.html)): a general authorisation to reproduce and use the data, citing the source and the bank's web address |
| **Currencies** | A static table: USD, EUR, JPY, GBP, CNY and XDR plus MXN. No request: `get_supported_currencies()` returns the table |
| **Update Frequency** | Every Mexican banking day; the FIX is determined at 12:00 Mexico City time |
| **Historical Data** | USD from 1991-11-12; the other five from 2018-07-31 |
| **Limits** | 200 requests every 5 minutes and 10 000 a day (the bank's documentation) |
| **API Docs** | [SIE API](https://www.banxico.org.mx/SieAPIRest/service/v1/), operation `consultaDatosSerieRango` |

### ⚙️ How It Works

The Banco de México publishes its series through the SIE API. The provider
(`backend/app/services/fx_providers/banxico/plugin.py`) asks for the series of every wanted currency in a single
request and reads the answer

```json
{"bmx": {"series": [{"idSerie": "SF43718", "titulo": "…", "datos": [{"fecha": "13/11/2026", "dato": "18.5525"}]}]}}
```

- **One request for every currency**: the series ids go in the URL, comma separated; the documentation allows up to 20
  series per request, the provider asks 6 at most. A currency with no series gets an empty list and is not asked; MXN
  alone, or a range that ends before the start, makes no request.
- **Start date**: `"min"`, and any start before 1991-11-12 (`FIRST_DAY`), asks from `FIRST_DAY`. The CF307 series simply
  answer from their own first day.
- **Values read as `Decimal`**: `dato` is a string. A value with thousands separators (`1,234.5`) is read too; no value
  passes through a float.
- **Base currency**: `fetch_rates()` with a `base_currency` other than MXN (or None) raises `ValueError`.

### 🔑 The Token

- It travels **only in the `Bmx-Token` header**, never in the URL, so it is in no access log of a proxy and in no error
  text.
- The field is declared in `settings_fields` as `token`: `SettingScope.SYSTEM` (instance-wide), `secret=True`,
  `required=True`. How an administrator sets it: [Plugin Settings](../../../../admin/configuration_secrets.md#plugin-settings).
- **No token → `NOT_CONFIGURED` before any call**: the boundary of the core (`call_fx_provider()` in
  `backend/app/services/fx/runtime.py`) raises `FXNotConfiguredError` when a required setting is missing, so the bank is
  never asked. The plugin refuses too: if `fetch_rates()` is reached without a token it raises `FXNotConfiguredError`
  before opening a connection.

### ↔️ Direction and the Series

Every series is «MXN per 1 unit of the foreign currency». The plugin returns the rate in the bank's direction:
`(day, CUR, "MXN", value)`. The FX service normalizes the pair; nothing is inverted in the plugin.

| Currency | Series | Table | From | Notes |
|----------|--------|-------|------|-------|
| USD | `SF43718` | CF102 | 1991-11-12 | The **FIX**, dated on the day it is **determined** (12:00, Mexico City). Not `SF60653`, the same FIX dated on its settlement day |
| EUR | `SF46410` | CF307 | 2018-07-31 | |
| JPY | `SF46406` | CF307 | 2018-07-31 | Four decimals only (0.1160): the rate moves in steps of about 0.1% |
| GBP | `SF46407` | CF307 | 2018-07-31 | |
| CNY | `SF290383` | CF307 | 2018-07-31 | |
| XDR | `SF46411` | CF307 | 2018-07-31 | The SDR (IMF basket) |

The series were read row by row in the SIE catalogue on 2026-11-19 (lane 75).

### 📅 The Day of a Rate

Every value is returned under the `fecha` the bank gives it (`DD/MM/YYYY`); the plugin keeps only the rows inside the
asked range. A day without a publication, a Mexican bank holiday, is `"dato": "N/E"`: that day is skipped and the
others are kept. The same happens to a value that is no positive number, or a row whose `fecha` cannot be read (debug
log).

### 📦 Request Budget

One request per call, whatever the number of currencies. A 14-day range and the `"min"` range (1991 onward) are each one
request. **Not verified**: the largest range one request accepts. It needs a real token, and none was available when the
plugin was written; if the bank answers a long range with an error, the sync would have to split it.

### 🚨 Errors

The call is one request, so its outcome is the whole call's.

| Answer | Result |
|--------|--------|
| No token set | `FXNotConfiguredError` (`NOT_CONFIGURED`), no request |
| HTTP 429, or HTTP 400 carrying the header `Bmx-secondsToReset` | `FXRateLimitedError` with `retry_after` = the seconds of that header (a 429 uses `Retry-After`, through `raise_if_fx_rate_limited()`); the core pauses the provider ([Paused Providers](../configuration.md#paused-providers)) |
| HTTP 400 `{"error": {"mensaje": "Token inválido", …}}` | `FXServiceError` («Banco de México refused the API token: …»). **Not** rate limited: no pause, the administrator must fix the token |
| Any other HTTP error, or a timeout after 60 s | `FXServiceError` («Banco de México API error: …»), logged as a warning |
| A 200 that is an HTML page | `FXServiceError` («… is an HTML page, not the SIE JSON …») |
| A 200 that is not JSON | `FXServiceError` («… is not JSON: first bytes …») |
| JSON without a `bmx.series` list | `FXServiceError` («… has no bmx.series list (endpoint changed)») |
| One value that is `N/E`, no number, zero or negative (X-R50) | That day only is skipped; the rest is kept |

### ⚖️ Terms

The bank's «Salvedad de uso» grants a general authorisation to reproduce and use its data, citing the source and the
bank's web address. The provider's description names the source in the four languages («Source: Banco de México (banxico.org.mx)»), and
`docs_url` points to the [user page](../../../../user/fx/providers/banxico.md).

The provider shows its note at **info** level (`warning_level = "info"`): which FIX, which date and the JPY step are
facts worth knowing, not a limit of the data that misleads.

### ⚠️ Limitations

- Needs a token: without one the provider is *to configure* and never called.
- No rate on Mexican bank holidays.
- EUR, JPY, GBP, CNY and XDR start on 2018-07-31; only USD goes back to 1991.
- JPY has four decimals: about 0.1% steps.
- The limits of the bank (200 requests every 5 minutes, 10 000 a day) are shared by every request made with the token.

### 🧪 Tests

`backend/test_scripts/test_services/test_fx_banxico.py` pins the direction of each series, the single request with the
token in its header, the start from 1991, the days kept as given, the skipped values, the missing token, the rate limit
with its wait, the refused token (not a rate limit), every answer that is not the series JSON, the static catalogue and
the one secret `token` field, all with synthetic answers written by hand (no network, no DB, no server). It is
registered among the provider error paths:

```bash
./dev.py test services provider-errors
```

The external test reads the real API and **skips** without the token (the instance's setting, or the variable
`LIBREFOLIO_PLUGIN_FX_BANXICO_TOKEN`):

```bash
LIBREFOLIO_PLUGIN_FX_BANXICO_TOKEN=<token> ./dev.py test external fx-providers --providers BANXICO
```

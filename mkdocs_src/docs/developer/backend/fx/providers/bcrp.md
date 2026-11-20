# 🇵🇪 BCRP — Banco Central de Reserva del Perú

| Property | Value |
|----------|-------|
| **Code** | `BCRP` |
| **Base Currency** | PEN |
| **API Endpoint** | `https://estadisticas.bcrp.gob.pe/estadisticas/series/api/PD04638PD/json/{yyyy-MM-dd}/{yyyy-MM-dd}` |
| **API Format** | JSON (BCRPData), sent as `text/html` |
| **API Key** | Not required |
| **Terms** | [Condiciones de uso](https://estadisticas.bcrp.gob.pe/estadisticas/series/ayuda/condiciones-de-uso): reproduction allowed without express authorisation, citing the source |
| **Currencies** | USD only (one series) |
| **Update Frequency** | Peruvian business days, published one to three days late |
| **Historical Data** | From 1997-01-02 |
| **API Docs** | [BCRPData API](https://estadisticas.bcrp.gob.pe/estadisticas/series/ayuda/api) |

### ⚙️ How It Works

BCRPData is the statistics API of Peru's central bank. The provider (`backend/app/services/fx_providers/bcrp/plugin.py`)
reads one series, `PD04638PD`, «Tipo de cambio - TC Interbancario (S/ por US$) - Venta»: the interbank exchange rate of
the US dollar, sell side.

- **One request for the whole range**: `fetch_rates()` asks the series once, from the start to the end of the range. The
  whole history (1997 onward) is about 470 KB and arrives in about 4.4 s.
- **JSON sent as `text/html`**: the answer is parsed from its text, whatever its content type.
- **Spanish day names**: each period is `{"name": "10.Nov.26", "values": ["3.41621428571429"]}`. The name is
  `dd.Mmm.yy` with Spanish month abbreviations (`Ene`, `Feb`, `Mar`, `Abr`, `May`, `Jun`, `Jul`, `Ago`, `Set`, `Oct`,
  `Nov`, `Dic`; `Sep` is accepted too). A two-digit year from 90 to 99 is in the 1990s, any other in the 2000s.
- **Values read as `Decimal`**: the value is a string with many decimals (the day's average of the interbank sells), kept
  whole.
- **Start date**: `"min"`, and any start before 1997-01-02, asks from `FIRST_DAY` (asked from 1990, the series answers
  `n.d.` before 1997). PEN alone makes no request; any currency other than USD gets an empty list.
- **Base currency**: `fetch_rates()` with a `base_currency` other than PEN (or None) raises `ValueError`.

### ↔️ Direction and Unit

The series is «S/ por US$», PEN per 1 USD. The plugin returns `(d, 'USD', 'PEN', PEN per 1 USD)`, «1 USD = v PEN»: on
2026-11-10, `(date(2026, 11, 10), 'USD', 'PEN', Decimal('3.41621428571429'))`.

### 📅 The Day of a Rate (D2)

Each value is returned under the day of its name. `"n.d."` (no data) marks the Peruvian holidays (356 days since 1997)
and the last days the bank has not published yet: on 2026-11-19, 17–19 November were still `n.d.`. **An `n.d.` day is
skipped, never stored as zero**; a later sync finds the value once it is published.

### 💰 Supported Currencies

`get_supported_currencies()` returns PEN and USD, without a request. The BCRP also publishes a euro series
(`PD04648PD`), left out: between 5 and 12 November 2026 it moved from 3.83 to 4.04 while USD × EUR/USD stayed at
3.77–3.79 (research, lane 75), so it is not a reference rate. Its other USD series (buy side, the banking system, the
11:00 and 13:30 quotes) are not used.

### 📦 Request Budget

Measured on 2026-11-19: one request for 14 days (0.72 s) and one for `"min"` (4.4 s, 7 440 days). No limit is
documented.

### 🚨 Errors

| Answer | Result |
|--------|--------|
| HTTP 429 | `FXRateLimitedError` (its `Retry-After`, through `raise_if_fx_rate_limited()`) |
| Any other HTTP error, or a network failure | `FXServiceError` («BCRP API error: …»), logged as a warning |
| An HTML page | `FXServiceError` («… request blocked by the site's firewall, or endpoint changed») |
| Text that is not JSON, or JSON without a `periods` list | `FXServiceError` |
| `"periods": []` (a range without data, a Sunday) | An empty list, no error |
| `n.d.`, a value that is no positive number, or a name that cannot be read (X-R50) | That day only is skipped |

**The site is behind a firewall** (Incapsula, Imperva): asking an unknown series answers an HTML page with a challenge
script instead of JSON. The provider never works around it (no headless browser, no change of identity): an HTML answer
fails the call with a clear error.

### ⚖️ Terms

The BCRP's conditions of use allow reproducing its statistics, in whole or in part, without express authorisation,
provided the source is cited. The provider's description ends with «Source: BCRP (BCRPData)» in the four languages.

The note (`warning_i18n`) is at **info** level: which rate, the delay of one to three days and the euro left out are
facts worth knowing, not a limit of the data that misleads.

### ⚠️ Limitations

- USD only.
- The last one to three days arrive at a later update.
- No rate on Peruvian holidays.

### 🧪 Tests

`backend/test_scripts/test_services/test_fx_bcrp.py` pins the direction, the digits kept whole, the Spanish month names
and the two-digit years, the single request, the start from 1997, the `n.d.` days skipped, the other skipped rows, the
empty periods, the 429, the HTML page of the firewall and every answer that is not the series JSON, all with synthetic
answers written by hand (no network, no DB, no server). It is registered among the provider error paths:

```bash
./dev.py test services provider-errors
```

The external test reads the real API:

```bash
./dev.py test external fx-providers --providers BCRP
```

# 🇦🇷 BCRA — Banco Central de la República Argentina

| Property | Value |
|----------|-------|
| **Code** | `BCRA` |
| **Base Currency** | ARS |
| **API Endpoint** | `https://api.bcra.gob.ar/estadisticascambiarias/v1.0/Cotizaciones/{code}?fechadesde=…&fechahasta=…&limit=1000` |
| **API Format** | JSON, **documented** (OpenAPI in the bank's [API catalogue](https://www.bcra.gob.ar/BCRAyVos/catalogo-de-APIs-banco-central.asp)) |
| **API Key** | Not required |
| **Terms** | [Aviso legal](https://www.bcra.gob.ar/aviso-legal/): informative, educational or academic use, citing the bank; no commercial use without permission. Developer decision Q2 (b): kept for a self-hosted instance, with a note; the paid cloud turns it off (`LIBREFOLIO_FX_PROVIDERS_ENABLED`) |
| **Currencies** | A fixed code map: 33 currencies plus ARS |
| **Update Frequency** | Argentine business days |
| **Historical Data** | From 2002-03-04 (`FIRST_DAY`, the first day of REF); some currencies start later |

### ⚙️ How It Works

The provider (`backend/app/services/fx_providers/bcra/plugin.py`) reads one series per currency from the BCRA's
«Estadísticas Cambiarias v1.0» API.

- **Windows**: `WINDOW_DAYS` (1 095 days, about 760 records) per request, oldest first, under the API's page limit of
  1 000 (`limit` must be between 10 and 1 000). A 14-day sync is one request per currency.
- **In parallel**: at most `MAX_PARALLEL` (3) currencies at once, `PAUSE_SECONDS` (0.3 s) between two request starts
  of the call, the [SARB](sarb.md) pattern. Three currencies at once take about the time of one (8.0 s against 18.4 s
  sequential, 4 windows each).
- **Values** are read as `Decimal` straight from the JSON text (`parse_float=Decimal`): `tipoCotizacion`, ARS per
  unit. `tipoPase` (the parity to the dollar) is not used.
- **An empty range** answers 200 with `count` 0 and no results: no rows. But once, four consecutive windows of REF
  answered empty and the same windows answered their rows a minute later; so an **empty window between two windows
  with values** fails that currency, rather than storing a silent hole.
- **A cut answer** (`metadata.resultset.count` above the records returned) fails that currency. `count` counts
  records, not dates: a date can carry two records.
- **Start date**: `"min"`, and any start before 2002-03-04, keeps from `FIRST_DAY`. ARS alone, or only currencies
  outside the map, makes no request.
- **Base currency**: `fetch_rates()` with a `base_currency` other than ARS (or None) raises `ValueError`.

### ↔️ Direction, Codes and the Two Dollar Rates

Every value is ARS per unit: `(d, CUR, 'ARS', tipoCotizacion / units)`. `CODES` maps the ISO code to the bank's:

| ISO | BCRA code | Note |
|-----|-----------|------|
| USD | `REF` | «DOLAR REFERENCIA COM 3500», the official reference rate |
| MXN | `MXP` | |
| VND | `VND` | quoted per 1 000 dong, divided by 1 000 |
| 29 others | the same | AUD AWG BOB BRL CAD CHF CLP CNY COP CZK DKK EUR GBP HKD ILS INR JPY NIO NOK NZD PEN PYG RSD RUB SEK SGD TRY UYU ZAR |
| XDR | `DEG` | the IMF's special drawing right (SDR, a basket of USD, EUR, CNY, JPY and GBP), built like the other currencies on the «USD» row: 2103.9547 ARS per 1 XDR on 2026-11-19 |

**Not served**: the «USD» row (`DOLAR E.E.U.U.`, definition not documented), XAU
and XAG (no ARS value), CNH (not ISO), VEB (three redenominations under one code), the legacy ATS, DEM, ESP, ITL.

**The two dollar rates**: the bank builds every other currency's `tipoCotizacion` on its «USD» row times the
currency's parity to the dollar (EUR 1.0977 × 1 559.5 = 1 711.86 on 2026-11-18), not on REF. The «USD» row and REF
differ, at most in the year, by 14.9% in 2002, 2.5% in 2008, 3.3% in 2014, 6.4% in 2018, 4.9% in 2019, 5.7% in 2023,
4.1% in 2025, and under 1% in most other years. So EUR/ARS through BCRA and EUR/USD × USD/ARS through REF can differ by
that much. **To be reviewed with the developer** (lane 75, L38).

**The method of A 3500 changed on 2026-01-01**: weighted averages of actual trades instead of a survey of quotes
(Comunicación A 8359).

### 📅 The Day of a Rate (D2) and the Duplicates

Each value is returned under its `fecha`, in ascending order. Measured on 2026-11-19: REF has 6 064 days from
2002-03-04, no weekend date and no zero.

- **First days**: most currencies from 2002-03-04; CNY 2006, HKD 2011, NIO and TRY 2012, NZD 2013, SGD 2014, INR and
  RUB 2015, VND 2017.
- **Duplicates**: a date can carry two or three records. Equal values are kept once; on five days (among them
  2007-03-02, 2008-10-17 and 2017-09-06, where REF reads 17.2183 and 37.6917) the values differ, and the day is
  dropped (X-R50), with one warning per currency.
- **Precision**: six decimals; small values are coarse in the early years (COP 0.00106 ARS in 2003, a step of about
  1%).

### 📦 Request Budget

Measured on 2026-11-19:

| Range | Requests | Answer | Time |
|-------|----------|--------|------|
| 14 days, the 32 currencies | 32 | 37 KB | 12.4 s |
| `"min"`, USD alone | 9 | 0.9 MB, 6 059 days | 12.1 s |
| `"min"`, USD, EUR and BRL | 27 | 2.4 MB | 15.4 s |
| `"min"`, the 32 currencies | 288 | 23 MB | 125 s |

A sync asks a provider only for the currencies of the configured pairs (`fx/sync.py`, the legs of the routes). Every
currency costs about 12 s from 2002, three of them at once: a full history stays under ~100 s up to about 20
currencies.

### 🚨 Errors

| Answer | Result |
|--------|--------|
| HTTP 429 on any request | `FXRateLimitedError` for the whole call (`raise_longest_refusal`); the currencies not started yet are never asked |
| HTTP 400 (with the API's `errorMessages`), any other HTTP error or a network failure | That currency is skipped, with a warning naming the cause |
| An HTML page, text that is not JSON, or JSON without a `results` list | That currency is skipped |
| A cut answer, or an empty window between two with values | That currency is skipped |
| Every asked currency skipped | `FXServiceError` naming each failure |
| A record of another code, an unreadable date, a value not positive | That record is skipped |
| Two different values for one currency on one day | That day is dropped for that currency |

### ⚖️ Terms

The [aviso legal](https://www.bcra.gob.ar/aviso-legal/) allows reuse «con fines informativos, educativos o
académicos», citing «Banco Central de la República Argentina», and forbids use «con fines comerciales, publicitarios o
de campaña sin autorización previa»; the bank may change or suspend the API without notice. Developer decision Q2
(b), 19/11/2026: the provider stays for a self-hosted instance, the note says so, and the paid cloud turns it off with
`LIBREFOLIO_FX_PROVIDERS_ENABLED`. Nothing downloaded from the bank is committed; the tests use synthetic answers only.
The RUB rate is the BCRA's own (Q3 (b)): the note says so.

The note (`warning_i18n`) is at **warning** level: non-commercial terms, a method change and two dollar rates are
limits that can mislead.

### ⚠️ Limitations

- The API can change or be suspended without notice.
- The other currencies are built on a dollar rate other than REF.
- A full history of many currencies takes minutes (288 requests for all 32).

### 🧪 Tests

`backend/test_scripts/test_services/test_fx_bcra.py` pins the code map, the windows, the parallel limit and the
pauses, the `Decimal` values, the skipped records, the duplicates, each way a series can fail (and that the others are
still returned), the cut and the empty answers, and the 429, all with synthetic answers written by hand (no network,
no DB, no server). It is registered among the provider error paths:

```bash
./dev.py test services provider-errors
```

The external test reads the real API:

```bash
./dev.py test external fx-providers --providers BCRA
```

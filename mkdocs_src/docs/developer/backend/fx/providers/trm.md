# 🇨🇴 TRM — Colombia (Superintendencia Financiera)

| Property | Value |
|----------|-------|
| **Code** | `TRM` |
| **Base Currency** | COP |
| **API Endpoint** | `https://www.datos.gov.co/resource/32sa-8pi3.json` (Socrata SODA, `$where`, `$order`, `$limit`, `$offset`) |
| **API Format** | JSON list, one row per validity interval |
| **API Key** | Not required (a Socrata app token is optional; without it requests share the anonymous pool) |
| **Terms** | Creative Commons Attribution-ShareAlike 4.0 International (the dataset's metadata), attribution to the Superintendencia Financiera de Colombia |
| **Currencies** | USD only |
| **Update Frequency** | Every Colombian banking day, the day before the TRM is valid |
| **Historical Data** | From 1991-12-02 |
| **Dataset** | [Tasa de Cambio Representativa del Mercado - TRM](https://www.datos.gov.co/Econom-a-y-Finanzas/Tasa-de-Cambio-Representativa-del-Mercado-TRM/32sa-8pi3) |

### ⚙️ How It Works

The TRM, «Tasa de Cambio Representativa del Mercado», is Colombia's official exchange rate of the US dollar. The
Superintendencia Financiera de Colombia (SFC) computes and certifies it, with the Banco de la República's methodology,
from the spot trades of the previous banking day. The provider (`backend/app/services/fx_providers/trm/plugin.py`) reads
it from the open-data portal datos.gov.co.

- **One request for the whole range**: `fetch_rates()` asks the rows whose validity overlaps the range:
  `$where = vigenciahasta >= '<start>T00:00:00' AND vigenciadesde <= '<end>T00:00:00'`, `$order = vigenciadesde`,
  `$limit = 50000` (`PAGE_SIZE`). A full page asks the next one with `$offset`; the dataset holds about 8 400 rows.
- **Fields**: `valor` (a number as text), `unidad` (always `COP`), `vigenciadesde` and `vigenciahasta` (floating
  timestamps, `2026-11-14T00:00:00.000`).
- **Values read as `Decimal`**: no value passes through a float.
- **Start date**: `"min"`, and any start before 1991-12-02, asks from `FIRST_DAY`. COP alone makes no request; any
  currency other than USD gets an empty list.
- **Base currency**: `fetch_rates()` with a `base_currency` other than COP (or None) raises `ValueError`.

### ↔️ Direction and Unit

The TRM is COP per 1 USD. The plugin returns `(d, 'USD', 'COP', COP per 1 USD)`, «1 USD = v COP»: for 14 November 2026,
`(date(2026, 11, 14), 'USD', 'COP', Decimal('3316.7'))`.

### 📅 The Day of a Rate (D2)

**A row is valid over an interval, not on one day.** On 2026-11-19 the dataset held, for example:

| `vigenciadesde` | `vigenciahasta` | `valor` |
|-----------------|-----------------|---------|
| 2026-11-13 | 2026-11-13 | 3301.91 |
| 2026-11-14 | 2026-11-17 | 3316.7 |
| 2026-11-18 | 2026-11-18 | 3309.55 |

The TRM of Saturday 14 to Tuesday 17 November (a weekend and a holiday) was computed from Friday 13's trades. 1 947 of
the 8 389 rows span several days; rows never overlap and leave no gap.

The rule (D2, developer decision, lane 75): **the provider returns one value for every day of the interval** inside the
asked range, because the SFC says the TRM is valid on those days. The 14→17 row gives four rows. So, unlike most
providers, TRM has a value on every calendar day. A day two rows both claimed would be skipped with a warning, never
picked at random (it has not happened).

The TRM valid tomorrow is published today: a day after the asked end is never returned, and the core discards future
days anyway.

### 📦 Request Budget

Measured on 2026-11-19: one request for `"min"` (1.5 s, 12 772 days) and one for 14 days (5.1 s: the anonymous pool
answers at its own pace, slower here for a short range than for the whole dataset). No limit is documented for anonymous requests.

### 🚨 Errors

| Answer | Result |
|--------|--------|
| HTTP 429 | `FXRateLimitedError` (its `Retry-After`, through `raise_if_fx_rate_limited()`) |
| Any other HTTP error, or a network failure | `FXServiceError` («TRM (datos.gov.co) API error: …»), logged as a warning |
| An HTML page, text that is not JSON, or JSON that is not a list (Socrata's error object `{"error": true, …}`) | `FXServiceError` |
| `[]` | An empty list, no error |
| A row whose `valor` is no positive number, whose `unidad` is not COP, or whose dates cannot be read or are reversed (X-R50) | That row is skipped |

### ⚖️ Terms

The dataset is published under Creative Commons Attribution-ShareAlike 4.0, with attribution to the Superintendencia
Financiera de Colombia. LibreFolio stores the values for the instance's owner and redistributes no dataset; the
provider's description names the source and the licence («Source: Superintendencia Financiera de Colombia
(datos.gov.co, CC BY-SA 4.0)») in the four languages.

The note (`warning_i18n`) is at **info** level: the computation on the previous banking day and the values on
non-banking days are facts worth knowing.

### ⚠️ Limitations

- USD only.
- A weekend or holiday value is the one computed on the banking day before.

### 🧪 Tests

`backend/test_scripts/test_services/test_fx_trm.py` pins the direction, one row per day of each validity interval, the
days clipped to the range, the exact query, the paging, the start from 1991, the skipped rows, the overlapping day, the
429 and every answer that is not a JSON list, all with synthetic answers written by hand (no network, no DB, no server).
It is registered among the provider error paths:

```bash
./dev.py test services provider-errors
```

The external test reads the real dataset:

```bash
./dev.py test external fx-providers --providers TRM
```

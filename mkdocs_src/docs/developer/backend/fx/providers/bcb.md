# 🇧🇷 BCB — Banco Central do Brasil

| Property | Value |
|----------|-------|
| **Code** | `BCB` |
| **Base Currency** | USD |
| **API Endpoint** | `https://ptax.bcb.gov.br/ptax_internet/consultaBoletim.do?method=gerarCSVFechamentoMoedaNoPeriodo&ChkMoeda=<id>&DATAINI=dd/mm/yyyy&DATAFIM=dd/mm/yyyy` («feed C») |
| **API Format** | CSV, no header, `;`-separated, decimal comma; one request per currency for any range |
| **API Key** | Not required |
| **Terms** | The PTAX dataset is published under the [Open Data Commons Open Database License (ODbL)](https://dadosabertos.bcb.gov.br/dataset/taxas-de-cambio-todos-os-boletins-diarios); parities other than USD/BRL come from Refinitiv and are not guaranteed by the bank |
| **Currencies** | A fixed table in the plugin (`SERIES`): on 2026-11-16, 152 currencies plus USD and BRL (154). No catalogue request at runtime |
| **Update Frequency** | Daily, Brazilian business days; the closing bulletin comes out around 13:00–13:10 Brasília time |
| **Historical Data** | From 1999-02-01 (`FLOOR`); VES from 2021-10-04 |
| **API Docs** | [PTAX dataset](https://dadosabertos.bcb.gov.br/dataset/taxas-de-cambio-todos-os-boletins-diarios) (the feed C path itself is not documented) |

### ⚙️ How It Works

The Banco Central do Brasil publishes the PTAX bulletin every Brazilian business day: for about 150 currencies, the
parity against the US dollar (*paridade*), and for each the price in reais (*cotação*). The provider
(`backend/app/services/fx_providers/bcb/plugin.py`) reads the closing bulletin through feed C, the CSV of one currency
over a period. USD is the provider's base: every currency is one step from the dollar, and BRL is one of them.

- **One request per currency, in series**: `fetch_rates()` sorts the asked currencies and sends one request for each,
  with the currency's `ChkMoeda` id, `DATAINI` and `DATAFIM`. One answer holds the whole range, the whole history
  included. Between two requests it waits `PAUSE_SECONDS` (1.2 s, D9): a slow, explicit pace. USD alone makes no
  request; an asked currency that is neither in `SERIES` nor BRL is not asked.
- **A fixed table of ids** (`SERIES`, ISO code → `ChkMoeda` id, BCB code, symbol): the `ChkMoeda` ids are internal to
  the bank and cannot be discovered at runtime. The table was built once by a script in the developer journal, from the
  bank's query form, its currency registry and one probe per currency (2026-11-16). Every answer is checked against it
  (see [Format checks](#format-checks-d10)).
- **BRL from the dollar's series**: BRL is read from USD's own series (`USD_SERIES`, `ChkMoeda` 61), as its cotação.
- **Values read as `Decimal`**: `_parse._number()` turns each decimal-comma string into a `Decimal`: no value passes
  through a float. The body is decoded as Latin-1.
- **Start date**: `"min"`, and any start before 1999-02-01, asks from `FLOOR` (1999-02-01); VES asks from its own first
  day, 2021-10-04. A range that ends before a currency's first day makes no request for it.
- **Base currency**: `fetch_rates()` with a `base_currency` other than USD (or None) raises `ValueError`.
- **Reference**: the open-source python-bcb project (MIT) reads the same feed; the lane 75 study in the developer
  journal holds the measurements behind this page.

### ↔️ Direction and Unit

A feed C row is:

```text
ddmmyyyy;<BCB code>;<A|B>;<symbol>;<cotação compra>;<cotação venda>;<paridade compra>;<paridade venda>
```

with the BCB code written without leading zeros (`5` for AFN). The type says how the parity reads:

- **Type A**: the parity is units of the currency per 1 USD → `(d, 'USD', CUR, v)`.
- **Type B** (EUR, GBP, AUD, XDR…): the parity is USD per 1 unit of the currency → `(d, CUR, 'USD', v)`.

The type is read **row by row**, not per currency (NGN was type B until 1998-08-04). The value is the mean of compra and
venda (`_parse.mean()`, the convention of the other providers); a row whose compra or venda is unreadable has no value.
The cotação is used for BRL only: the mean cotação of the USD series, BRL per 1 USD → `(d, 'USD', 'BRL', v)`. For small
units the cotação is rounded, so the other currencies are always read from the parity. Every route through BCB goes
through USD. The FX service normalizes the pair (alphabetical order, inverted when needed); nothing is inverted in the
plugin.

Worked example, the rows of the tests (written by hand in the feed's shape):

| Row | Value | Plugin returns |
|-----|-------|----------------|
| `13112026;630;A;NGN;0,004175;0,004189;1345,0000;1345,6000` | mean parity 1345.3 | `(2026-11-13, 'USD', 'NGN', 1345.3)`: 1 USD = 1345.3 NGN |
| `13112026;978;B;EUR;6,2321;6,2334;1,1028;1,1029` | mean parity 1.10285 | `(2026-11-13, 'EUR', 'USD', 1.10285)`: 1 EUR = 1.10285 USD |
| `13112026;220;A;USD;5,6512;5,6518;1,0000;1,0000` | mean cotação 5.6515 | `(2026-11-13, 'USD', 'BRL', 5.6515)`: 1 USD = 5.6515 BRL |

**Codes the table renames**:

- **XDR**: the IMF's unit is listed as «SDR» by the bank, but feed C already writes `XDR`; the table uses `XDR`.
- **SLL → SLE**: the bank publishes the Sierra Leone leone in old leones (SLL); the ISO list has only SLE. The plugin
  stores it as SLE, the parity divided by `SLL_PER_SLE` (1000) on every date (developer decision, lane 75).
- **VES**: the series is read from 2021-10-04, after the redenomination (÷10⁶) inside the same BCB code; earlier days
  are never asked.

### 📅 The Day of a Rate (D2)

Each row carries one date, the Brazilian business day of the bulletin. Weekends and Brazilian holidays have no row.

The rule (D2, developer decision, lane 75): **every row is returned under its date**. `_parse.read_rows()` ignores a row
dated outside the asked range; a date seen twice in one answer loses that day, with a warning («BCB: NGN has two
bulletins on …: the day is dropped»). Two bulletins a day appear only before 1999, which `FLOOR` never asks. The sync,
not the plugin, drops every day after the sync's end (`_is_date_within_sync_range()` in
`backend/app/services/fx/sync.py`).

**Why 1999-02-01**: before that day feed C holds two bulletins a day (1993–1999), a cotação not in reais (before
1994-07-01) and wrong types (NGN rows of type B with a type A parity in 1998). From 1999-02-01 the checks of the lane 75
study are clean for every currency sampled.

### 💰 Supported Currencies

On 2026-11-16, 152 currencies plus USD and BRL (`SERIES` plus the two):

AED, AFN, ALL, AMD, AOA, ARS, AUD, AWG, AZN, BBD, BDT, BHD, BIF, BMD, BND, BOB, BRL, BSD, BTN, BWP, BYN, BZD, CAD, CDF,
CHF, CLF, CLP, CNY, COP, COU, CRC, CUP, CVE, CZK, DJF, DKK, DOP, DZD, EGP, ERN, ETB, EUR, FJD, FKP, GBP, GEL, GHS, GIP,
GMD, GNF, GTQ, GYD, HKD, HNL, HTG, HUF, IDR, ILS, INR, IQD, IRR, ISK, JMD, JOD, JPY, KES, KGS, KHR, KMF, KRW, KWD, KYD,
KZT, LAK, LBP, LKR, LRD, LSL, LYD, MAD, MDL, MGA, MKD, MMK, MNT, MOP, MRU, MUR, MVR, MWK, MXN, MYR, MZN, NAD, NGN, NIO,
NOK, NPR, NZD, OMR, PAB, PEN, PGK, PHP, PKR, PLN, PYG, QAR, RON, RSD, RUB, RWF, SAR, SBD, SCR, SDG, SEK, SGD, SHP, SLE,
SOS, SRD, SSP, STN, SVC, SYP, SZL, THB, TJS, TMT, TND, TOP, TRY, TTD, TWD, TZS, UAH, UGX, USD, UYU, UZS, VES, VND, VUV,
WST, XAF, XCD, XCG, XDR, XOF, XPF, YER, ZAR, ZMW.

119 of them are not in the ECB provider's list (`FALLBACK_CURRENCIES` in `backend/app/services/fx_providers/ecb/plugin.py`),
among them NGN, KES, GHS, EGP, VND, PKR and DOP.

#### 📋 The catalogue rule

`get_supported_currencies()` makes no request: it returns the keys of `SERIES` plus USD and BRL. Left out of the table
when it was built: **MRO** (the old ouguiya, a stale series; MRU is in), **XAU** (gold, quoted per gram) and
**CNH** (offshore yuan, not an ISO code). A currency the bank adds later needs a new row in `SERIES`.

### 🔍 Format checks (D10) {: #format-checks-d10 }

`backend/app/services/fx_providers/bcb/_parse.py` checks every answer before any value is read. A row must have 8
fields, a `ddmmyyyy` date, the BCB code and symbol of the asked currency, and type `A` or `B`; anything else means the
feed changed, and the whole answer is one `FXServiceError` for that currency. The «no data» answer is an HTML page with
HTTP 200: the text «Não existe informação…» inside a `msgErro` element. `_parse.check_html()` reads it by the range
length (`NO_DATA_IS_AN_ERROR_FROM_DAYS`, 7):

- **Under 7 days**: no bulletin is normal (a weekend, Carnival; the longest gap since 2015 is 5 days): no rate, no
  warning.
- **7 days or more**: an error, «its ChkMoeda id has probably changed». The same page answers an unknown id, and a dead
  id must not look like an empty period.

### 🚨 Errors

The requests are one per currency, so a failure costs one currency only (XRL-H09); a 429 stops the whole call.

| Answer | Result |
|--------|--------|
| HTTP 200 with the «no data» page, range shorter than 7 days | No row, no error: the currency gets an empty list |
| HTTP 200 with the «no data» page, range of 7 days or more | `FXServiceError` («BCB has no bulletin for NGN in N days (…): its ChkMoeda id has probably changed»): that currency is skipped with one warning («BCB fetch failed for NGN, skipping: …»), the others arrive |
| HTTP 200 with any other HTML page | `FXServiceError` («BCB answer for NGN is an HTML page, not the CSV (endpoint changed or request refused)»): that currency is skipped with one warning |
| A row with another field count, an unreadable date or code, another currency's code or symbol, a type other than `A`/`B` | `FXServiceError` («… is not the expected CSV …», «… carries another currency …», «… has an unknown type …»): that currency is skipped with one warning |
| HTTP 429 | `FXRateLimitedError` (`raise_if_fx_rate_limited()`); the call stops and the core pauses the provider ([Paused Providers](../configuration.md#paused-providers)) |
| Any other HTTP error (a 500, a timeout after 60 s) | `FXServiceError` («BCB request failed for NGN: …»): that currency is skipped with one warning |
| One value that is no number, zero or negative (X-R50) | That day only is skipped (debug log); the rest of the currency is kept |
| A date seen twice in one answer | That day is dropped (warning); the other days are kept |
| A row dated outside the asked range | Ignored |

### ⚖️ Terms

- **Licence**: the bank publishes the PTAX dataset («Taxas de câmbio — todos os boletins diários») on its open-data
  portal under the [ODbL](https://dadosabertos.bcb.gov.br/dataset/taxas-de-cambio-todos-os-boletins-diarios). The
  dataset's listed resources are the OData API; feed C is not among them, but it gives the same values. The developer
  decided (lane 75, 2026-11-16) to use feed C under the dataset's ODbL.
- **Attribution**: the provider's description carries it in the four languages, shown in the route picker: «Source:
  Banco Central do Brasil, PTAX, ODbL», with the note that parities other than USD/BRL come from Refinitiv and are not
  guaranteed by the bank. The user page repeats it word for word.
- **robots.txt** (checked 2026-11-16): the feed's host `ptax.bcb.gov.br` has none (a «Page not found» page).
- **Nothing downloaded from the bank is in the repository**: the tests use synthetic answers written by hand.
- **Note in the route picker**: the provider's `warning_i18n` text, at **info** level (`warning_level = "info"`): ℹ️ on
  every route that uses BCB, not ⚠️. The English text:

    > BCB rates are the mean of the buying and selling PTAX closing rates. Their base is the US dollar: every route
    > through BCB goes through USD. The Sierra Leone leone is published in old leones and stored as SLE (divided by
    > 1000).

### 📏 Measured

- **Live check, 2026-11-16**: BRL 5.7321 per USD, EUR 1.1007 USD, NGN 1348.365, SLE 22.7955, XDR 1.3456 USD, VES
  912.87925; first rows NGN and EUR 1999-02-01, VES 2021-10-04, MRU 2018-01-08.
- **Against Banca d'Italia, 2026-11-13** (147 shared currencies, units per 1 USD): median difference 0.10%, 126
  currencies within 0.5%. No difference of an order of magnitude: no unit trap beyond SLL.

### ⚠️ Limitations

- No data at weekends and on Brazilian holidays.
- Parities other than USD/BRL come from Refinitiv and are not guaranteed by the bank.
- Every route through BCB goes through USD.
- The feed C path and the `ChkMoeda` ids are not documented and can change: a changed id shows as the «no data» error
  on a range of 7 days or more, and `SERIES` must then be rebuilt.
- One request per currency: N currencies cost N requests in series, with 1.2 s between two of them. Measured on
  2026-11-16, 30 currencies took 63.6 s with the scheduler's 14-day horizon and 101.5 s with the whole history
  (`"min"`, 197 020 rows).
- **A first full-history sync of many currencies is long**: the sync waits for the provider's whole answer. Its 120 s
  wait on a route's legs (`asyncio.wait_for(..., timeout=120.0)` in `backend/app/services/fx/sync.py`) starts only after
  every provider of the sync has answered (phase 2 gathers the fetches, phase 3 waits on the legs), so it never cuts a
  slow fetch and never switches route because of time (lane 75, L25c). A sync started from the interface waits up to
  120 s for its answer (`FX_SYNC_TIMEOUT_MS`, or a sync window's longer **Timeout**; see [Architecture](../architecture.md)): beyond about 35 BCB currencies
  of full history, the interface stops waiting first. The answer stays in the core's provider cache for 300 s
  (`_fx_fetch_cache`, ttl 300): a second sync within 5 minutes uses it.
- History starts on 1999-02-01 (VES on 2021-10-04); earlier days are never asked.

### 🧪 Tests

`backend/test_scripts/test_services/test_fx_bcb.py` pins the direction (types A and B, BRL from the dollar's cotação,
the type read row by row), SLL stored as SLE ÷ 1000, the SDR read as XDR, one request per currency in series, the start
from 1999-02-01 and VES from 2021-10-04, the rows kept under their day and those outside the range dropped, the
unreadable or zero values, the «no data» page on a short range, every answer that is not the currency's CSV (the «no
data» page on a long range, another HTML page, a wrong field count, code, symbol, type or date, a 500), the 429, the
fixed catalogue and the ODbL attribution in the four descriptions, with synthetic answers written by hand (no network,
no DB, no server). It is registered among the provider error paths:

```bash
./dev.py test services provider-errors
```

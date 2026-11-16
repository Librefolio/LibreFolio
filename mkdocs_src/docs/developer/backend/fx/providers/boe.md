# 🇬🇧 BOE — Bank of England

| Property | Value |
|----------|-------|
| **Code** | `BOE` |
| **Base Currency** | GBP |
| **API Endpoint** | `https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp?csv.x=yes` |
| **API Format** | CSV (`DATE,<series>` then `DD Mon YYYY,value`), one series per request |
| **API Key** | Not required |
| **Licence** | UK Open Government Licence ([Bank of England legal page](https://www.bankofengland.co.uk/legal), «Bank of England Database») |
| **Currencies** | 15 (`CURRENCY_SERIES`) |
| **Update Frequency** | Daily, UK business days |
| **Historical Data** | From 1975 for most currencies (EUR from 1999, CNY and INR from 2005); the database accepts no `Datefrom` before 1963-01-01 |
| **API Docs** | [BOE Statistical Interactive Database](https://www.bankofengland.co.uk/boeapps/database/) |

### ⚙️ How It Works

The Bank of England publishes exchange rates in its Statistical Interactive Database (IADB). Each currency has one
series code, asked with its own request, in parallel.

- **Series codes**: daily spot rates, `XUDL…S`, every one labelled by the Bank «<currency> into Sterling»: foreign
  currency per 1 GBP. A code ending in `D` is against the US dollar (`XUDLERD` is «Euro into US $»): never one of these.
- **Quotation**: returned as published, `(d, 'GBP', CUR, v)`, «1 GBP = v CUR»; the FX service normalizes the pair.
- **Start date**: `"min"` and any earlier `Datefrom` are raised to `FIRST_DAY` (1963-01-01): before it the database
  answers a 302 to `ErrorPage.asp?ei=905`. A range that ends before it makes no request.
- **Response check**: `_check_csv()` requires the first line `DATE,<series>`. An HTML page, an empty answer or the CSV of
  another series raises `FXServiceError` («BOE answer for USD is not the CSV of series XUDLUSS: an HTML page …»): nothing
  is parsed or stored, the currency is skipped and the error is logged once.
- **Too many requests**: an HTTP 429 on any currency's request refuses the whole call. After the parallel fetch, `raise_longest_refusal()` raises the `FXRateLimitedError` with the longest `Retry-After`, and the core pauses the provider ([Paused Providers](../configuration.md#paused-providers)).

### 🗺️ Series Mapping

| Currency | BOE Series | Bank's label | Returned tuple |
|----------|------------|--------------|----------------|
| USD 🇺🇸 | `XUDLUSS` | US $ into Sterling | `(d, GBP, USD, v)` |
| EUR 🇪🇺 | `XUDLERS` | Euro into Sterling | `(d, GBP, EUR, v)` |
| JPY 🇯🇵 | `XUDLJYS` | Japanese Yen into Sterling | `(d, GBP, JPY, v)` |
| CHF 🇨🇭 | `XUDLSFS` | Swiss Franc into Sterling | `(d, GBP, CHF, v)` |
| CAD 🇨🇦 | `XUDLCDS` | Canadian Dollar into Sterling | `(d, GBP, CAD, v)` |
| AUD 🇦🇺 | `XUDLADS` | Australian Dollar into Sterling | `(d, GBP, AUD, v)` |
| NZD 🇳🇿 | `XUDLNDS` | New Zealand Dollar into Sterling | `(d, GBP, NZD, v)` |
| SEK 🇸🇪 | `XUDLSKS` | Swedish Krona into Sterling | `(d, GBP, SEK, v)` |
| NOK 🇳🇴 | `XUDLNKS` | Norwegian Krone into Sterling | `(d, GBP, NOK, v)` |
| DKK 🇩🇰 | `XUDLDKS` | Danish Krone into Sterling | `(d, GBP, DKK, v)` |
| CNY 🇨🇳 | `XUDLBK89` | Chinese Yuan into Sterling | `(d, GBP, CNY, v)` |
| HKD 🇭🇰 | `XUDLHDS` | Hong Kong Dollar into Sterling | `(d, GBP, HKD, v)` |
| SGD 🇸🇬 | `XUDLSGS` | Singapore Dollar into Sterling | `(d, GBP, SGD, v)` |
| ZAR 🇿🇦 | `XUDLZRS` | South African Rand into Sterling | `(d, GBP, ZAR, v)` |
| INR 🇮🇳 | `XUDLBK97` | Indian Rupee into Sterling | `(d, GBP, INR, v)` |

`test_fx_boe_quotes.py` pins every series, its endpoint, `csv.x=yes`, the start date and the response check
against a table written by hand, with synthetic answers only.

### 🔗 The download path and robots.txt

Up to 1.3 the provider asked `/boeapps/database/fromshowcolumns.asp`. Measured on 2026-11-16, that URL answers the HTML
page «Data Series» to every request (the page's own CSV is now a JavaScript button), so BOE downloaded nothing. The same
parameters with `csv.x=yes` on `/boeapps/database/_iadb-fromshowcolumns.asp` answer `application/csv`; without
`csv.x=yes` that path answers HTML too.

The site's `robots.txt` lists `Disallow: /boeapps/database/_iadb-FromShowColumns.asp` (present since 2024 at least,
absent in 2020). **Decision of the developer (lane 75, 2026-11-16):** robots.txt addresses search-engine crawlers, not
a user's own fetch of an OGL-licensed dataset, so the provider uses this path. No anti-bot measure is involved or
evaded: plain requests, an honest User-Agent, no headless browser, no IP rotation. The path is not documented and may
change again; the response check turns that into a clear error instead of wrong data.

!!! warning "Before 1.4, EUR came from the wrong series"

    Up to 1.3, EUR read `XUDLERD` («Euro into US $», EUR per 1 USD) and stored it as GBP/EUR. Rates stored from BOE for
    EUR are wrong until the user syncs them again: a sync upserts on `(date, base, quote)` and overwrites them.

### ⚠️ Limitations

- One request per currency, sent in parallel (`asyncio.gather`).
- No data on UK bank holidays and weekends.
- Some currencies have limited historical coverage (see the table above).
- The download path is undocumented (see above).

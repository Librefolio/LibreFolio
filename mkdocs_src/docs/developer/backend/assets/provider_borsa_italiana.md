# 🇮🇹 Borsa Italiana Provider (`borsa_italiana`)

The Borsa Italiana provider fetches financial data from [borsaitaliana.it](https://www.borsaitaliana.it/) using the [`borsa-italiana-scraping`](https://github.com/Librefolio/borsaItaliana-scraping) library. It supports stocks, bonds (including BTP), ETFs listed on Borsa Italiana markets (MTA, MOT, ETFPlus), and funds/SICAVs exposed on Borsa fund-detail pages.

---

## ⚙️ How it Works

1. **Identifier**: An ISIN code (e.g., `IT0003128367` for ENEL S.p.A.) for listed instruments.
2. **Identifier Types**: `ISIN` for listed instruments. Mutual funds are priced by a Borsa **internal code** carried in `provider_params.codice_fondo` (see [Mutual funds](#mutual-funds-nav-by-internal-code) below); the asset identifier is still the real ISIN when the fund page exposes one, otherwise an `OTHER` identifier is used.
3. **`provider_params`**:
    - `language` — optional (`"en"` or `"it"`, default `"en"`). Controls the language of asset names, metadata descriptions, and the provider URL.
    - `codice_fondo` — optional Borsa internal fund code (e.g. `2FADB602822`). When present, current/historical value use the **fund NAV path** instead of the market API.

### 💱 Currency

All data is returned in **EUR** — Borsa Italiana is an Italian exchange.

### 💰 Current Value (`get_current_value`)

- **Funds** (when `provider_params.codice_fondo` is set): returns the fund NAV **only if the published NAV is dated today**. A fund NAV is published once per day with a lag, so exposing a stale NAV as the "current" value would misstate the portfolio. When the NAV date ≠ today, the provider raises `NO_DATA` and the core falls back to the **last recorded buy price** as the unit-value estimate.
- **Listed instruments**: uses `ottieni_prezzo_corrente(isin)` from the scraping library.
- Returns `FACurrentValue` with price, date, currency, and source (`"Borsa Italiana"`).

### 📈 Historical Data (`get_history_value`)

- **Funds** (when `provider_params.codice_fondo` is set): the fund page exposes only the **latest NAV** (no series), dated to the day it actually refers to (never today). The provider returns a **single price point** at that real NAV date; the core backward-fills the gaps up to the requested range. Out-of-range NAV dates yield no points.
- **Listed instruments**: uses `ottieni_storico(isin, periodo)` from the `grafici.borsaitaliana.it` JSON API.
    - Returns full **OHLCV data** (open, high, low, close, volume) for each trading day.
    - **Period selection**: The API uses fixed windows (`1M`, `3M`, `6M`, `1Y`, `3Y`, `5Y`, `MAX`). The provider automatically selects the smallest period that covers the requested `start_date..end_date` range.
    - Results are filtered in-memory to the exact requested date range.
    - The core handles gap filling (weekends, holidays) — the plugin returns only actual trading days.

### 🧾 Mutual funds (NAV by internal code)

Mutual funds / SICAVs are **not** on the XMIL market API, so `ottieni_storico` / `ottieni_prezzo_corrente` cannot price them. Their only public NAV source is the fund detail page `/borsa/fondi/dettaglio/{code}.html`, addressed by a Borsa **internal code** (`2FADB…`) that is **not** the ISIN. The scraping library exposes:

- `ottieni_dati_fondo(codice, sessione)` — fetch NAV, currency, NAV date (dd/mm/yy), name, and the real **ISIN extracted from the page** (`DatiFondo`). `DatiFondo` also carries the descriptive sections scraped from the page — `caratteristiche`, `societa_gestione`, `costi` (each a `label → value` dict, `N.D.` placeholders dropped) — consumed by `fetch_asset_metadata` to enrich the fund description.
- `ottieni_dati_fondo_da_url(url, sessione)` / `estrai_codice_da_url(url)` — the URL variant used by `resolve_url`.

The provider captures the internal code into `provider_params.codice_fondo` at asset creation (from search or `resolve_url`); pricing afterwards uses that stored code with **no external search**. Price fetches never hit any web search — that invariant is what keeps automated syncs deterministic.

### 🔎 Search (`search`)

- Uses `cerca(query)` — the internal JSON search engine of borsaitaliana.it.
- Searches across all instrument types: stocks, bonds, ETFs, ETC/ETN, and funds.
- Fund names are indexed with Borsa abbreviations (for example `Obbligaz.` instead of `Obbligazionaria`), so the provider retries common full-word variants with abbreviated terms.
- **Funds**: `cerca` returns the Borsa **internal code** in the `isin` field (not a real ISIN). The provider fetches each fund page **once per code** (in-search cache) via `ottieni_dati_fondo` to recover the real ISIN, sets it as the `identifier` (`ISIN`), and carries the internal code in `provider_params.codice_fondo`. If the page can't be fetched or no ISIN is present, it falls back to the code as an `OTHER` identifier — still priceable by NAV.
- **Dual-language results**: emits two entries per instrument (🇮🇹 Italiano + 🇬🇧 English) with flag emojis in `display_name`. Each result carries `provider_params: {language: "en"|"it"}` so the user's selection is propagated on assignment.
- **Result ordering**: results are **grouped by the cerca-level identifier** (the internal code for funds, the real ISIN otherwise), preserving first-seen order, and within each group **Italian is emitted before English**. This keeps sibling funds — whose internal codes may differ by a single letter — from interleaving across languages. Grouping also de-duplicates per `(identifier, language)`.
- **Last-resort external fallback**: when `cerca` returns nothing, the search orchestration calls the LibreFolio [`web_link_finder`](search_link_finder.md) stack to turn the query into a candidate Borsa page URL, then `resolve_url`s it. The caller can pass **`hints`** (report-extracted ISIN + names) which drive a two-stage "stringone" query and an **identifier post-filter** that narrows the resolved siblings to the exact ISIN when it is known — all handled centrally, see [Asset Search & Link-Finder](search_link_finder.md). Best-effort, interactive-only, never on price fetches.

### 📋 Metadata (`fetch_asset_metadata`)

- **Listed instruments (ISIN path)**: uses `ottieni_scheda(isin, lingua)` — scrapes the instrument detail page in the configured language.
- Extracts:
    - **Name**: from `<h1>` tag on the page, appended with language flag emoji (e.g., `"ENEL S.p.A. 🇬🇧"`).
    - **Type**: mapped from instrument type field (e.g., `obbligazione` → BOND, `azione` → STOCK, `etf` → ETF).
    - **Currency**: negotiation currency (default EUR).
    - **Description**: assembled from page description, market, issuer, maturity date, coupon rate, structure, tipology, coupon frequency.
    - **Ticker**: if available on the page (mainly for stocks).
    - **Geographic Area**: inferred from issuer name (e.g., "Republic of Italy" → `ITA`).
    - **Sector**: inferred from `settore` (stocks) or `tipologia` (bonds) fields.
- Bond-specific fields available in the raw data: `cedola_annua`, `scadenza`, `emittente`, `rendimento_lordo`, `struttura_bond`, `frequenza_cedola`.
- **Funds** (when `provider_params.codice_fondo` is set): funds are not on the XMIL scheda, so metadata is built from the **fund detail page** by internal code instead. The `short_description` is assembled from the fund **name**, the real **ISIN**, and the non-`N.D.` entries scraped from the page's **Caratteristiche**, **Società di Gestione** and **Costi** sections (e.g. `… | ISIN: LU2178929613 | Classe: P | Grado di Rischio: 3 | Categoria Assogestioni: Bilanciati | Costi — Gestione: 1.3 …`). The internal code is persisted in `identifier_other` as a JSON-list entry (`["2FADB…"]`). The section fields are read defensively, so metadata degrades to just *name + ISIN* if the installed scraping library predates the enriched `DatiFondo`.

### 🔗 `get_asset_url`

For listed instruments, returns `https://www.borsaitaliana.it/borsa/search/scheda.html?code={ISIN}&lang={language}`. For funds with `provider_params.codice_fondo`, returns `/borsa/fondi/dettaglio/{codice_fondo}.html?lang={language}` so the link targets the NAV page keyed by the internal fund code. The `lang` parameter follows the user's `provider_params.language` selection (default `en`).

### 🔁 `resolve_url` (inverse of `get_asset_url`)

The provider opts into the generic **URL → search-item** capability:

- `resolvable_url_domains = ["borsaitaliana.it"]` → `supports_url_resolution` is `True`.
- `resolve_url(url)` recognises two public page families:
    - **Fund detail pages** (`/borsa/fondi/dettaglio/{code}.html`) — fetches the page and returns the **full canonical set a normal search would emit** for that fund: the **IT + EN pair** (Italian first, with flag in `display_name`), each `{identifier: <ISIN from page> or code, identifier_type, display_name, currency, type: "FUND", provider_params: {codice_fondo, language}}`.
    - **Stock / bond / ETF scheda pages** (`…/scheda/{ISIN}[-{MIC}].html`) — returns the same IT + EN canonical set, priced by ISIN.

It is only a different **entry point** — the orchestration flattens the list and de-dupes by `(identifier, language)`. Anything that is not a recognisable Borsa page (off-domain, no extractable fund code or ISIN path) returns `None`. Best-effort: fetch/parse errors return `None`, never raise.

This lets an externally discovered page URL (e.g. found via `web_link_finder`, or pasted by the user in a future UI) be turned into a ready-to-create asset with the correct pricing params.

### 🌐 `web_link_finder` (last-resort external search)

!!! info "Central reference"

    The link-finder is **generic**. This section keeps only the Borsa-Italiana-relevant summary —
    the full contract (three layers, `hints`, identifier filter, config, invariants) lives on
    [Asset Search & Link-Finder](search_link_finder.md), which is the source of truth.

`backend/app/services/web_link_finder.py` is a **LibreFolio-level** module (deliberately *not* inside the scraping library, so the choice of external engine stays a LibreFolio concern). It turns a free-text query/ISIN into candidate **provider-domain** URLs, used **only at search time** as a last resort when a provider's on-site search yields nothing.

- **Best-effort**: any failure (rate-limit, anomaly page, network/parse error) yields `[]` and is never fatal — the search always completes and emits `done`.
- **Async-safe**: sync I/O runs in `asyncio.to_thread`; short timeout, small TTL cache, domain-filtered hits, structured logs.
- **Pluggable engine**: default `DdgsEngine` wraps the [`ddgs`](https://pypi.org/project/ddgs/) metasearch library (bing/brave/google/DuckDuckGo/… aggregated via `backend="auto"`) with an `ApiKeyEngine` seam for a paid API (Brave/Bing/SerpAPI) later; `searxng` reserved for a deferred Fase B.
- **Config** (all optional env vars): `LIBREFOLIO_WEB_LINK_FINDER_ENABLED` (`1`/`0`, default `1`), `_ENGINE` (`ddgs`|`apikey`), `_API_KEY`, `_DDGS_REGION` (default `wt-wt`), `_DDGS_BACKEND` (default `auto`), `_TIMEOUT` (s), `_MAX`.

!!! warning "Invariant"

    External search is only ever hit during **interactive asset search**. Price fetches (frequent, automated) must **never** call `web_link_finder` — once an asset exists it is priced by its stored `provider_params` (a fund's `codice_fondo`), not by search.

---

## 🔌 Technical Details

### HTTP Session

The provider maintains a **shared `Sessione` instance** across all calls:

- **WAF handling**: The library manages Imperva WAF cookies automatically.
- **JWT token**: Extracted from the interactive chart page (required for the `grafici.borsaitaliana.it` API).
- **Rate limiting**: Built-in minimum pause between requests (0.5s default).
- **Shutdown**: The session is closed via `shutdown()` at app teardown.

### `params_schema` (Dynamic UI Form)

The provider exposes optional parameters via `params_schema`:

| Key | Type | Options | Default | Description |
|-----|------|---------|---------|-------------|
| `language` | `select` | `en` (🇬🇧 English), `it` (🇮🇹 Italiano) | `en` | Language for names and metadata |
| `codice_fondo` | `text` | — | — | Borsa internal fund code (e.g. `2FADB602822`); when set, current/history use the fund NAV path |

Uses `option_labels` for human-readable display in the frontend dropdown.

### Error Handling

| Library Exception | Mapped Error Code | Meaning |
|---|---|---|
| `StrumentoNonTrovato` | `NOT_FOUND` | ISIN not recognized |
| `DatiNonDisponibili` | `NO_DATA` | No data available (market closed, delisted) |
| `RicercaNonDisponibile` | `FETCH_ERROR` | Search endpoint down |
| `BorsaItalianaErrore` | `FETCH_ERROR` | Generic library error |

### Dependencies

```
borsa-italiana-scraping @ git+https://github.com/Librefolio/borsaItaliana-scraping.git
```

Transitive: `httpx`, `beautifulsoup4`, `lxml`.

---

## 🧪 Test Cases

| Identifier | `provider_params` | Description |
|---|---|---|
| `IT0003128367` | — | ENEL S.p.A. (stock) |
| `LU2178929613` | `{codice_fondo: "2FADB602822"}` | Eurizon Next 2.0 Alloc. Divers. 40 P (fund, NAV by code) |

Search test query: `"ENEL"` (listed) / `"EURIZON NEXT 2.0 DIVERSIFICATO 40 P"` (fund by report name).
`resolve_url` test: `https://www.borsaitaliana.it/borsa/fondi/dettaglio/2FADB602822.html` → IT + EN fund search-items with ISIN `LU2178929613` + `codice_fondo`.

---

## 🔗 Related Documentation

- 🏗️ [Asset Architecture](architecture.md) — Sync pipeline and caching
- 🔎 [Asset Search & Link-Finder](search_link_finder.md) — The generic search stack this provider implements
- 🔌 [Asset Providers Overview](system_providers.md) — All providers comparison
- 📈 [Asset Plugin Guide](../../architecture/patterns/asset_plugin_guide.md) — How to create a new provider

# 🇮🇹 Borsa Italiana Provider (`borsa_italiana`)

The Borsa Italiana provider fetches financial data from [borsaitaliana.it](https://www.borsaitaliana.it/) using the [`borsa-italiana-scraping`](https://github.com/Librefolio/borsaItaliana-scraping) library. It supports stocks, bonds (including BTP), and ETFs listed on Borsa Italiana markets (MTA, MOT, ETFPlus).

---

## ⚙️ How it Works

1. **Identifier**: An ISIN code (e.g., `IT0003128367` for ENEL S.p.A.).
2. **Identifier Types**: Only `ISIN` is accepted.
3. **`provider_params`**: Optional `language` field (`"en"` or `"it"`, default `"en"`). Controls the language of asset names, metadata descriptions, and the provider URL.

### 💱 Currency

All data is returned in **EUR** — Borsa Italiana is an Italian exchange.

### 💰 Current Value (`get_current_value`)

- Uses `ottieni_prezzo_corrente(isin)` from the scraping library.
- **Strategy** (fastest first):
    1. Fetches the latest point from the historical API (1M period).
    2. Falls back to scraping the instrument page (`ottieni_scheda`).
- Returns `PrezzoCorrente` with price, date, currency, and source (`"api"` or `"scraping"`).

### 📈 Historical Data (`get_history_value`)

- Uses `ottieni_storico(isin, periodo)` from the `grafici.borsaitaliana.it` JSON API.
- Returns full **OHLCV data** (open, high, low, close, volume) for each trading day.
- **Period selection**: The API uses fixed windows (`1M`, `3M`, `6M`, `1Y`, `3Y`, `5Y`, `MAX`). The provider automatically selects the smallest period that covers the requested `start_date..end_date` range.
- Results are filtered in-memory to the exact requested date range.
- The core handles gap filling (weekends, holidays) — the plugin returns only actual trading days.

### 🔎 Search (`search`)

- Uses `cerca(query)` — the internal JSON search engine of borsaitaliana.it.
- Searches across all instrument types: stocks, bonds, ETFs, ETC/ETN.
- **Dual-language results**: emits two entries per ISIN (🇬🇧 English + 🇮🇹 Italiano) with flag emojis in `display_name`. Each result carries `provider_params: {language: "en"|"it"}` so the user's selection is propagated on assignment.
- Results are deduplicated by `(ISIN, language)` pair.

### 📋 Metadata (`fetch_asset_metadata`)

- Uses `ottieni_scheda(isin, lingua)` — scrapes the instrument detail page in the configured language.
- Extracts:
    - **Name**: from `<h1>` tag on the page, appended with language flag emoji (e.g., `"ENEL S.p.A. 🇬🇧"`).
    - **Type**: mapped from instrument type field (e.g., `obbligazione` → BOND, `azione` → STOCK, `etf` → ETF).
    - **Currency**: negotiation currency (default EUR).
    - **Description**: assembled from page description, market, issuer, maturity date, coupon rate, structure, tipology, coupon frequency.
    - **Ticker**: if available on the page (mainly for stocks).
    - **Geographic Area**: inferred from issuer name (e.g., "Republic of Italy" → `ITA`).
    - **Sector**: inferred from `settore` (stocks) or `tipologia` (bonds) fields.
- Bond-specific fields available in the raw data: `cedola_annua`, `scadenza`, `emittente`, `rendimento_lordo`, `struttura_bond`, `frequenza_cedola`.

### 🔗 `get_asset_url`

Returns `https://www.borsaitaliana.it/borsa/search/scheda.html?code={ISIN}&lang={language}` — the `lang` parameter follows the user's `provider_params.language` selection (default `en`).

---

## 🔌 Technical Details

### HTTP Session

The provider maintains a **shared `Sessione` instance** across all calls:

- **WAF handling**: The library manages Imperva WAF cookies automatically.
- **JWT token**: Extracted from the interactive chart page (required for the `grafici.borsaitaliana.it` API).
- **Rate limiting**: Built-in minimum pause between requests (0.5s default).
- **Shutdown**: The session is closed via `shutdown()` at app teardown.

### `params_schema` (Dynamic UI Form)

The provider exposes one optional parameter via `params_schema`:

| Key | Type | Options | Default | Description |
|-----|------|---------|---------|-------------|
| `language` | `select` | `en` (🇬🇧 English), `it` (🇮🇹 Italiano) | `en` | Language for names and metadata |

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

| Identifier | Type | Description |
|---|---|---|
| `IT0003128367` | ISIN | ENEL S.p.A. (stock) |

Search test query: `"ENEL"`.

---

## 🔗 Related Documentation

- 🏗️ [Asset Architecture](architecture.md) — Sync pipeline and caching
- 🔌 [Asset Providers Overview](system_providers.md) — All providers comparison
- 📈 [Asset Plugin Guide](../../architecture/patterns/asset_plugin_guide.md) — How to create a new provider

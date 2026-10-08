# 🔍 JustETF Provider (`justetf`)

The JustETF provider fetches ETF prices and metadata from [justetf.com](https://www.justetf.com/) using the [`justetf-scraping`](https://github.com/Alfystar/justetf-scraping) library. It provides comprehensive ETF data including sector and geographic distributions.

📖 **User Guide**: [JustETF — User Manual](../../../user/assets/providers/justetf.md)

---

## ⚙️ How it Works

1. **Identifier**: An ISIN code (e.g., `IE00B4L5Y983` for iShares Core MSCI World).
2. **Identifier Types**: Only `ISIN` is accepted.
3. **`provider_params`**: `{"currency": "EUR"|"USD"|"CHF"|"GBP"}` (default: EUR).

### 💱 Currency Architecture

The provider supports 4 currencies via JustETF's chart API (`load_chart(isin, currency)`). JustETF performs server-side FX conversion.

| Currency | Current Value | History | Notes |
|----------|:---:|:---:|---|
| EUR | ✅ | ✅ | gettex live quote, falling back to the daily `latestQuote`; chart |
| USD | ✅ | ✅ | Daily `latestQuote` only + chart (converted by JustETF) |
| CHF | ✅ | ✅ | Daily `latestQuote` only + chart (converted by JustETF) |
| GBP | ✅ | ✅ | Daily `latestQuote` only + chart (converted by JustETF) |

**Key distinction**: `fundCurrency` (from overview API) = NAV denomination ≠ trading currency. A USD-denominated fund (e.g., MSCI World) trades in EUR on European exchanges.

### 💰 Current Value (`get_current_value`)

1. **EUR — live gettex quote.** `_ensure_live_feed(isin)` starts (or reuses) the persistent feed, then the quote is read from `_live_quote_store`, else fetched once with `load_live_quote(isin)`. The market-maker `mid` is preferred over `last`, which stays stuck at the opening-auction level all day on thinly traded ETFs. The date comes from the quote timestamp.
2. **Any currency — daily fallback.** When no live price is found (and always for USD/CHF/GBP), `load_raw_chart(isin, currency)["latestQuote"]["raw"]`, dated `latestQuoteDate`. This is how USD, CHF and GBP get a current value.
3. Neither available → `NOT_FOUND`; any other exception → `FETCH_ERROR`.

### 📈 Historical Data (`get_history_value`)

- Uses `load_chart(isin, currency, add_current)` from justetf-scraping.
- `currency` read from `provider_params` (default EUR).
- `add_current=True` only if `end_date >= today` AND `currency == "EUR"` — gettex quotes are EUR-only.
- Returns `close` prices. Only today's EUR point (with `add_current`) is enriched with intraday open/high/low from `load_intraday_ohlc(isin)`, when the installed library provides it.
- Date range filtering is done in-memory after fetching the full chart.
- Cache key includes currency: `chart_{isin}_{currency}_{add_current}`.

### 🔎 Search (`search`)

- Searches against a **cached ETF list** (`load_overview()` DataFrame).
- Search is performed in-memory across: `name`, `ticker`, `wkn`, and ISIN (index).
- Case-insensitive string matching using pandas vectorized operations.
- **Multi-currency**: emits 4 results per ETF match (EUR/USD/CHF/GBP) with flag emojis.
- Fund's native currency marked with 👑 (e.g., `"🇺🇸👑 iShares Core MSCI World"` for a USD-denominated fund).
- All results have `identifier_type: ISIN` and `type: "ETF"`.

### 📋 Metadata (`fetch_asset_metadata`)

- Uses `get_etf_overview(isin, include_gettex=False)` for detailed profile data.
- Extracts:
    - **Description**: `description + TER + distribution_policy`
    - **Geographic Area**: `countries[]` → normalized to ISO 3166-1 alpha-3 codes via `normalize_country_to_iso3()`, renormalized to sum to 1.0
    - **Sector Area**: `sectors[]` → validated against `FinancialSector` enum, unknown sectors logged and mapped to "Other"
    - **Currency**: from `provider_params["currency"]` (user's chosen price currency)
    - **Identifiers**: `identifier_isin` (input ISIN), `identifier_ticker` (if available)
- `asset_type` is always `ETF`.

### 🔗 `get_asset_url`

Returns `https://www.justetf.com/en/etf-profile.html?isin={identifier}`.

### 📡 Live Quote Streaming

The JustETF provider maintains persistent **WebSocket connections** to the Gettex exchange for real-time price feeds:

- **`iterate_live_quote(isin)`** opens a WebSocket stream and yields price updates as they arrive.
- A background **daemon thread** per ISIN keeps the connection alive, reconnecting with exponential backoff (1 s, doubling, capped at 60 s).
- Prices are stored in a module-level `_live_quote_store` dictionary.
- **`get_current_value()`** (EUR only): ensures the persistent feed first (`_ensure_live_feed`), then reads `_live_quote_store`, falling back to a one-shot `load_live_quote()`.
- **`shutdown_live_feeds()`** stops all daemon threads (called from the provider's `shutdown()` method at app teardown).

### 📅 Asset Events

During sync, the provider parses dividend data from `load_chart()` and generates **DIVIDEND events** via the standard event pipeline.

---

## ⚡ Caching Strategy

| Cache | Key | TTL | Max Size | Purpose |
|---|---|---|---|---|
| **ETF list** | `"etf_list"` | 1 hour | 100 | Avoid reloading the full overview DataFrame for each search |
| **Chart data** | `chart_{isin}_{currency}_{add_current}` | 1 hour | 500 | Cache historical chart per ISIN and currency |
| **Overview** | `overview_{isin}` | 1 hour | 500 | Cache ETF profile/metadata per ISIN |

All caches are global (module-level) TTL caches via `get_ttl_cache()`. They are populated lazily and cleared on server restart. Live gettex quotes are not TTL-cached: they sit in `_live_quote_store`, refreshed by the feed threads.

!!! info "Pre-warm"

    The ETF list cache is warmed at startup via `_prewarm_provider_caches()` in `main.py`. This makes the first search instant rather than waiting ~2-3 seconds for `load_overview()`.

---

## 🧪 Test Configuration

| Property | Value |
|---|---|
| `test_cases` | `[{identifier: "IE00B4L5Y983", identifier_type: ISIN}]` |
| `test_search_query` | `"iShares Core S&P 500"` |

---

## ⚠️ Limitations

- **ISIN only**: Does not accept tickers — use Yahoo Finance for ticker-based search.
- **Live price in EUR only**: the gettex feed is EUR; USD/CHF/GBP current values are the daily `latestQuote`, converted by justETF.
- **Scraping fragility**: The library scrapes justetf.com HTML. Site layout changes may break it.
- **Blocking I/O**: All justetf-scraping calls are synchronous — wrapped in `asyncio.to_thread()` to avoid blocking the event loop.

---

## 📦 Dependency

- **Library**: [`justetf-scraping`](https://github.com/Alfystar/justetf-scraping) — installed from the local subrepo or PyPI.
- **Optional import**: If not installed, the provider raises `AssetSourceError("NOT_AVAILABLE")` on every call.
- **Transitive**: `pandas`, `requests`, `beautifulsoup4`.

---

## 🔗 Related Documentation

- 📖 [JustETF — User Guide](../../../user/assets/providers/justetf.md) — End-user configuration guide
- 📦 [Providers Overview](system_providers.md) — All available providers
- 💰 [Asset Architecture](architecture.md) — Sync pipeline and price queries
- 📈 [Asset Plugin Guide](../../architecture/patterns/asset_plugin_guide.md) — How to create a new provider



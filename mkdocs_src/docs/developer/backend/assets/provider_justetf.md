# 🔍 JustETF Provider (`justetf`)

The JustETF provider fetches ETF prices and metadata from [justetf.com](https://www.justetf.com/) using the [`justetf-scraping`](https://github.com/Alfystar/justetf-scraping) library. It provides comprehensive ETF data including sector and geographic distributions.

📖 **User Guide**: [JustETF — User Manual](../../../user/assets/providers/justetf.en.md)

---

## ⚙️ How it Works

1. **Identifier**: An ISIN code (e.g., `IE00B4L5Y983` for iShares Core MSCI World).
2. **Identifier Types**: Only `ISIN` is accepted.
3. **No `provider_params`**: JustETF does not require any additional configuration.

### 💰 Current Value (`get_current_value`)

- Uses `get_gettex_quote(isin)` to fetch real-time data from the Gettex exchange WebSocket.
- Extracts `last` price (or `mid` as fallback).
- Currency defaults to `EUR` (Gettex is a European exchange).
- Timestamp is parsed from the WebSocket response.

### 📈 Historical Data (`get_history_value`)

- Uses `load_chart(isin, "EUR", add_current)` from justetf-scraping.
- `add_current=True` if `end_date >= today` — appends today's gettex quote to the chart.
- Returns `close` prices only (no OHLV data).
- Date range filtering is done in-memory after fetching the full chart.

### 🔎 Search (`search`)

- Searches against a **cached ETF list** (`load_overview()` DataFrame).
- Search is performed in-memory across: `name`, `ticker`, `wkn`, and ISIN (index).
- Case-insensitive string matching using pandas vectorized operations.
- All results have `identifier_type: ISIN` and `type: "ETF"`.

### 📋 Metadata (`fetch_asset_metadata`)

- Uses `get_etf_overview(isin, include_gettex=False)` for detailed profile data.
- Extracts:
    - **Description**: `description + TER + distribution_policy`
    - **Geographic Area**: `countries[]` → normalized to ISO 3166-1 alpha-3 codes via `normalize_country_to_iso3()`, renormalized to sum to 1.0
    - **Sector Area**: `sectors[]` → validated against `FinancialSector` enum, unknown sectors logged and mapped to "Other"
    - **Currency**: `fund_currency`
    - **Identifiers**: `identifier_isin` (input ISIN), `identifier_ticker` (if available)
- `asset_type` is always `ETF`.

### 🔗 `get_asset_url`

Returns `https://www.justetf.com/en/etf-profile.html?isin={identifier}`.

### 📡 Live Quote Streaming

The JustETF provider maintains persistent **WebSocket connections** to the Gettex exchange for real-time price feeds:

- **`iterate_live_quote(isin)`** opens a WebSocket stream and yields price updates as they arrive.
- A background **daemon thread** per ISIN keeps the connection alive with exponential backoff on disconnection.
- Prices are stored in a module-level `_live_quote_store` dictionary.
- **`get_current_value()`** fast-path: checks `_live_quote_store` first, falls back to a one-shot `get_gettex_quote()`, then optionally starts a persistent feed.
- **`shutdown_live_feeds()`** stops all daemon threads (called from the provider's `shutdown()` method at app teardown).

### 📅 Asset Events

During sync, the provider parses dividend data from `load_chart()` and generates **DIVIDEND events** via the standard event pipeline.

---

## ⚡ Caching Strategy

| Cache | Key | TTL | Max Size | Purpose |
|---|---|---|---|---|
| **ETF list** | `"etf_list"` | 1 hour | 100 | Avoid reloading the full overview DataFrame for each search |
| **Chart data** | `chart_{isin}_{add_current}` | 1 hour | 500 | Cache historical chart per ISIN |
| **Gettex quote** | `gettex_{isin}` | 30 sec | 200 | Short-lived cache for real-time quotes |
| **Overview** | `overview_{isin}` | 1 hour | 500 | Cache ETF profile/metadata per ISIN |

All caches are global (module-level) TTL caches via `get_ttl_cache()`. They are populated lazily and cleared on server restart.

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
- **EUR-centric**: Chart data is always in EUR. Multi-currency support depends on justetf.com availability.
- **Scraping fragility**: The library scrapes justetf.com HTML. Site layout changes may break it.
- **Blocking I/O**: All justetf-scraping calls are synchronous — wrapped in `asyncio.to_thread()` to avoid blocking the event loop.

---

## 📦 Dependency

- **Library**: [`justetf-scraping`](https://github.com/Alfystar/justetf-scraping) — installed from the local subrepo or PyPI.
- **Optional import**: If not installed, the provider raises `AssetSourceError("NOT_AVAILABLE")` on every call.
- **Transitive**: `pandas`, `requests`, `beautifulsoup4`.

---

## 🔗 Related Documentation

- 📖 [JustETF — User Guide](../../../user/assets/providers/justetf.en.md) — End-user configuration guide
- 📦 [Providers Overview](system_providers.md) — All available providers
- 💰 [Asset Architecture](architecture.md) — Sync pipeline and price queries
- 📈 [Asset Plugin Guide](../../architecture/patterns/asset_plugin_guide.md) — How to create a new provider



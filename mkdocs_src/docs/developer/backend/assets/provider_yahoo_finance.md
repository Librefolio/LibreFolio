# 📈 Yahoo Finance Provider (`yfinance`)

The Yahoo Finance provider fetches stock, ETF, crypto, and index prices using the [yfinance](https://github.com/ranaroussi/yfinance) library. It is the primary market data provider for LibreFolio.

📖 **User Guide**: [Yahoo Finance — User Manual](../../../user/assets/providers/yahoo-finance.md)

---

## ⚙️ How it Works

1. **Identifier**: A Yahoo Finance ticker symbol (e.g., `AAPL`, `BTC-USD`, `IE00B4L5Y983`).
2. **Identifier Types**: `TICKER` and `ISIN` are both accepted. ISIN is resolved by yfinance internally.
3. **No `provider_params`**: Yahoo Finance does not require any additional configuration.

### 💰 Current Value (`get_current_value`)

1. **Cache check** (120s TTL) — if a cached result exists, returns immediately (no HTTP call).
2. Calls `ticker.info` — the Yahoo `quoteSummary` endpoint. Returns `regularMarketPrice`, `currency`, and `regularMarketTime` in a **single lightweight call**.
3. Fallback price: `currentPrice` → `previousClose` (if `regularMarketPrice` is null).
4. **No `history()` call at all** — current value polling never touches the chart API.

!!! warning "Avoid `history()` and `fast_info` for current price"
    - `ticker.history()` calls the chart API and logs noisy `Entering history()` lines.
    - `ticker.fast_info` internally triggers **2 heavy HTTP calls** (`range=1y` + `range=5d`).
    - `ticker.info` uses the `quoteSummary` endpoint — lighter, returns price + currency together.

!!! tip "Cache TTL vs Polling Interval"
    Frontend polls every **30s** for responsive UI, but the backend cache has a **120s TTL**. This means 3 out of 4 polls return instantly from cache; Yahoo Finance is called at most once per ticker every **2 minutes**.

### 📈 Historical Data (`get_history_value`)

- Calls `ticker.history(start=..., end=...)` — returns OHLCV data for trading days only.
- End date is shifted by +1 day (yfinance end is exclusive).
- Timezone handling: `DatetimeIndex` is converted to UTC before extracting `.date()`.
- Returns only **actual trading days** — the core layer fills weekends/holidays.

### 🔎 Search (`search`)

- Uses `yfinance.Search(query)` for real-time ticker search.
- Minimum query length: **2 characters**.
- Results limited to **top 20** quotes.
- `quoteType` is normalized to LibreFolio asset types: `equity → STOCK`, `etf → ETF`, `mutualfund → FUND`, `cryptocurrency → CRYPTO`, etc.
- Currency is fetched per-symbol via `_fetch_currency()` (cached separately, 24-hour TTL).

### 📋 Metadata (`fetch_asset_metadata`)

- Fetches full `ticker.info` from Yahoo Finance.
- Extracts: `asset_type`, `currency`, `short_description` (from `longBusinessSummary`), `sector` (single-sector distribution), `identifier_ticker`, `identifier_isin`.
- ISIN is obtained via `ticker.isin` (not available for all markets).
- Unknown sectors are logged as warnings and mapped to "Other".

### 🔗 `get_asset_url`

Returns `https://finance.yahoo.com/quote/{identifier}`.

### 📅 Asset Events

During sync, the provider generates:

- **`DIVIDEND` events** from `ticker.dividends` — ex-dividend date + per-share amount.
- **`SPLIT` events** from `ticker.splits` — split date + ratio value (e.g., `4.0` for a 4:1 split).

Events are persisted via `_upsert_asset_events()`, keyed by `provider_assignment_id`. Re-syncing replaces stale events.

---

## ⚡ Caching Strategy

| Cache | Key | TTL | Max Size | Purpose |
|---|---|---|---|---|
| **Current value** | `identifier` | 120 sec | 200 | Avoid repeated `ticker.info` calls during LiveTicker polling (frontend polls every 30s, 3/4 are cache hits) |
| **Search results** | `query.lower()` | 10 min | 1000 | Avoid repeated search API calls |
| **Currency lookup** | `symbol` | 24 hours | 2000 | Currency doesn't change — used by `search()` only |

Caches use `get_ttl_cache()` (in-memory, per-process). They are populated lazily on first access and cleared on server restart.

!!! info "No history caching"

    Historical data is NOT cached at the provider level — the core layer persists prices in the database. Subsequent requests are served from DB (see [Architecture — Price Query](architecture.md#data-flow-price-query)).

---

## 🧪 Test Configuration

| Property | Value |
|---|---|
| `test_cases` | `[{identifier: "AAPL", identifier_type: TICKER}]` |
| `test_search_query` | `"Apple"` |

---

## ⚠️ Limitations

- **Rate limits**: Yahoo Finance may throttle requests. No built-in rate limiter — rely on core sync Semaphore.
- **ISIN resolution**: Not all ISINs are resolvable by yfinance (depends on market coverage).
- **Data gaps**: Some tickers may have missing days or delayed data.

---

## 📦 Dependency

- **Library**: [`yfinance`](https://pypi.org/project/yfinance/) — installed via `pipenv install yfinance`.
- **Optional import**: If `yfinance` is not installed, the provider raises `AssetSourceError("NOT_AVAILABLE")` on every call.
- **Transitive**: `pandas` (required by yfinance).

---

## 🔗 Related Documentation

- 📖 [Yahoo Finance — User Guide](../../../user/assets/providers/yahoo-finance.md) — End-user configuration guide
- 📦 [Providers Overview](system_providers.md) — All available providers
- 💰 [Asset Architecture](architecture.md) — Sync pipeline and price queries
- 📈 [Asset Plugin Guide](../../architecture/patterns/asset_plugin_guide.md) — How to create a new provider




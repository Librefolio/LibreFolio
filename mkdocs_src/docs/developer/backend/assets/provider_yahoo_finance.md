# 📈 Yahoo Finance Provider (`yfinance`)

The Yahoo Finance provider fetches stock, ETF, crypto, and index prices using the [yfinance](https://github.com/ranaroussi/yfinance) library. It is the primary market data provider for LibreFolio.

**Implementation**: `backend/app/services/asset_source_providers/yahoo_finance.py`

📖 **User Guide**: [Yahoo Finance — User Manual](../../../user/assets/providers/yahoo-finance.md)

---

## ⚙️ How it Works

1. **Identifier**: A Yahoo Finance ticker symbol (e.g., `AAPL`, `BTC-USD`, `IE00B4L5Y983`).
2. **Identifier Types**: `TICKER` and `ISIN` are both accepted. ISIN is resolved by yfinance internally.
3. **No `provider_params`**: Yahoo Finance does not require any additional configuration.

### 💰 Current Value (`get_current_value`)

1. The asset-source service checks its **core current-value cache** (120s TTL) before invoking
   the provider.
2. Calls `ticker.info` — the Yahoo `quoteSummary` endpoint. Returns `regularMarketPrice`, `currency`, and `regularMarketTime` in a **single lightweight call**.
3. Fallback price: `currentPrice` → `previousClose` (if `regularMarketPrice` is null).
4. **No `history()` call at all** — current value polling never touches the chart API.

!!! warning "Avoid `history()` and `fast_info` for current price"

    - `ticker.history()` calls the chart API and logs noisy `Entering history()` lines.
    - `ticker.fast_info` internally triggers **2 heavy HTTP calls** (`range=1y` + `range=5d`).
    - `ticker.info` uses the `quoteSummary` endpoint — lighter, returns price + currency together.

!!! tip "Cache TTL vs Polling Interval"

    Frontend polls every **30s** for responsive UI, while the core cache has a **120s TTL**.
    Repeated polls for the same provider key can therefore return without another Yahoo call.

### 📈 Historical Data (`get_history_value`)

The public method now delegates its local work to focused helpers without changing its contract:

1. **Acquire — `_acquire_history_data()`**
   - `start_date == "min"` calls `ticker.history(period="max")`.
   - A finite range calls `ticker.history(start=start_date, end=end_date + 1 day)`, preserving
     LibreFolio's inclusive end date over yfinance's exclusive `end`.
   - Currency metadata falls back to `USD`.
   - Dividend and split series are acquired independently and best-effort; one failing does not
     suppress the other or the prices.
2. **Map — `_map_history_prices()`**
   - Yahoo index values are converted to UTC before extracting the calendar date.
   - Rows are filtered to the requested inclusive range.
   - A row with `Close = NaN` is skipped. Optional `Open`, `High`, `Low`, or `Volume` NaNs
     become `None`.
   - The provider returns only actual trading days; the query layer performs backward fill.
3. **Events — `_parse_dividend_events()` and `_parse_split_events()`**
   - Positive in-range dividends and non-trivial in-range split ratios become typed asset events.
   - The two parsers are also isolated best-effort, so either event family can survive a failure
     in the other.

Validation and data failures remain typed `AssetSourceError`s: unsupported identifier types use
`INVALID_IDENTIFIER_TYPE`, a missing optional dependency uses `NOT_AVAILABLE`, empty/unusable
history uses `NO_DATA`, and malformed or unexpected Yahoo responses use `FETCH_ERROR`.

!!! info "No provider-internal thread hop"

    Yahoo's yfinance calls remain synchronous and direct. The provider does not call
    `asyncio.to_thread()`; the asset-source service invokes the whole provider coroutine through
    `asset_sources.core._run_provider_in_thread()` in a dedicated thread with a new event loop.

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

Event acquisition and parsing are best-effort and independent. Events that are returned are
persisted by `asset_sources/price_store.py::_upsert_asset_events()`, keyed by
`provider_assignment_id`.

---

## ⚡ Caching Strategy

| Owner / Cache | Key | TTL | Max Size | Purpose |
|---|---|---|---|---|
| **Core current value** | Provider code + identifier + identifier type (refresh also includes the provider-parameter hash) | 120 sec | 300 | Avoid repeated `ticker.info` calls during current-price polling and refresh. |
| **Core history** | Provider code + identifier + identifier type + provider-parameter hash | 15 min | 500 | Reuse fetched date ranges during provider-driven refresh. |
| **Core search query** | Provider code + normalized query | 15 min | 500 | Avoid repeating the same provider search. |
| **Yahoo currency lookup** | `symbol` | 24 hours | 2000 | Cache the provider's `fast_info` currency sub-operation used by `search()`. |

All are in-memory, per-process TTL caches created with `get_ttl_cache()`. The shared result caches
are owned by `asset_sources/core.py`; Yahoo owns only its currency sub-operation cache.

!!! info "No provider-level history cache"

    Yahoo has no provider-level history cache. The outer refresh layer may reuse its core history
    cache and persists fetched prices to the database. `get_prices_bulk()` is DB-only; it never
    calls Yahoo while serving a historical query (see
    [Architecture — Price Query](architecture.md#data-flow-price-query)).

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
- **Optional import**: If `yfinance` is not installed, current/history/search calls raise an
  `AssetSourceError` with error code `NOT_AVAILABLE`; metadata refresh degrades to `None`.
- **Transitive**: `pandas` (required by yfinance).

---

## 🔗 Related Documentation

- 📖 [Yahoo Finance — User Guide](../../../user/assets/providers/yahoo-finance.md) — End-user configuration guide
- 📦 [Providers Overview](system_providers.md) — All available providers
- 💰 [Asset Architecture](architecture.md) — Sync pipeline and price queries
- 📈 [Asset Plugin Guide](../../architecture/patterns/asset_plugin_guide.md) — How to create a new provider

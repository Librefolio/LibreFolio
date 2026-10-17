# 📈 Yahoo Finance Provider (`yfinance`)

The Yahoo Finance provider fetches stock, ETF, crypto, and index prices using the [yfinance](https://github.com/ranaroussi/yfinance) library. It is the primary market data provider for LibreFolio.

**Implementation**: `backend/app/services/asset_source_providers/yahoo_finance/plugin.py`

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
4. `as_of_date` is the date of `regularMarketTime` in the exchange's timezone,
   `info["exchangeTimezoneName"]`: UTC when Yahoo gives none or one `zoneinfo` does not know,
   and the server's today without `regularMarketTime`. `FACurrentValue.exchange_timezone`
   declares that timezone (`None` when unknown). Up to 1.2.1 the date was always UTC's, the day
   before for the part of a session that falls before UTC midnight, such as Sydney's or
   Auckland's (Z-33).
5. **No `history()` call at all** — current value polling never touches the chart API.

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
   - Otherwise the currency is Yahoo's own code (`ticker.info["currency"]`), passed on unchanged
     as `FAHistoricalData.currency`: `GBp` for a London line quoted in pence. The price points and
     the dividends carry `GBP` (their schemas upper-case the code) with the numbers in pence, and
     the refresh keeps the raw code on the assignment
     ([The Provider's Own Quote Currency](architecture.md#reported-currency)). Two guards in
     `test_yahoo_finance_errors.py` pin both: no validator on that field, no conversion here.
   - The exchange's timezone is the history index's own (yfinance localizes it to
     `tz_exchange`), else `ticker.info["exchangeTimezoneName"]`, kept when `zoneinfo` knows it
     (`exchange_zone()`, `backend/app/utils/exchange_dates.py`) and declared as
     `FAHistoricalData.exchange_timezone` (`Europe/Rome`), `None` otherwise. The refresh keeps it
     on the assignment ([The Exchange's Timezone](architecture.md#exchange-timezone)).
   - Dividend and split series are acquired independently and best-effort; one failing does not
     suppress the other or the prices.
2. **Map — `_map_history_prices()`**
   - Each row takes the calendar date of its own index value (`_normalize_yahoo_date()`):
     yfinance 1.7.0 stamps a daily bar, a dividend and a split at midnight in the exchange's
     timezone (`scrapers/history.py`, `tz_localize(tz_exchange)`), so that date is the session's.
     Up to 1.2.1 the plugin converted the index to UTC first, which gave the day before the
     session for every exchange east of UTC: Milan all year, London in summer time, Tokyo
     (Z-33). The rows stored that way are checked once, at the first refresh after the upgrade
     ([The Exchange's Timezone](architecture.md#exchange-timezone)).
   - Rows are filtered to the requested inclusive range.
   - A row with `Close = NaN` is skipped. Optional `Open`, `High`, `Low`, or `Volume` NaNs
     become `None`.
   - The provider returns only actual trading days; the query layer performs backward fill.
3. **Events — `_parse_dividend_events()` and `_parse_split_events()`**
   - Positive in-range dividends and non-trivial in-range split ratios become typed asset events,
     dated by `_normalize_yahoo_date()` as the prices.
   - The two parsers are also isolated best-effort, so either event family can survive a failure
     in the other.

Validation and data failures remain typed `AssetSourceError`s: unsupported identifier types use
`INVALID_IDENTIFIER_TYPE`, a missing optional dependency uses `NOT_AVAILABLE`, empty/unusable
history uses `NO_DATA`, and malformed or unexpected Yahoo responses use `FETCH_ERROR`.

!!! info "No provider-internal thread hop"

    Yahoo's yfinance calls remain synchronous and direct. The provider does not call
    `asyncio.to_thread()`; the asset-source service invokes the whole provider coroutine through
    `assets.core._run_provider_in_thread()` in a dedicated thread with a new event loop.

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
persisted by `assets/event_store.py::_upsert_asset_events()`, keyed by
`provider_assignment_id`. They are dated on the exchange's day, as the prices; those an older
version stored a day early are re-dated once ([Asset Events](events.md#yahoo-redate)).

---

## ⚡ Caching Strategy

| Owner / Cache | Key | TTL | Max Size | Purpose |
|---|---|---|---|---|
| **Core current value** | Provider code + identifier + identifier type (refresh also includes the provider-parameter hash) | 120 sec | 300 | Avoid repeated `ticker.info` calls during current-price polling and refresh. |
| **Core history** | Provider code + identifier + identifier type + provider-parameter hash | 15 min | 500 | Reuse fetched date ranges during provider-driven refresh; the entry also keeps the reported currency and exchange timezone. The one-time date check reads past it. |
| **Core search query** | Provider code + normalized query | 15 min | 500 | Avoid repeating the same provider search. |
| **Yahoo currency lookup** | `symbol` | 24 hours | 2000 | Cache the provider's `fast_info` currency sub-operation used by `search()`. |

All are in-memory, per-process TTL caches created with `get_ttl_cache()`. The shared result caches
are owned by `assets/core.py`; Yahoo owns only its currency sub-operation cache.

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

- **Rate limits**: Yahoo Finance may refuse for too many requests. `_is_rate_limited()` recognises
  yfinance's `YFRateLimitError` and, in any error message, «429» as a whole word, «too many requests»
  or «rate limit»; `_yf_with_retry()` then raises `AssetRateLimitedError` at once, without retrying
  in the thread, and search and metadata let it through instead of answering `[]` or `None`. The core
  pauses the provider ([Provider Pauses](architecture.md#provider-pauses)); yfinance gives no
  `Retry-After`, so the pause is the core's own. A false positive costs a pause of about a minute.
  Other transient errors (timeouts, reset connections, `503`…) are still retried: at most three
  attempts, 1.5 s and then 3 s apart.
- **ISIN resolution**: Not all ISINs are resolvable by yfinance (depends on market coverage).
- **Prices in pence**: a London line quoted in pence (`GBp`) is stored in pence as `GBP`. Its
  holdings are right once the asset's quote base is 100, and the Dashboard warns until then
  (`QUOTE_IN_MINOR_UNIT`, see [Data Quality Banner](../../frontend/data-quality-banner.md)); its
  dividends stay in pence whatever the base.
- **Data gaps**: Some tickers may have missing days or delayed data.
- **Rows dated a day early by 1.2.1 or earlier**: the one-time check re-dates them; its
  [limits](architecture.md#exchange-timezone-limits) list the rows it cannot reach, such as those
  of an asset whose `yfinance` assignment was removed before it.
- **Adjusted closes**: `ticker.history()` is called without `auto_adjust`, so yfinance's default
  (`True`) applies: the stored OHLC are adjusted for dividends and splits as of each fetch, and
  a row keeps the adjustment of the fetch that last wrote it (Z-35, open after 1.3).

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

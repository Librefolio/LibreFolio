# 🔌 Asset Providers (Developer)

This section provides the technical deep-dive for each asset pricing provider in LibreFolio. For the end-user perspective, see the [User Manual — Providers](../../../user/assets/providers/index.md).

## 📦 Providers at a Glance

| Provider | Code | Features | `get_asset_url` | `params_schema` | Identifier Types | Test Level |
|:---|:---|:---|:---:|:---:|:---|:---|
| [**Yahoo Finance**](provider_yahoo_finance.md) | `yfinance` | History, Search, Metadata | ✅ | — | TICKER, ISIN | Beta |
| [**JustETF**](provider_justetf.md) | `justetf` | History, Search, Metadata | ✅ | — | ISIN | Beta |
| [**Borsa Italiana**](provider_borsa_italiana.md) | `borsa_italiana` | History, Search, Metadata | ✅ | — | ISIN | Beta |
| [**CSS Scraper**](provider_cssscraper.md) | `cssscraper` | Current Value | ✅ | ✅ | URL | Beta |
| [**Scheduled Investment**](provider_scheduled_investment.md) | `scheduled_investment` | History (Calc), Events | — | ✅ | AUTO_GENERATED | Beta |
| **Mock Provider** | `mockprov` | History, Search | — | — | TICKER, ISIN | Alpha |

### 🔑 Feature Key

- 📈 **History**: Can fetch historical OHLC data.
- 🔎 **Search**: Supports searching for assets by name/ticker. Detected via `test_search_query is not None`.
- 📋 **Metadata**: Can fetch asset details (sector, description, identifiers) via `fetch_asset_metadata()`.
- 💰 **Current Value**: Can fetch the latest real-time price.
- 📊 **Events**: Can produce asset events (dividends, interest, settlements) via `supports_events = True`.
- 🔗 **`get_asset_url`**: Generates a link to the provider's page for this asset (e.g., Yahoo Finance quote page).
- 🧩 **`params_schema`**: Exposes a form schema for the frontend to render dynamic configuration fields.
- 🧪 **Probe**: All providers support `POST /assets/provider/probe` for dry-run testing (`current_price`, `history`, `metadata` operations).

### 📝 Notes

- **CSS Scraper** `get_asset_url` returns the identifier itself (which is the URL to scrape).
- **Scheduled Investment** uses `AUTO_GENERATED` identifier type — no external identifier needed.
- **Mock Provider** (`mockprov`) is only registered when `LIBREFOLIO_TEST_MODE` is enabled.

---

## 📈 [Yahoo Finance (`yfinance`)](provider_yahoo_finance.md)

The primary market data provider — fetches stock, ETF, crypto, and index prices using the [yfinance](https://github.com/ranaroussi/yfinance) library.

- **Features**: History, Search, Metadata, Current Value
- **Identifier types**: `TICKER`, `ISIN`
- **Key details**: `ticker.info` for current price (no `history()` or `fast_info`), search caching (10 min TTL), currency caching (24h), sector/geographic metadata
- 📖 [Technical Details →](provider_yahoo_finance.md)
- 📖 [User Guide →](../../../user/assets/providers/yahoo-finance.md)

---

## 🔍 [JustETF (`justetf`)](provider_justetf.md)

Specialized ETF provider — fetches data from [justetf.com](https://www.justetf.com/) including sector and geographic distributions.

- **Features**: History, Search, Metadata, Current Value (Gettex)
- **Identifier types**: `ISIN`
- **Key details**: Cached ETF list for instant search, Gettex WebSocket for real-time quotes, geographic/sector distributions, pre-warm at startup
- 📖 [Technical Details →](provider_justetf.md)
- 📖 [User Guide →](../../../user/assets/providers/justetf.md)

---

## 🇮🇹 [Borsa Italiana (`borsa_italiana`)](provider_borsa_italiana.md)

Italian market data provider — fetches stocks, bonds (BTP), and ETFs listed on Borsa Italiana using the [`borsa-italiana-scraping`](https://github.com/Librefolio/borsaItaliana-scraping) library.

- **Features**: History, Search, Metadata, Current Value
- **Identifier types**: `ISIN`
- **Provider params**: Optional `language` (`"en"` / `"it"`) — controls names, metadata, and search results language
- **Key details**: Full OHLCV history, dual-language search with flag emojis, instrument page scraping for metadata, geographic/sector inference, shared HTTP session with WAF/JWT handling
- 📖 [Technical Details →](provider_borsa_italiana.md)

---

## 🌐 [CSS Scraper (`cssscraper`)](provider_cssscraper.md)

A versatile provider that can extract a current price from **any public webpage** using a CSS selector. Useful for tracking assets from niche sources without an API.

- **Features**: Current Value only (no historical data)
- **Identifier type**: `URL`
- **Key config**: `current_css_selector`, `currency`, `decimal_format`
- 📖 [Technical Details →](provider_cssscraper.md)
- 📖 [User Guide →](../../../user/assets/providers/css-scraper.md)

---

## 📅 [Scheduled Investment (`scheduled_investment`)](provider_scheduled_investment.md)

A synthetic, deterministic provider that calculates asset value based on a predefined interest schedule. No external calls, no DB access — pure math.

- **Features**: Calculated History, Auto-generated Events (💵 INTEREST, 🏁 MATURITY_SETTLEMENT)
- **Identifier type**: `AUTO_GENERATED`
- **Key config**: `initial_value`, `schedule[]`, `day_count`, `interest_type`, `late_interest`
- 📖 [Technical Details →](provider_scheduled_investment.md)
- 📖 [User Guide →](../../../user/assets/providers/scheduled-investment.md)

---

## 🔗 Related Documentation

- 📅 [Asset Events](events.md) — Event types, dedup strategy, MATURITY_SETTLEMENT
- 📐 [Day Count Conventions](../../../financial-theory/fundamentals/day-count.md) — ACT/365, ACT/360, 30/360, ACT/ACT
- 📊 [Asset Types](../../../financial-theory/instruments/asset-types/index.md) — CROWDFUND_LOAN, BOND, etc.
- 💰 [Asset Architecture](architecture.md) — Sync pipeline and event persistence
- 📈 [Asset Plugin Guide](../../architecture/patterns/asset_plugin_guide.md) — How to create a new provider

# 💼 Assets

Assets are the core of LibreFolio. They represent any financial instrument you own or track: stocks, ETFs, bonds, cryptocurrencies, or custom instruments like savings accounts with scheduled interest.

<div class="lf-screenshot-carousel" data-carousel="carousel-assets-list" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="assets" data-name="list" data-title="🔲 Card Grid View" alt="Asset List Page (Grid)">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="assets" data-name="list-table" data-title="📋 Data Table View" alt="Asset List Page (Table)">
</div>

## 📌 What is an Asset?

An asset in LibreFolio is a financial instrument with:

- **Identity**: name, ISIN, ticker, or other identifiers
- **Type**: stock, ETF, bond, crypto, commodity, etc.
- **Currency**: the currency used to store the asset's prices — normally the one it is quoted in
- **Provider**: an optional pricing provider that automatically fetches current prices and history
- **Classification**: sector and geographic distribution (pie charts + world map)
- **Transactions**: buy, sell, dividend, interest operations linked to a portfolio

## 📋 Asset List

Navigate to **Assets** in the sidebar to see all your assets. The list page provides:

- 🔀 **Grid / Table Layouts**: Choose between a card-based visual grid or a dense, sortable data table. Your layout preference is automatically persisted in your browser's `localStorage` and will be loaded in future sessions.
- 🔎 **Search**: Filter the list in real time by asset name.
- 🏷️ **Type & Currency Filters**: Show only some asset types (e.g. ETFs, Stocks, Bonds, Crypto) or only some currencies.
- 🗃️ **Active / Inactive**: The list starts with active assets only. Switch on **Inactive** to see deactivated (archived) assets as well, or switch off **Active** to see only those.
- ⏱️ **Time Delta Selector**: Change the timeframe used to calculate price changes (e.g., `1W`, `1M`, `3M`, `6M`, `1Y`, `2Y`, `3Y`, `5Y`).
- 📉 **Absolute / Percentage Delta**: In grid view, the toolbar's **Abs / %** control applies to
  every asset card. The % button on an individual card changes only that card; using the toolbar
  again clears local overrides and returns every card to the selected global mode.
  The control appears only on the **Assets** tab, in grid view: the **Correlation** tab's toolbar
  does not show it. Its setting belongs to the whole page, so it is still there when you come back
  from the **Correlation** tab — a single card's own choice is not. Unlike the layout, it is not
  saved: leaving the page resets it to **%**.
- 🔄 **Sync & Refresh**: On the **Assets** tab, sync real-time pricing data for all configured providers or manually refresh the list. On the [**Correlation**](correlation.md) tab, the same two buttons act on the selection: **Sync selection** syncs the prices of the selected assets and the exchange rates that convert them, and **Reload All** reloads every analysis of the selection.
- 🖱️ **Context Menu**: Right-click any row in the data table layout for quick actions (**Sync**, **Refresh**, **Merge**, **Delete**). Sync is disabled for assets without a pricing provider and for archived assets; Merge folds a duplicate asset into another one — transactions, prices, and events converge on the target and the source asset is deleted.

Click on any asset card to navigate to its **[detail page](detail/index.md)**. There, the **‹ ›** arrows in the header step through the assets in the order this list shows them — search, filters and sort included.

### 🗂️ Your Assets, Other Users' Assets, Watched

In both layouts the list is split into up to three panels, each with its own count. A panel with
nothing in it is not shown.

| Panel | What it holds |
|---|---|
| **Your assets** | Assets held now in a broker you own |
| **Other users' assets** | Assets held now only by other users — in brokers you do not own |
| **Watched** | Assets held by no one now — never bought or already sold, kept on the radar |

What decides the panel is the position **today**, not the past: having once traded an asset does
not keep it among *Your assets*. When you sell your whole position, the asset moves to
*Other users' assets* if someone else still holds it, and to *Watched* otherwise. Brokers shared
with you as **Editor** or **Viewer** count as other users' brokers, and a position closed down to a
negligible leftover counts as not held.

In table view each panel is a table of its own: column widths, order and visibility stay aligned
across the three, while each table has its own pages.

### 🗑️ Deleting an Asset

LibreFolio blocks deletion when **any transaction anywhere in the database** still uses the
asset, including transactions in brokers you cannot access. The blocked result includes a
**Transactions** link already filtered to that asset.

The Transactions page still applies normal broker access: the link shows only matching
transactions in brokers you can view. Its visible rows may therefore be fewer than the global
transaction count reported by the deletion blocker.

## 🧭 Features

### ➕ [Create & Edit](create-edit.md)

Step-by-step guide for creating new assets, configuring providers, and editing existing assets.

### 🧪 [Correlation Tab](correlation.md)

Compare a selection of assets side by side — correlation matrix, losses, risk against return, and historical replay, in percentages only.

### 📊 [Asset Detail Page](detail/index.md)

The heart of asset analysis — interactive chart, technical signals, measures, classification, and data editor.

### 🔌 [Providers](providers/index.md)

Automatic price fetching from Yahoo Finance, justETF, Borsa Italiana, CSS Scraper, or the Scheduled Investment engine.

---

## 📡 Real-time Pricing & Live Ticker

To keep you updated on market movements without forcing constant page refreshes, LibreFolio displays compact, live price badges on the **Assets list** and **Asset Detail** pages.

### ⏱️ Automatic Polling

When viewing these pages, your browser polls the backend every **30 seconds** for current asset prices. This process runs silently in the background and is completely non-blocking (the UI is ready instantly, and prices load as they arrive). The Dashboard does not poll: it shows the latest stored prices.

### 🎨 Visual Indicators

Badges transition colors dynamically to indicate recent price movements relative to the previous poll:

* 🟢 **Green (Up)**: The asset price has increased.
* 🔴 **Red (Down)**: The asset price has decreased.
* ⚪ **Gray (Neutral)**: The price is unchanged, loading, or the market is currently closed.

!!! note "Market Closure & Fallbacks"

    During weekends or market closures, the Live Ticker will display the last available closing price in a neutral gray badge.

### 🔌 Caching & Background Scheduler

To ensure fast load times and prevent your instance from getting rate-limited or blocked by external providers (such as Yahoo Finance), LibreFolio uses a dual-layer strategy:

1. **Background Scheduler**: A background daemon on the server refreshes all active asset prices at a regular interval (default: every 10 minutes, configurable by administrators in Global Settings). This keeps the database and local price cache warm.
2. **On-Demand Polling Cache**: When the frontend polls the backend, it reads from this warm local cache. If the cache is cold, the provider fetches the price and stores it with a 120-second TTL (Time-To-Live). Subsequent page refreshes or dashboard views from other users hit the local cache directly.

---

## 🔗 Related

- 📚 **[Financial Theory — Asset Types](../../financial-theory/instruments/asset-types/index.md)** — Stock, ETF, Bond, Crypto, etc.
- 💱 **[FX Rates](../fx/index.md)** — Currency exchange rates used for cross-currency conversion

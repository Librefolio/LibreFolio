# 💼 Assets

Assets are the core of LibreFolio. They represent any financial instrument you own or track: stocks, ETFs, bonds, cryptocurrencies, or custom instruments like savings accounts with scheduled interest.

<div class="lf-screenshot-carousel" data-carousel="carousel-assets-list" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="assets" data-name="list" data-title="🔲 Card Grid View" alt="Asset List Page (Grid)">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="assets" data-name="list-table" data-title="📋 Data Table View" alt="Asset List Page (Table)">
</div>

## 📌 What is an Asset?

An asset in LibreFolio is a financial instrument with:

- **Identity**: name, ISIN, ticker, or other identifiers
- **Category**: stock, ETF, bond, crypto, commodity, etc.
- **Currency**: the currency the asset is denominated in
- **Provider**: an optional pricing provider that automatically fetches current prices and history
- **Classification**: sector and geographic distribution (pie charts + world map)
- **Transactions**: buy, sell, dividend, interest operations linked to a portfolio

## 📋 Asset List

Navigate to **Assets** in the sidebar to see all your assets. The list page provides:

- 🔀 **Grid / Table Layouts**: Choose between a card-based visual grid or a dense, sortable data table. Your layout preference is automatically persisted in your browser's `localStorage` and will be loaded in future sessions.
- 🔎 **Smart Search**: Filter assets in real-time by entering a name, ISIN, ticker, or broker name.
- 🏷️ **Type Filters**: Filter the list to display only specific classes (e.g. ETFs, Stocks, Bonds, Crypto).
- 🗃️ **Archived Assets**: Toggle between active holdings and archived assets to keep your list clean.
- ⏱️ **Time Delta Selector**: Change the timeframe used to calculate price changes (e.g., `1D`, `1W`, `1M`, `YTD`, `ALL`).
- 🔄 **Sync & Refresh**: Sync real-time pricing data for all configured providers or manually refresh the list.
- 🖱️ **Context Menu**: Right-click any row in the data table layout for quick actions (Edit, Delete, Sync).

Click on any asset card to navigate to its **[detail page](detail/index.md)**.

## 🧭 Features

### ➕ [Create & Edit](create-edit.md)

Step-by-step guide for creating new assets, configuring providers, and editing existing assets.

### 📊 [Asset Detail Page](detail/index.md)

The heart of asset analysis — interactive chart, technical signals, measures, classification, and data editor.

### 🔌 [Providers](providers/index.md)

Automatic price fetching from Yahoo Finance, justETF, CSS Scraper, or the Scheduled Investment engine.

---

## 📡 Real-time Pricing & Live Ticker

To keep you updated on market movements without forcing constant page refreshes, LibreFolio displays compact, live price badges on the **Dashboard** and **Asset Detail** pages.

### ⏱️ Automatic Polling

When viewing these pages, your browser polls the backend every **30 seconds** for current asset prices. This process runs silently in the background and is completely non-blocking (the UI is ready instantly, and prices load as they arrive).

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

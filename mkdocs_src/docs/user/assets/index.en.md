# 💼 Assets

Assets are the core of LibreFolio. They represent any financial instrument you own or track: stocks, ETFs, bonds, cryptocurrencies, or custom instruments like savings accounts with scheduled interest.

<div class="screenshot-container" style="max-width: 800px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="list" alt="Assets List Page" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
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

- **Search**: filter assets by name, ISIN, or ticker
- **Type filter**: show only specific asset types (ETF, Stock, Bond, etc.)
- **Active/All toggle**: show only active assets or include archived ones
- **Sync All**: fetch latest prices for all assets with a provider
- **Refresh All**: reload asset data from the database

Click on any asset card to navigate to its **[detail page](detail/index.en.md)**.

## 🧭 Features

### ➕ [Create & Edit](create-edit.en.md)

Step-by-step guide for creating new assets, configuring providers, and editing existing assets.

### 📊 [Asset Detail Page](detail/index.en.md)

The heart of asset analysis — interactive chart, technical signals, measures, classification, and data editor.

### 🔌 [Providers](providers/index.en.md)

Automatic price fetching from Yahoo Finance, justETF, CSS Scraper, or the Scheduled Investment engine.

---

## 🔗 Related

- 📚 **[Financial Theory — Asset Types](../../financial-theory/instruments/asset-types/index.md)** — Stock, ETF, Bond, Crypto, etc.
- 💱 **[FX Rates](../fx/index.md)** — Currency exchange rates used for cross-currency conversion

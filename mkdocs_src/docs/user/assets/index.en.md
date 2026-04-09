# 💼 Assets

Assets are the core of LibreFolio. They represent any financial instrument you own or track: stocks, ETFs, bonds, cryptocurrencies, or custom instruments like savings accounts with scheduled interest.

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

Click on any asset card to navigate to its **detail page**.

## ➕ Creating an Asset

1. Click **+ New Asset** on the assets page
2. Fill in the basic information:
    - **Name** (required)
    - **Category** (required)
    - **Currency** (required)
    - **Identifiers**: ISIN, ticker, CUSIP, SEDOL, etc.
3. Optionally configure a **Provider** for automatic price fetching
4. Optionally add **Sector** and **Geographic** distributions
5. Click **Save**

## 📊 Asset Detail Page

The detail page is the heart of asset analysis. It includes:

### 🔧 Header & Controls

- **Back button**: return to the asset list
- **Asset info**: name, type badge, currency, current price
- **Edit**: open the edit modal to modify asset properties
- **Sync**: fetch latest price data from the provider
- **Refresh**: reload data from the database

### 📈 Price Chart

An interactive ECharts chart showing historical price data with:

- **Date range filter**: select a time window (1W, 1M, 3M, 6M, 1Y, ALL, or custom range)
- **Currency selector**: view prices in the asset's native currency or your portfolio base currency
- **Absolute/Percentage toggle**: switch between absolute price values and percentage change
- **Event markers**: dividends, splits, and other corporate events are shown as markers on the chart

### 📐 Technical Signals

Toggle the **Signals** panel to overlay technical indicators on the chart:

- **EMA** (Exponential Moving Average) — configurable period
- **MACD** (Moving Average Convergence Divergence)
- **RSI** (Relative Strength Index)
- **Bollinger Bands** — configurable period and standard deviation
- **Asset Comparison** — compare with another asset's performance

Each signal can be added, configured, and removed individually.

### 📏 Measure Tool

Enable the **Measure** tool to interactively measure price differences, percentage changes, and time intervals between any two points on the chart.

### 🗂️ Classification

If sector or geographic distributions are configured, the detail page shows:

- **Sector pie chart**: breakdown by industry sector
- **Geographic world map**: geographic allocation with an interactive world map
- **Geographic pie chart**: percentage breakdown by country/region

### ✏️ Data Editor

Toggle the **Edit Data** panel to manually add, modify, or delete individual price data points directly on the chart.

## 🛠️ Editing an Asset

Click the **Edit** button on the detail page to open the asset modal with all fields pre-populated. All fields are editable, including provider configuration and distributions.

## 🧪 Testing Provider Configuration

After configuring a provider, click **Test Configuration** to verify that pricing data can be fetched. The test checks:

- **Current Price**: fetches the latest price
- **History**: fetches historical price data (if supported)

Results are displayed inline with execution times. A ⚠️ warning means the operation is not supported by this provider (e.g., CSS Scraper doesn't support history).

## 🔌 Provider Assignment

Each asset can have one pricing provider assigned. See [Providers](providers/index.en.md) for details on available providers and their configuration.

## ⏱️ Fetch Interval

The fetch interval controls how often LibreFolio automatically refreshes the asset's price data. Default is 24 hours (24:00). Format: `HH:MM`.

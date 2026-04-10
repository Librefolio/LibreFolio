# 🔍 Asset Detail Page

Click on any asset from the [Asset List](../index.md) to open its detail page. Here you can visualize, analyze, and manage price data for that specific asset.

<div class="screenshot-container" style="max-width: 800px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-chart" alt="Asset Detail Page" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

The detail page is organized into several features, each accessible from the toolbar:

---

## 🧭 Features

### 📈 [Interactive Chart](chart.en.md)

The main view — a full ECharts-powered chart with zoom, pan, date range filtering, and currency conversion. Event markers (dividends, splits, interest) are overlaid directly on the price line.

### 📊 [Signals](signals.en.md)

Overlay technical indicators (EMA, MACD, RSI, Bollinger Bands, Asset Comparison) on the chart. Each signal is computed in real-time from the price data and can be toggled independently.

### 📐 [Measures](measures.en.md)

Click-to-click measurement tool. Select two points on the chart to see the delta, percentage change, and annualized return between them.

### 🗂️ [Classification](classification.en.md)

Sector pie chart, geographic world map, and country breakdown — when classification data is configured for the asset.

### ✏️ [Data Editor](data-editor.en.md)

View, add, edit, or delete individual price data points directly on the chart.

### 📅 [Events](events.en.md)

Asset-level events (dividends, interest, splits, price adjustments) shown as markers on the chart.

---

## 🔧 Header & Controls

- **← Back button**: return to the asset list (or previous page)
- **Asset info**: name, type badge, currency, current price
- **Edit** (✏️): open the edit modal to modify asset properties
- **Sync** (🔄): fetch latest price data from the provider
- **Refresh** (↻): reload data from the database

---

## 🔗 Related

- ➕ **[Create & Edit](../create-edit.en.md)** — Creating and configuring assets
- 📋 **[Asset Overview](../index.md)** — Back to the asset list page


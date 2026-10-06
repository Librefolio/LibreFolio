# 🔍 Asset Detail Page

Click on any asset from the [Asset List](../index.md) to open its detail page. Here you can visualize, analyze, and manage price data for that specific asset.

<div class="screenshot-container" style="max-width: 800px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-chart" alt="Asset Detail Page" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

The detail page is organized into two tabs: **Overview** (all the features below) and **Risk & Scenarios**.

!!! info "Beta"

    The **Risk & Scenarios** tab belongs to the Risk Analysis subsystem, which is currently in **beta**. It is not covered by this documentation yet — the sections below describe the Overview tab.

---

## 🧭 Features

### 📈 [Interactive Chart](chart.md)

The main view — a full ECharts-powered chart with zoom, pan, date range filtering, and currency conversion. Event markers (dividends, splits, interest) are overlaid directly on the price line.

### 📊 [Signals](signals.md)

Overlay any of the **22 backend technical indicators** (trend, momentum, volatility, volume, and risk families), comparison series, and synthetic benchmark curves on the chart. Each signal is computed by the backend from the stored price history and can be configured and toggled independently.

### 📐 [Measures](measures.md)

Click-to-click measurement tool. Select two points on the chart to see the delta, percentage change, and annualized return between them.

### 🗂️ [Classification](classification.md)

Sector pie chart, geographic world map, and country breakdown — when classification data is configured for the asset.

### ✏️ [Data Editor](data-editor.md)

View, add, edit, or delete individual price data points directly on the chart.

### 📅 [Events](events.md)

Asset-level events (dividends, interest, splits, price adjustments) shown as markers on the chart.

---

## 🔧 Header & Controls

- **← Back button**: return to the asset list (or previous page) in one step, even after browsing with the arrows — the browser's Back button skips those moves too
- **Asset info**: name, type badge, currency, current price
- **‹ › Previous / Next asset**: step to the previous or next asset without going back to the list, keeping the same date range; the counter between the arrows (e.g. 3/12) shows where you are. There is no wrap-around: the arrow is disabled at either end, and both are hidden when there is only one asset to browse. The order they follow:
    - **opened from the Assets page**: that list as you left it — its search, type, currency and archived filters, its grid or table view and, in the table, its column sort and filters
    - **opened any other way** (a link or bookmark, a page reload, another page such as the Dashboard or Transactions), or for an asset that list does not show: every asset in the Assets page's default order — archived ones only when the asset you opened is archived itself
- **Edit** (✏️): open the edit modal to modify asset properties
- **Sync** (🔄): fetch latest price data from the provider
- **Refresh** (↻): reload data from the database

---

## 🔗 Related

- ➕ **[Create & Edit](../create-edit.md)** — Creating and configuring assets
- 📋 **[Asset Overview](../index.md)** — Back to the asset list page


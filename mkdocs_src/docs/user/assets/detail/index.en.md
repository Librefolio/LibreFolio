# 🔍 Asset Detail Page

Click an asset on the [Assets page](../index.md) to open its own page: its price history, the tools to analyse it, and the data behind it.

<div class="screenshot-container" style="max-width: 800px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-chart" alt="Asset Detail Page" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

The page has two tabs: **Overview**, described below, and **Risk & Scenarios**.

!!! info "Beta"

    The **Risk & Scenarios** tab is still in beta: it opens with the notice *Risk Analysis is in beta.* and is not covered by this documentation yet.

---

## 🧭 What the Overview shows

From top to bottom:

### 📊 [Signals](signals.md)

Draw any of the **22 technical indicators**, another asset or currency pair, or a reference curve over the chart.

### 📈 [Interactive Chart](chart.md)

The price history, or the **[Rolling Return](chart.md#rolling-return)** over a window you choose (1W, 1M, 3M, 1Y or a custom length). Zoom, pan, and convert it to another currency.

### ✏️ [Data Editor](data-editor.md)

Add, fix or delete prices and events, one by one or from a CSV file.

### 📐 [Measures](measures.md)

Click two points of the chart to read the change between them.

### 🗂️ [Classification](classification.md)

The sector and country breakdown, in the **Metadata & Classification** panel.

### 📅 [Events](events.md)

Dividends, splits, interest and other asset events, drawn as markers on the chart.

---

## 🔧 Header and toolbar

- **←** goes back to the list, or to the page you came from, in one step, even after browsing with the arrows.
- **The asset** — a dot (green active, red archived), its name, type and currency, a **Transactions (N)** link when it has any, its provider (or **✏️ Manual**), and a link to its web page: the one you set on the asset, or else the provider's.
- **‹ n/N ›** — the previous or next asset, keeping the same dates (see the panel below).
- **Date range** and **Convert to** — the period and the currency of the [chart](chart.md).
- **AI Export** — copies the asset's data for an AI assistant ([Asset AI Export](../../ai-export/asset.md)).
- **Edit** (✏️) — opens the asset form ([Create & Edit](../create-edit.md)).
- **Sync** (🔄) — downloads the latest prices, with those of the compared assets and the exchange rates the chart needs; it reads **Recalculate** for a Scheduled Investment. Not available for an asset without a provider or an archived one.
- **Reload** (↻) — reloads the page's data from what LibreFolio has stored.

??? info "🧭 Which order the ‹ › arrows follow"

    - **Opened from the Assets page**: the list as you left it — its search, filters, grid or table view and, in the table, its sort and column filters.
    - **Opened any other way** (a link or bookmark, a reload, the Dashboard, Transactions…), or for an asset that list does not show: every asset in the Assets page's default order, archived ones only when the asset you opened is archived.
    - The counter (for example 3/12) shows where you are. The arrows stop at both ends and disappear when there is only one asset to browse.

---

## 🔗 Related

- ➕ **[Create & Edit](../create-edit.md)** — Creating and configuring assets
- 📋 **[Asset Overview](../index.md)** — Back to the asset list page


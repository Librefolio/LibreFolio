# 🔍 Asset Detail Page

Click an asset on the [Assets page](../index.md) to open its own page: its price history, the tools to analyse it, and the data behind it.

<div class="screenshot-container" style="max-width: 800px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-chart" alt="Asset Detail Page" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

The page has two tabs: **Overview**, described below, and **[Risk & Scenarios](#risk-scenarios)**.

---

## 🧭 What the Overview shows

From top to bottom:

### 📊 [Signals](signals.md)

Draw any of the **24 technical indicators**, another asset or currency pair, or a reference curve over the chart.

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

## 🛡️ Risk & Scenarios {: #risk-scenarios }

An x-ray of this one asset, drawn with the same blocks as the Dashboard's [Risk tab](../../dashboard/risk.md), on the period and in the currency the page shows. Its blocks:

- 📉 **[How Much Can It Hurt?](../../dashboard/risk.md#how-much-can-it-hurt)** — the losses this asset actually went through: a bad day, thirty bad days, the worst fall, how far below its peak it is today.
- 📈 **[How Does It Move?](../../dashboard/risk.md#how-does-it-move)** — the green twins: the best day, thirty good days, the largest rally, and what its days were like.
- ⚖️ **Compared with a Reference** — the asset's volatility, annual return, Sortino and Sharpe, and the same against a benchmark you choose, as in [Am I Being Paid for This Risk?](../../dashboard/risk.md#being-paid). The asset's own row is there even with no benchmark chosen; the benchmark is the one shared with the Dashboard, and the asset itself cannot be its own reference.
- 🔮 **[What If…?](../../dashboard/risk.md#what-if)** — a past crisis replayed on the asset, said in one sentence; a shock by sector or region; a simulation.

The **risk-free rate** under the period line is the one of the Dashboard and of every risk page: changing it here changes it there → [Risk tab](../../dashboard/risk.md#good-to-know).

What differs from the Dashboard:

- **Your position**: when you own the asset, the amounts are on the value of your position today, across all your brokers, and a line above the blocks says which value. When you do not own it, the blocks show percentages only.
- **No diversification block**: one asset has nothing to diversify.
- **Prices from a plan**: on a scheduled investment and on an asset of type *Crowdfund*, *Real estate crowdfunding* or *Held asset*, a note says that the prices come from the plan, not from the market — volatility and VaR then say how regular the plan is, not how risky the asset is.
- **The toolbar's buttons**: the tab has no **Sync** of its own — the toolbar's **Sync** and **Reload** update it too, and its **Date range** and **Convert to** set its period and currency. A notice about missing data may still offer its own **Sync**.

---

## 🔧 Header and toolbar

- **←** goes back to the list, or to the page you came from, in one step, even after browsing with the arrows.
- **The asset** — a dot (green active, red archived), its name, type and currency, a **⇄ Transactions** badge with their number when it has any, and its provider badge (or **✏️ Manual**). When the asset has a web page — the one you set on it, or else the provider's — the provider badge shows ↗ and opens it in a new tab.
- **‹ n/N ›** — the previous or next asset, keeping the same dates (see the panel below).
- On a phone, ← and ‹ n/N › share the top row, the name has the next one, and the badges follow.
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


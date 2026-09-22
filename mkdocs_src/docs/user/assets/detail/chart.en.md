# 📈 Interactive Chart

The chart is the centerpiece of the asset detail page. It can show the asset's price history or a backend-computed Rolling Return over that history.

_Last updated: 2026-09-16_

<div class="screenshot-container" style="max-width: 800px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-chart" alt="Asset Price Chart" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔀 Primary Modes

Use the two buttons above the chart to choose its primary series:

- **Prices** (line-chart icon) shows the resolved price series.
- **Rolling Return** (percent icon) shows the price-only percentage return for each chart date against the resolved close exactly _N_ calendar days earlier.

Opening or reloading an asset starts in **Prices** mode. LibreFolio remembers the Rolling Return window, but it does not persist the selected primary mode.

### 🗓️ Rolling Return Window

The four presets are exact calendar-day aliases:

| Preset | Window sent for calculation |
|---|---:|
| **1W** | 7 days |
| **1M** | 30 days |
| **3M** | 90 days |
| **1Y** | 365 days |

Choose the compact **Custom** control to enter a positive whole number and select **W**, **M**, or **Y**. Custom windows use fixed multipliers: 7 days per week, 30 days per month, and 365 days per year. For example, `3M` in the Custom control means 90 calendar days.

Every preset and any supported positive **Custom** window remain available when _N_ is longer than the selected date range. The visible span does not cap the lookback or force a switch back to **Prices**.

The selected window is part of this asset's browser-local chart settings. It is stored in `localStorage` under the current account and asset, so it survives a reload in the same browser; it is not written to the backend database.

### 🧮 Calculation, Currency, and Provenance

Rolling Return is calculated by the backend from the resolved daily close series. The selected chart currency is applied before the calculation, and Asset comparison lines use that same target currency and the same _N_-day window.

The selected start and end bound output dates only. For the exact _t − N_ reference, the backend loads history from _N_ calendar days before the selected start (or the earliest possible date) and may resolve those dates from still earlier factual price or FX observations. A valid line can therefore begin on the selected start even when _N_ is longer than the visible range.

Each primary or comparison-asset line starts on its own first selected date where both the current value and exact _t − N_ reference resolve. Late inception or missing leading price/FX coverage shortens only that line; a later missing current or reference value leaves a gap in that line without truncating the others.

For every returned point, the backend also reports the requested reference date and the actual price and FX observations used. The tooltip exposes that provenance, and the stale-gradient setting can visualize stale price or FX inputs on the line. LibreFolio does not interpolate or fabricate a replacement return: normal source resolution may carry forward an earlier factual price or FX rate, with its actual date and staleness preserved. Missing or invalid endpoints remain gaps. Mixed valid and missing points produce a typed **partial** result; only a range with zero valid points is **unavailable**.

Asset prices, asset events, and FX rates are persisted source data. The rolling-return series and its provenance are computed on request and kept only for the current page runtime; they are not saved as new history. Rolling Return is price-only: it does not include events, cash flows, transactions, or portfolio P&L.

### 🗄️ Data Ownership at a Glance

| Layer | What it owns |
|---|---|
| **Backend database** | Source Asset price and event history, and source FX-rate history |
| **Browser `localStorage`** | Chart settings, the selected Rolling Return window, and comparison configuration such as selections, parameters, order, and styles—never source or computed series |
| **Browser `sessionStorage`** | The shared visible start/end date range for the current tab |
| **Current page runtime only** | Computed Rolling Return and comparison series, their provenance, and measurements; a reload discards them |

---

## 🎛️ Filter Bar

The filter bar above the chart provides controls for customizing the view:

### 📅 Date Range

Select a time window for the chart data:

- **Presets**: 1W, 1M, 3M, 6M, 1Y, 2Y, YTD, MAX — when the bar has leftover space, extra **fill presets** appear to use it (3Y, 5Y, 10Y and WTD, MTD, QTD)
- **Custom**: pick a start and end date using the calendar picker

This date range controls output dates. In Rolling Return mode it is separate from the _N_-day comparison window above.

### 💱 Currency Selector

View prices in:

- The asset's **native currency** (e.g., USD for Apple)
- Your **portfolio base currency** (e.g., EUR) — automatically converted using FX rates

The selected currency also becomes the target currency for the backend Rolling Return calculation.

**Page Sync** includes every already-configured FX route required by the primary asset, comparison assets, or their events in either **Prices** or **Rolling Return** mode. A missing pair remains a remediation item: Page Sync does not include or register it automatically.

### 📊 Absolute / Percentage Toggle

In **Prices** mode:

- **Absolute**: shows the actual price values
- **Percentage** (%): shows percentage change from the first data point in the selected range

Rolling Return is already a percentage series, so this toggle is hidden in that mode.

### 📅 Event Markers

In **Prices** mode, dividends, splits, interest payments, and other [asset events](events.md) appear as colored markers on the chart:

- 💰 **Dividend** — cash distribution
- 💵 **Interest** — interest payment
- 📊 **Split** — stock split
- 📝 **Price Adjustment** — write-down or re-rating
- 🏁 **Maturity Settlement** — asset reached maturity

Hover over a marker to see the event details (date, type, value).

---

## 🎨 Aesthetics

Click the **Settings** (⚙️) button to toggle the inline aesthetics panel (area fill, baseline colors, grid lines, stale gradient, Y-axis scale). These controls remain available in Rolling Return mode, which always uses a percentage line chart; area fill and the percentage-axis profile apply there. Candlesticks, event markers, and the data editor are available only in **Prices** mode.

The **Measure** tool is available in both primary modes. **Prices** and **Rolling Return** keep separate in-page measurements and summary tables; see [Measures](measures.md).

The same aesthetics settings — plus overlay signals — can also be edited for all asset charts at once from the **Chart Settings** modal on the [Assets list page](../index.md), which shows a live preview while you edit; see [Chart Settings](../../fx/chart-settings.md) for how the modal and its preview work (the Assets scope is independent from FX).

---

## 🔗 Related

- 📊 **[Signals](signals.md)** — Overlay technical indicators
- 📐 **[Measures](measures.md)** — Measure price differences
- 📅 **[Events](events.md)** — Understand event markers

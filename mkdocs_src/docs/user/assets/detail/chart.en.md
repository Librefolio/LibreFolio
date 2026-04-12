# 📈 Interactive Chart

The price chart is the centerpiece of the asset detail page, providing a visual history of the asset's price over time.

<div class="screenshot-container" style="max-width: 800px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-chart" alt="Asset Price Chart" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🎛️ Filter Bar

The filter bar above the chart provides controls for customizing the view:

### 📅 Date Range

Select a time window for the chart data:

- **Presets**: 1W, 1M, 3M, 6M, 1Y, ALL
- **Custom**: pick a start and end date using the calendar picker

### 💱 Currency Selector

View prices in:

- The asset's **native currency** (e.g., USD for Apple)
- Your **portfolio base currency** (e.g., EUR) — automatically converted using FX rates

### 📊 Absolute / Percentage Toggle

- **Absolute**: shows the actual price values
- **Percentage** (%): shows percentage change from the first data point in the selected range

### 📅 Event Markers

Dividends, splits, interest payments, and other [asset events](events.md) appear as colored markers on the chart:

- 💰 **Dividend** — cash distribution
- 💵 **Interest** — interest payment
- 📊 **Split** — stock split
- 📝 **Price Adjustment** — write-down or re-rating
- 🏁 **Maturity Settlement** — asset reached maturity

Hover over a marker to see the event details (date, type, value).

---

## 🎨 Aesthetics

Click the **Settings** (⚙️) button to toggle the aesthetics panel for chart customization (line color, style, etc.).

---

## 🔗 Related

- 📊 **[Signals](signals.md)** — Overlay technical indicators
- 📐 **[Measures](measures.md)** — Measure price differences
- 📅 **[Events](events.md)** — Understand event markers


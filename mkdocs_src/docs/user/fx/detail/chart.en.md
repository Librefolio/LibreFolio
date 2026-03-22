# 📉 Interactive Chart

The heart of the Pair Detail page — a full-featured **ECharts-powered** chart that lets you visualize exchange rate history with powerful interactive tools.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="detail-chart" alt="FX Detail Chart" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔀 View Modes

Toggle between two display modes using the toolbar:

- 📈 **Absolute** — Shows the raw exchange rate values (e.g., 1 EUR = 1.0845 USD). Best for seeing actual rate levels.
- 📊 **Percentage (%)** — Shows the percentage change from the first visible data point. Best for comparing relative movements and overlaying multiple signals.

When switching to % mode, all overlay signals are also recalculated as percentages from their respective starting points.

---

## 🔍 Navigation & Zoom

| Action | Desktop | Mobile |
|--------|---------|--------|
| **Pan** | Click + drag | Touch + drag |
| **Zoom in** | Mouse wheel up | Pinch out |
| **Zoom out** | Mouse wheel down | Pinch in |
| **Reset zoom** | Double-click | Double-tap |

You can also use the **time range presets** (1W, 1M, 3M, 6M, 1Y, 2Y) or select a **Custom** date range to quickly jump to specific periods.

!!! info "Data availability"
    If the selected time range exceeds the available data, LibreFolio displays whatever is available. Use **Sync** to try fetching older data from the provider — but note that some providers have limited historical coverage.

---

## 💬 Tooltip

Hover over any point on the chart to see:

- 📅 The **date**
- 💱 The **exchange rate** with full precision
- 📊 The **percentage change** from the previous data point

---

## 🧰 Toolbar

The chart toolbar provides quick access to:

- 📊 **View mode toggle** — Absolute / Percentage
- ⏱️ **Time range** — 1W, 1M, 3M, 6M, 1Y, 2Y, Custom
- 📈 **[Signals](signals.md)** — Toggle technical indicator overlays
- 📏 **[Measures](measures.md)** — Click-to-click measurement tool
- ✏️ **[Data Editor](data-editor.md)** — Edit individual data points
- ⚙️ **[Chart Settings](../chart-settings.md)** — Visual customization

---

## 🔗 Related

- ⚙️ **[Chart Settings](../chart-settings.md)** — Customize colors, line width, area fill, grid
- 📈 **[Signals](signals.md)** — Overlay technical indicators on the chart

# 📉 Interactive Chart

The heart of the pair detail page: the pair's rate history over the selected period.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="detail-chart" alt="FX Detail Chart" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔀 Abs or % view

Switch with **Abs** / **%** in the chart's top-left corner; the page opens in % view.

- 📊 **%** — the change since the first day of the period. Overlays start from 0 % too, so their
  moves compare at a glance.
- 📈 **Abs** — the rate itself, e.g. 1 EUR = 1.0845 USD.

---

## 🔍 Zoom, pan and period

| Action | Desktop | Mobile |
|--------|---------|--------|
| **Zoom** | Mouse wheel | Pinch |
| **Pan** | Click and drag | Drag with two fingers (one finger scrolls the page) |

- **Period**: the presets **1W** to **2Y**, **YTD** and **All**, or **Custom** (a number of days,
  weeks, months or years back from today); click the dates to pick them on a calendar. More presets
  appear when the toolbar has room. The pages of the same browser tab share the period.
- On a long period the chart groups the rates by week or month and shows a **Weekly** or
  **Monthly** badge: zoom in for daily rates.
- On a narrow screen the axis shows fewer, shorter dates; the first and the last always stay.

??? info "📅 History shorter than the period — when the chart starts later"

    A banner shows the date the data is available from. **Sync** may fetch older rates, if the
    provider publishes them; otherwise enter them in the [Data Editor](data-editor.md).

---

## 💬 Tooltip

Hover the chart, or touch it on mobile, to see:

- 📅 the **date** (or the week or month, when the chart groups the rates);
- 💱 the **rate** and the value of each overlay;
- 📊 the **change since the start of the period**: Δ and % in Abs view, % in % view;
- ⚠️ **Stale: N day(s) old** on days without a new rate, such as weekends and bank holidays.

---

## 🧰 Chart buttons

- 📏 **Measure** — see [Measures](measures.md).
- ✏️ **Edit Rates** — see [Data Editor](data-editor.md).
- ⚙️ **Aesthetics** — colours, fill, grid and axis ranges, as in [Chart Settings](../chart-settings.md).
- 📊 The **Signals** panel above the chart — see [Signals](signals.md).

---

## 🔗 Related

- ⚙️ **[Chart Settings](../chart-settings.md)** — Chart look and overlay signals
- 📈 **[Signals](signals.md)** — Technical indicators on the chart

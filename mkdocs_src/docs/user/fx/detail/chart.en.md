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
  weeks, months or years back from today); click the dates to pick them on a calendar. The two ends
  must be different days: the day you click first cannot be clicked again, and a typed date equal to
  the other end turns red. More presets appear when the toolbar has room. The pages of the same
  browser tab share the period.
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

## 🔁 Rolling Return {: #rolling-return }

Two buttons above the chart choose what it draws: **Prices** (the rate history, as above) and
**Rolling Return**.

In **Rolling Return** every point answers *how much has the rate moved over the last N days?* It
compares that day's rate with the rate N calendar days earlier. Example: on EUR → USD with the **3M**
window (90 days), if the rate is 1.0845 today and was 1.0500 ninety days ago, the point reads
**+3.3 %**. Above zero the first currency bought more of the second than N days before; below zero, less.

- 🗓️ **Window** — next to the two buttons: **1W**, **1M**, **3M**, **1Y**, or **Custom** (a whole
  number of weeks, months or years). Until you pick one, the window is automatic: the largest preset
  that fits the period on screen. The window may be longer than the period: LibreFolio reads the older
  rates it needs. The **?** button opens the [same explanation](../../assets/detail/chart.md#rolling-return)
  given for assets, and the [Chart Settings](../chart-settings.md#rolling-return-view) preview draws
  this view too.
- 💱 **Compare with another pair** — add an **FX Pair** in the [Signals](signals.md#data-comparison)
  panel: each compared pair draws its own rolling return, with the same window. In this mode the panel
  offers only these comparisons; your other signals stay saved and come back with **Prices**.
- 🔄 **Direction** — the return follows the direction the page shows, EUR → USD or USD → EUR.
- 📏 ✏️ **Measure** and **Edit Rates** are hidden: they work on the rates, so they belong to **Prices**.
- 💾 **Remembered** — the mode and the window are saved with this pair's chart settings, in this
  browser. The pair's card in the FX list shares them: a card in **Rolling Return** opens the page in
  it, and the page opens again in the mode you left it in. Going back to **Prices** is immediate.

Changing the period, the window, the direction or the compared pairs, or clicking **Refresh**,
computes the return again, and a spinner shows until the answer arrives. If no return can be
computed, the chart shows the reason instead of a curve.

---

## 🧰 Chart buttons

- 📏 **Measure** — see [Measures](measures.md). **Prices** only.
- ✏️ **Edit Rates** — see [Data Editor](data-editor.md). **Prices** only.
- ⚙️ **Aesthetics** — colours, fill, grid and axis ranges, as in [Chart Settings](../chart-settings.md).
- 📊 The **Signals** panel above the chart — see [Signals](signals.md).

---

## 🔗 Related

- ⚙️ **[Chart Settings](../chart-settings.md)** — Chart look and overlay signals
- 📈 **[Signals](signals.md)** — Technical indicators on the chart

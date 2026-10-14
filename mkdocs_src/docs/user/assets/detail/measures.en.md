# 📐 Measures

The Measure tool answers *how much did it change between these two days?* Pick two points on the chart and read the change of the asset, and of the lines drawn with it, between them.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-measures" alt="Asset Measures Panel" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🛠️ Take a measure

1. Click **📏 Add measurement** at the top right of the chart: the **Measures** panel opens below it.
2. Click the **start** point on the chart, then the **end** point.
3. The new measure opens with its table, and the chart draws it in its own colour.

**+ Add measurement** in the panel's header measures the whole chart instead, from its first to its last point: handy on a phone. Each measure's header holds its colour and 🗑️ to remove it; expand the measure to change its dates.

Measures are not saved: reloading the page empties the panel. **Prices** and **Rolling Return** keep separate measures.

---

## 💵 In Prices mode

The table has a row for the asset (a second one in its own currency when the chart is converted) and one for each line drawn on the price axis, such as a comparison asset or a moving average. Next to the **Start** and **End** values:

- **Δ Abs** — the difference $V_{end} - V_{start}$, in the line's unit.
- **Δ %** — the change $\frac{V_{end} - V_{start}}{V_{start}}$ → [Returns & Growth Rates](../../../financial-theory/fundamentals/returns.md)
- **Δ%/yr** — the same change as a yearly rate over the $d$ calendar days between the points, $(1 + \Delta\%)^{365/d} - 1$ → [Returns & Growth Rates](../../../financial-theory/fundamentals/returns.md)

The measure's summary line adds the number of days.

---

## 📈 In Rolling Return mode

The values are already returns, so the table compares them:

- **Start**, **End** — the rolling return on each of the two dates.
- **Δ pp** — End minus Start, in percentage points → [Rolling return over calendar days](../../../financial-theory/fundamentals/returns.md#rolling-return-calendar)
- **Days** — the calendar days between the two points.

---

## 🔗 Related

- 📈 **[Interactive Chart](chart.md)** — Chart controls and date range filtering
- 📊 **[Signals](signals.md)** — Technical indicator overlays

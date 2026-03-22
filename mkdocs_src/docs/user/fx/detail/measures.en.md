# 📐 Measures

The Measures panel provides a **click-to-click measurement tool** for analyzing rate movements between any two points on the chart.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="detail-measures" alt="FX Measures Panel" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🖱️ How to Use

1. Click the **Measures** toggle button (📏) in the chart toolbar
2. The measures panel opens below the chart
3. **Click** on a starting point on the chart — this sets the "from" date and rate
4. **Click** on an ending point — this sets the "to" date and rate
5. The panel immediately shows the computed metrics between the two points

---

## 📊 Computed Metrics

For each measurement, the panel displays:

| Metric | Description | Example |
|--------|-------------|---------|
| **Date Range** | From → To dates | Jan 15, 2024 → Mar 20, 2024 |
| **Days** | Calendar days between the two points | 65 days |
| **Delta (Δ)** | Absolute rate change | +0.0342 |
| **Percentage (%)** | Relative change as percentage | +3.12% |
| **Annualized Return** | Projected annual return based on the measured period | +17.8% p.a. |

!!! info "📚 Annualized Return"
    The annualized return uses the **Compound Annual Growth Rate (CAGR)** formula. For a comprehensive explanation including log returns, compounding, and when to use which method, see:

    :material-book-open-variant: **[Returns & Growth Rates — Financial Theory](../../../financial-theory/returns.md)**

---

## 🔁 Multiple Measurements

You can take multiple measurements in sequence — each new click pair replaces the previous measurement. This lets you quickly compare movements across different time windows.

---

## 💡 Tips

- 🔍 **Zoom in** before measuring for better precision on the click points
- 📰 Use measurements to compare **pre/post event** rate movements (e.g., before and after a central bank announcement)
- ⚠️ The annualized return is most meaningful for periods of **30+ days** — very short periods can produce misleading annualized figures

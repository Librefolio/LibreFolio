# 📐 Measures

The Measure tool compares two available points on the active primary series. **Prices** and **Rolling Return** have separate in-page measure collections and separate summary tables, so switching modes does not mix their rows.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-measures" alt="Asset Measures Panel" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🛠️ How to Use

1. Click the **Measure** button (📐) in the toolbar
2. The measure panel opens below the chart
3. Click a **start point** on the chart
4. Click an **end point** on the chart
5. Expand the new measure to see the table for the current mode

You can also use **Add Measure** to create a measure from the first and last available points in the current chart data.

---

## 💵 Prices Mode Measures

In **Prices** mode, the table reports each measurable primary or comparison series:

| Column | Meaning |
|---|---|
| **Signal** | The price or overlay series being measured |
| **Start** | Value at the start date |
| **End** | Value at the end date |
| **Δ** | Absolute price difference |
| **Δ%** | Relative percentage change between the endpoints |
| **Annualized** | The endpoint change annualized over the selected dates |

The compact measure summary also shows the number of calendar days between the endpoints.

## 📈 Rolling Return Measures

Rolling Return uses its own table and percentage-point semantics:

| Column | Meaning |
|---|---|
| **Signal** | The asset's Rolling Return or an Asset comparison line |
| **Start** | Rolling Return at the start date, shown as a percentage |
| **End** | Rolling Return at the end date, shown as a percentage |
| **Δ pp** | End minus start, shown in percentage points |
| **Days** | Calendar days between the two endpoints |

The Return table deliberately does not reinterpret its percentage endpoints as another percentage change or annualized return.

---

## 🧠 Runtime State

Measure definitions and results are calculated in the browser from the currently rendered series. They stay available while you switch between **Prices** and **Rolling Return** during the current page runtime, but a page reload starts with empty measure tables.

The underlying prices and FX rates are backend-persisted source data. Measurement rows, endpoint calculations, and measure-line styles are runtime-only: they are not written to the backend database or to the chart-settings `localStorage` record.

The visible chart range is separate shared browser state: only its start and end dates are kept in `sessionStorage` for the current tab. Chart settings, the Rolling Return window, and comparison configuration stay in `localStorage`; neither browser store receives measurement rows or computed return/comparison series.

---

## 🔗 Related

- 📈 **[Interactive Chart](chart.md)** — Chart controls and date range filtering
- 📊 **[Signals](signals.md)** — Technical indicator overlays

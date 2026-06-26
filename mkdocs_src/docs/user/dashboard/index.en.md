# 📊 Dashboard

The Dashboard is your **portfolio's command center** — a single screen that tells you what your portfolio is worth, how it's performing, and where your money is allocated.

<div class="lf-screenshot-carousel" data-carousel="carousel-dashboard-main" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
  <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="dashboard" data-name="main" data-title="📈 Main View (Absolute)" alt="Dashboard — Absolute Mode">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="main-pct" data-title="📈 Main View (Percentage)" alt="Dashboard — Percentage Mode">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="allocation-type-now" data-title="📊 Allocation" alt="Dashboard — Allocation">
</div>

---

## 🗂️ Layout

| Section | Location | Contents |
|---------|----------|---------|
| **[KPI Cards](kpi-cards.md)** | Top row | [Net Worth](kpi-cards.md#card-1--net-worth) · [Period P&L](kpi-cards.md#card-2--period-pl) · [Returns](kpi-cards.md#card-3--returns) |
| **[Growth Chart](charts.md#portfolio-growth-chart)** | Middle left | Absolute stacked area + percentage return series |
| **[Allocation Panel](charts.md#allocation-panel)** | Middle right + bottom | Type / Sector / Geography — current and historical |

---

## 🎛️ Date Range & Broker Filter

At the top of the dashboard you can select:

- **Time range** — presets from 1 week to All-Time, or a custom range via the date picker
- **Broker filter** — show all brokers or focus on one or more
- **Target currency** — converts all values into a single currency

!!! tip "Scope matters"

    When you filter to a single broker, cash transfers *to other brokers* become external flows for that scope. This affects [Deposited Capital](../../financial-theory/technical-analysis/performance-metrics/deposited-capital.md) and [P&L](../../financial-theory/technical-analysis/performance-metrics/period-pnl.md) calculations.

---

## 🌡️ Data Quality Banner

If any prices or FX rates are missing on the end date, a banner appears at the top explaining which assets could not be valued. Assets without a price provider (entered manually, such as real-estate crowdfunding projects) are permanently valued at purchase cost — this is intentional and does not generate a warning.

---

## 🔗 In this section

- 💰 **[KPI Cards](kpi-cards.md)** — Net Worth, Period P&L, and Returns explained
- 📊 **[Charts](charts.md)** — Growth Chart and Allocation Panel explained

## 🔗 Related theory

- **[NAV / Net Worth](../../financial-theory/technical-analysis/performance-metrics/nav.md)**
- **[Book Value](../../financial-theory/technical-analysis/performance-metrics/book-value.md)**
- **[Period P&L](../../financial-theory/technical-analysis/performance-metrics/period-pnl.md)**
- **[Deposited Capital & Total P&L](../../financial-theory/technical-analysis/performance-metrics/deposited-capital.md)**
- **[Performance Metrics overview](../../financial-theory/technical-analysis/performance-metrics/index.md)**

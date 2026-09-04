# 📊 Dashboard

The Dashboard is your **portfolio's command center** — a single screen that tells you what your portfolio is worth, how it's performing, and where your money is allocated.

<div class="lf-screenshot-carousel" data-carousel="carousel-dashboard-main" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
  <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="dashboard" data-name="main" data-title="📈 Main View (Absolute)" alt="Dashboard — Absolute Mode">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="main-pct" data-title="📈 Main View (Percentage)" alt="Dashboard — Percentage Mode">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="allocation-type-now" data-title="📊 Allocation" alt="Dashboard — Allocation">
</div>

## 🗂️ Tabbed Layout

The Dashboard interface is organized into three primary tabs, allowing you to switch between different levels of detail:

1. **Overview** (default): Key metrics, cash balances, and visual charts of your portfolio.
2. **[Positions & Analysis](positions.md)**: Open holdings, weights, and detailed tax lot (FIFO) analysis.
3. **Transactions**: Recent operations list with a read-only detail viewer.

---

## 📈 Overview Tab

The Overview tab is the default landing page. It is structured into the following sections:

| Section | Description |
|---------|-------------|
| **[KPI Cards](kpi-cards.md)** | Summary of Net Worth, Period P&L, and rate-of-return metrics. |
| **Cash Balances** | Liquid balances grouped by currency across the active broker scope. |
| **[Growth Chart](charts.md#portfolio-growth-chart)** | Stacked area chart showing asset cost, cash, and returns over time. |
| **[Allocation Panel](charts.md#allocation-panel)** | Donut and historical stacked charts grouped by Type, Sector, and Geography. |

### 🪙 Cash Balances

Directly below the KPI cards, the **Cash Balances** panel displays your total liquid cash aggregated by currency. For example, if you hold USD in broker A and EUR in broker B, both balances will be displayed side-by-side. 

When you apply a broker filter, the cash balances automatically update to reflect only the cash held within the selected brokers.

---

## 🎛️ Date Range, Filters & AI Export

At the top right of the dashboard, you have several controls to customize your view:

- **Time range** — presets from 1 week to All-Time (MAX), or a custom range via the date picker.
- **Broker filter** — filter all metrics to one or more specific brokers.
- **Target currency** — converts all assets and cash balances dynamically into a single selected currency for aggregate viewing.
- **AI Export** (:material-brain:) — opens a clipboard export. Choose **Data
  Snapshot** for factual data only, or an **analysis task** that automatically
  includes its instructions and response contract, then select the **detail
  level** (Compact, Standard, or Full). The backend snapshot follows the active
  broker filter, date range, and target currency; LibreFolio does not contact an
  AI service. See [Portfolio AI Export](../ai-export/portfolio.md) or the
  [AI Export overview](../ai-export/index.md).

!!! tip "Scope matters"

    When you filter to a single broker, cash transfers *to other brokers* become external flows for that scope. This affects [Deposited Capital](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md) and [P&L](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md) calculations.

!!! note "Sharing affects these numbers"

    The dashboard aggregates only the brokers **you have access to**, and every amount from a broker you co-own is **scaled by your ownership share**: an Owner with a 50% share sees half of that broker's value, income, and P&L counted in the totals (a 0% share is valid and contributes nothing). Editors and Viewers — who always carry a 0% share by rule — see the broker's **full** amounts instead. See [Broker Sharing](../brokers/sharing.md) for details.

---

## 🌡️ Data Quality Banner

If any prices or FX rates are missing on the end date, a banner appears at the top explaining which assets could not be valued. Assets without a price provider (entered manually, such as real-estate crowdfunding projects) are permanently valued at purchase cost — this is intentional and does not generate a warning.

---

## 🔗 In this section

- 💰 **[KPI Cards](kpi-cards.md)** — Net Worth, Period P&L, and Returns explained
- 📊 **[Charts](charts.md)** — Growth Chart and Allocation Panel explained
- 🔍 **[Positions & Analysis](positions.md)** — Open positions, table vs. map views, and detailed FIFO tax lot analysis.

## 🔗 Related theory

- **[NAV / Net Worth](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md)**
- **[Book Value](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/book-value.md)**
- **[Period P&L](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md)**
- **[Deposited Capital & Total P&L](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)**
- **[Performance Metrics overview](../../financial-theory/technical-analysis/performance-metrics/index.md)**

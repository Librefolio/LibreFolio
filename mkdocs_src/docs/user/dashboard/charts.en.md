# 📊 Charts

*[⬅️ Back to Dashboard Overview](index.md)*

The chart section sits below the KPI cards and gives you a **historical and structural view** of your portfolio over the selected time range.

---

## 📈 Portfolio Growth Chart

The growth chart shows how your portfolio evolved in value over the selected period. Use the **Abs / %** toggle in the top-right corner to switch between two views.

<div class="lf-screenshot-carousel" data-carousel="carousel-growth" data-carousel-interval="5000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
  <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="dashboard" data-name="main" data-title="📈 Absolute Mode" alt="Growth Chart — Absolute Mode">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="main-pct" data-title="📈 Percentage Mode" alt="Growth Chart — Percentage Mode">
</div>

### ABS mode — absolute values

The chart uses a **stacked area + overlay lines** design:

| Element | Color | Meaning |
|---------|-------|---------|
| Area — **Asset Cost** | Blue | Cost basis of all open positions (average cost × quantity) |
| Area — **Returns** | Emerald | Portfolio returns sitting as liquid cash (interest, realized gains not yet reinvested) |
| Area — **Capital** | Grey-green | Undeployed deposits sitting in cash |
| Line — **[NAV](../../financial-theory/technical-analysis/performance-metrics/nav.md)** | Dark green solid | Total portfolio value at current market prices |
| Line — **[Deposited Capital](../../financial-theory/technical-analysis/performance-metrics/deposited-capital.md)** | Grey dashed | Net external capital contributed over time |

**The gap between the NAV line and the Deposited Capital line = Total P&L** — all gains ever generated, including unrealized gains, realized gains, interest, and dividends, minus fees and taxes.

#### Tooltip breakdown

When you hover over the chart, the tooltip shows:

- **NAV** — total portfolio value at that date
- **Deposited Capital** — net capital you contributed up to that date
- **Total P&L** — the difference (NAV − Deposited Capital)
- **Asset Cost** / **Returns** / **Capital** — the three cash components

!!! tip "Reading income-driven portfolios (P2P, bonds)"

    For portfolios like P2P lending where assets are valued at their purchase price (no live market price), NAV ≈ Asset Cost. The gap between NAV and Deposited Capital may not be visible as a chart gap — but the tooltip **Total P&L** shows the correct value.

    When you reinvest all returns into new assets, the Returns area stays near zero, and the earned income ends up embedded in the Asset Cost area. This is mathematically correct: your cost basis grew because you reinvested profit.

🔗 **Theory**: [Deposited Capital & Total P&L](../../financial-theory/technical-analysis/performance-metrics/deposited-capital.md) · [Cash Decomposition](../../financial-theory/technical-analysis/performance-metrics/deposited-capital.md#three-pool-cash-decomposition)

### % mode — rate of return

All series start at 0% at the beginning of the selected period and show how each return metric evolved:

| Series | What it shows |
|--------|--------------|
| **[MWRR cumulative](../../financial-theory/technical-analysis/performance-metrics/mwrr.md)** | Your personal money-weighted return including deposit timing |
| **[TWRR](../../financial-theory/technical-analysis/performance-metrics/twrr.md)** | Pure asset strategy return, ignoring when you deposited |
| **[ROI](../../financial-theory/technical-analysis/performance-metrics/roi.md)** | Raw return on net invested capital |

The gap between MWRR and TWRR is the [Timing Effect](../../financial-theory/technical-analysis/performance-metrics/timing-effect.md).

!!! note "MWRR unavailable"

    If a **Data Quality banner** appears saying MWRR is unreliable, the MWRR series is hidden from the % chart. The issue typically occurs when the period has very large cash flows relative to the starting portfolio size, causing the mathematical solver to be unstable. ROI and TWRR are always shown.

---

## 🥧 Allocation Panel

The allocation panel shows how your portfolio is distributed at the current point in time and how it evolved historically.

<div class="lf-screenshot-carousel" data-carousel="carousel-alloc" data-carousel-interval="5000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
  <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="dashboard" data-name="allocation-type-now" data-title="By Type (Current)" alt="Allocation by Type — Current">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="allocation-sector-now" data-title="By Sector (Current)" alt="Allocation by Sector — Current">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="allocation-geo-now" data-title="By Geography (Current)" alt="Allocation by Geography — Current">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="allocation-type-history" data-title="By Type (Historical)" alt="Allocation History by Type">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="allocation-sector-history" data-title="By Sector (Historical)" alt="Allocation History by Sector">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="allocation-geo-history" data-title="By Geography (Historical)" alt="Allocation History by Geography">
</div>

### Three dimensions

| Dimension | What it shows |
|-----------|--------------|
| **Type** | ETF, Stock, Bond, Crypto, Real Estate, Liquidity (cash) |
| **Sector** | Industry sector: 💻 Technology, 🏦 Financials, 💊 Health Care, etc. |
| **Geography** | Country or region of each asset's primary listing |

### Now vs. History tabs

- **Now** — Donut chart of current allocation at `date_to`. Hover any slice to see the exact percentage and absolute value.
- **History** — 100% stacked area chart showing how allocation shifted over time. Useful for visualizing portfolio rebalancing across months or years.

### Cash as Liquidity

**Cash** (your broker balance) always appears as the **Liquidity** slice in both Type and Sector views. In the Geography map, cash is not assigned to any country and does not appear.

!!! info "Broker scope"

    When you filter to specific brokers, the allocation shows only the assets and cash within those brokers.

---

## 🔗 Related

- 💰 **[KPI Cards](kpi-cards.md)** — Net Worth, Period P&L, Returns
- 💼 **[NAV / Net Worth](../../financial-theory/technical-analysis/performance-metrics/nav.md)**
- 💸 **[Deposited Capital & Total P&L](../../financial-theory/technical-analysis/performance-metrics/deposited-capital.md)**
- 📈 **[TWRR](../../financial-theory/technical-analysis/performance-metrics/twrr.md)** · **[MWRR](../../financial-theory/technical-analysis/performance-metrics/mwrr.md)** · **[Timing Effect](../../financial-theory/technical-analysis/performance-metrics/timing-effect.md)**

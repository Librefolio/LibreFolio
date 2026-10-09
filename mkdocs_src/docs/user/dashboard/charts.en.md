# 📊 Charts

Below the KPI cards, the **Portfolio Growth** chart and the **Asset Allocation** panel show where your portfolio has been and what it is made of. Both follow the Dashboard's time range and broker filter, and a broker's page shows them for that broker alone.

---

## 📈 Portfolio Growth Chart {: #portfolio-growth-chart }

The growth chart shows how your portfolio evolved over the selected period: the **Abs / % / P&L** toggle in its top-right corner switches between absolute values, rates of return, and the money actually earned.

The chart remembers your last view, P&L sub-view included, in this browser and for each user, and shares it with the broker pages. It starts on **Abs**. Without rate-of-return data, **%** is greyed out and the chart shows **Abs**; your choice comes back the next time you open the chart with data to draw.

<div class="lf-screenshot-carousel" data-carousel="carousel-growth" data-carousel-interval="5000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
  <div class="lf-screenshot-carousel-item is-active chart-crop-container" data-title="📈 Absolute Mode" alt="Growth Chart — Absolute Mode">
     <img class="gallery-img" data-category="dashboard" data-name="main" alt="Growth Chart — Absolute Mode">
  </div>
  <div class="lf-screenshot-carousel-item chart-crop-container" data-title="📈 Percentage Mode" alt="Growth Chart — Percentage Mode">
     <img class="gallery-img" data-category="dashboard" data-name="main-pct" alt="Growth Chart — Percentage Mode">
  </div>
</div>

**Hide amounts** (the eye button in the top bar) turns every amount on the axis and in the tooltips into `•••`; signs, currencies, lines, and colours stay. See [Privacy mode](../settings/preferences.md#privacy-mode).

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="privacy-masked" alt="The Dashboard with Hide amounts on: the crossed-out eye button in the header, the amounts of the KPI cards and of Cash Balances shown as ••• with their sign and currency, the percentages still readable, and the Portfolio Growth axis masked" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 💶 Abs — absolute values

| Element | Color | Meaning |
|---------|-------|---------|
| Area — **Purchase Cost** | Blue | What the positions you hold cost you (average cost × quantity) |
| Area — **Returns** | Emerald | Returns held as cash (dividends, interest, realized gains not yet reinvested) |
| Area — **Capital** | Grey-green | Deposits not yet invested, held as cash |
| Line — **[Net Asset Value](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md)** | Dark green solid | Total portfolio value at current market prices |
| Line — **[Deposited Capital](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)** | Grey dashed | Net external capital contributed over time |

**The gap between the two lines is your Total P&L**: every gain ever made (unrealized, realized, interest, and dividends) minus fees and taxes. The tooltip shows both lines, the Total P&L in green or red, and the breakdown: **Assets at Cost** (the blue area, assets moving between your brokers included), **Returns**, and **Capital**.

**Assets valued at their purchase price**, such as P2P loans with no live market price, keep NAV close to Purchase Cost, so the gap can be thin: read **Total P&L** in the tooltip.

🔗 **Theory**: [Deposited Capital & Total P&L](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md) · [Cash Decomposition](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md#three-pool-cash-model)

### 📉 % — rate of return

Each line is the return accumulated since the start of the selected period:

| Series | What it shows |
|--------|--------------|
| **[MWRR cumulative](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/mwrr.md)** | Your personal money-weighted return including deposit timing |
| **[TWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/twrr.md)** | Pure asset strategy return, ignoring when you deposited |
| **[ROI](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/roi.md)** | Raw return on net invested capital |

The gap between MWRR and TWRR is the [Timing Effect](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/timing-effect.md). If the [Data Quality banner](index.md#data-quality-banner) says **MWRR chart unavailable**, the MWRR line is hidden; TWRR and ROI stay.

### 💰 P&L — the money you made {: #pnl-mode }

**P&L** plots your **Total P&L** (NAV minus deposited capital): how much money the portfolio has actually made since inception. Zooming in does not restart the count at zero.

A second toggle, at the top-left of the plot, picks how to draw it (icons only on a narrow chart):

| View | What it draws | The question it answers |
|------|---------------|------------------------|
| **Line** | Accumulated P&L as a single line | How has my result moved over time? |
| **Candles** | One candle per period, from a day to a year | How wide was the swing inside each period? |
| **Income** | Bars of the cash that actually moved | Where did the money come from, and what did it cost me? |

#### Line — accumulated P&L {: #pnl-line }

- The line is **green above zero and red below**.
- A **dashed grey line** marks the P&L of the first day in view: the gap to it is what you gained or lost since the left edge.

<div class="lf-screenshot-carousel" style="margin: 1.5rem 0 2.5rem 0;">
  <div class="lf-screenshot-carousel-item is-active chart-crop-container" alt="The Portfolio Growth chart in P&L mode, Line view: the Total P&L line in green, the dashed grey line at the P&L of the first day in view, and a dashed line per broker">
     <img class="gallery-img" data-category="dashboard" data-name="growth-pnl-line" alt="The Portfolio Growth chart in P&L mode, Line view: the Total P&L line in green, the dashed grey line at the P&L of the first day in view, and a dashed line per broker">
  </div>
</div>

**Broker lines.** With two or more brokers in scope, each broker gets a dashed line and a tooltip row with its share of the total; the shares add up to the total every day. A share is not the broker's own performance: money in transit counts for the broker it left, so a broker line can jump on a transfer date. With one broker, or on a broker's page, only the total is drawn.

#### Candles — the swing inside the period {: #pnl-candles }

Each period of the [width you pick](#pnl-width) becomes a **candle** made of P&L values, not prices. Its **close** is exactly the Total P&L that **Line** shows for that day.

<div class="lf-screenshot-carousel" style="margin: 1.5rem 0 2.5rem 0;">
  <div class="lf-screenshot-carousel-item is-active chart-crop-container" alt="The Portfolio Growth chart in P&L mode, Candles view at 3D: the synthetic P&L candles, the width buttons from 3D to 6M in the top-right corner of the plot, the period labels on the axis, and the Synthetic caption under the chart">
     <img class="gallery-img" data-category="dashboard" data-name="growth-pnl-candles" alt="The Portfolio Growth chart in P&L mode, Candles view at 3D: the synthetic P&L candles, the width buttons from 3D to 6M in the top-right corner of the plot, the period labels on the axis, and the Synthetic caption under the chart">
  </div>
</div>

!!! warning "Highs and lows are hypothetical"

    A candle's top and bottom add up each asset's own daily high and low, which were not reached at the same moment: that portfolio state may never have existed, as the caption under the chart says (*Synthetic — cross-asset high/low are hypothetical and non-simultaneous*). Read them as how far the portfolio *could* have swung.

Also expect:

- **No volume** — a portfolio's P&L has no traded volume.
- **Thin bodies, long wicks** — open and close are usually close while the summed range is wide.
- **Gaps** — a day on which a held asset could not be valued has no candle rather than a guessed one.

The tooltip gives the period, **Open**, **Close**, **High**, and **Low**, plus a row per broker when two or more are in scope.

#### Income — the cash that actually moved {: #pnl-income }

**Income** leaves valuations aside and plots your real cash flows. Each bar is the **sum** of its period's flows, in up to three columns:

| Column | Bars | What it represents |
|--------|------|--------------------|
| Income and costs | **Dividend** · **Interest** above zero, **Fees & taxes** below it | What the portfolio paid you, and what the activity cost you |
| Deposits | **Deposit** | Fresh money you put in (withdrawals are not drawn) |
| Purchases | **Purchase Cost**, in two zones: **New capital** at the bottom, **Reinvested** on top | What you spent on buys, split by where the money came from |

<div class="lf-screenshot-carousel" style="margin: 1.5rem 0 2.5rem 0;">
  <div class="lf-screenshot-carousel-item is-active chart-crop-container" alt="The Portfolio Growth chart in P&L mode, Income view at 1M: monthly groups of bars for Interest, Fees & taxes below zero, Deposit and Purchase Cost">
     <img class="gallery-img" data-category="dashboard" data-name="growth-pnl-income" alt="The Portfolio Growth chart in P&L mode, Income view at 1M: monthly groups of bars for Interest, Fees & taxes below zero, Deposit and Purchase Cost">
  </div>
</div>

How to read it:

- **New capital or reinvested.** A purchase first spends the returns already held as cash at that broker (**Reinvested**, green as in **Abs**); the rest is **New capital** (blue). Sales are never drawn.
- **Signs are kept.** A negative correction on a past dividend shrinks the dividend bar; fees and taxes stay below zero.
- **It matches the KPIs.** For the same dates and brokers, **Dividend** and **Interest** add up exactly to the **Dividends & interest** row of the [Period P&L card](kpi-cards.md#card-1-period-pl).
- **One legend entry.** Both purchase zones are named **Purchase Cost**: one click hides both, and the **Abs** area of the same name too.
- **Missing exchange rates.** An amount that cannot be converted on its date is left out, not counted as zero; the [Data Quality banner](index.md#data-quality-banner) reports it.

!!! warning "The purchase bars are not the Purchase Cost KPI"

    The bars are a **flow**: what you spent on buys in each period. The **Purchase Cost** row of the [Net Worth card](kpi-cards.md#card-3-net-worth) is a **level**: what the positions you still hold cost you on the end date. Sales and earlier purchases count in the KPI but have no bar.

#### Candle width — 1D to 1Y {: #pnl-width }

In **Candles** and **Income**, the buttons in the top-right corner of the plot, from **1D** to **1Y**, set how much time one candle, or one group of bars, covers. The chart still shows the whole range, and zooming never changes the width.

- **Calendar periods.** **1W** runs from Monday to Sunday, **1M** is a calendar month, **3M** a quarter, **6M** a half-year, **1Y** a year; **3D** and **2W** are fixed blocks of days.
- **Axis labels.** Each label names the start of its period, even one the range covers only in part; months and years appear only where they change, and crowded labels tilt or thin out.
- **Only widths that fit** the chart and the range are offered; **Income** starts at **1W**.
- **Where it starts.** **Candles** take the finest width available; **Income** opens on **1M**, or the nearest width available, each time you enter it. Reloading the page resets the width.
- **Partial periods are faded.** A period the range starts partway through, or a last one cut short by a range ending in the past, is drawn faded, and its tooltip says *Partial: N of M days*. Otherwise, the period in progress is drawn whole, with *In progress: N of M days*.

---

## 🥧 Allocation Panel {: #allocation-panel }

The **Asset Allocation** panel shows how your portfolio is split, today and over time. Pick a dimension with the **By Type**, **By Sector**, and **Geographic** tabs, and a view with the two buttons in the top-right corner: the pie for **Now**, the area chart for **History**.

<div class="lf-screenshot-carousel" data-carousel="carousel-alloc" data-carousel-interval="5000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
  <div class="lf-screenshot-carousel-item is-active alloc-crop-container" data-title="By Type (Current)" alt="Allocation by Type — Current">
     <img class="gallery-img" data-category="dashboard" data-name="allocation-type-now" alt="Allocation by Type — Current">
  </div>
  <div class="lf-screenshot-carousel-item alloc-crop-container" data-title="By Sector (Current)" alt="Allocation by Sector — Current">
     <img class="gallery-img" data-category="dashboard" data-name="allocation-sector-now" alt="Allocation by Sector — Current">
  </div>
  <div class="lf-screenshot-carousel-item alloc-crop-container" data-title="By Geography (Current)" alt="Allocation by Geography — Current">
     <img class="gallery-img" data-category="dashboard" data-name="allocation-geo-now" alt="Allocation by Geography — Current">
  </div>
  <div class="lf-screenshot-carousel-item alloc-crop-container" data-title="By Type (Historical)" alt="Allocation History by Type">
     <img class="gallery-img" data-category="dashboard" data-name="allocation-type-history" alt="Allocation History by Type">
  </div>
  <div class="lf-screenshot-carousel-item alloc-crop-container" data-title="By Sector (Historical)" alt="Allocation History by Sector">
     <img class="gallery-img" data-category="dashboard" data-name="allocation-sector-history" alt="Allocation History by Sector">
  </div>
  <div class="lf-screenshot-carousel-item alloc-crop-container" data-title="By Geography (Historical)" alt="Allocation History by Geography">
     <img class="gallery-img" data-category="dashboard" data-name="allocation-geo-history" alt="Allocation History by Geography">
  </div>
</div>

### 🗂️ Three dimensions

| Tab | What it shows |
|-----|--------------|
| **By Type** | What each holding is — its [asset type](../../financial-theory/instruments/asset-types/index.md), such as Stock, ETF, Bond, Fund, or Crypto — plus **Liquidity** for your cash. Subtypes count with their [family](../../financial-theory/instruments/asset-types/index.md#families-and-subtypes), such as an **Equity ETF** with your other ETFs. |
| **By Sector** | Industry sector: 💻 Technology, 🏦 Financials, 💊 Health Care, etc. |
| **Geographic** | Where your assets are invested, country by country, according to each asset's geographic distribution |

### 🕰️ Now and History

- **Now** — the allocation on the last day of the selected range: a donut for **By Type** and **By Sector**, a world map for **Geographic**. Hover a slice or a country for its percentage and amount. By type, the donut can have [two rings](#allocation-type-rings).
- **History** — a 100% stacked area chart of how the allocation shifted over time, handy to see rebalancing. By type, each family is one area; hovering a date lists its subtypes, such as *Generic ETF* and *Equity ETF*.

The panel remembers the view and the tab in this browser, for each user, and shares them with the broker pages.

### 🍩 Two rings by type {: #allocation-type-rings }

As soon as you hold an asset with a subtype, such as an **Equity ETF** or **Real estate crowdfunding**, the **Now** donut of **By Type** draws two rings:

- **Inner ring** — one slice per family, with its icon where it fits: all your ETFs (generic **ETF** and every subtype) together, **Crowdfund** with **Real estate crowdfunding**, and every other type, **Liquidity** included, on its own. These are the families the asset [Type menu](../assets/create-edit.md#choosing-the-asset-type) groups together.
- **Outer ring** — thinner and set apart, it splits each family that holds a subtype into its members, in shades of the family's colour, captioned where there is room. The generic member reads *Generic ETF* or *Generic Crowdfund*.
- **Hover** a slice for its share and amount; on the outer ring, a last line starting with **↳** gives the whole family's share.
- **The legend** lists families only: clicking one hides its slices on both rings.

With no subtype at all, the donut keeps a single ring.

### 💵 Cash as Liquidity

Your cash is the **Liquidity** slice of **By Type** and **By Sector**; the **Geographic** map leaves it out, as cash belongs to no country. With the broker filter on, the panel shows only the selected brokers' assets and cash.

---

## 🔗 Related

- 💰 **[KPI Cards](kpi-cards.md)** — Net Worth, Period P&L, Returns
- 💼 **[NAV / Net Worth](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md)**
- 💸 **[Deposited Capital & Total P&L](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)**
- 📈 **[TWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/twrr.md)** · **[MWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/mwrr.md)** · **[Timing Effect](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/timing-effect.md)**
- 🛠️ **[Chart internals](../../developer/frontend/components/charts.md)** — for developers: how these charts are built

---

*[⬅️ Back to Dashboard Overview](index.md)*

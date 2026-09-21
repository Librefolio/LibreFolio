# 📊 Charts

The chart section sits below the KPI cards and gives you a **historical and structural view** of your portfolio over the selected time range.

---

## 📈 Portfolio Growth Chart {: #portfolio-growth-chart }

The growth chart shows how your portfolio evolved over the selected period. Use the **Abs / % / P&L** toggle in the top-right corner to switch between the three views: absolute values, rates of return, and the money actually earned.

<div class="lf-screenshot-carousel" data-carousel="carousel-growth" data-carousel-interval="5000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
  <div class="lf-screenshot-carousel-item is-active chart-crop-container" data-title="📈 Absolute Mode" alt="Growth Chart — Absolute Mode">
     <img class="gallery-img" data-category="dashboard" data-name="main" alt="Growth Chart — Absolute Mode">
  </div>
  <div class="lf-screenshot-carousel-item chart-crop-container" data-title="📈 Percentage Mode" alt="Growth Chart — Percentage Mode">
     <img class="gallery-img" data-category="dashboard" data-name="main-pct" alt="Growth Chart — Percentage Mode">
  </div>
</div>

### ABS mode — absolute values

The chart uses a **stacked area + overlay lines** design:

| Element | Color | Meaning |
|---------|-------|---------|
| Area — **Asset Cost** | Blue | Cost basis of all open positions (average cost × quantity) |
| Area — **Returns** | Emerald | Portfolio returns sitting as liquid cash (interest, realized gains not yet reinvested) |
| Area — **Capital** | Grey-green | Undeployed deposits sitting in cash |
| Line — **[NAV](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md)** | Dark green solid | Total portfolio value at current market prices |
| Line — **[Deposited Capital](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)** | Grey dashed | Net external capital contributed over time |

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

🔗 **Theory**: [Deposited Capital & Total P&L](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md) · [Cash Decomposition](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md#three-pool-cash-model)

### % mode — rate of return

All series start at 0% at the beginning of the selected period and show how each return metric evolved:

| Series | What it shows |
|--------|--------------|
| **[MWRR cumulative](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/mwrr.md)** | Your personal money-weighted return including deposit timing |
| **[TWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/twrr.md)** | Pure asset strategy return, ignoring when you deposited |
| **[ROI](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/roi.md)** | Raw return on net invested capital |

The gap between MWRR and TWRR is the [Timing Effect](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/timing-effect.md).

!!! note "MWRR unavailable"

    If a **Data Quality banner** appears saying MWRR is unreliable, the MWRR series is hidden from the % chart. The issue typically occurs when the period has very large cash flows relative to the starting portfolio size, causing the mathematical solver to be unstable. ROI and TWRR are always shown.

### P&L mode — the money you made {: #pnl-mode }

The third position of the toggle drops the valuation narrative and answers a single question: **how much money has this portfolio actually made?** The value plotted is your **Total P&L** — NAV minus deposited capital — counted **since inception** and never re-based.

That last point matters when you zoom: narrowing the view to March does not restart the count at zero in March, it shows the accumulated result as it stood on each day of March. To read "how much did I gain since the left edge of the view", use the dashed reference line described below.

Selecting **P&L** reveals a second picker at the top-left of the plot, with three mutually exclusive submodes:

| Submode | What it draws | The question it answers |
|---------|---------------|------------------------|
| **Line** | Accumulated P&L as a single line | How has my result moved over time? |
| **Candles** | One synthetic candle per day, week, or month | How wide was the swing inside each period? |
| **Income** | Signed bars of the cash that actually moved | Where did the money come from, and what did it cost me? |

On narrow screens the three buttons fold down to their icons only; the labels stay available to screen readers and as hover tooltips.

#### Line — accumulated P&L {: #pnl-line }

A single line of your Total P&L, drawn **green while it is above zero and red while it is below** — so a portfolio that has spent time under water shows it directly.

A **dashed grey horizontal line** marks the P&L you had already accumulated on the first day visible in the view. The gap between the curve and that line is what you gained (or lost) *since the left edge*, while the scale itself stays anchored to the since-inception figure.

When the effective broker scope contains **two or more brokers**, one dashed coloured line per broker is added, each named after its broker in the legend below the chart. On every single day, those broker lines **add up exactly to the total** — they are the additive contributions that compose the total, computed inside the one combined scope.

!!! warning "Broker lines are contributions, not standalone performance"

    A broker line is that broker's share of the combined result — it is **not** the same thing as opening that broker on its own and reading its performance there.

    The difference shows up around internal transfers: value in transit stays attributed to the **departure** broker until it arrives, then moves to the destination. An individual broker line can therefore jump on the transfer dates while the total stays perfectly smooth. That is expected, not a glitch.

With a single broker in scope — and on a broker's own detail page — only the total line is drawn.

Hovering shows the Total P&L for that date, plus one signed row per broker when the broker lines are present.

#### Candles — the swing inside the period {: #pnl-candles }

Instead of one point per period, each period becomes a **candle** whose open, high, low, and close are all expressed in P&L, not in price. The **close is exactly the same Total P&L** the Line submode draws for that date — the two submodes never tell different stories about where you ended up.

The high and the low are a different matter, and this is the one thing to understand before reading them:

!!! warning "The extremes are hypothetical"

    Each asset's own daily high and low are summed across the portfolio, independently of one another. Nothing guarantees that every asset hit its high at the same moment, so the top of a candle is a portfolio state that **may never have existed**. The same applies to the bottom.

    The chart says so permanently, in the caption under the plot:

    > *Synthetic — cross-asset high/low are hypothetical and non-simultaneous, not a real intraday series.*

    A shorter form of the same warning is repeated inside the tooltip. Treat the extremes as an indication of how much the portfolio *could* have swung, never as a measured intraday series.

Three further things to expect:

- **There is no volume.** The panel you may be used to under a price candlestick chart is deliberately absent: a portfolio's P&L has no traded volume of its own, so none is invented.
- **Thin candles are normal here.** Open and close are usually close to each other, while the summed high/low spread is wide — so the bodies look small between long wicks. That is the shape of the data, not a defect.
- **Gaps are honest.** If a held asset could not be valued on a given day, that day has no candle at all rather than a guessed or zeroed one. Assets with no known intraday range contribute a flat open = high = low = close instead of a made-up spread, which is another reason bodies can be thin.

When the chart groups days into weeks or months, the candle opens at the **first day's open**, closes at the **last day's close**, and takes the **highest high** and **lowest low** of the days in between.

Broker lines behave as in the Line submode: with two or more brokers in scope, each broker's closing P&L is overlaid as a dashed line on top of the candles.

The tooltip lists **Open, Close, High, Low** for the period, followed by the broker rows when present.

#### Income — the cash that actually moved {: #pnl-income }

This submode leaves valuations behind entirely and plots your **real, personal cash flows** as bars: only days where something actually happened get a bar, so the chart is deliberately sparse.

Six series are drawn, in three groups:

| Group | Bars | What it represents |
|-------|------|--------------------|
| **Income** (stacked) | Dividend · Interest | Money the portfolio paid you |
| **Costs** | Fees & taxes | What the activity cost you — negative, so it hangs below the axis |
| **Capital** | Deposit | Fresh external money you put in |
| **Purchases** (stacked) | New capital · Reinvested | What you spent on buys that day, split by where the money came from |

The purchases pair is the interesting one: it separates buying with **fresh capital** you deposited from buying with **returns you had already earned** and put back to work. Both halves together equal that day's total purchase outflow.

!!! info "Signed, not absolute"

    Values keep their sign. A negative correction on a past dividend **reduces** the dividend bar rather than being counted as more income, and fees and taxes stay negative instead of being flipped into a positive "cost" magnitude.

    Both asset-linked entries and broker-level ones (a custody fee charged to the account with no asset attached) are counted — each exactly once.

Because of that, the totals reconcile with the KPI cards: over the same window and the same broker scope, the dividend and interest bars add up exactly to the **Dividends & interest** row of the [Period P&L card](kpi-cards.md#card-1-period-pl).

The tooltip shows Dividend and Interest with their **Total** — which covers income only. Fees & taxes, deposits, and purchases are listed below it as separate rows when they are non-zero, precisely because they are not earnings: a deposit does not make you richer, and money spent on a purchase has only changed shape.

No broker lines are drawn in this submode.

When the chart groups days into weeks or months, these bars **add up the days in the group** — unlike the line and the candles, which carry a running level forward, a flow is only meaningful as a sum.

!!! note "When a currency cannot be converted"

    If a transaction cannot be converted into your display currency on its date, it is left out of the sums instead of being silently shown as zero, and the missing currency pair is reported through the usual data-quality channel.

#### The zoom window — 1W / 1M / 1Y / All {: #pnl-zoom }

The buttons in the top-right corner of the plot set how much history is visible: the **last week, month, or year**, or **All** for the full range. They are available in all three P&L submodes.

- It is the **same zoom** you get by dragging or scrolling on the chart, so you can click a preset and then fine-tune it by hand.
- Your choice **survives switching submodes** — pick 1M on the line, switch to candles, and you are still looking at the last month.
- It changes **what you look at, not what is computed**. The values stay counted since inception, and the date range selected at the top of the dashboard still decides which data exists in the first place.

---

## 🥧 Allocation Panel {: #allocation-panel }

The allocation panel shows how your portfolio is distributed at the current point in time and how it evolved historically.

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
- 💼 **[NAV / Net Worth](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md)**
- 💸 **[Deposited Capital & Total P&L](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)**
- 📈 **[TWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/twrr.md)** · **[MWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/mwrr.md)** · **[Timing Effect](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/timing-effect.md)**

---

*[⬅️ Back to Dashboard Overview](index.md)*

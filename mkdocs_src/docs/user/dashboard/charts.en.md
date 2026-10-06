# 📊 Charts

The chart section sits below the KPI cards and gives you a **historical and structural view** of your portfolio over the selected time range.

---

## 📈 Portfolio Growth Chart {: #portfolio-growth-chart }

The growth chart shows how your portfolio evolved over the selected period. Use the **Abs / % / P&L** toggle in the top-right corner to switch between the three views: absolute values, rates of return, and the money actually earned.

LibreFolio remembers the view you last picked — **Abs**, **%**, or **P&L**, and within P&L the **Line**, **Candles**, or **Income** submode — in this browser, separately for each user. The Dashboard and a broker's detail page share that memory, so the view you leave in one is the view you find in the other. Until you pick one, the chart opens on **Abs**, and P&L opens on **Line**.

If you left the chart on **%** but there is no rate-of-return data to draw, the **%** button is disabled and the chart shows **Abs** for now. Your choice is kept: **%** comes back the next time you open the chart with rate-of-return data to show.

<div class="lf-screenshot-carousel" data-carousel="carousel-growth" data-carousel-interval="5000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
  <div class="lf-screenshot-carousel-item is-active chart-crop-container" data-title="📈 Absolute Mode" alt="Growth Chart — Absolute Mode">
     <img class="gallery-img" data-category="dashboard" data-name="main" alt="Growth Chart — Absolute Mode">
  </div>
  <div class="lf-screenshot-carousel-item chart-crop-container" data-title="📈 Percentage Mode" alt="Growth Chart — Percentage Mode">
     <img class="gallery-img" data-category="dashboard" data-name="main-pct" alt="Growth Chart — Percentage Mode">
  </div>
</div>

!!! tip "Hiding the amounts"

    The eye button in the top bar, labelled **Hide amounts** (or **Show amounts** once they are hidden), hides your amounts. This chart follows it straight away, in both directions, without reloading the page:

    - On the vertical axis of **Abs** and **P&L**, each value becomes `•••` or `-•••`: the sign stays, while the `k` or `M` suffix is hidden along with the digits, so not even the order of magnitude shows.
    - In the tooltips, every amount keeps its currency code and its sign; only the digits turn into `•••`. In the **Abs** tooltip, **Assets at Cost**, **Returns**, and **Capital** show `—` when they are zero, whether the amounts are hidden or not.
    - The **%** view shows rates of return, not money, so nothing is hidden there.

    The lines, candles, bars, and their colors stay as they are — green and red still tell a gain from a loss. Only the amounts are hidden.

    The setting belongs to this browser, not to your account: switching to another account in the same browser keeps the amounts hidden.

### ABS mode — absolute values

The chart uses a **stacked area + overlay lines** design:

| Element | Color | Meaning |
|---------|-------|---------|
| Area — **Purchase Cost** | Blue | Cost basis of all open positions (average cost × quantity) |
| Area — **Returns** | Emerald | Portfolio returns sitting as liquid cash (interest, realized gains not yet reinvested) |
| Area — **Capital** | Grey-green | Undeployed deposits sitting in cash |
| Line — **[Net Asset Value](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md)** | Dark green solid | Total portfolio value at current market prices |
| Line — **[Deposited Capital](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)** | Grey dashed | Net external capital contributed over time |

**The gap between the NAV line and the Deposited Capital line = Total P&L** — all gains ever generated, including unrealized gains, realized gains, interest, and dividends, minus fees and taxes.

#### Tooltip breakdown

When you hover over the chart, the tooltip shows, from top to bottom:

- **Net Asset Value**, in bold — total portfolio value at that date
- **Deposited Capital** — net capital you contributed up to that date
- **Total P&L**, in bold — the difference between the two, with its sign: green for a gain, red for a loss. A small reminder line under it spells out the formula, *P&L = NAV − Deposited Capital*.

Then, below a divider, what the portfolio is made of:

- **Assets at Cost** — what the positions you still hold cost you, including assets on their way from one broker to another. It is the blue area, which the legend calls **Purchase Cost**.
- **Returns** and **Capital** — the two cash pools: returns held as cash, and deposits not yet invested.

Each of these last three rows shows `—` when its value is zero.

!!! tip "Reading income-driven portfolios (P2P, bonds)"

    For portfolios like P2P lending where assets are valued at their purchase price (no live market price), NAV ≈ Purchase Cost. The gap between NAV and Deposited Capital may not be visible as a chart gap — but the tooltip **Total P&L** shows the correct value.

    When you reinvest all returns into new assets, the Returns area stays near zero, and the earned income ends up embedded in the Purchase Cost area. This is mathematically correct: your cost basis grew because you reinvested profit.

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
| **Candles** | One synthetic candle per period, of a width you pick — from one day up to a year | How wide was the swing inside each period? |
| **Income** | Bars of the cash that actually moved | Where did the money come from, and what did it cost me? |

When the chart itself is narrow (on a phone, or in a narrow window), the three buttons fold down to their icons only; the labels stay available to screen readers and as hover tooltips.

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

    > *Synthetic — cross-asset high/low are hypothetical and non-simultaneous*

    The caption stays on a single line: when the chart is too narrow to show it whole, it scrolls slowly to reveal the rest (unless your system is set to reduce motion, in which case it stays still).

    Treat the extremes as an indication of how much the portfolio *could* have swung, never as a measured intraday series.

Three further things to expect:

- **There is no volume.** The panel you may be used to under a price candlestick chart is deliberately absent: a portfolio's P&L has no traded volume of its own, so none is invented.
- **Thin candles are normal here.** Open and close are usually close to each other, while the summed high/low spread is wide — so the bodies look small between long wicks. That is the shape of the data, not a defect.
- **Gaps are honest.** If a held asset could not be valued on a given day, that day has no candle at all rather than a guessed or zeroed one. Assets with no known intraday range contribute a flat open = high = low = close instead of a made-up spread, which is another reason bodies can be thin.

When a candle covers several days, it opens at the **first day's open**, closes at the **last day's close**, and takes the **highest high** and **lowest low** of those days. Days without a candle of their own are simply skipped; a period with no valued day at all gets no candle, and its tooltip says *No data available*.

Only the total is drawn as candles, with no broker lines laid over them. Hovering a candle shows its width and the whole calendar period it stands for, such as *1M - 2026-10-01 → 2026-10-31*, then *In progress: N of M days* if the period has not ended yet, or *Partial: N of M days* if it is over and the selected range covers only part of it, and *Value at* the last day with data in the period. At **1D**, the header is just the candle's date, with no span and no *Value at* line. Below come **Open**, **Close**, **High**, **Low** for the period and, when two or more brokers are in scope, one signed row per broker with its P&L at the close of the period.

#### Income — the cash that actually moved {: #pnl-income }

This submode leaves valuations behind entirely and plots your **real, personal cash flows** as bars. Each bar is the **sum** of the flows on the days its period covers — unlike the line and the candles, which carry a running level forward, a flow is only meaningful as a sum. A period in which nothing happened sums to zero, so it has no bar.

Each period gets up to three columns, side by side:

| Column | Bars | What it represents |
|--------|------|--------------------|
| Income and costs | **Dividend** · **Interest** above zero, **Fees & taxes** below it | Money the portfolio paid you, and what the activity cost you. It is a single stack that splits by sign, so fees and taxes hang below the axis. |
| Deposits | **Deposit** | Fresh external money you put in. Only deposits are drawn — withdrawals are not. |
| Purchases | **Purchase Cost**, in two zones: **New capital** at the bottom, **Reinvested** on top | What you spent on buys in that period, split by where the money came from |

The purchase column is the interesting one: it separates buying with **capital you deposited** from buying with **returns you had already earned** and put back to work. When you buy, the returns already held as cash at that broker count as spent first; whatever the purchase needs beyond them is new capital. Each zone wears the colour its money has in the **Abs** view: new capital the blue of the **Purchase Cost** area, reinvested money the green of the **Returns** area. Only purchases of an asset count — sales are never drawn as bars.

The legend shows these six series as five entries: both purchase zones carry the name **Purchase Cost**, so one click hides both. The blue area of the **Abs** view has that same name, and the legend remembers what you hid by name — so hiding **Purchase Cost** in one view hides it in the other too.

!!! info "Signed, not absolute"

    Values keep their sign. A negative correction on a past dividend **reduces** the dividend bar rather than being counted as more income, and fees and taxes stay negative instead of being flipped into a positive "cost" magnitude. Deposits and purchases are amounts you put in or spent, so they are drawn above zero.

    Both asset-linked entries and broker-level ones (a custody fee charged to the account with no asset attached) are counted — each exactly once.

Because of that, the totals reconcile with the KPI cards: over the same window and the same broker scope, the dividend and interest bars add up exactly to the **Dividends & interest** row of the [Period P&L card](kpi-cards.md#card-1-period-pl).

!!! warning "The purchase bars are not the Purchase Cost KPI"

    The bars are **gross purchases**, a **flow**: what you spent on buys in each period. The **Purchase Cost** row of the [Net Worth card](kpi-cards.md#card-3-net-worth) is a **level**: what the positions you still hold on the end date cost you.

    Adding up the bars does not give the KPI. Sales lower the KPI but never appear as bars, and positions bought before the period count in the KPI but have no bar.

Hovering a period shows its width and the whole calendar period, as for the candles, plus *In progress: N of M days* on the period that has not ended yet, or *Partial: N of M days* on a period that is over and that the selected range covers only in part. Unlike the candles, there is no *Value at* line: a sum has no closing value.

Below that, every amount carries its sign. **Dividend** and **Interest** come first, then, under a divider, their **Total** — which covers income only. **Fees & taxes**, **Deposit**, and the purchases follow under a second divider, each only when it is non-zero, precisely because they are not earnings: a deposit does not make you richer, and money spent on a purchase has only changed shape. The purchases show as a bold **Purchase Cost** row with its two halves under it, *↳ New capital* and *↳ Reinvested*.

No broker lines are drawn in this submode.

!!! note "When a currency cannot be converted"

    If a transaction cannot be converted into your display currency on its date, it is left out of the sums instead of being silently shown as zero, and the missing currency pair is reported through the usual data-quality channel.

#### The candle width — 1D to 1Y {: #pnl-width }

In **Candles** and **Income**, a row of buttons in the top-right corner of the plot sets which **calendar period** one candle — or one group of Income bars — covers: **1D**, **3D**, **1W**, **2W**, **1M**, **3M**, **6M**, or **1Y**. The **Line** submode has none: a line has no body to widen.

- **A width, not a time window.** It does not choose how much history you see — the chart still covers the whole selected range; only the number of candles changes.
- **Calendar periods.** Each width is a period of the calendar, not a count of days: **1D** is a day, **1W** a week from Monday to Sunday, **1M** a month from the 1st, **3M** a quarter (January–March, April–June, July–September, October–December), **6M** half a year (January–June or July–December), and **1Y** a calendar year. **3D** and **2W** have no calendar unit: they are fixed blocks of three days and of two weeks — each two-week block starts on a Monday — counted from a fixed starting point, so their edges never move as the days go by. The letters follow the interface language.
- **Only widths that can be drawn.** A width the chart cannot draw at its current size, for the selected range, is removed rather than greyed out. Each candle needs a minimum width on screen, and a width that would leave fewer than three periods is dropped too, except **1D**, which is always offered when it fits. **Income** keeps a visible gap between one period and the next, wider than the small gap between the three bars of a period, so that each group reads on its own; it offers a width only if every bar can still be drawn at least 4.5 pixels wide. That is why its narrowest width depends on the size of the chart: over a nine-month range, it is **2W** in a desktop window, but **1M** on a phone. **Income** never offers a width narrower than **1W**. There is always at least one width to pick.
- **Where it starts.** **Candles** open on the finest width they can draw. **Income** opens on **1M** every time you enter it: when you switch to it from **Line** or **Candles**, when you come back to **P&L** from **Abs** or **%** with Income still selected, and when the page opens on Income. If 1M cannot be drawn, Income opens on the nearest width that can: over a one-month range, for example, that is **2W**, because a month-long range touches only two calendar months — fewer than the three a width needs. Your choice is not remembered when you reload the page.
- **When it changes.** Inside Income, the width you pick stays as long as you remain there, and switching from Income to Candles keeps it: **Candles** and **Income** share the width, except that entering Income opens on 1M. When the width you picked can no longer be drawn — the chart got narrower, or you changed the date range — it moves up to the next wider one that can, or to the widest one left if none is wider.
- **Your view stays put.** Changing the width does not move what you are looking at: the same days stay visible, and only the number of candles changes. Zooming and dragging on the chart still work as usual and never change the width, and the date range at the top of the dashboard still decides which data exists in the first place.

The periods at the two ends of the selected range are often incomplete. Two rules decide how they are drawn:

- **The period in progress is drawn whole.** The period that contains today has not ended yet: its missing days are simply the future, so it is drawn like the others, and its tooltip says how far it has got — *In progress: N of M days*.
- **A partial period is drawn faded.** A period that is over, but that the range covers only in part, would look weaker than the others when it is only shorter. So it is drawn at half opacity, and its tooltip says *Partial: N of M days*. That happens to the period the range starts in, when the range starts partway through it, and to the period it ends in, when a range that ends in the past stops partway through it.

For example, on 6 October, the **YTD** preset at **1M** shows ten whole months, January to October, with October in progress (*In progress: 6 of 31 days*). A three-month range, such as the **3M** preset on the same day, starts on 6 July instead: at **1M**, its July is faded (*Partial: 26 of 31 days*).

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
- **History** — 100% stacked area chart showing how allocation shifted over time. Useful for visualizing portfolio rebalancing across months or years. With the **Type** dimension, each asset family is a single area: all your ETFs together — generic ETFs plus every ETF subtype, such as **Equity ETF** or **Bond ETF** — and **Real estate crowdfunding** together with generic crowdfunding. Hovering a date shows each family's total with its subtypes listed under it, the generic one labelled as in the donut, for example *Generic ETF*.

LibreFolio remembers whether you left the panel on **Now** or **History**, and which dimension you were viewing (Type, Sector, or Geography) — in this browser, separately for each user. The Dashboard and a broker's detail page share that memory. If you left it on **History**, it opens on History and loads its data straight away, just as if you had clicked it.

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

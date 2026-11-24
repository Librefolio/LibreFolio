# 🛡️ Risk Tab

The **Risk** tab of the [Dashboard](index.md) shows how risky your portfolio is, through plain questions — from what really happened to what could happen. It sits between **Positions & Analysis** and **Transactions**, and every broker's page has the same tab for that broker alone.

Each block below follows one pattern: what it answers, a screenshot, its tools and how to read them.

- 📉 **[How Much Can It Hurt?](#how-much-can-it-hurt)** — the losses your portfolio actually went through
- 📈 **[How Does It Move?](#how-does-it-move)** — the positive twin of the first: the best moments of the period, and what the days were like
- 🧩 **[Am I as Diversified as I Think?](#diversification)** — which holdings carry the risk, and which move together
- ⚖️ **[Am I Being Paid for This Risk?](#being-paid)** — return against risk, holding by holding and against a benchmark
- 🔮 **[What If…?](#what-if)** — a past crisis, a shock you choose, or a simulation
- 🚩 **[Notices and Missing Data](#notices)** — what the data lacked, and what to do about it

---

## 📉 How Much Can It Hurt? {: #how-much-can-it-hurt }

How much could you lose, and how bad has it already been? Every figure here is something your portfolio really went through in the period; deposits and withdrawals do not count as gains or losses.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="risk-hurt" alt="The How much can it hurt? block: the A bad day, Thirty bad days and The worst fall cards, each with its amount, and their detail lines (the worst day and when, the worst 30 days and when, the worst fall's dates and how long it lasted, recovery needed, Drawdown at risk, Average beyond the threshold, Ulcer index); then Time spent below the peak, and the Distribution of daily returns with the VaR threshold" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

**Tools shown**

- **A bad day**, **Thirty bad days** — your average loss on the worst 5% of days, or of 30-day stretches → [Conditional Value at Risk](../../financial-theory/technical-analysis/risk-metrics/conditional-value-at-risk.md)
- **VaR threshold** — on *Distribution of daily returns*: the daily loss that only the worst 5% of days went beyond; a dashed line marks it on the chart, and hovering a bar tells how many days fell in it and whether it lies beyond the threshold; the wheel or two fingers zoom into the chart, and with many bars a slider appears under it → [Value at Risk](../../financial-theory/technical-analysis/risk-metrics/value-at-risk.md)
- **The best days** — on the same chart, the right tail in green: the gain that only the best 5% of days went beyond, the mirror of the VaR threshold; the line under the chart says where it starts, and hovering a green bar says it is among the best days
- **The worst day** — under *A bad day*: the single worst day of the period, and when it was → [Worst Realization](../../financial-theory/technical-analysis/risk-metrics/worst-realization.md)
- **The worst 30 days** — under *Thirty bad days*: the worst 30-day stretch the portfolio really went through, and when it was. *Thirty bad days* itself is an average of the worst 5%, which no single stretch ever printed
- **The worst fall** — the deepest drop from a high to a later low, when it began and ended, and how long it lasted → [Max Drawdown](../../financial-theory/technical-analysis/risk-metrics/max-drawdown.md)
- **Drawdown at risk** — how far below its peak the portfolio stood, its worst 5% of days aside → [Drawdown at Risk](../../financial-theory/technical-analysis/risk-metrics/drawdown-at-risk.md)
- **Average beyond the threshold** — how far below its peak it stood, on average, on those worst days → [Conditional Drawdown at Risk](../../financial-theory/technical-analysis/risk-metrics/conditional-drawdown-at-risk.md)
- **Below the peak, today** — how far below its last high the portfolio stands today → [Current Drawdown](../../financial-theory/technical-analysis/risk-metrics/current-drawdown.md)
- **Ulcer index** — under *The worst fall*, beside Drawdown at risk: how deep and how long the falls were; lower is calmer → [Ulcer Index](../../financial-theory/technical-analysis/risk-metrics/ulcer-index.md)

**How to read it**

- **Different horizons**: the cards go from a day to a month to the worst fall, so never add them up.
- **The amount** beside each percentage is that loss applied to your net worth.
- **Every card has the same shape**: a title and a subtitle, the percentage with its amount, then detail rows with the name on the left and the figure on the right. A date is written the way your language writes it.
- **Below the peak, today** appears only while your portfolio is below its last high.
- **The ? and ⓘ icons** next to a figure open its theory page.

---

## 📈 How Does It Move? {: #how-does-it-move }

The other side of *How much can it hurt?*: the best moments of the period, and what the days were like. Each card is the green twin of a red one above, measured on the same days.

**Tools shown**

- **The best day** — the best single day of the period, and when it was; under it, the **Average day**: the average up day and the average down day → [Best Day](../../financial-theory/technical-analysis/risk-metrics/return-shape.md#best-day), [Average Day](../../financial-theory/technical-analysis/risk-metrics/return-shape.md#average-day)
- **Thirty good days** — the best 30 days the portfolio really went through, from one day to another, and when: the twin of *The worst 30 days*. It can be negative: a portfolio that only fell still has a best stretch → [Best 30 Days](../../financial-theory/technical-analysis/risk-metrics/return-shape.md#best-30-days)
- **The largest rally** — the largest rise from a low to a later high, when it began and ended, and how long it lasted: the twin of *The worst fall*. Under it, the **Positive streak**: the longest run of days in a row with a gain → [Largest Rally](../../financial-theory/technical-analysis/risk-metrics/return-shape.md#largest-rally), [Positive Streak](../../financial-theory/technical-analysis/risk-metrics/return-shape.md#positive-streak)
- **What the days were like** — **gains against losses** (Omega): for every 1 lost on the bad days, how many were gained on the good ones (*1.25×* means 1.25 gained for every 1 lost; a bad day is one below your risk-free rate, 0% until you set one) → [Gains Against Losses (Omega)](../../financial-theory/technical-analysis/risk-metrics/omega-ratio.md). Under it:
    - **Positive days** — the share of the days with a gain; a day at exactly zero does not count → [Positive Days](../../financial-theory/technical-analysis/risk-metrics/return-shape.md#positive-days)
    - **Semi-deviation** — how much the portfolio swings on the way down, on a yearly basis, written beside the whole swing it is part of: *9.8% downward · out of a 13.9% swing over the period* means the falls weigh less than the rises. Both come from the same days as the cards → [Downside Deviation](../../financial-theory/technical-analysis/risk-metrics/sortino-ratio.md#downside-deviation)
    - **Below the peak, on average** — how far below its highest level the portfolio stood on an average day: the whole time spent under a peak, not only the worst fall → [Below the Peak, on Average](../../financial-theory/technical-analysis/risk-metrics/return-shape.md#average-drawdown)
    - **Extreme days** — how much more often very large days, up or down, came than a bell curve would give: *1×* is the bell curve, above it the tails are fatter → [Extreme Days](../../financial-theory/technical-analysis/risk-metrics/return-shape.md#extreme-days)

**How to read it**

- **The amount** beside the best day, the thirty good days and the largest rally is that gain applied to your net worth today; the largest rally says so, as the worst fall does.
- **A dash says why**: a period with no gaining day has no best day, no average up day and no streak; one with no losing day has no average down day; one with no day below your risk-free rate has no gains against losses; the line under the figure gives the reason.
- **A rally of 0.0%**, with no dates, means the portfolio never rose from a low in the period: a measured zero, not a missing figure.
- **Volatility, annual return, Sharpe and Sortino** are not repeated here: they are in the table of *Am I being paid for this risk?*, measured on the portfolio as you hold it today, while this block reads the period as you lived it; the swing beside the semi-deviation can therefore differ from that table's volatility, and the semi-deviation's tooltip says so. On an asset's page the two are the same series.

---

## 🧩 Am I as Diversified as I Think? {: #diversification }

Owning many holdings is not the same as being diversified. This block shows which holdings really carry your risk, and which move together so closely that they are the same bet.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="risk-diversification" alt="The Am I as diversified as I think? block: the sentence under the title; the cards How many independent bets do I really hold?, Did spreading the money achieve anything? and How much of me is not measured here?; the holdings with weight, risk contribution and the two-sided bar; and Which of these are the same bet?, with its matrix, The most alike and The ones that offset" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

**Tools shown**

- **How many independent bets do I really hold?** — the effective number of positions: how evenly your money is spread among the positions that have a price — cash and holdings without prices are left out, so it never exceeds their count → [Concentration](../../financial-theory/technical-analysis/risk-metrics/concentration.md)
- **Did spreading the money achieve anything?** — how much your holdings cushion each other: 1 means no benefit, higher means more, up to about √N for N positions → [Concentration](../../financial-theory/technical-analysis/risk-metrics/concentration.md)
- **How much of me is not measured here?** — cash, plus holdings without usable prices → [Data Quality](../../financial-theory/technical-analysis/risk-metrics/data-quality.md#excluded-weight)
- **Weight** and **risk contribution** — each holding's share of your money, and of your risk → [Risk Contribution](../../financial-theory/technical-analysis/risk-metrics/risk-contribution.md)
- **Which of these are the same bet?** — how closely each pair of holdings moves together → [Correlation](../../financial-theory/technical-analysis/risk-metrics/correlation.md)

**How to read it**

- **A long red bar** to the right marks a holding that carries more of your risk than its weight suggests; when one stands out, the sentence under the title names it.
- **In the matrix**, blue pairs move together, so holding both adds little; red pairs move in opposite directions and cushion each other. Its five order buttons — by similarity, type, sector, region and name — are always there; one your holdings have no data for is greyed out and says why when tapped.
- **Hover a square** for its value in words. The lists *The most alike* and *The ones that offset* pick out the pairs worth a look.

---

## ⚖️ Am I Being Paid for This Risk? {: #being-paid }

Risk is worth taking only if it pays. This block sets the return of your portfolio and of each holding against its swings — in a table and in a chart — and, if you choose one, against a benchmark.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="risk-paid" alt="The Am I being paid for this risk? block, compared with MSCI World Index: the table opened by the Portfolio and benchmark rows, with Weight, Volatility, Ann. return, Sortino, Sharpe, Beta and Correlation; the risk/return chart with the dots of the holdings and of the portfolio sized by weight, the benchmark's diamond and the dashed line from the risk-free rate; and the notes under the chart" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

**Tools shown**

- **Volatility** — how much the returns swing over a year → [Volatility](../../financial-theory/technical-analysis/risk-metrics/volatility.md)
- **Ann. return** — the average return, scaled to a year → [Observed Annualization](../../financial-theory/technical-analysis/risk-metrics/observed-annualization.md)
- **Sortino** — the return earned for each unit of downward swings → [Sortino Ratio](../../financial-theory/technical-analysis/risk-metrics/sortino-ratio.md)
- **Sharpe** — the return earned for each unit of swings, up or down → [Sharpe Ratio](../../financial-theory/technical-analysis/risk-metrics/sharpe-ratio.md)
- **Beta** — how much a holding moves when the benchmark moves → [Beta & Active Return](../../financial-theory/technical-analysis/risk-metrics/beta-active-return.md)
- **Correlation** — how closely a holding moves with the benchmark → [Correlation](../../financial-theory/technical-analysis/risk-metrics/correlation.md)
- **Compared with** and the dashed line — your benchmark, and the line between better and worse paid → [Benchmark Selection](../../financial-theory/technical-analysis/risk-metrics/benchmark-selection.md#the-risk-return-line)

**How to read it**

- **Choose a benchmark** in **Compared with** — a tracker of a broad world index is the most meaningful. It applies to every Risk page, and adds the **Beta** and **Correlation** columns.
- **Above the dashed line**, a dot was better paid for its risk than the benchmark — or, with no benchmark, than your portfolio.
- **Click** a column title to sort the table, or a row to find its dot in the chart.
- **The Portfolio row** (*Portfolio, today's holdings*) replays today's holdings, at today's weights, over the period — the title says *on the current composition* — so it is not the history of your trades. Returns come from prices only, without dividends or coupons for now.

---

## 🔮 What If…? {: #what-if }

What would a past crisis, or a shock you imagine, do to the portfolio you hold today — and what could lie ahead? The block starts closed: click its title to open it.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="risk-whatif" alt="The What if…? block open: the Historical replay: Partial notice, Add: Hypothetical shock and Simulation, and the Historical replay box after Run replay, with the Global Financial Crisis preset and its period, the box of the asset left out, the total sentence, and the table with Weight, Return, Contribution, Impact and Effect" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

**Tools shown**

- **Historical replay** — a real past period, applied to your portfolio as it is today → [Historical Replay](../../financial-theory/technical-analysis/risk-metrics/historical-replay.md)
- **Hypothetical shock** — a fall or a rise you assume for each asset class, sector or region → [Hypothetical Shock](../../financial-theory/technical-analysis/risk-metrics/hypothetical-shock.md)
- **Simulation** — a range of possible futures, built from your own history → [Simulation Modes](../../financial-theory/technical-analysis/risk-metrics/simulation-modes.md)

**How to read it**

- **Add a tool** with the **Add:** buttons; its **×** closes it and drops its result. The tools you leave open come back next time, in this browser.
- **Historical replay**: pick a crisis in **Preset**, or your own **Period**, then **Run replay**. Holdings with no prices for that period are left out, and a button may offer a period in which they all have prices.
- **Hypothetical shock**: click a scenario, such as *Equity crash*, to run it; **Show the shock per bucket** lets you change its assumptions.
- **Simulation**: pick a mode — *Reshuffled history* is recommended — and a horizon, in days or as years, months and days (`2y3m5d`), then **Simulate**. Read the cone as a range of possibilities, not a forecast.

!!! note "The simulation depends on the history it reads"

    It does not read the page's period: by default it uses all the history your holdings share, up to today, and the result says which dates and how many observations. Under **Days drawn from** you can choose **A period I choose** instead — a calmer or a rougher stretch of that shared history, never before it and never after today: a start too early moves to where the shared history begins, and the result says so. A holding with less history than the horizon stays out — its weight counts as cash, and the result names it — unless none of them reaches the horizon: then all take part, and when their shared history is shorter than the horizon an amber line says so — see [How Much History the Simulation Reads](../../financial-theory/technical-analysis/risk-metrics/simulation-modes.md#why-beta).

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="risk" data-name="whatif-simulation" alt="The What if…? Simulation box: the model warning, the five modes with Reshuffled history recommended, horizon, paths and seed, and after Simulate the terminal figures, the cone and What this simulation assumed" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🚩 Notices and Missing Data {: #notices }

A risk figure is only as good as the prices behind it. When data is missing or old, the tab says so, and what that changed.

**Tools shown**

- **Data quality** — missing or old prices and rates, and the holdings they leave out → [Data Quality](../../financial-theory/technical-analysis/risk-metrics/data-quality.md)

**How to read it**

- **The banner at the top** lists missing or old prices and exchange rates: fix them with its buttons, or with **Sync** at the top right.
- **A currency pair with no exchange-rate route** gets its own button in the banner, one per pair (tooltip **Add FX pair**): it opens the **Add New Currency Pair** window right there, already filled in with that pair, and the tab recalculates by itself once the pair is saved and its rates are downloaded → [Adding a Currency Pair](../fx/add-pair.md)
- **The notice above the blocks** says which results are partial, and why.
- **A banner inside a block** names a figure that could not be computed, with the reason.
- **A dash (—)** means a figure could not be measured: it never means zero.
- **To try again**, press **Refresh**, or run the What If…? tool again.

---

## 🔎 Good to Know {: #good-to-know }

- **The Dashboard's tab covers your portfolio** — every broker you own with a share above 0%, at your share — over the Dashboard's date range and currency. A broker filter narrows it as it narrows the other tabs: the risk is then the one of the brokers the filter keeps, and a subtitle says so.
- **On a broker's page**, the tab shows the same blocks for that broker alone.
- **Changing the period or the currency** recalculates every block and clears the What If…? results: run them again.
- **The risk-free rate**, beside **Compare with** in the block *Am I being paid for this risk?* (on a single asset's tab, under the line with the period and the currency), is what you could earn without taking risk: 0% until you set it, applied when you press Enter or leave the field. Sharpe and Sortino count the return above it; **Gains / losses** and the semi-deviation count from it, and their sentences name the rate they used. It is one value for every risk page. The ⓘ beside it suggests where to read one: the latest yield of a short government bill → [Sharpe Ratio](../../financial-theory/technical-analysis/risk-metrics/sharpe-ratio.md)
- **Calculation details**, folded at the bottom of each block, shows how much data the figures rest on.

---

## 🔗 Related {: #related }

- 🧪 **[Correlation Tab](../assets/correlation.md)** — the same questions, asked of a selection of assets you choose
- 📚 **[Risk Metrics](../../financial-theory/technical-analysis/risk-metrics/index.md)** — the theory behind every figure; each block's book icon opens it
- 📊 **[Dashboard](index.md)** — the other tabs, the date range, the currency and the broker filter
- 🏦 **[Brokers](../brokers/index.md)** — each broker's page, with its own Risk tab
- 🛠️ **[Technical details](../../developer/frontend/components/features/risk-lab.md#dashboard-risk-tab)** — for developers: how this tab works inside

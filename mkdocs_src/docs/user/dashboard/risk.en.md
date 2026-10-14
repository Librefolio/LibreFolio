# 🛡️ Risk Tab

The **Risk** tab of the [Dashboard](index.md) shows how risky your portfolio is, through four plain questions — from what really happened to what could happen. It sits between **Positions & Analysis** and **Transactions**, and every broker's page has the same tab for that broker alone.

Each block below follows one pattern: what it answers, a screenshot, its tools and how to read them.

- 📉 **[How Much Can It Hurt?](#how-much-can-it-hurt)** — the losses your portfolio actually went through
- 🧩 **[Am I as Diversified as I Think?](#diversification)** — which holdings carry the risk, and which move together
- ⚖️ **[Am I Being Paid for This Risk?](#being-paid)** — return against risk, holding by holding and against a benchmark
- 🔮 **[What If…?](#what-if)** — a past crisis, a shock you choose, or a simulation
- 🚩 **[Notices and Missing Data](#notices)** — what the data lacked, and what to do about it

---

## 📉 How Much Can It Hurt? {: #how-much-can-it-hurt }

How much could you lose, and how bad has it already been? Every figure here is something your portfolio really went through in the period; deposits and withdrawals do not count as gains or losses.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="risk-hurt" alt="The How much can it hurt? block: the A bad day, A bad month and The worst fall cards, each with its amount, and their detail lines (worst day actually seen, how long the fall lasted, recovery needed, Drawdown at risk, Average beyond that threshold); then Time spent below the peak with the Ulcer index, and the Distribution of daily returns with the VaR threshold" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

**Tools shown**

- **A bad day**, **A bad month** — your average loss on the worst 5% of days, or of one-month stretches → [Conditional Value at Risk](../../financial-theory/technical-analysis/risk-metrics/conditional-value-at-risk.md)
- **VaR threshold** — on *Distribution of daily returns*: the daily loss that only the worst 5% of days went beyond → [Value at Risk](../../financial-theory/technical-analysis/risk-metrics/value-at-risk.md)
- **Worst day actually seen** — the single worst day of the period → [Worst Realization](../../financial-theory/technical-analysis/risk-metrics/worst-realization.md)
- **The worst fall** — the deepest drop from a high to a later low → [Max Drawdown](../../financial-theory/technical-analysis/risk-metrics/max-drawdown.md)
- **Drawdown at risk** — how far below its peak the portfolio stood, its worst 5% of days aside → [Drawdown at Risk](../../financial-theory/technical-analysis/risk-metrics/drawdown-at-risk.md)
- **Average beyond that threshold** — how far below its peak it stood, on average, on those worst days → [Conditional Drawdown at Risk](../../financial-theory/technical-analysis/risk-metrics/conditional-drawdown-at-risk.md)
- **Currently down from the peak** — how far below its last high the portfolio stands today → [Current Drawdown](../../financial-theory/technical-analysis/risk-metrics/current-drawdown.md)
- **Ulcer index** — under *Time spent below the peak*: how deep and how long the falls were; lower is calmer → [Ulcer Index](../../financial-theory/technical-analysis/risk-metrics/ulcer-index.md)

**How to read it**

- **Different horizons**: the cards go from a day to a month to the worst fall, so never add them up.
- **The amount** under each percentage is that loss applied to your net worth.
- **Currently down from the peak** appears only while your portfolio is below its last high.
- **The ? and ⓘ icons** next to a figure open its theory page.

---

## 🧩 Am I as Diversified as I Think? {: #diversification }

Owning many holdings is not the same as being diversified. This block shows which holdings really carry your risk, and which move together so closely that they are the same bet.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="risk-diversification" alt="The Am I as diversified as I think? block: the sentence under the title; the cards How many independent bets do I really hold?, Did spreading the money achieve anything? and How much of me is not measured here?; the holdings with weight, risk contribution and the two-sided bar; and Which of these are the same bet?, with its matrix, The most alike and The ones that offset" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

**Tools shown**

- **How many independent bets do I really hold?** — how evenly your money is spread → [Concentration](../../financial-theory/technical-analysis/risk-metrics/concentration.md)
- **Did spreading the money achieve anything?** — how much your holdings cushion each other → [Concentration](../../financial-theory/technical-analysis/risk-metrics/concentration.md)
- **How much of me is not measured here?** — cash, plus holdings without usable prices → [Data Quality](../../financial-theory/technical-analysis/risk-metrics/data-quality.md#excluded-weight)
- **Weight** and **risk contribution** — each holding's share of your money, and of your risk → [Risk Contribution](../../financial-theory/technical-analysis/risk-metrics/risk-contribution.md)
- **Which of these are the same bet?** — how closely each pair of holdings moves together → [Correlation](../../financial-theory/technical-analysis/risk-metrics/correlation.md)

**How to read it**

- **A long red bar** to the right marks a holding that carries more of your risk than its weight suggests; when one stands out, the sentence under the title names it.
- **In the matrix**, blue pairs move together, so holding both adds little; red pairs move in opposite directions and cushion each other.
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
- **The Portfolio row** replays today's holdings, at today's weights, over the period — the title says *on the current composition* — so it is not the history of your trades. Returns come from prices only, without dividends or coupons for now.

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
- **Simulation**: pick a mode — *Reshuffled history* is recommended — and a horizon, then **Simulate**. Read the cone as a range of possibilities, not a forecast.

!!! note "The simulation is still in beta"

    Its outcome depends heavily on how much history the period holds compared with the horizon — see [Why the Simulation Is Still in Beta](../../financial-theory/technical-analysis/risk-metrics/simulation-modes.md#why-beta).

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="risk" data-name="whatif-simulation" alt="The What if…? Simulation box: the beta notice and the model warning, the five modes with Reshuffled history recommended, horizon, paths and seed, and after Simulate the terminal figures, the cone and What this simulation assumed" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🚩 Notices and Missing Data {: #notices }

A risk figure is only as good as the prices behind it. When data is missing or old, the tab says so, and what that changed.

**Tools shown**

- **Data quality** — missing or old prices and rates, and the holdings they leave out → [Data Quality](../../financial-theory/technical-analysis/risk-metrics/data-quality.md)

**How to read it**

- **The banner at the top** lists missing or old prices and exchange rates: fix them with its buttons, or with **Sync** at the top right.
- **The notice above the blocks** says which results are partial, and why.
- **A banner inside a block** names a figure that could not be computed, with the reason.
- **A dash (—)** means a figure could not be measured: it never means zero.
- **To try again**, press **Refresh**, or run the What If…? tool again.

---

## 🔎 Good to Know {: #good-to-know }

- **The Dashboard's tab covers your whole portfolio** — every broker you own with a share above 0% — over the Dashboard's date range and currency. It ignores the broker filter: a subtitle says so, and the amounts under the percentages are hidden while a filter is on.
- **On a broker's page**, the tab shows the same blocks for that broker alone.
- **Changing the period or the currency** recalculates every block and clears the What If…? results: run them again.
- **Calculation details**, folded at the bottom of each block, shows how much data the figures rest on.

---

## 🔗 Related {: #related }

- 🧪 **[Correlation Tab](../assets/correlation.md)** — the same questions, asked of a selection of assets you choose
- 📚 **[Risk Metrics](../../financial-theory/technical-analysis/risk-metrics/index.md)** — the theory behind every figure; each block's book icon opens it
- 📊 **[Dashboard](index.md)** — the other tabs, the date range, the currency and the broker filter
- 🏦 **[Brokers](../brokers/index.md)** — each broker's page, with its own Risk tab
- 🛠️ **[Technical details](../../developer/frontend/components/features/risk-lab.md#dashboard-risk-tab)** — for developers: how this tab works inside

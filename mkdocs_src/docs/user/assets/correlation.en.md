# 🧪 Correlation Tab

The **Correlation** tab of the [Assets page](index.md) asks the same questions of a **selection of assets** you put together — assets you own, assets you only watch, or a broker's holdings. Open it from **Assets** in the sidebar, then the **Correlation** tab in the toolbar. A selection has no weights, so the tab shows percentages and ratios, never money: for your own money, see the Dashboard's [Risk tab](../dashboard/risk.md).

Each block below follows one pattern: what it answers, a screenshot, its tools and how to read them.

- 🧺 **[Building the Selection](#building-the-selection)** — which assets are compared
- 🕸️ **[Correlation](#correlation)** — which of them move together
- 📉 **[How Much Did Each of These Hurt?](#how-much-did-each-hurt)** — the losses of each one
- 📈 **[How Did Each One Move?](#how-did-each-move)** — the best moments of each one, and what its days were like
- ⚖️ **[What Did Each of These Pay for Its Risk?](#what-did-each-pay)** — risk against return
- ⏮️ **[What If…?](#what-if)** — a past episode, replayed
- 🚩 **[Notices and Missing Data](#each-section-speaks-for-itself)** — what the data lacked

---

## 🧺 Building the Selection {: #building-the-selection }

The card at the top answers *which assets are compared?* Each chip is one selected asset, and the tab remembers your selection in this browser.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="risk" data-name="lab-asset-picker" alt="The + panel open over the selection card: search, Type and Currency filters, two assets ticked with Add 2, and, read-only, the assets that cannot be analysed in the period, each with its reason" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

**Tools shown**

- **Eligibility check** — whether an asset has enough prices in the period to be analysed → [Data Quality](../../financial-theory/technical-analysis/risk-metrics/data-quality.md)

**How to read it**

- **Add assets with the +**, remove one with its **×**, or change many at once with **Select all**, **Deselect all**, **Invert** and **My assets** — up to **100 assets**.
- **The counter** — *3 in the analysis, of 42 that can be analysed* — counts the selected assets being analysed, out of all those that could be over the period set in the toolbar.
- **A dashed chip** cannot be analysed in this period: it stays selected, but out of the results. **An amber chip** is analysed, with a warning. Hover or tap a chip to read why.
- **If the period leaves some assets without prices**, an amber strip offers **Use the period in which all have prices**, which moves the page's dates to fit them all.

---

## 🕸️ Correlation {: #correlation }

This section answers *which of these move together?* — to spot the assets that are really the same bet, and any that cushion the others.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="risk" data-name="lab-correlation" alt="The Correlation section with five assets: the triangular matrix with its legend, the five order buttons and the type, sector and region badges; The most alike pairs RE Loan Roma with RE Loan Milano at 0.94, near-identical, and The ones that offset is empty" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

**Tools shown**

- **Correlation coefficient (ρ)** — how closely two assets moved together, from −1 (always opposite) to +1 (always together) → [Correlation](../../financial-theory/technical-analysis/risk-metrics/correlation.md#interpretation)
- **Order by similarity** — the default order: closely linked assets sit side by side, so redundant groups show up as blocks → [Correlation](../../financial-theory/technical-analysis/risk-metrics/correlation.md#why-the-matrix-answers-am-i-diversified)

**How to read it**

- **One square per pair**: blue when the two assets move together, red when they move in opposite directions, grey when they move independently. Hover or tap it for the value in words.
- **Start from the two lists**: **The most alike** names the pairs that are almost the same exposure, **The ones that offset** the pairs that cushion each other. An empty list is a finding. Click a pair to find it in the matrix.
- **A dash is not a zero**: the pair could not be measured — too little history, or a price that never moved.
- **The order buttons** rearrange the matrix; they never change a value. All five are always there — by similarity, type, sector, region and name; one the selection has no data for is greyed out, and tapping it says why: no type, sector or region known for these assets, or their details still loading or not loaded — reload the page to try again.
- **Above the matrix**, one row of badges per type, sector and region tells what the selection holds, each group with how many assets it covers.

---

## 📉 How Much Did Each of These Hurt? {: #how-much-did-each-hurt }

This section puts every asset on the same scale of harm: its worst losses in the period, and how far it still stands below its peak.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="risk" data-name="lab-hurt-table" alt="The How much did each of these hurt? table: one row per asset with Bad day, Bad month, Worst fall and how long it lasted, Below peak now and Rise to peak" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

**Tools shown**

- **Bad day** — the average loss on the worst 5% of days (CVaR at 95%) → [Conditional Value at Risk](../../financial-theory/technical-analysis/risk-metrics/conditional-value-at-risk.md)
- **Bad month** — the same over real one-month stretches → [Conditional Value at Risk](../../financial-theory/technical-analysis/risk-metrics/conditional-value-at-risk.md)
- **Worst fall** — the deepest drop from a peak; *lasted N d* counts the days until the asset was back there, or until the end of the period → [Max Drawdown](../../financial-theory/technical-analysis/risk-metrics/max-drawdown.md)
- **Below peak now** — how far it stands below its highest level in the period → [Current Drawdown](../../financial-theory/technical-analysis/risk-metrics/current-drawdown.md)
- **Rise to peak** — the gain needed to get back there: 20% below takes +25% → [What It Takes to Get Back](../../financial-theory/technical-analysis/risk-metrics/current-drawdown.md#what-it-takes-to-get-back)

**How to read it**

- **Each column is its own horizon**, from a day to the whole period: compare the assets down a column, never add the columns up.
- **Not a ranking**: the table opens in your selection's order. Click a column title to sort it, or hover it for what it measures.
- **On a short period**, **Bad day** and **Bad month** can stay empty while the drawdown columns are filled: they need more history.

---

## 📈 How Did Each One Move? {: #how-did-each-move }

This section is the other side of the one above: for each selected asset, its best moments over the period and what its days were like.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="risk" data-name="lab-move-table" alt="The How did each one move? table: one row per asset with Best day, Best 30 days and Largest rally with their dates, Gains / losses, Positive days and Semi-dev." style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

**Tools shown**

- **Best day** — the best single day of the period, with its date under the figure → [Best Day](../../financial-theory/technical-analysis/risk-metrics/return-shape.md#best-day)
- **Best 30 days** — the best 30 days the asset really went through, from one day to another, with the dates: the twin of **Bad month**, read on the same overlapping one-month stretches. It can be negative: an asset that only fell still has a best stretch → [Best 30 Days](../../financial-theory/technical-analysis/risk-metrics/return-shape.md#best-30-days)
- **Largest rally** — the largest rise from a low to a later high, with its dates and how long it lasted: the twin of **Worst fall** → [Largest Rally](../../financial-theory/technical-analysis/risk-metrics/return-shape.md#largest-rally)
- **Gains / losses** — for every euro lost on the bad days, how many were gained on the good ones: *1.22×* means 1.22 gained for every 1 lost. A bad day is one below your risk-free rate, 0% until you set one → [Gains Against Losses (Omega)](../../financial-theory/technical-analysis/risk-metrics/omega-ratio.md)
- **Positive days** — the share of the days with a gain; a day at exactly zero does not count → [Positive Days](../../financial-theory/technical-analysis/risk-metrics/return-shape.md#positive-days)
- **Semi-dev.** — the semi-deviation: how much the asset swings on the way down, on a yearly basis, in the same unit as the volatility → [Downside Deviation](../../financial-theory/technical-analysis/risk-metrics/sortino-ratio.md#downside-deviation)

Four more columns are hidden at first: open the column toggle in the section's header, beside the manual icon, to show them.

- **Average day ±** — the average up day and the average down day → [Average Day](../../financial-theory/technical-analysis/risk-metrics/return-shape.md#average-day)
- **Positive streak** — the longest run of days in a row with a gain, with its dates → [Positive Streak](../../financial-theory/technical-analysis/risk-metrics/return-shape.md#positive-streak)
- **Below peak, avg.** — how far below its highest level the asset stood on an average day of the period: the whole time spent under a peak, not only the worst fall. An asset that never fell shows 0.0% → [Below the Peak, on Average](../../financial-theory/technical-analysis/risk-metrics/return-shape.md#average-drawdown)
- **Extreme days** — how much more often very large days, up or down, came than a bell curve would give: *1×* is the bell curve, *2.4×* means fatter tails → [Extreme Days](../../financial-theory/technical-analysis/risk-metrics/return-shape.md#extreme-days)

**How to read it**

- **Compare the assets down a column**, never add the columns up: a day, 30 days and the whole period are different horizons.
- **Not a ranking**: the table opens in your selection's order. Click a column title to sort it, or hover it for what it measures.
- **A dash says why.** Hover or tap it: an asset that never gained in the period has no best day, no average up day and no streak; one with no losing day has no average down day; one with no day below your risk-free rate has no **Gains / losses**; one whose price never moved has no **Extreme days**.
- **An asset that never rose** shows **0.0%** under **Largest rally**, with no dates: a measured zero, not a missing figure.
- **On a short period**, **Largest rally** and **Below peak, avg.** can be the only figures filled: the other columns need more history.
- **Same days as the table above.** Every figure is measured over the same period as *How much did each of these hurt?*, and choosing a benchmark under *Compared with* never changes this table.

---

## ⚖️ What Did Each of These Pay for Its Risk? {: #what-did-each-pay }

This section sets risk against reward — how much each asset swung, and what it returned on average per year — in a table and a chart. With a benchmark chosen under *Compared with*, it also shows how each asset moved with it.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="risk" data-name="lab-risk-return" alt="What did each of these pay for its risk? with S&P 500 as the benchmark: its tinted row opening the table, the period line, and the chart with the asset circles, the benchmark's diamond and the dashed line" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

**Tools shown**

- **Volatility** — how much the returns swung, on a yearly basis → [Volatility](../../financial-theory/technical-analysis/risk-metrics/volatility.md)
- **Ann. return** — the *average annual return*: the period's average return, scaled to a year → [Observed Annualization](../../financial-theory/technical-analysis/risk-metrics/observed-annualization.md)
- **Sortino** — the return earned per unit of downward swing → [Sortino Ratio](../../financial-theory/technical-analysis/risk-metrics/sortino-ratio.md)
- **Sharpe** — the return earned per unit of volatility → [Sharpe Ratio](../../financial-theory/technical-analysis/risk-metrics/sharpe-ratio.md)
- **Beta** — with a benchmark: how much the asset moved when the benchmark moved → [Beta & Active Return](../../financial-theory/technical-analysis/risk-metrics/beta-active-return.md#interpretation)
- **Correlation** — with a benchmark: how closely the two moved together → [Benchmark Selection](../../financial-theory/technical-analysis/risk-metrics/benchmark-selection.md#interpretation)
- **Risk/return line** — with a benchmark: the dashed line drawn through it on the chart → [The Risk/Return Line](../../financial-theory/technical-analysis/risk-metrics/benchmark-selection.md#the-risk-return-line)

**How to read it**

- **Not a ranking**: the table opens with the benchmark's row, then your selection in its own order. Click a column title to sort it.
- **The line under the table** gives the exact period behind the figures, and says when it is shorter than yours — usually because of an asset with a shorter history.
- **On the chart**, further right means more swing and higher means more average return; the benchmark is the diamond. A circle above the dashed line was better paid for its risk than the benchmark. Click a row or a circle to highlight that asset in both.

!!! warning "The average annual return is not the return you lived through"

    On a very volatile asset, the return actually lived through is lower: do not read the height of a dot as what the asset earned. It also comes from prices alone — coupons and dividends are not included yet.

### 🎯 Choosing the Benchmark {: #choosing-the-benchmark }

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="risk" data-name="lab-benchmark-picker" alt="The Compared with picker open: search, Type and Currency filters, the usable assets, then, read-only, those not usable over this period, each with its reason" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

- **One benchmark for every risk page**: your choice under *Compared with* also applies to the Dashboard, broker and asset risk pages, so that they stay comparable.
- **Its row opens the table**, with a dash under **Beta** and **Correlation**: the benchmark is not compared with itself. It may also be one of your selected assets.
- **Assets that cannot be measured over the period** are listed apart in the picker, read-only. A benchmark among them stays chosen but is not used until you pick a period that suits it.

---

## ⏮️ What If…? {: #what-if }

This section answers *how did each of these come through a real past episode?* — a built-in crisis or a period you choose, replayed with real returns. Click its title to open it. Only the historical replay is offered: a hypothetical shock or a simulation would need weights.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="risk" data-name="lab-replay" alt="What if…? after Run replay: the box of assets left out, grouped by reason, with the button that replays the shorter period, above the table with Return and Effect" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

**Tools shown**

- **Historical replay** — each asset's real return over a past period → [Historical Replay](../../financial-theory/technical-analysis/risk-metrics/historical-replay.md)

**How to read it**

- **Choose a Preset**, such as the *Global Financial Crisis*, or set the **Period**, then press **Run replay**. Changing the selection or the page's dates clears the result.
- **The table** shows each asset's **Return**, worst first, with a bar: red for a loss, green for a gain. There is no total: a selection has no weights to add up.
- **Assets without prices at the ends of the period** are left out and listed above the table, with the reason. When possible, a button replays the shorter period in which they all have prices.

---

## 🚩 Notices and Missing Data {: #each-section-speaks-for-itself }

When something is wrong with the data, the tab says so once, right below the selection card, and names the results it affects.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="risk" data-name="lab-notice" alt="Top of the Correlation tab: the folded data-quality banner, the notice Some results are partial with its Measurements affected badges, and the Correlation section's amber banner Unavailable for the selected data" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

**Tools shown**

- **Data quality** — missing or outdated prices and exchange rates, and the results they make partial → [Data Quality](../../financial-theory/technical-analysis/risk-metrics/data-quality.md)

**How to read it**

- **The data-quality banner** lists what to fix, each problem with its action, such as **Sync prices** or **Sync rates**. Click it to open the list.
- **A currency pair with no exchange-rate route** gets its own button in that banner, one per pair (tooltip **Add FX pair**): it opens the **Add New Currency Pair** window right there, already filled in with that pair, and the analysis recalculates by itself once the pair is saved and its rates are downloaded → [Adding a Currency Pair](../fx/add-pair.md)
- **The notice** below it names the **partial** results and their cause. A partial result still shows its figures: read them with that cause in mind.
- **A section's own amber banner** means a result did not come back at all, often because the period is too short: choose a longer one, or sync the prices.
- **What if…?** reports its own problems inside its section.

---

## 🔎 Good to Know {: #reading-the-numbers }

- **One period for all the assets.** Every figure covers the same days for every selected asset, so the rows can be compared. An asset with a shorter history shortens that period for all of them, and their figures change: this is expected → [Data Quality](../../financial-theory/technical-analysis/risk-metrics/data-quality.md#alignment-what-missing-data-actually-costs)
- **One currency.** Returns are measured in your **Default Currency**, set in [Preferences](../settings/preferences.md) (the instance's default if you never chose one), exchange-rate moves included.
- **A dash is not a zero.** The figure could not be measured for that asset over this period; hover or tap it to read why.
- **The risk-free rate**, beside **Compare with**, is what you could earn without taking risk: 0% until you set it, applied when you press Enter or leave the field. Sharpe and Sortino count the return above it; **Gains / losses** and the semi-deviation count from it, and their sentences name the rate they used. It is one value for every risk page. The ⓘ beside it suggests where to read one: the latest yield of a short government bill → [Sharpe Ratio](../../financial-theory/technical-analysis/risk-metrics/sharpe-ratio.md)
- **Another page, another figure.** Another page or another selection measures over different days: compare figures only when they cover the same period.

---

## 🔗 Related {: #related }

- 📋 **[Asset List](index.md)** — the Assets tab, its toolbar and its date range
- 🛡️ **[Dashboard Risk Tab](../dashboard/risk.md)** — the same questions, for your own portfolio
- 📊 **[Risk Metrics](../../financial-theory/technical-analysis/risk-metrics/index.md)** — the theory behind every section of this tab
- 🛠️ **[Technical details](../../developer/frontend/components/features/risk-lab.md)** — for developers: how this tab works inside

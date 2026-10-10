# 🧪 Correlation Tab

The **Correlation** tab of the [Assets page](index.md) asks the same questions of a **selection of assets** you put together — assets you own, assets you only watch, or a broker's holdings. Open it from **Assets** in the sidebar, then the **Correlation** tab in the toolbar. A selection has no weights, so the tab shows percentages and ratios, never money: for your own money, see the Dashboard's [Risk tab](../dashboard/risk.md).

Each block below follows one pattern: what it answers, a screenshot, its tools and how to read them.

- 🧺 **[Building the Selection](#building-the-selection)** — which assets are compared
- 🕸️ **[Correlation](#correlation)** — which of them move together
- 📉 **[How Much Did Each of These Hurt?](#how-much-did-each-hurt)** — the losses of each one
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
    <img class="gallery-img" data-category="risk" data-name="lab-correlation" alt="The Correlation section with five assets: the triangular matrix with its legend, order buttons and sector and region badges; The most alike pairs RE Loan Roma with RE Loan Milano at 0.94, near-identical, and The ones that offset is empty" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

**Tools shown**

- **Correlation coefficient (ρ)** — how closely two assets moved together, from −1 (always opposite) to +1 (always together) → [Correlation](../../financial-theory/technical-analysis/risk-metrics/correlation.md#interpretation)
- **Order by similarity** — the default order: closely linked assets sit side by side, so redundant groups show up as blocks → [Correlation](../../financial-theory/technical-analysis/risk-metrics/correlation.md#why-the-matrix-answers-am-i-diversified)

**How to read it**

- **One square per pair**: blue when the two assets move together, red when they move in opposite directions, pale when they move independently. Hover or tap it for the value in words.
- **Start from the two lists**: **The most alike** names the pairs that are almost the same exposure, **The ones that offset** the pairs that cushion each other. An empty list is a finding. Click a pair to find it in the matrix.
- **A dash is not a zero**: the pair could not be measured — too little history, or a price that never moved.
- **The order buttons** rearrange the matrix; they never change a value.

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
- **The notice** below it names the **partial** results and their cause. A partial result still shows its figures: read them with that cause in mind.
- **A section's own amber banner** means a result did not come back at all, often because the period is too short: choose a longer one, or sync the prices.
- **What if…?** reports its own problems inside its section.

---

## 🔎 Good to Know {: #reading-the-numbers }

- **One period for all the assets.** Every figure covers the same days for every selected asset, so the rows can be compared. An asset with a shorter history shortens that period for all of them, and their figures change: this is expected → [Data Quality](../../financial-theory/technical-analysis/risk-metrics/data-quality.md#alignment-what-missing-data-actually-costs)
- **One currency.** Returns are measured in your **Default Currency**, set in [Preferences](../settings/preferences.md) (the instance's default if you never chose one), exchange-rate moves included.
- **A dash is not a zero.** The figure could not be measured for that asset over this period; hover or tap it to read why.
- **Another page, another figure.** Another page or another selection measures over different days: compare figures only when they cover the same period.

---

## 🔗 Related {: #related }

- 📋 **[Asset List](index.md)** — the Assets tab, its toolbar and its date range
- 🛡️ **[Dashboard Risk Tab](../dashboard/risk.md)** — the same questions, for your own portfolio
- 📊 **[Risk Metrics](../../financial-theory/technical-analysis/risk-metrics/index.md)** — the theory behind every section of this tab
- 🛠️ **[Technical details](../../developer/frontend/components/features/risk-lab.md)** — for developers: how this tab works inside

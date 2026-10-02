# 🧪 Correlation Tab

The **Correlation** tab of the [Assets page](index.md) is a small laboratory. Instead of your portfolio, it examines a **selection of assets** that you put together — assets you own, assets you only watch, or the holdings of a broker — and asks the same questions of each of them: which of them move together, how much each one hurt, what each one paid for the risk it carried, and how each one came through a real past episode.

To open it, go to **Assets** in the sidebar and switch from the **Assets** tab to the **Correlation** tab in the toolbar.

!!! info "Percentages and ratios only — no money, by design"

    A selection has no weights: it says *which* assets, never *how much* of each. Without weights there is nothing to add up, so **no amount of money appears anywhere on this tab**. Every result is a percentage or a ratio, plus a few durations in days and observation counts. Questions about your own money are answered by the **Risk** tab of the Dashboard, which works from your actual positions.

---

## 🧺 Building the Selection {: #building-the-selection }

The panel at the top of the tab holds the selection: one chip per asset, and a counter such as *3 selected of 42*. As soon as one asset is selected, the [four sections](#the-four-sections) appear below the panel; with an empty selection, the tab asks you to *Select at least one asset*.

### 🚪 What the Tab Opens With {: #what-the-tab-opens-with }

The tab never opens on an arbitrary block of assets. It starts from the first of these that applies:

1. **Your last selection**, remembered in this browser — minus any asset deleted or merged since.
2. **Your assets** — those with transactions in brokers you own, the ones the Assets tab lists under *Your assets*.
3. **A small starting set** — the six active assets with the most transactions, when you own none.

A selection holds at most **100 assets**. That limit is a ceiling, not a starting point: the tab opens on it only if you left the selection full last time or own at least 100 assets. Every change you make is remembered as you go, so your next visit starts where this one ended.

### ➕ Adding and Removing Assets {: #adding-and-removing-assets }

- **Add asset to matrix** searches the assets of the list and adds the one you pick.
- The **×** on a chip removes that asset.
- At 100 assets, the picker and **Select all** are disabled, and a note says that the limit has been reached.

### 🧰 Bulk Actions {: #bulk-actions }

Four buttons change many assets at once:

| Button | What it does |
|---|---|
| **Select all** | Adds every asset that matches the current filters — archived ones included — up to the limit |
| **Deselect all** | Removes the assets that match the current filters; the others stay selected |
| **Invert** | Among the assets that match the current filters, the selected ones leave and the others join |
| **My assets** | Resets the selection to your own assets, ignoring the filters |

### 🏷️ Type and Currency Filters {: #type-and-currency-filters }

The **Type** and **Currency** chips narrow the assets that **Select all**, **Deselect all** and **Invert** act on, and the total shown in the counter. They never remove an asset that is already selected, and with nothing chosen they mean *every type* and *every currency*. **Clear filters** switches them all off.

!!! note "The toolbar filters belong to the Assets tab"

    The search box and the type, currency and archived filters of the page toolbar stay visible on this tab, but they do not apply here: the Correlation tab always works from the full asset list, through its own filters described above. The toolbar's **date range** is the exception — it sets the window the tab's figures are measured over (see [One Shared Window](#one-shared-window)).

### 🏦 Preloading a Broker's Assets {: #preloading-a-brokers-assets }

**Preload the assets of…** is a shortcut, not a filter. Choose a broker you can access, and the selection is **replaced** by the assets that broker holds at the end of the page's date range (up to 100). From there you can add and remove assets freely; choosing **Choose a broker…** again leaves the selection as it is.

!!! warning "A chosen broker reloads with the date range"

    While a broker stays chosen in that control, changing the page's date range loads its assets again and replaces the selection — including any change you made by hand.

---

## 🧭 The Four Sections {: #the-four-sections }

Below the selection, four sections each ask one question of every selected asset, in this order. The first three are always open; the last one starts closed.

### 🕸️ Correlation {: #correlation }

The first section, **Correlation**, answers *which of these move together?* It holds a matrix of Pearson correlation coefficients, computed on returns in the tab's currency, and beside it a short list of the pairs worth looking at.

- **Each pair appears once.** The diagonal — where every asset correlates perfectly with itself — and the mirrored upper half are left out.
- **Hover a square** to read both asset names, the coefficient ρ with its reading in words, and the observations behind it. With up to 12 assets, the coefficient is also printed inside each square.
- **Matrix order**: **By similarity**, the default, places assets that move together side by side, so groups of redundant assets show up as blocks; **By name** turns that grouping off.

The reading in words follows the coefficient:

| Coefficient ρ | Reading shown |
|---|---|
| Above 0.7 | they move together |
| From 0.3 to 0.7 | they move together in part |
| From 0 up to 0.3 | they move independently |
| Below 0 | they move in opposite directions |

Beside the matrix, two lists put the answer into words:

- **The most alike** — the pairs with the highest positive correlation, highest first. A pair at 0.9 or above is flagged **near-identical**: two products bought for what is really a single exposure.
- **The ones that offset** — the pairs that move in opposite directions, most negative first. This list is often empty, and it says so: an empty list is a finding, not a missing result.

With more than 20 assets the matrix becomes too dense to read: on wide screens the lists move ahead of it, and they show up to eight pairs instead of five.

The matrix needs at least two assets to show a pair. When a square has no coefficient, its tooltip says why: **Insufficient history** when the window holds fewer than 20 observations, or **Undefined** when an asset's price did not move at all over the window. See [Correlation](../../financial-theory/technical-analysis/risk-metrics/correlation.md) for how the coefficient is computed and what it cannot see.

### 📉 How Much Did Each of These Hurt? {: #how-much-did-each-hurt }

The second section, **How much did each of these hurt?**, puts every selected asset on the same scale of harm. Each asset gets a row, headed by its icon and its name on one line — a name too long to fit scrolls by itself — and the columns run from the shortest horizon to the longest:

| Column | What it tells you |
|---|---|
| **Bad day** | The average loss on the worst 5% of days (CVaR 95%, one day) |
| **Bad month** | The same over every run of 30 calendar days, compounded from real returns — not scaled up from the bad day. Those 30 days hold about 21 observations when the tab counts market days only, and 30 when it counts every day (see [One Shared Window](#one-shared-window)) |
| **Worst fall** | The deepest drop from a peak to a later low within the window. The line under it, *lasted N d*, counts the calendar days from that peak until the asset was back at it — or until the end of the window, if it has not recovered |
| **Below peak now** | How far the asset stands, at the end of the window, below the highest level it reached within the window |
| **Rise to peak** | The gain it still needs to get back to that peak |

**Rise to peak** is there to teach an asymmetry: the way back is steeper than the way down, because the rise starts from a smaller base. An asset **20% below its peak needs +25%** to return to it, not +20%.

Every loss is drawn in the same red for every asset, and the page never ranks the assets by itself: the table opens in the order of the selection, and only a click on a column title sorts it, as in the [next section](#what-did-each-pay). Each figure's title explains it in a tooltip — hover it, or tap it on a touch screen — but links nowhere: the book icon in the section's header opens the manual's [Risk Metrics](../../financial-theory/technical-analysis/risk-metrics/index.md) pages, the eye icon beside it shows or hides columns, and the theory behind the columns is in [Conditional Value at Risk](../../financial-theory/technical-analysis/risk-metrics/conditional-value-at-risk.md), [Max Drawdown](../../financial-theory/technical-analysis/risk-metrics/max-drawdown.md) and [Current Drawdown](../../financial-theory/technical-analysis/risk-metrics/current-drawdown.md).

### ⚖️ What Did Each of These Pay for Its Risk? {: #what-did-each-pay }

The third section, **What did each of these pay for its risk?**, sets risk against reward, asset by asset: first in a table, then in a chart of the same figures.

- **The table** gives the figures of every asset — **Volatility**, **Average annual return**, **Sortino** and **Sharpe** — one row per asset, named as in the previous section. Sortino measures the return per unit of downside risk, Sharpe per unit of total volatility. Each figure's title explains it in a tooltip: hover it, or tap it on a touch screen. The eye icon beside the section's book icon shows or hides columns.
- **Only you sort it.** The table opens in the order of the selection. A click on a column title sorts by that figure — ascending, then descending, then back to the selection's order — and [dashes](#a-dash-is-not-a-zero) stay last whichever way it sorts; the **Asset** title sorts by name. The figures are printed plainly, with no colours and no arrows in the cells: the page never ranks the assets by itself.
- **Under the table, a line gives the period** the figures were computed over: its first and last day, and its length in calendar years, months and days (1 July to 1 October, both ends counted, is 3 months and 1 day). These are always the dates actually used, and a difference of a few days from the page's date range at either end, such as a weekend or a holiday on which no selected asset is quoted can leave, does not make the line call the period shorter: it does so, recalling the selected dates, only when an asset — or the benchmark — with a shorter history makes the period start more than seven days after the range's first day, or end more than seven days before its last (see [One Shared Window](#one-shared-window)). It also says that volatility and the average annual return are annualised, and that Sharpe and Sortino derive from them. Beta and correlation, the benchmark columns described below, are not annualised.
- **The chart** places one dot per asset — annualised volatility across, average annual return up — as soon as at least two points can be placed.
- **No line is drawn through the points.** On a portfolio, a line through the portfolio's own point separates "better paid" from "worse paid" for the risk taken. A selection has no whole, so there is nothing to be above or below: the chart shows the trade-off and leaves the judgement to you.
- **The table and the chart share one selection.** A click on a row, or on its dot, selects that asset in both: the row is highlighted, and the dot is drawn larger and in green. A second click on it clears the selection; a click on another asset, in either, moves the selection there. The benchmark's dot has no row, so a click on it selects nothing.

!!! warning "The average annual return is not the return you lived through"

    The **average annual return** is the window's average return scaled to a year — the quantity a risk/return chart is built on. It describes the past; it is not a forecast. On a very volatile asset, the return actually lived through over the same window is lower, because volatility erodes compounding. Do not read the height of a dot as what the asset earned.

Sharpe and Sortino are computed here against a **risk-free rate of zero**: the tab has no control to set one.

Two more columns, **Beta** (how much the asset moves when the benchmark moves) and **Correlation** (how closely the two move together), join the table only when a benchmark applies — and the benchmark then appears on the chart as a larger diamond:

- it is **chosen on this tab, under *Compared with***: the last row of the panel at the top of the tab, below the selected assets — a setting of the whole tab. It is the same choice as on every other risk page — the Dashboard's Risk tab, a broker's detail page, an asset's detail page — so that their comparisons stay comparable: choosing it here changes it there too, and the reverse. The ⓘ next to *Compared with* explains what the benchmark is for: the reference against which beta and correlation are read;
- it **cannot be one of the selected assets**: a yardstick cannot also be one of the things it measures. The picker's list leaves the selected assets out, except the current choice, which always stays visible: a benchmark that is also in the selection still shows, with an amber ⚠ beside it whose tooltip explains why beta and correlation are missing. Remove it from the selection, or choose another benchmark, to get the columns back;
- the columns also stay hidden when the benchmark could not be measured over the window.

See [Volatility](../../financial-theory/technical-analysis/risk-metrics/volatility.md), [Sharpe Ratio](../../financial-theory/technical-analysis/risk-metrics/sharpe-ratio.md), [Sortino Ratio](../../financial-theory/technical-analysis/risk-metrics/sortino-ratio.md) and [Beta & Active Return](../../financial-theory/technical-analysis/risk-metrics/beta-active-return.md).

### ⏮️ What If…? {: #what-if }

The last section, **What if…?**, starts closed: click its title to open it. On this tab it holds a single rung, **Historical replay** — real returns from a real period. There is no hypothetical shock and no simulation here: on a selection without weights, the tab keeps to what really happened.

1. Pick a **Preset** — a built-in episode such as the *Global Financial Crisis* or the *COVID-19 crash*, or a *Custom period* — or set the **From** and **To** dates yourself. Until you change them, the dates follow the page's date range.
2. Press **Run replay**: the replay runs only when you ask for it.
3. Read one bar per asset — what that asset actually returned over the period, worst first: losses to the left in red, gains to the right in green. There is no total, because a selection has no composition to add up.

The replay keeps its period, give or take the seven days of the [staleness threshold](../../financial-theory/technical-analysis/risk-metrics/data-quality.md#staleness-threshold): each asset must be priced at both ends of it. An asset that is not is **left out of the replay**: it gets no bar, and the other assets are replayed without it. The section is then marked **Partial**, and a note names the assets left out and says why — for example *First quote after the replay window began: … — left out of the replay.* If none of the selected assets can be replayed, the section is marked **Unavailable for the selected data**. An asset is left out when:

- it has no price in the period, nor in the seven days before it begins;
- it was quoted before the period, but not in the seven days before it begins;
- its first price comes more than seven days after the period begins;
- it has no price in the last seven days of the period;
- its currency has no exchange rate into the tab's currency over the period.

Changing the selection or the page's date range clears a finished replay: run it again for the new answer. See [Historical Replay](../../financial-theory/technical-analysis/risk-metrics/historical-replay.md) for the method.

---

## 🔎 Reading the Numbers {: #reading-the-numbers }

A few properties of this tab are easy to misread. Each one is deliberate, not a fault.

### 📅 One Shared Window {: #one-shared-window }

Every figure is measured over **one window, the same for every selected asset**. It is built from the page's date range — the date picker in the toolbar, the same one the Assets tab uses (the replay uses its own period, as described above) — by three rules:

1. **It starts on the first day on which every selected asset can be valued** — has a price, and an exchange rate into the tab's currency if it is quoted in another. When they all can be valued from before the date range, the window simply starts with the range; an asset whose history begins later moves the start for all of them.
2. **From there, every date on which at least one selected asset is quoted counts** — quoted meaning that a price was recorded for that very day. A price recorded on a weekend or a market holiday is a **carry, not a quote**, when it repeats the previous close exactly (see [Stored Carries](../../financial-theory/technical-analysis/risk-metrics/data-quality.md#stored-carries)): it adds no date, so a weekend counts only when an asset's price really moved on it, as a crypto-asset's can.
3. **An asset that is not quoted on one of those dates enters with its last price**, so its price does not move that day: its return is zero — or, for an asset quoted in another currency, only the exchange rate's move. Over a weekend, a holiday or a day on which only another market traded, that is ordinary and marks nothing. Only a price held over for **more than seven calendar days** — the [staleness threshold](../../financial-theory/technical-analysis/risk-metrics/data-quality.md#staleness-threshold) — makes every section measured over the window say so: its measurements are marked **Partial**, with a note naming the assets, as in *Prices older than 7 days for 1 asset: …*; an exchange rate held over for more than seven days does the same, with *Exchange rates older than 7 days: …*.

A date on which one of the assets cannot be valued even so is left out for all of them. That is what makes the rows comparable: two assets side by side fell, rose and moved over exactly the same days.

The price of that fairness is shared too:

- **Adding an asset with a shorter history narrows the window for all of them, and their figures change.** Removing it widens the window again. This is expected, not an error.
- **Adding an asset quoted on days the others are not adds those days for all of them** — a day its market is open and theirs is closed, or a weekend on which its price really moves. On those days the others enter with their last price, so their figures change as well.
- **A benchmark, when one applies, joins the window** of *How much did each of these hurt?* and *What did each of these pay for its risk?* — it is [chosen](#what-did-each-pay) under *Compared with*, in the panel at the top of the tab — because it is measured together with the selection there: a benchmark with a shorter history narrows those two sections as well, and the days on which it is quoted count there too. The correlation matrix is computed without it and keeps the selection's own window.
- **An asset that cannot be valued at all** over the window — no price up to its last day, or no exchange rate into the tab's currency — narrows nothing: it is left out of the calculation. It disappears from the matrix, keeps a row of dashes in the tables, and the sections say that an asset was excluded.

To see what a section was measured over, open **Calculation details** at its bottom. It shows the number of **Observations** behind the figures, together with the **Coverage**, the annualization factor and the return basis. It gives figures rather than dates. For the dates, look under the table of *What did each of these pay for its risk?*: a [line](#what-did-each-pay) there gives the first and last day of that section's window and its length in calendar years, months and days, while its Calculation details keeps the figures. The observations can move either way when you add an asset: down if its history is shorter, up if it is quoted on days the others are not. **Coverage** looks at every date in the date range on which at least one asset is quoted, and gives the share the window keeps: below 100%, the window starts later than the range, or skips days on which an asset could not be valued.

### 💱 One Currency {: #one-currency }

Returns are measured in the instance's default currency — the one your administrator sets in [Global Settings](../../admin/settings.md) — not in the display currency of your personal preferences. An asset quoted in another currency is therefore measured after conversion, exchange-rate movements included.

### ➖ A Dash Is Not a Zero {: #a-dash-is-not-a-zero }

A dash (—) means *this could not be measured for that asset over this window*. It never means zero: a zero is a measurement, a dash is the absence of one. A selected asset always keeps its row, so a row of dashes means "not measurable here", never "not selected".

The tables carry no standing note about this: the explanation sits on the dash itself. Hover a dash — or tap it on a touch screen — to read it.

### 🧩 Each Section Speaks for Itself {: #each-section-speaks-for-itself }

The sections do not stand or fall together. The drawdown columns need very little history; the other figures need at least 20 observations, and the bad month more still. So on a short window, **Worst fall**, **Below peak now** and **Rise to peak** can be filled in while the bad day, the bad month and the whole risk/return section cannot.

Rather than going blank, each section states its own condition in amber above its content:

- which measurement fell short, and how — **Partial**, **Unavailable for the selected data** or **Calculation failed**;
- for a measurement that did not run, the limit that stopped it — for example *Insufficient history for this calculation.*;
- the calculation's own notes, such as prices older than seven days or an asset excluded from the calculation.

A **Partial** section still shows its figures: the notes say what they are missing.

### 🔀 Same Asset, Another Figure Elsewhere {: #same-asset-another-figure }

The same asset can show a different volatility here than on another page — or here, with another selection. Each page prepares its own window: this tab measures each asset over the window of the whole selection, including the days on which only the other assets are quoted; other pages measure over their own period and their own series. Compare two figures only when they were measured over the same window; **Calculation details** is where you check.

---

## 🔗 Related {: #related }

- 📋 **[Asset List](index.md)** — the Assets tab, its toolbar and its date range
- 📊 **[Risk Metrics](../../financial-theory/technical-analysis/risk-metrics/index.md)** — the questions behind every section of this tab
- 🕸️ **[Correlation](../../financial-theory/technical-analysis/risk-metrics/correlation.md)** — how the matrix is computed, and what it cannot see
- 🌊 **[Conditional Value at Risk](../../financial-theory/technical-analysis/risk-metrics/conditional-value-at-risk.md)** — the bad day and the bad month
- 📉 **[Max Drawdown](../../financial-theory/technical-analysis/risk-metrics/max-drawdown.md)** — the worst fall and how long it lasted
- 📍 **[Current Drawdown](../../financial-theory/technical-analysis/risk-metrics/current-drawdown.md#what-it-takes-to-get-back)** — below the peak now, and what it takes to get back
- 🎯 **[Benchmark Selection](../../financial-theory/technical-analysis/risk-metrics/benchmark-selection.md)** — why relative figures need a shared benchmark
- ⏮️ **[Historical Replay](../../financial-theory/technical-analysis/risk-metrics/historical-replay.md)** — what a real past episode did
- 🧪 **[Data Quality](../../financial-theory/technical-analysis/risk-metrics/data-quality.md#alignment-what-missing-data-actually-costs)** — the shared calendar, and what a missing date costs

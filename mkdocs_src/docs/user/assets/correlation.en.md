# 🧪 Correlation Tab

The **Correlation** tab of the [Assets page](index.md) is a small laboratory. Instead of your portfolio, it examines a **selection of assets** that you put together — assets you own, assets you only watch, or the holdings of a broker — and asks the same questions of each of them: which of them move together, how much each one hurt, what each one paid for the risk it carried, and how each one came through a real past episode.

To open it, go to **Assets** in the sidebar and switch from the **Assets** tab to the **Correlation** tab in the toolbar.

!!! info "Percentages and ratios only — no money, by design"

    A selection has no weights: it says *which* assets, never *how much* of each. Without weights there is nothing to add up, so **no amount of money appears anywhere on this tab**. Every result is a percentage or a ratio, plus a few durations in days and observation counts. Questions about your own money are answered by the **Risk** tab of the Dashboard, which works from your actual positions.

---

## 🧺 Building the Selection {: #building-the-selection }

The card at the top of the tab holds the selection. Its first row carries the buttons that change many assets at once and, on the right, a counter such as *3 in the analysis, of 42 that can be analysed*:

- the **first number** counts the selected assets the tab is analysing right now;
- the **second** counts every asset it could analyse over the page's date range — every asset in LibreFolio, not only the ones you hold, as long as it has enough prices in that period (see [What Can Be Analysed](#what-can-be-analysed)).

Hover the counter, or tap it on a touch screen, for the same explanation. The card's second row holds the selection itself, one chip per asset, followed by the **+** that adds more.

As soon as at least one selected asset can be analysed, the [four sections](#the-four-sections) appear below the card; until then, the tab says *Select at least one asset.*

### 🚪 What the Tab Opens With {: #what-the-tab-opens-with }

The tab never opens on an arbitrary block of assets. It starts from the first of these that applies:

1. **Your last selection**, remembered in this browser for your account — minus any asset deleted or merged since.
2. **What you hold** — the assets in which you have an open position on the last day of the page's date range, in the brokers you can access.
3. **A small starting set** — the six active assets with the most transactions, when you hold none.

A selection holds at most **100 assets**. That limit is a ceiling, not a starting point: the tab opens on it only if you left the selection full last time or hold at least 100 assets. Every change you make is remembered as you go, so your next visit starts where this one ended.

### ✅ What Can Be Analysed {: #what-can-be-analysed }

Before anything is measured, the tab asks the risk engine which assets can be analysed over the page's date range. The answer reads each asset's own quotes in that period — a price stored on a weekend or a market holiday that only repeats the close before it is not a quote — and comes in three levels:

| Verdict | When |
|---|---|
| **Cannot be analysed in the period** | No price has ever been recorded for the asset; it has no prices in the period; it has fewer than 20 quotes in it; or its currency has no exchange rate into the tab's currency at the start or at the end of the period |
| **Can be analysed, with a warning** | Its first quote comes more than seven days after the period begins, or its last price more than seven days before the period ends |
| Can be analysed | Every other case |

The verdict decides what happens to an asset you selected:

- **One that cannot be analysed stays in the selection, but out of the analysis.** Its chip has a dashed border and its name is struck through, none of the sections includes it, and a note under the chips counts such assets — *1 selected asset cannot be analysed in the period and stays out of the analysis.* Choose a date range that suits it, and it comes back on its own.
- **One with a warning is analysed.** Its chip has an amber border, and what the warning describes still shapes the figures — see [One Shared Window](#one-shared-window).

Hover or tap a chip with a dashed or an amber border to read the reason, such as *First quote on …, after the start of the period*. If the check itself cannot be made, the card says *Eligibility could not be checked: every asset stays selectable.*, and nothing is kept out.

### 📆 A Period in Which All Have Prices {: #common-period }

When it is the page's date range that leaves some selected assets short — one starts quoting after the period begins, one stops before it ends, one is quoted only outside it — an amber strip at the top of the card says so: *With the chosen period, 2 selected assets have no prices for part of it.*

Its button, **Use the period in which all have prices (… – …)**, moves the page's date range — the toolbar's, which the Assets tab shares — to a period over which every selected asset that has prices at all can be analysed without a warning: the chosen period cut down to the span in which they are all quoted or, when that does not work, the span itself. The button's tooltip names the assets it brings back. The proposal is checked before it is offered, so the strip appears only when such a period exists. An asset for which no price has ever been recorded plays no part in it: no period could bring it back.

### ➕ Adding and Removing Assets {: #adding-and-removing-assets }

The **+** after the chips — its tooltip reads *Add asset to matrix* — opens a panel for adding several assets in one go:

1. **Find them.** The panel lists, by name, the assets of the list that are not selected yet. Each row shows the asset's icon, name, type and currency, with an ⚠ when the asset [can be analysed only with a warning](#what-can-be-analysed) — hover it for the reason. The search box finds an asset by its name, its currency or its type, every word you type having to match; the **Type** and **Currency** filters narrow the list further (see [below](#type-and-currency-filters)).
2. **Tick them.** Click the rows you want. **Select visible** ticks every row that the search and the filters leave on screen; it reads **Deselect visible** when there is nothing left to tick.
3. **Add them.** **Add N** puts the ticked assets in the selection and closes the panel; **Cancel** closes it without adding anything.

The assets that cannot be analysed in the period are listed apart at the bottom of the panel, under *Cannot be analysed in the period*: read-only, each with a padlock and its reason. Each time the panel opens, the search is empty and nothing is ticked; the filters stay as you left them.

<!-- [Screenshot Placeholder: risk/lab-asset-picker — the + panel open over the selection card: search box, Type and Currency filters, ticked rows with Add N, and the read-only "Cannot be analysed in the period" part with its reasons] -->

- The **×** on a chip removes that asset.
- At 100 assets the **+** and **Select all** are disabled, and a note under the chips says *The API limit of 100 assets has been reached.* Inside the panel, once the ticked rows fill the room that is left, the other rows are disabled and the same note appears.

### 🧰 Bulk Actions {: #bulk-actions }

Three buttons in the card's first row change many assets at once. They act on every asset of the list that [can be analysed](#what-can-be-analysed) in the period, whatever filter is set in the **+** panel or on the Assets tab:

| Button | What it does |
|---|---|
| **Select all** | Adds every asset that can be analysed in the period — inactive ones included — up to the limit of 100 |
| **Deselect all** | Empties the selection, the assets that cannot be analysed included |
| **Invert** | Among the assets that can be analysed, the selected ones leave and the others join; the ones that cannot be analysed stay where they are |

A fourth button, **My assets**, loads [what you hold](#preloading-a-brokers-assets).

### 🏷️ Type and Currency Filters {: #type-and-currency-filters }

The **Type** and **Currency** filters live in the **+** panel, and they narrow only its list: they never remove an asset that is already selected, and they never change what the bulk actions do. Each menu offers every type or currency of the asset list, with the number of assets it would still bring in — not selected yet, and analysable in the period; a value whose assets are all in reads 0 and stays in the menu. With nothing chosen they mean *every type* and *every currency*. **Clear filters** switches them all off.

!!! note "The toolbar filters belong to the Assets tab"

    On this tab the page toolbar hides the search box and the **Active**/**Inactive**, currency and type filters: they narrow the Assets tab's list, while this tab always works from the full asset list, through its own search and filters in the **+** panel. The toolbar keeps the **date range**, which sets the period the tab analyses and the window its figures are measured over (see [One Shared Window](#one-shared-window)), and two buttons that act on the selection: **Sync selection**, for the prices of the selected assets and the exchange rates that convert them, and **Reload All**, which reloads every analysis of the selection.

### 🏦 Loading What You Hold {: #preloading-a-brokers-assets }

**My assets** opens a short menu: **All my holdings**, or one of the brokers you can access, listed under *By broker*. Either choice **replaces** the selection with the assets held there on the last day of the page's date range, up to 100 — those that cannot be analysed in the period included, as dashed chips.

It is a command, not a filter: it runs once, when you choose it, and the selection is then yours to change; a later change of dates does not run it again. When nothing is held there on that day, the selection stays as it was, and a note says *Nothing is held there on the last day of the period: the selection is unchanged.*

---

## 🧭 The Four Sections {: #the-four-sections }

Below the selection card, four sections each ask one question of every asset in the analysis, in this order. The first three are always open; the last one starts closed. Between the card and the first section, a banner and a notice say what is wrong with the data and what it did to the figures — see [What Is Missing, What Is Partial](#each-section-speaks-for-itself).

### 🕸️ Correlation {: #correlation }

The first section, **Correlation**, answers *which of these move together?* It holds a matrix of Pearson correlation coefficients, computed on returns in the tab's currency, and beside it a short list of the pairs worth looking at.

- **Each pair appears once.** The diagonal — where every asset correlates perfectly with itself — and the mirrored upper half are left out. Each square prints its coefficient to two decimals and takes its colour from one scale, red at −1, neutral at 0 and blue at +1; the legend under the matrix puts its two ends and its middle into words.
- **Hover a square** to read the coefficient ρ with its reading in words, the observations and the coverage behind it, and the two assets, each with its largest sectors and regions when they are known. A matrix too wide for the card scrolls sideways.
- **The buttons above the matrix change its order** — the arrangement, never the coefficients:
    - **By similarity**, the default, places side by side the assets whose movements are most closely linked — in the same direction or in opposite ones — so groups of redundant assets show up as blocks;
    - **By type** groups them by asset type;
    - **By sector** and **By region** group each asset under the sector, or the country, that holds at least half of its classified weight; then come the assets spread more evenly (*Diversified*), those classified only as *Other*, and those with no classification (*Unclassified*). Each of the two appears only when at least one asset of the matrix has that classification;
    - **By name** sorts them alphabetically.

Above the matrix, when the classification of the selected assets is known, two rows of badges, **Sector** and **Region**, show what the selection is made of, whatever the order: each group once, with the number of assets in it. The row the matrix is grouped by has its title underlined, and a row too narrow for its names folds to icons and counts — hover a badge for its name.

The reading in words follows the coefficient. It is a reading aid, not a verdict:

| Coefficient ρ | Reading shown |
|---|---|
| Above 0.7 | they move together |
| From 0.3 to 0.7 | they move together in part |
| Between −0.3 and 0.3 | they move independently |
| −0.3 or below | they move in opposite directions |

A pair at 0.9 or above is also flagged **near-identical**.

Beside the matrix, two lists put the answer into words. Each pair comes with its coefficient — blue when positive, red when negative, as in the matrix — and a short tag:

- **The most alike** keeps only the pairs above 0.7, highest first: *very similar*, or **near-identical** at 0.9 or above — two products bought for what is really a single exposure. With none, it says *No pair moves clearly together.*
- **The ones that offset** keeps only the pairs at −0.3 or below, most negative first: *offsetting*, or *opposite* at −0.7 or below. This list is often empty, and it says so — *No pair offsets another: nothing here cushions anything else.* An empty list is a finding, not a missing result.

A pair above −0.3 and up to 0.7 joins neither list: the lists name only what the coefficient clearly supports. Click a pair in a list to find its square in the matrix, with its tooltip open, and click it again to close it; clicking a square selects its pair in the list, when it is there.

Each list shows up to five pairs. With more than 20 assets the matrix becomes too dense to read: on wide screens the lists move ahead of it, and they show up to eight pairs each.

<!-- [Screenshot Placeholder: risk/lab-correlation — the Correlation section with at least four assets: the triangular matrix with its legend and order buttons, and beside it the two lists "The most alike" and "The ones that offset"] -->

The matrix needs at least two assets to show a pair. When a square has no coefficient, it shows a dash, and its tooltip says why: **Insufficient history** when the window holds fewer than 20 observations, or **Undefined** when an asset's price did not move at all over the window. See [Correlation](../../financial-theory/technical-analysis/risk-metrics/correlation.md) for how the coefficient is computed, how its reading bands are set, and what it cannot see.

### 📉 How Much Did Each of These Hurt? {: #how-much-did-each-hurt }

The second section, **How much did each of these hurt?**, puts every asset in the analysis on the same scale of harm. Each asset gets a row, headed by its icon and its name on one line — a name too long to fit scrolls by itself — and the columns run from the shortest horizon to the longest:

| Column | What it tells you |
|---|---|
| **Bad day** | The average loss on the worst 5% of days (CVaR 95%, one day) |
| **Bad month** | The same over every run of 30 calendar days, compounded from real returns — not scaled up from the bad day. Those 30 days hold about 21 observations when the tab counts market days only, and 30 when it counts every day (see [One Shared Window](#one-shared-window)) |
| **Worst fall** | The deepest drop from a peak to a later low within the window. The line under it, *lasted N d*, counts the calendar days from that peak until the asset was back at it — or until the end of the window, if it has not recovered |
| **Below peak now** | How far the asset stands, at the end of the window, below the highest level it reached within the window |
| **Rise to peak** | The gain it still needs to get back to that peak |

**Rise to peak** is there to teach an asymmetry: the way back is steeper than the way down, because the rise starts from a smaller base. An asset **20% below its peak needs +25%** to return to it, not +20%.

Every loss is drawn in the same red for every asset, and the page never ranks the assets by itself: the table opens in the order of the selection, and only a click on a column title sorts it, as in the [next section](#what-did-each-pay). Each figure's title explains it in a tooltip — hover it, or tap it on a touch screen — but links nowhere: the book icon in the section's header opens the manual's [Risk Metrics](../../financial-theory/technical-analysis/risk-metrics/index.md) pages, the eye icon beside it shows or hides columns, and the theory behind the columns is in [Conditional Value at Risk](../../financial-theory/technical-analysis/risk-metrics/conditional-value-at-risk.md), [Max Drawdown](../../financial-theory/technical-analysis/risk-metrics/max-drawdown.md) and [Current Drawdown](../../financial-theory/technical-analysis/risk-metrics/current-drawdown.md).

Drag the right edge of a column's title to resize the column: each figure's column starts out exactly as wide as its title in your language, and cannot be dragged narrower than that. The names are not pinned to the left: when the table is too wide to fit, they scroll sideways with their figures.

<!-- [Screenshot Placeholder: risk/lab-hurt-table — the "How much did each of these hurt?" table: one row per asset with Bad day, Bad month, Worst fall with its "lasted N d" line, Below peak now and Rise to peak] -->

### ⚖️ What Did Each of These Pay for Its Risk? {: #what-did-each-pay }

The third section, **What did each of these pay for its risk?**, sets risk against reward, asset by asset: first in a table, then in a chart of the same figures.

- **The table** gives the figures of every asset — **Volatility**, **Ann. return**, **Sortino** and **Sharpe** — one row per asset, named as in the previous section, with columns that resize and scroll the same way; a benchmark, when one applies, has a row of its own, described below. Sortino measures the return per unit of downside risk, Sharpe per unit of total volatility. Each figure's title explains it in a tooltip: hover it, or tap it on a touch screen. **Ann. return** is short for **Average annual return**, the full name its tooltip opens with. The eye icon beside the section's book icon shows or hides columns, and lists that one by its full name.
- **Only you sort it.** The table opens with the benchmark's row, when there is one, then the selection in its own order. A click on a column title sorts by that figure — ascending, then descending, then back to the opening order — and moves the benchmark's row like any other; [dashes](#a-dash-is-not-a-zero) stay last whichever way it sorts, and the **Asset** title sorts by name. The figures are printed plainly, with no colours and no arrows in the cells: the page never ranks the assets by itself.
- **Under the table, a line gives the period** the figures were computed over: its first and last day, and its length in calendar years, months and days (1 July to 1 October, both ends counted, is 3 months and 1 day). These are always the dates actually used, and a difference of a few days from the page's date range at either end, such as a weekend or a holiday on which no selected asset is quoted can leave, does not make the line call the period shorter: it does so, recalling the selected dates, only when an asset — or the benchmark — with a shorter history makes the period start more than seven days after the range's first day, or end more than seven days before its last (see [One Shared Window](#one-shared-window)). It also says that volatility and the average annual return are annualised, and that Sharpe and Sortino derive from them. Beta and correlation, the benchmark columns described below, are not annualised.
- **The chart** places one dot per asset — annualised volatility across, average annual return up — as soon as at least two points can be placed, the benchmark's included. The assets are circles; the benchmark is a larger diamond.
- **A line runs through the benchmark, never through the selection.** When a benchmark is on the chart, a dashed line starts on the vertical axis at the risk-free rate — zero on this tab — and runs through the benchmark's diamond, on as far as the most volatile dot. Its slope is the benchmark's Sharpe ratio, so a dot above the line was better paid for its risk than the benchmark — it has a higher Sharpe ratio — and a dot below it was paid less: a comparison with the reference you chose, not a grade. With no benchmark there is no line. On a portfolio, the line then runs through the portfolio's own point instead; a selection has no whole to draw it through, so the chart shows the trade-off and leaves the judgement to you.
- **Notes under the chart** say how to read it: that the dots use the average annual return — with, in bold, the warning below — and that the return comes from prices alone. When the line is drawn, two more say what being above it means and where the line comes from, the second with a question-mark icon that opens [The Risk/Return Line](../../financial-theory/technical-analysis/risk-metrics/benchmark-selection.md#the-risk-return-line); with no line, no note speaks of one.
- **The table and the chart share one selection.** A click on a row, or on its dot, selects that asset in both, the benchmark included: the row is highlighted, and the dot is drawn larger — in green for an asset, while the benchmark's diamond keeps its own colour. A second click on it clears the selection; a click on another row or dot moves the selection there.

<!-- [Screenshot Placeholder: risk/lab-risk-return — "What did each of these pay for its risk?" with a benchmark chosen: the table opened by the benchmark's tinted row, the period line under it, and the chart with the asset circles, the benchmark's diamond and the dashed line through it] -->

!!! warning "The average annual return is not the return you lived through"

    The **average annual return** is the window's average return scaled to a year — the quantity a risk/return chart is built on. It describes the past; it is not a forecast. On a very volatile asset, the return actually lived through over the same window is lower, because volatility erodes compounding. Do not read the height of a dot as what the asset earned.

    It also comes **from prices alone**: coupons and dividends are not included yet. An asset that pays out part of its return as income — a bond's coupons, a stock's dividends — therefore shows a lower return here than it actually paid.

Sharpe is computed here against a **risk-free rate of zero**, and Sortino against a **target return of zero**: the tab has no control to set either.

Two more columns, **Beta** (how much the asset moves when the benchmark moves) and **Correlation** (how closely the two move together), join the table only when a benchmark applies — and the benchmark then has a row of its own:

- it is **chosen under *Compared with***, in the only section of the tab that measures against a benchmark: at the top of this section, above its table, as on the Dashboard. It is the same choice as on every other risk page — the Dashboard's Risk tab, a broker's detail page, an asset's detail page — so that their comparisons stay comparable: choosing it here changes it there too, and the reverse. The ⓘ next to *Compared with* explains what the benchmark is for: the reference against which beta and correlation are read;
- **its row opens the table**, tinted in the amber of its diamond, with a small diamond before its name: a mark of what it is, not a grade. When the benchmark is not one of the selected assets, the row is added for it, with its volatility, average annual return, Sharpe and Sortino, measured over the same window as the assets; under **Beta** and **Correlation** it shows a dash, whose tooltip explains that they do not apply because that asset is the benchmark itself: compared with itself, both would be 1 by construction;
- it **may be one of the selected assets** — a core ETF, for example, that the others are compared against. The picker lists every asset, the selected ones included. That asset keeps its own row, which moves to the top as the benchmark's, and its own figures, measured like the others'; its **Beta** and **Correlation** show the same dash. On the chart it is drawn once, as the benchmark;
- the assets that cannot be analysed over the page's date range are set apart at the bottom of the picker's list, read-only, under *Not usable over this period*, each with its reason — the same verdicts as the **+** panel of the selection. A benchmark already chosen that falls among them stays chosen: the picker still shows it, and lists it in that part. But it is **not used**, and the tab does not even try to measure it: until a date range over which it can be measured, the section shows no **Beta** or **Correlation** columns, no benchmark row, no diamond and no line, just as when no benchmark is chosen;
- the columns also stay hidden, and the benchmark gets no row, when it could not be measured over the window.

<!-- [Screenshot Placeholder: risk/lab-benchmark-picker — the "Compared with" picker open at the top of the section, with the read-only "Not usable over this period" part at the bottom of its list and each asset's reason] -->

See [Volatility](../../financial-theory/technical-analysis/risk-metrics/volatility.md), [Sharpe Ratio](../../financial-theory/technical-analysis/risk-metrics/sharpe-ratio.md), [Sortino Ratio](../../financial-theory/technical-analysis/risk-metrics/sortino-ratio.md) and [Beta & Active Return](../../financial-theory/technical-analysis/risk-metrics/beta-active-return.md).

### ⏮️ What If…? {: #what-if }

The last section, **What if…?**, starts closed: click its title to open it. On this tab it holds a single rung, **Historical replay** — real returns from a real period. There is no hypothetical shock and no simulation here: on a selection without weights, the tab keeps to what really happened.

1. Pick a **Preset** — a built-in episode such as the *Global Financial Crisis* or the *COVID-19 crash*, or a *Custom period* — or set the **Period** yourself: a quick range ending today (**1W**, **1M**, **3M**, **6M**, **1Y**, **2Y** or **YTD**, plus a few more when the box has room; there is no **All** here), or the **From** and **To** dates. A quick range or a date of your own sets the crisis aside, since the period is no longer the crisis's, and the menu shows **No preset**; choosing **No preset**, the menu's first entry, sets the crisis aside too, but keeps its dates. Until you change them, the dates follow the page's date range.
2. Press **Run replay**: the replay runs only when you ask for it.
3. Read the table: one row per asset replayed, worst first, with its **Return** over the period and its **Effect** — a bar, red to the left for a loss and green to the right for a gain, every bar on the same scale. The columns a portfolio would fill — weight, contribution, amount — are left out, because a selection has none of them, and there is no total: a selection has no composition to add up. Click a column title to sort by it, and drag the edge of a title to widen its column, the bar's included.

The replay keeps its period, give or take the seven days of the [staleness threshold](../../financial-theory/technical-analysis/risk-metrics/data-quality.md#staleness-threshold): each asset must be priced at both ends of it. An asset that is not is **left out of the replay**: it gets no row, and the other assets are replayed without it. Above the table, the replay first [says what it left out](../../financial-theory/technical-analysis/risk-metrics/historical-replay.md#what-the-result-shows): a box lists those assets, grouped by reason, each as a badge with its icon and its name, under a header such as *Left out of the replay: 2 assets; the figures speak for the others.* A selection has no weights, so the badges show no shares of the value and nothing counts as cash: an asset left out is [simply omitted](../../financial-theory/technical-analysis/risk-metrics/historical-replay.md#what-takes-its-place). The section around the replay does not repeat that list: it is just marked **Partial**.

If none of the assets can be replayed, there is no table, and the section is marked **Unavailable for the selected data**. In place of the table, the block lists the assets, grouped the same way, under *Nothing to replay: no asset has usable prices over this period.*

The block groups the assets under these reasons:

- **No prices in the period** — it has no price in the period, nor in the seven days before it begins;
- **First quoted after the period began** — its first price comes more than seven days after the period begins;
- **No recent price when the period began** — it was quoted before the period, but not in the seven days before it begins;
- **No recent price at the end of the period** — it has no price in the last seven days of the period;
- **No exchange rate to your currency** — its currency has no exchange rate into the [tab's currency](#one-currency) over the period.

When assets were left out at the edges of the period — a first quote after it began, a gap just before it, no recent price at its end — the block can propose [the part of the period in which they are priced too](../../financial-theory/technical-analysis/risk-metrics/historical-replay.md#the-common-period). A button inside the box of what was left out, below the badges — for example **Replay from … to …: 2 assets come back** — sets those dates and runs the replay in one click. It appears even when nothing at all could be replayed. If you replayed one of the built-in crises, still chosen in the menu, that part is shorter than the episode, and the block says so: *Only part of the crisis.* An asset left out for having no prices in the period, or no exchange rate, is never part of the proposal: no shorter period would bring it back.

<!-- [Screenshot Placeholder: risk/lab-replay — What if…? on the Correlation tab after Run replay over a period that cuts an asset short: the box of assets left out, as badges grouped by reason, with the "Replay from … to …" button, above the Return and Effect table] -->

Changing the selection or the page's date range clears a finished replay: run it again for the new answer. See [Historical Replay](../../financial-theory/technical-analysis/risk-metrics/historical-replay.md) for the method.

---

## 🔎 Reading the Numbers {: #reading-the-numbers }

A few properties of this tab are easy to misread. Each one is deliberate, not a fault.

### 📅 One Shared Window {: #one-shared-window }

Every figure is measured over **one window, the same for every asset in the analysis**. It is built from the page's date range — the date picker in the toolbar, the same one the Assets tab uses (the replay uses its own period, as described above) — by three rules:

1. **It starts on the first day on which every asset in the analysis can be valued** — has a price, and an exchange rate into the tab's currency if it is quoted in another. When they all can be valued from before the date range, the window simply starts with the range; an asset whose history begins later moves the start for all of them.
2. **From there, every date on which at least one of them is quoted counts** — quoted meaning that a price was recorded for that very day. A price recorded on a weekend or a market holiday is a **carry, not a quote**, when it repeats the previous close exactly (see [Stored Carries](../../financial-theory/technical-analysis/risk-metrics/data-quality.md#stored-carries)): it adds no date, so a weekend counts only when an asset's price really moved on it, as a crypto-asset's can.
3. **An asset that is not quoted on one of those dates enters with its last price**, so its price does not move that day: its return is zero — or, for an asset quoted in another currency, only the exchange rate's move. Over a weekend, a holiday or a day on which only another market traded, that is ordinary and marks nothing. Only a price held over for **more than seven calendar days** — the [staleness threshold](../../financial-theory/technical-analysis/risk-metrics/data-quality.md#staleness-threshold) — makes the [notice above the sections](#each-section-speaks-for-itself) say so: it names the measurements over the window as partial, with a note naming the assets, as in *Prices older than 7 days for 1 asset: …*; an exchange rate held over for more than seven days does the same, with *Exchange rates older than 7 days: …*.

A date on which one of the assets cannot be valued even so is left out for all of them. That is what makes the rows comparable: two assets side by side fell, rose and moved over exactly the same days.

The price of that fairness is shared too:

- **Adding an asset with a shorter history narrows the window for all of them, and their figures change.** Removing it widens the window again. This is expected, not an error.
- **Adding an asset quoted on days the others are not adds those days for all of them** — a day its market is open and theirs is closed, or a weekend on which its price really moves. On those days the others enter with their last price, so their figures change as well.
- **A benchmark, when one applies, joins the window** of *What did each of these pay for its risk?* only — it is [chosen](#what-did-each-pay) under *Compared with*, at the top of that section — because it is measured together with the selection there: a benchmark with a shorter history narrows that section, and the days on which it is quoted count there. *How much did each of these hurt?* and the correlation matrix are computed without it and keep the selection's own window, whatever the benchmark. A benchmark that is also one of the selected assets changes no window: it is already part of the selection, and every section measures it as such.
- **An asset that cannot be analysed over the period narrows nothing either.** With no prices in it, fewer than 20 quotes or no exchange rate into the tab's currency at its ends, it is [kept out of the analysis](#what-can-be-analysed) before any section measures it: it stays in the selection as a dashed chip, and none of the sections includes it. Should the calculation itself still have to leave an asset out — when the eligibility check could not be made, for instance — that asset disappears from the matrix, keeps a row of dashes in the tables, and the notice above the sections says that it was excluded.

To see what a section was measured over, open **Calculation details** at its bottom. It shows the number of **Observations** behind the figures, together with the **Coverage**, the annualization factor and the return basis. It gives figures rather than dates. For the dates, look under the table of *What did each of these pay for its risk?*: a [line](#what-did-each-pay) there gives the first and last day of that section's window and its length in calendar years, months and days, while its Calculation details keeps the figures. The observations can move either way when you add an asset: down if its history is shorter, up if it is quoted on days the others are not. **Coverage** looks at every date in the date range on which at least one asset is quoted, and gives the share the window keeps: below 100%, the window starts later than the range, or skips days on which an asset could not be valued.

### 💱 One Currency {: #one-currency }

Returns are measured in the instance's default currency — the one your administrator sets in [Global Settings](../../admin/settings.md) — not in the display currency of your personal preferences. An asset quoted in another currency is therefore measured after conversion, exchange-rate movements included.

### ➖ A Dash Is Not a Zero {: #a-dash-is-not-a-zero }

A dash (—) means *this could not be measured for that asset over this window* — save for one case: in the benchmark's own row, the dash under Beta and Correlation means that they [do not apply](#what-did-each-pay). It never means zero: a zero is a measurement, a dash is the absence of one. An asset in the analysis always keeps its row, so a row of dashes means "not measurable here", never "not selected". A selected asset that cannot be analysed in the period has no row at all: its dashed chip in the selection card says why.

The tables carry no standing note about this: the explanation sits on the dash itself. Hover a dash — or tap it on a touch screen — to read it.

### 🧩 What Is Missing, What Is Partial {: #each-section-speaks-for-itself }

The sections do not stand or fall together. The drawdown columns need very little history; the other figures need at least 20 observations, and the bad month more still. So on a short window, **Worst fall**, **Below peak now** and **Rise to peak** can be filled in while the bad day, the bad month and the whole risk/return section cannot.

What did not come back at all is said where it is missing, in an amber banner at the top of its own section:

- which measurement, and how — **Unavailable for the selected data** or **Calculation failed**;
- the limit that stopped it — for example *Insufficient history for this calculation.*

An answer can also be set aside on its way. When the data changes while a section is waiting for it — prices synced, the tab reloaded — the answer would describe data that no longer exists, so the section asks again, up to three times in all. If none of those answers can arrive, its banner says *The answer was set aside because the data changed while it was arriving. Run the analysis again.* A section left with no figures to show also offers **Retry**; the replay is simply run again with **Run replay**.

What is only partial, and every note, is said **once**, in a single notice between the selection card and the correlation matrix. The sections read the same selection over the same window, so the same stale price or excluded asset, repeated under each of them, would read as several problems. The notice puts the cause first: it lists every note once, however many sections carry it — prices older than seven days for the assets it names, say, or an asset excluded from the calculation. Then, under *Measurements affected*, it names each partial measurement once, as a badge — for example *Correlation*, *Bad day*, *Bad month*, *Per-asset drawdowns*, *Per-asset risk and return*. A partial measurement still shows its figures: the notice says what they are missing.

Its title and its colour follow what it holds:

- *Some results are partial*, in amber, when at least one measurement is partial;
- *Holdings without prices, left out of some measurements*, in blue, when the only cause it names is an asset that has no price source and no price ever recorded — a standing fact about that asset, not a fault of this answer;
- *Worth knowing about these results* when there are only notes — in blue when they are all of that same kind, in amber otherwise.

With nothing to say, there is no notice.

<!-- [Screenshot Placeholder: risk/lab-notice — the top of the Correlation tab with a stale or excluded asset: the folded data-quality banner, the notice with its causes and the "Measurements affected" badges, and below it a section's amber banner naming a measurement that did not come back] -->

**What if…?** keeps its own status and notes, because it replays a period of its own rather than the shared window: see [What If…?](#what-if).

Above the notice, right below the selection card, a **data-quality banner** lists what is wrong with the data itself, for all four sections, **What if…?** included: prices that are outdated or missing, and exchange rates that are outdated, missing or without a source. It appears only when there is something to fix, and starts folded: its header counts the errors and warnings, and clicking it opens the list. Each kind of problem is listed once, covering every asset or currency pair that any section ran into, with its own action. **Sync prices** and **Sync rates** open the same sync as the toolbar's **Sync selection** on this tab, for the prices of the selected assets and the exchange rates that convert them; the other actions are links, to the page of each asset that has no price, or to the FX pages — to [add a pair](../fx/add-pair.md) that has no source, or to enter a manual pair's rates by hand. The banner and the notice can mention the same fact, such as an outdated price: the banner offers the fix, the notice says what it did to the figures.

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

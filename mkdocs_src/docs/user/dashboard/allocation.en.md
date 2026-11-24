# 🥧 Allocation Tab

The **Allocation** tab of the [Dashboard](index.md) answers one question: **where am I exposed, looking at only a part of my portfolio?** You keep the classes you care about, take out what you do not want counted, and the tab shows how that part splits by sector, area, type or asset. It sits between **Positions & Analysis** and **Risk**, and every broker's page has the same tab for that broker alone.

- 🧮 **[The three boxes](#three-boxes)** — what the 100% is, what the filter leaves out, what is excluded
- 🎚️ **[Filters](#filters)** — classes, what to take out of the 100%, single assets
- 🔀 **[Dimensions and views](#dimensions-and-views)** — sector, area, type or asset; now or over time
- 📋 **[The table](#table)** — the slices, the assets behind them, what is excluded
- 🧩 **[The Class × dimension matrix](#matrix)** — where the selection sits in the whole portfolio
- 📌 **[Good to know](#good-to-know)** — scope, privacy, what is remembered

For the quick look at your allocation on the Overview tab, see the [Allocation Panel](charts.md#allocation-panel): its **Analyze →** link opens this tab.

<div class="screenshot-container" style="max-width: 900px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="allocation-tab" alt="The Allocation tab: the three boxes on top (Base of the 100%, Outside the filter, Excluded from the 100%), the filters beside the chart, the donut chart with the base in its middle, and the table of slices below" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🧮 The Three Boxes {: #three-boxes }

Every euro of your net worth lands in exactly one of three places, and the three boxes on top of the tab show them:

| Box | What it holds |
|-----|---------------|
| **Base of the 100%** | The part you are looking at: the amount that the chart and the table split into slices, with its share of the whole portfolio and a bar that draws it. |
| **Outside the filter** | What your class filter leaves out: every asset of a class you switched off, and your cash when **Liquidity** is off, listed class by class. |
| **Excluded from the 100%** | What you took out yourself (a whole asset, or the **Unclassified** or **Other** part of the slices) and two amounts LibreFolio cannot place in the current dimension, each with its reason. |

**Base + Outside the filter + Excluded from the 100% = your net worth** on the last day of the period, the same figure as the Net Worth [KPI card](kpi-cards.md). With no filter on, the base is the whole portfolio and the other two boxes say *Nothing*.

The two amounts LibreFolio cannot place are fixed rows, not choices:

- **Securities in transit between brokers** — units that have left one broker and not yet reached the other have no asset on that day, so they have no sector, area or type. They are always shown as excluded.
- **Cash has no country** — in the **Area** dimension, cash belongs to no country, so with **Liquidity** on it is shown as excluded.

On a phone the three boxes become one: the base, its bar, and a line with the other two amounts.

---

## 🎚️ Filters {: #filters }

<div class="screenshot-container" style="max-width: 420px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="allocation-filters" alt="The filter panel with its three folding panels: Classes, with a switch and an amount for each class; Outside the 100%, with the Unclassified and Other switches; and Included assets, with one switch for each asset" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

On a wide screen the filters are a column beside the chart; on a phone they open from the **Filters** button above it, with the number of active choices on the button, and every choice also appears as a chip you can remove with one click. Each change recalculates the whole tab.

### 🏷️ Classes {: #filters-classes }

A **class** is what an asset *holds*, not the label it carries: an ETF of stocks counts as **Stocks**, a bond ETF as **Bonds**, and so on for commodities, real estate and crypto. An ETF with no declared content stays **ETF**, and your cash is **Liquidity**. Only the classes you hold in the period are listed, each with its amount on the last day and a switch; the count at the top says how many are on.

### ➖ Outside the 100% {: #filters-outside }

Switches that take a part of the slices out of the base, where the current dimension has it:

| Bucket | What it is | Where it exists |
|--------|------------|-----------------|
| **Unclassified** | The part with no declared sector, country or type | Sector, Area and Type |
| **Other** | The «Other» sector of the data sources | Sector only |

The panel shows only the buckets that exist in the dimension you are looking at, and hides itself when there are none (the **Asset** dimension has neither). **Liquidity** is not here: it is a class, switched on and off with the others.

### 🔎 Included assets {: #filters-assets }

Every asset of the classes that are on, each with a switch: switching one off takes the whole asset out of the base, and its value moves to **Excluded from the 100%**. Above 10 assets a search box lets you find one by name or ticker.

**Remove filters** brings everything back. Your choices are remembered for each page: the Dashboard and every broker's page have their own, so a selection made on one broker never changes another. The first time you open a page it shows the whole portfolio.

---

## 🔀 Dimensions and Views {: #dimensions-and-views }

**Group by** picks what the slices split by:

| Dimension | Slices |
|-----------|--------|
| **Sector** | Industry sectors, with **Liquidity** for your cash |
| **Area** | Countries, drawn on a world map coloured on the selection: a line under the map says what the colours mean (100% is the base). Cash has no country and is a fixed excluded row |
| **Type** | The asset types you hold, plus **Liquidity** |
| **Asset** | One slice per asset |

The tab opens on **Sector** and **Now**; the dimension and the view are not remembered, only the filters are.

- **Now** — the split on the last day of the period: a donut with the base written in its middle, or the map for **Area**. Hovering a slice shows its percentage and amount.
- **History** — the same selection over the period, drawn in steps: each slice holds its value until the next change. Handy to see how the part you picked evolved. If the selection held nothing in the period, the tab says so.

If the base is zero or less, no share can be computed and the tab says so instead of drawing equal slices. A negative cash balance (an overdraft) cannot be drawn on the donut either: a note shows its amount, which stays in the table.

---

## 📋 The Table {: #table }

Under the chart, one row per slice, largest first:

| Column | What it shows |
|--------|---------------|
| *The dimension* | The sector, country, type or asset |
| **Amount** | The slice's value |
| **% of the selection** | Its share of the base: this column adds up to 100% |
| **% of the portfolio** | Its share of the whole portfolio: this column adds up to the base's share |
| **Assets** | How many assets make the slice up |

Click a row to open the assets that make it up, each with its amount and its share of the slice; click again to close it.

What is excluded stays at the bottom, struck through and with no share: the assets and buckets you took out, then the fixed rows (**Cash has no country**, **Securities in transit between brokers**).

---

## 🧩 The Class × Dimension Matrix {: #matrix }

Under the table, a grid with one row per class and one column per bucket of the dimension you chose above: **Sector**, **Area** or **Type**. There is no matrix for **Asset**, where each asset sits in one class only.

<div class="screenshot-container" style="max-width: 900px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="allocation-matrix" alt="The Class by Sector matrix at the first opening: one row for each class, one column for each sector, every cell showing its share of the whole portfolio in a tint proportional to its weight, with the cells the selection keeps framed" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

- Every cell is a **share of the whole portfolio**, whatever the filters say; a dot means the cell is empty. The tint only draws the weight of the cell next to the heaviest one.
- The **framed cells** are the selection: the classes that are on, in the columns you did not take out. So you see where your selection sits in the whole.
- **Click a cell** (or a class name) to keep only that class; click the same class again to bring every class back.
- **Click the Unclassified or Other column** to take it out of the 100%, and click it again to put it back.
- What has no column — cash in the geography, securities in transit — is listed under the grid, so the grid and that line add up to your net worth.

The matrix is shown under the table in both **Now** and **History**.

---

## 📌 Good to Know {: #good-to-know }

- **Scope.** The Dashboard's tab covers your owned brokers at your ownership share, over the Dashboard's date range, broker filter and currency. A broker's page counts that broker **whole**, whatever your share, like the rest of its page. See [Broker Sharing](../brokers/sharing.md).
- **The period.** The split is the one of the period's **last day**; the lists of classes and assets cover every asset held on any day of the period, so an asset sold meanwhile can still be listed (with a zero amount).
- **Privacy.** The privacy toggle hides every amount, including the one in the middle of the donut; percentages stay visible.
- **Refresh.** The **Refresh** button of the page recalculates this tab too.
- **Where the numbers come from.** Every amount and percentage is computed by the backend from the same figures as the rest of the Dashboard; the tab only draws them.

!!! note "Not financial advice"

    The tab describes how your portfolio is composed. It does not tell you what to buy, sell or rebalance.

---

## 🔗 Related {: #related }

- 📊 **[Dashboard](index.md)** — the other tabs, the date range, the currency and the broker filter
- 🥧 **[Charts](charts.md#allocation-panel)** — the Allocation Panel of the Overview, with its **Analyze →** link
- 🔍 **[Positions & Analysis](positions.md)** — the holdings behind the slices
- 🏦 **[Brokers](../brokers/index.md)** — each broker's page, with its own Allocation tab

# 🔍 Positions & Analysis

The **Positions** tab shows what you hold, what each position earned in the period and, one click away, the FIFO lots behind any position. Each broker's page has the same tab for that broker alone, with the same table settings.

- 📋 **[Holdings](#holdings)** — what you own on the end date
- 📈 **[Period](#performance)** — what each position earned in the period
- 🔬 **[FIFO Lots Analysis](#fifo-lots-analysis)** — the lots behind one position

<div class="lf-screenshot-carousel" data-carousel="carousel-positions-views" data-carousel-interval="6000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
  <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="dashboard" data-name="positions-holdings-table" data-title="📋 Portfolio (Table)" alt="Portfolio Table View">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="positions-holdings-map" data-title="🗺️ Portfolio (Map / Treemap)" alt="Portfolio Map View">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="positions-performance-table" data-title="📈 Period (Table)" alt="Period Table View">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="positions-performance-map" data-title="📊 Period (Map / Chart)" alt="Period Map View">
</div>

---

## 🎛️ Choosing a view

- **[Portfolio](#holdings) / [Period](#performance)** switches between what you own and what each position earned; **Table / Map** (the two icons) between a table and a chart.
- **The eye icon** (in Table) shows, hides or reorders the columns; **Reset layout** restores them. **See all →** opens the Assets page.
- **To dig into a position**, open its **⋮** menu in a table, or right-click it in any view: **Analyze Lots** opens the [FIFO Lots Analysis](#fifo-lots-analysis) below, **View Asset** the asset's page.

LibreFolio remembers your choices.

---

## 📋 Holdings — what you own {: #holdings }

What do you own on the end date, and how is each position doing? **Portfolio** lists one row per asset and broker, the largest value first.

**Columns shown**

| Column | What it shows |
|:---|:---|
| **Asset** | The asset, with its type icon |
| **Δ1** / **Δ1%** | Today's move of the unrealized P&L at today's quantity, in money and in % of yesterday's value |
| **Unrealized P&L** / **P&L %** | Current value minus what the open position cost, in money and in % of that cost → [Book Value](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/book-value.md) |
| **Annualized** | Yearly compound return since the first transaction, income and fees included → [Net Annualized Return](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/net-annualized-return.md) |
| **YOC** | The last year's dividends and interest per unit, against its average price → [Yield on Cost](#yield-on-cost-yoc) |
| **Value** / **Weight** | What the position is worth, and its share of your Net Worth, cash included |
| **Qty** | Shares, units or coins held |
| **Price** *(hidden)* | The unit price used: the market price, or the price of your last purchase or sale when there is no quote; `—` for an asset valued at what it cost you, which has no price at all → [Price Resolution](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/price-resolution.md) |
| **Avg. Cost** *(hidden)* | Average purchase price per unit, each purchase at its own date's exchange rate → [Weighted Average Cost](../../financial-theory/technical-analysis/performance-metrics/weighted-average-cost.md) |
| **Oldest open lot** *(hidden)* | Opening date of the oldest lot still open at this broker; a stock split keeps the dates |
| **Brokers** | The broker holding the position |

**How to read it**

- **Weight counts cash**, so the rows add up to less than 100% when you hold cash.
- **Weight shows `—` when your Net Worth is zero or below**, for example when you have borrowed more cash than your holdings are worth: a share of it would mean nothing.
- **Avg. Cost keeps each purchase's exchange rate**, while Value uses the end date's: the Unrealized P&L includes what the rate did since.
- **In the Map**, tiles are grouped by broker and asset type; size is the value, colour the P&L %. Scroll to zoom, drag to move, and **Reset zoom** (↺) shows everything again.

??? info "➖ Empty cells — when a value is missing"

    - **`—` in Unrealized P&L, P&L % or Avg. Cost**: part of what you paid is unknown — an exchange rate missing on a purchase date, or a transfer or adjustment without a cost basis —, or, for Unrealized P&L and P&L % only, the price cannot be converted because the end date's exchange rate is missing. The [Data Quality banner](index.md#data-quality-banner) names what to fix.
    - **`—` in Price, with an Unrealized P&L of `0`**: the asset has no price at all — no market price and no purchase or sale, as when you received it through an adjustment or a transfer — so its Value is what it cost you.
    - **Δ1** and **Δ1%** need a market price; **Annualized** needs a position old enough for a yearly rate to mean anything.

### 💸 Yield on Cost (YOC) {: #yield-on-cost-yoc }

How much income does each unit pay you, compared with what it cost? **YOC** compares the dividends and interest each unit received over the **last 365 days** with its average purchase price.

**How to read it**

- **One value per asset and broker**, over the year that ends on the end date: moving the start date does not change it.
- **Gross, not after tax**: separate tax and fee transactions are not subtracted.
- **Hover a value** for the income per unit, the period and the exchange rates used — each payment at its own date's rate.
- **`0.00%`** means income recorded at zero, or corrections that exactly cancel it; a plain **`-`** means no income in the last year.

🔗 **Theory**: [Yield on Cost](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/yield-on-cost.md) — the exact rules, and how YOC differs from dividend yield or CAGR

??? info "🚦 A dash with an ⓘ icon — when YOC is unavailable"

    LibreFolio shows no partial YOC. When an input fails, hover the amber ⓘ for the reason: less than a year of history at this broker and no income yet, a payment with no units held the day before, a purchase, sale, transfer or split history that does not add up, a missing exchange rate, or an unknown average price. Once that is fixed, YOC is computed again. A dash also appears when corrections recorded in the last year — older negative dividend or interest rows — add up to more than the income itself: the ⓘ then reads *Corrections exceed the income of the last year.*

---

## 📈 Period — what each position earned {: #performance }

Which positions made or lost money in the period, and how? **Period** lists every position of the period, open or closed since, the biggest movers first. LibreFolio computes it the first time you open it, so it can take a moment.

**Metrics shown**

- **Period P&L**, split as on the [Period P&L card](kpi-cards.md#card-1-period-pl) into **Unrealized change**, **Sales**, **Dividends & interest** and **Costs** → [Period P&L](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md)
- **Annualized** — the period result as a yearly rate, over the time the position was held in the period → [Net Annualized Return](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/net-annualized-return.md)
- **Δ1** / **Δ1%** for open positions and, hidden by default, **Start Value**, **End Value**, **Oldest open lot** and **Status**
- **Other Period Effects** — what belongs to no position: **Unallocated income** and **Unallocated costs**, recorded without an asset; **FX on cash**, what the exchange rates did in the period to cash you hold in another currency, with a row only for a broker whose cash they moved; **Transfers at market value**, when you look at only some of your brokers, the gain that securities moved to or from a broker outside your selection made before crossing the boundary, one row per broker ([Transfers at market value](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md#transfers-at-market-value)); and the **Other / reconciliation residual**, what is left — a currency exchanged at a cost, the exchange-rate move of cash on its way between two of your brokers, securities on their way between them on the first or last day of the period, or a sale left out of **Sales** because a rate or a purchase cost is missing → [FX on cash](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md#fx-on-cash)

**How to read it**

- **Closed positions** are in italics, or carry a **Closed** badge in the chart; to list one kind only, show **Status** and filter it.
- **In the Map**, gains stack right of zero and losses left, the net result closing the row; each percentage compares with the position's start value.
- **A position's Period P&L** can differ from its lifetime gain: only the period counts.
- **Start Value** and **End Value** are worked out as the **Value** in **Portfolio** — same prices, an asset with no price at what it cost you, each day's exchange rate — so the rows plus the **Other Period Effects** add up to the [Period P&L card](kpi-cards.md#card-1-period-pl). A **`—`** in **Unrealized change** means a value could not be computed, such as a missing exchange rate or purchase cost: it is not a zero.
- **Securities moved between two of your brokers** during the period split their result: the sending broker's row keeps what they did until they arrived, the receiving broker's what they did after; the total does not change.

??? tip "🙈 Hide amounts — what the chart still shows"

    With **Hide amounts** on (the eye button in the top bar), the chart's amounts and axis turn into `•••`, as in `+€•••`. Signs, currencies, percentages, bar lengths and colours stay, so you still see who gained or lost, and how much compared with the others. See [Privacy mode](../settings/preferences.md#privacy-mode).

---

## 🔬 FIFO Lots Analysis {: #fifo-lots-analysis }

Which purchases make up a position, where are they held, and how has each one done? The **FIFO Lots Analysis** answers lot by lot: each purchase opens a *lot*, and each sale closes the **oldest** open lots first — First-In, First-Out.

Choose **Analyze Lots** on a position and the panel opens below, for the brokers of the page: your broker filter on the Dashboard, the broker itself on its own page. **View Asset** (↗) opens the asset, **✕** closes the panel.

<div class="lf-screenshot-carousel" data-carousel="carousel-fifo-lots-analysis" data-carousel-interval="6000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
  <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="dashboard" data-name="fifo-lots-panel" data-title="🔍 Overview" alt="FIFO Lots Analysis Overview">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-wac-chart" data-title="📈 WAC / Market Price" alt="WAC and Market Price Chart">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-gantt-chart" data-title="🕒 Lot Life & Custody" alt="Lot Life and Custody Gantt Chart">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-table" data-title="📋 Unified Lots Table" alt="Unified Lots Table">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-comparison-chart" data-title="💰 Value Comparison" alt="Value Comparison Chart">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-comparison-chart-return" data-title="📊 Return Comparison" alt="Return Comparison Chart">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-custody-modal" data-title="🧾 Lot Detail Modal" alt="Lot Detail Modal">
</div>

**How the blocks work together**

- **One selection**: click bubbles, bars or table rows to pick lots; with none picked, every visible lot counts. **Open / Closed**, on the timeline, filters every block.
- **Double-click to jump**: from a chart marker to the lots of that transaction, from a timeline bar to its table row, and back.
- **Full broker amounts**: on a broker you co-own, your share is not applied here, unlike the KPI cards and Holdings.

🔗 **Theory**: [FIFO Engine](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/index.md) · [FIFO Lot Analysis](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md) · [FIFO matching](../../financial-theory/instruments/transaction-types/buy-sell.md#fifo-matching) · [Taxation](../../financial-theory/fundamentals/taxation.md)

### 💹 1. Avg. Cost / Market Price

How does the price compare with what you paid, and where does each lot stand?

**Metrics shown**

- **Market Price** — dashed where LibreFolio estimates it from your last trade → [Valuation Price Chain](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md#valuation-price-chain)
- **Avg. Cost** — one line per broker, and a dashed **Combined** line when the asset sits at several → [Weighted Average Cost](../../financial-theory/technical-analysis/performance-metrics/weighted-average-cost.md)
- **Bubbles** — one per long lot, at its total return, among the markers of your transactions and payments → [FIFO Lot Analysis](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md)

**How to read it**

- **Abs / %** shows prices or their change from the first point; **Auto / From 0** sets where the axis starts.
- **Bubble colour** is the opening broker, its **size** the lot's quantity (**Abs**) or its opening value (**%**); a **dashed border** means valued at cost.
- **A gap in an Avg. Cost line** is a day whose average cost is unknown: no wrong average is drawn.
- **The Market Price line** covers the whole period, days without an open lot included: after you sell everything, it runs on to the end date.

### 🕒 2. Lot Life & Custody

When was each lot open, and which broker held it?

**Metrics shown**

- **Bars** — one per lot, coloured by the broker holding it and as thick as the quantity held; dashed violet while in transit, with a lane per broker after a transfer → [FIFO Engine](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/index.md)

**How to read it**

- **Open / Closed** keeps only open lots, only closed ones, or both.
- **A thinner bar** lost part of its quantity, for example to a partial sale.
- **Click** a bar to select its lot, **double-click** it to find its row in the table.
- **The markers on a bar** are the lot's events: ▲ purchase, ▼ sale, ◆ transfer, **+** adjustment in, **×** adjustment out and │ split. Hover a marker, tap it or reach it with the keyboard to see what happened, the date, the quantity (hidden as ••• in privacy mode) and the broker: a transfer between your brokers reads **From** and **To**, one with a broker outside the panel names only the broker you are looking at, and a point where several events fall on the same day lists them all. Click or double-click a marker as you would its bar.

### 📋 3. Lots Table

Every lot with its figures, following the panel's filter and selection.

**Metrics shown**

- **Opening Date**, **Total P&L**, **Total return**, **Annualized**, **Current Value**, **Open Quantity** and **Custody**, with a **Totals** row → [FIFO Lot Analysis](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md)
- **Income** when a lot received some, and **Fees**, **Taxes**, **Net P&L** and **Net return** when a lot bears costs → [Costs & Net Metrics](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md#costs-and-net-metrics)

**How to read it**

- **Click** a row to select it, **double-click** to find it in the timeline; the row colour is the opening broker.
- **The ⋮ menu** offers **View lot detail**, **Go to lot in Gantt**, **Go to opening transaction** and **Copy lot identifier** — a stable reference, handy for support.
- **More columns**, such as **Opening Value**, wait behind the eye icon.

### 💰 4. Value / Return Comparison

What are the selected lots worth, and what have they earned since opening? With none selected, the chart covers every visible lot.

**Metrics shown**

- **Value** — **Residual value**, **Sale proceeds** and **Cumulative income** stacked up to the **Comprehensive value**, against the **Opening value** → [FIFO Lot Analysis](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md)
- **Return** — the result since opening, in money (**Abs**) or percent (**%**): an **Aggregate return**, plus a line per lot when you compare several

**How to read it**

- **Comprehensive value above Opening value**: the lots gained, sales and income included.
- **A dashed line** in **Value** means a lot's current value is estimated at cost: its asset has no price at all — no market price, and no purchase or sale up to the end date.
- **A flat start**: until the asset's first price — market price, purchase or sale — a lot, for example one you received through an adjustment, is valued at what it cost you, with no gain or loss. A day whose price has no exchange rate is left out instead.

### 🧾 5. Lot Detail

The whole story of one lot. Open it with **View lot detail** (⋮) or by clicking its **Custody** cell.

**Metrics shown**

- **Summary** — opening and current value, proceeds, **FIFO P&L**, **Total P&L**, **Total return**, and **Cash yield** when the lot received income → [FIFO Lot Analysis](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md)
- **Net breakdown** — the total P&L minus the fees and taxes allocated to the lot → [Costs & Net Metrics](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md#costs-and-net-metrics)
- **Current Custody** and **History** — where the lot is now, and every event since its opening. A transfer between two of your brokers reads as two rows, *A → In transit* and *In transit → B*, even when the units leave and arrive on the same day

**How to read it**

- **Quantities are the broker's full holdings**, as the ⓘ beside them says.
- **A transfer with a broker outside the panel** counts as units coming in or going out. Units received open a new lot on the day they arrive, at the cost the transfer carries. Units sent close their lots on the day they leave, at that day's market price, so the gain they made at this broker counts as realized here. The lot's History labels these moves **TRANSFER+** and **TRANSFER-**, and the charts mark them as transfers — ◆ on Lot Life & Custody, **Transfer In** and **Transfer Out** on the markers of Avg. Cost / Market Price — without naming the other broker. To follow the original lots through the move, open the panel with both brokers (no broker filter on the Dashboard). A transfer still on its way on the panel's last day shows its units as in transit.
- **Go to transaction** opens the transaction of the History row you picked — by default, the opening one.

??? warning "⚠️ When the panel warns you"

    - **A folded banner** lists what is missing — a rate, a price, a purchase cost — with a chip per affected lot that finds its bubble. Fix it as for the [Data Quality banner](index.md#data-quality-banner). The folded banner also lists income and costs that no lot could take — a dividend paid after every lot was sold, for example — each with its own amount and date.
    - **A red message** means the quantities or transfers of some of the asset's transactions do not add up, so its lots cannot be rebuilt. It lists each transaction to fix with its day, its broker, what is wrong and a **Go to transaction** button. Meanwhile the panel hides the lots, their timeline and the comparison, and the first chart keeps only its **Avg. Cost** lines and the **Market Price**. Fix those transactions and the lots come back.
    - **Valued at cost**: on the days before the asset's first price — no market price, no purchase or sale — its lots are valued at what they cost, with no market gain or loss, and the banner names those days. With no price at all up to the end date, the lot's bubble has a dashed border.

---

## 🔗 Related

- 💰 **[KPI Cards](kpi-cards.md)** — the same results for the whole portfolio
- 💸 **[Transactions](../transactions/index.md)** — the Dashboard's **Transactions** tab lists the operations of the selected range and brokers
- 🛠️ **[Technical details](../../developer/frontend/pages/index.md#dashboard)** — for developers: how the Positions tab and the lots panel work inside

---

*[⬅️ Back to Dashboard Overview](index.md)*

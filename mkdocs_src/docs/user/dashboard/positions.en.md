# 🔍 Positions & Analysis

*[⬅️ Back to Dashboard Overview](index.md)*

The **Positions** tab of the dashboard allows you to inspect open holdings, analyze performance, and drill down into matching tax lots.

<div class="lf-screenshot-carousel" data-carousel="carousel-positions-views" data-carousel-interval="6000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
  <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="dashboard" data-name="positions-holdings-table" data-title="📋 Holdings (Table)" alt="Holdings Table View">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="positions-holdings-map" data-title="🗺️ Holdings (Map / Treemap)" alt="Holdings Map View">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="positions-performance-table" data-title="📈 Performance (Table)" alt="Performance Table View">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="positions-performance-map" data-title="📊 Performance (Map / Chart)" alt="Performance Map View">
</div>

---

## 🔍 Positions Tab

The **Positions** panel has two semantic modes: **Holdings** and **Performance**.

Use the view toggle to switch between them, and the table/map toggle to change the visual layout.

#### 📋 Holdings View

The **Holdings** view shows the current open-position snapshot. The table has 13 columns:

| Column | Description |
|:---|:---|
| **Asset** | Asset name with type icon — click to open the asset detail page. |
| **Δ1** | Change in unrealized P&L versus yesterday, keeping today's quantity constant. |
| **Δ1%** | The same daily change as a percentage of yesterday's position market value. |
| **Unrealized P&L** | Open gain/loss: current value minus residual cost basis. |
| **P&L %** | Unrealized P&L as a percentage of the residual cost basis. |
| **Annualized** | Net annualized return (CAGR) of the still-open lots, from the first transaction to today — for comparison across positions held for different durations. |
| **Value** | Total value at current market prices (\(\text{Price} \times \text{Quantity}\)). |
| **Weight** | Proportional share of this position relative to the total portfolio value. |
| **Qty** | Current shares, units, or coins held. |
| **Brokers** | Broker account(s) holding the position. |
| **Price** *(hidden by default)* | Current asset price from the connected data provider. |
| **Avg. Cost** *(hidden by default)* | Average cost per unit of the currently open position (Weighted Average Cost). |
| **Oldest open lot** *(hidden by default)* | Opening date of the oldest FIFO lot still open for this position. |

Use the **eye icon** in the table toolbar to show or hide columns — your choices are remembered across sessions.

#### 📈 Performance View

The **Performance** view loads on demand and shows open and closed positions together. In the table/chart, **Status** is filterable inside the component, not a top-level toggle.

#### 🗺️ Visual Style: Table vs. Map

| Visual Mode | Core Features | Optimal Use Case |
|:---|:---|:---|
| **📋 Table View** | • Sortable grid layout<br>• Precise numerical values<br>• Quick column sorting | Standard bookkeeping, searching specific asset quantities, or comparing WAC values. |
| **🗺️ Map View** | • Visual Treemap visualization<br>• Size indicates asset weight<br>• Color intensity indicates performance (green = gain, red = loss) | Quick visual diagnostics, spotting over-allocation, or identifying underperforming assets. |

---

## 🔬 FIFO Lots Analysis {: #fifo-lots-analysis }

When you click on a position in either Table or Map view, LibreFolio expands an inline **FIFO Lots Analysis** panel directly **below** the Positions view. It uses a vertical slide transition and scrolls into view automatically — it is **not** a right-side slide-over. If needed, a data-quality banner appears first, then the analysis blocks stay in this order: WAC / Market Price, Lot Life & Custody, unified lots table, Value / Return comparison, and the lot detail modal. By default, no explicit selection means **all currently visible lots** are included across the linked charts.

<div class="lf-screenshot-carousel" data-carousel="carousel-fifo-lots-analysis" data-carousel-interval="6000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
  <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="dashboard" data-name="fifo-lots-panel" data-title="🔍 Overview" alt="FIFO Lots Analysis Overview">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-wac-chart" data-title="📈 WAC / Market Price" alt="WAC and Market Price Chart">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-gantt-chart" data-title="🕒 Lot Life & Custody" alt="Lot Life and Custody Gantt Chart">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-table" data-title="📋 Unified Lots Table" alt="Unified Lots Table">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-comparison-chart" data-title="💰 Value Comparison" alt="Value Comparison Chart">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-comparison-chart-return" data-title="📊 Return Comparison" alt="Return Comparison Chart">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-custody-modal" data-title="🧾 Lot Detail Modal" alt="Lot Detail Modal">
</div>

### 1. WAC / Market Price

This first chart compares the asset's **Market Price** with the per-broker **WAC** lines and the combined WAC line for the selected position.

- Toggle **ABS / %** to switch between absolute prices and percentage evolution from the range start.
- In **ABS** mode, toggle **Auto / From 0** to choose whether the Y axis is tightly fitted or forced to start at zero.
- Event markers and lot-performance bubbles help you connect buys, sells, transfers, splits, and income events to the cost basis history.
- Clicking lot bubbles updates the shared lot selection used by the other blocks.
- **Bubble color** matches the lot's **opening broker** — the same colors used by the custody bars in block 2 below.
- **Bubble size** reflects the lot's **opening value** (its original cost basis): larger bubbles started as larger investments.
- A **dashed bubble border** marks a lot currently shown **at cost** because no live market price is available for it yet.

🔗 **Theory**: Refer to **[Weighted Average Cost (WAC)](../../financial-theory/technical-analysis/performance-metrics/weighted-average-cost.md)** for cost-basis rules, and **[Valuation Price Chain](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md#valuation-price-chain)** for how market prices are resolved.

### 2. Lot Life & Custody

The **Lot life & custody** block is a Gantt-style timeline showing when each lot was open and where it was held over time.

- Use the **Open / Closed** filter to show only open lots, only closed lots, or both.
- Each bar represents a lot's life; transfers create extra custody lanes so you can see broker-to-broker moves and in-transit periods.
- **Bar color** identifies the **custody broker** currently holding that segment of the lot — matching broker badges are listed in the legend below the chart. A dashed violet segment marks a period **in transit** between brokers (transfer initiated but not yet arrived).
- **Bar thickness** is proportional to the **quantity held** during that exact segment — a lot that was partially sold or split shows thinner bars afterward.
- Clicking a bar selects that lot across the shared analysis; double-clicking can jump back to the matching row in the table.

🔗 **Theory**: See **[FIFO Engine — Lot Lifecycle & Matching Model](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/index.md)** for how lot states, splits, and transfers between brokers are defined.

### 3. Unified Lots Table

v3 replaces the old split **Open Lots** and **Closed Lots** tables with one **unified table**.

- The table shows the current lot set with columns such as opening date, total return, current value, custody, and **Status**.
- Shared filtering means the table always reflects the same visible lot set as the charts above.
- Each row's **Actions** menu includes:
    - **View lot detail**
    - **Go to lot in Gantt**
    - **Go to opening transaction**
    - **Copy lot identifier**

### 4. Value / Return Comparison

This comparison chart focuses on the lots currently selected in the panel. If you have not selected specific lots, it uses **all visible lots**.

- Switch between **Value** and **Return** using the top-right mode toggle.
- **Value** mode compares the selected lots in absolute money terms and also offers the **Auto / From 0** Y-axis toggle.
- **Return** mode compares percentage return from each lot's opening date across the same selected lot set.

### 5. Lot Detail Modal

Choose **View lot detail** from the table row actions to open the **FIFO Lot Detail** modal for a specific lot.

- The summary includes **Total P&L**, **Total return**, **Asset income**, **Cash yield**, FIFO P&L, opening/current value, and other lot-level metrics.
- **Current Custody** shows how the lot is currently distributed across brokers or in-transit slices.
- **History** lists the full custody and lifecycle chronology, including transfers and other lot events, with a direct **Go to transaction** action for the relevant transaction.

!!! info "FIFO matching logic"

    LibreFolio resolves lot closures strictly with **First-In, First-Out (FIFO)** matching: sell quantities always consume the **oldest eligible open lot first** before newer lots are touched.

    For deeper theory and formulas, see:

    - **[Taxation Theory](../../financial-theory/fundamentals/taxation.md)**
    - **[Buy/Sell Transaction Model](../../financial-theory/instruments/transaction-types/buy-sell.md#fifo-matching)**
    - **[FIFO Lot Analysis](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md)**

---

## 💸 Transactions Tab

The **Transactions** tab on the Dashboard displays a complete, paginated list of all operations recorded across the active portfolio scope (buy/sell orders, dividend payouts, cash deposits, transfers, etc.).

For a detailed explanation of the transaction list, filters, and how to read the read-only transaction details, please refer to the dedicated **[Transactions Overview](../transactions/index.md)** page.

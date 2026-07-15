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

The **Positions** tab provides a detailed breakdown of all the financial instruments currently held in your portfolio (Stocks, ETFs, Bonds, Cryptocurrencies, etc.). 

The Positions tab allows you to switch between two primary metric modes using the view toggle, each focusing on a different aspect of your holdings:

#### 📋 Holdings View

The **Holdings** view focuses on bookkeeping, quantities, and current asset valuation. It helps you monitor your current portfolio exposure and baseline metrics.

| Metric | Description |
|:---|:---|
| **Quantity** | Current shares, units, or coins held in your portfolio. |
| **Market Price** | Live asset price retrieved from the connected data provider. |
| **Market Value** | Total value at current market prices (\(\text{Price} \times \text{Quantity}\)). |
| **Average Price (WAC)** | The Weighted Average Cost paid to acquire the current open position. |
| **Weight** | Proportional share of this asset relative to the total portfolio value. |

#### 📈 Performance View

The **Performance** view focuses on absolute and relative returns. It helps you analyze the profitability of your open positions, factoring in historical transactions and income.

| Metric | Description |
|:---|:---|
| **Total Value** | Current value of the holdings (matches Market Value). |
| **Unrealized P&L** | Paper gain or loss calculated as \(\text{Market Value} - \text{Book Value}\). |
| **ROI %** | Rate of return relative to the cost basis of the position. |
| **Total P&L** | Cumulative absolute returns (includes past closed sales & dividends). |

#### 🗺️ Visual Style: Table vs. Map

| Visual Mode | Core Features | Optimal Use Case |
|:---|:---|:---|
| **📋 Table View** | • Sortable grid layout<br>• Precise numerical values<br>• Quick column sorting | Standard bookkeeping, searching specific asset quantities, or comparing WAC values. |
| **🗺️ Map View** | • Visual Treemap visualization<br>• Size indicates asset weight<br>• Color intensity indicates performance (green = gain, red = loss) | Quick visual diagnostics, spotting over-allocation, or identifying underperforming assets. |

---

## 🔬 FIFO Lots Analysis {: #fifo-lots-analysis }

When you click on a position in either Table or Map view, a **FIFO Lots Analysis** panel slides out from the right side of the screen. This panel provides a deep-dive tax and lot matching history for that specific asset.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="fifo-lots-panel" alt="FIFO Lots Analysis Panel">
</div>

### 1. Bubble Timeline

The **Bubble Timeline** chart visualizes all buys and sells over the selected period:

- 🟢 **Green Bubbles**: Represent buy transactions. The size of the bubble represents the quantity purchased.
- 🔴 **Red Bubbles**: Represent sell transactions. The size represents the quantity sold.
- 🔵 **Blue Line**: Traces the historical progression of your Weighted Average Cost (WAC/Book value per share).
- 🔍 **Tooltips**: Hovering over any bubble reveals the date, transaction type, quantity, and transaction price.

### 2. WAC Price Chart

This chart overlays the **Weighted Average Cost (WAC)** line onto the historical **Market Price** line. This helps you visualize when you bought relative to market movements and whether your current holdings are in profit or loss.

🔗 **Theory**: Refer to **[Weighted Average Cost (WAC)](../../financial-theory/technical-analysis/performance-metrics/weighted-average-cost.md)** for how cost basis is computed, and **[Valuation Price Chain](../../financial-theory/technical-analysis/performance-metrics/nav.md#valuation-price-chain)** for how market prices are resolved by data providers.

### 3. Open Lots Table

Displays active **Tax Lots** that are currently open (not yet matched with a sale). It shows:

- 📅 **Acquisition Date**: The exact date the shares were bought.
- 💰 **Acquisition Price**: The original purchase price.
- 📦 **Quantity remaining**: The shares from this lot still held.
- 📊 **Lot Value**: Current market value of this specific lot.
- 📈 **Unrealized P&L**: Gain or loss specific to this purchase.

### 4. Closed Lots Table

Displays the **realized sales** history where a buy lot was matched against a sell lot. It helps you track:

- 🤝 **Matching Date**: The sale date.
- 📦 **Quantity matched**: The shares closed.
- 💸 **Realized P&L**: The final gain or loss recognized from matching this purchase with the sale.

!!! info "FIFO matching logic"

    LibreFolio resolves tax lots strictly following the **First-In, First-Out (FIFO)** accounting methodology. The oldest acquired shares are matched first against any incoming sell operations.

    For a detailed theoretical overview of how FIFO matching maps to capital gains computation and taxation, please refer to **[Taxation Theory](../../financial-theory/fundamentals/taxation.md)** and the **[Buy/Sell Transaction Model](../../financial-theory/instruments/transaction-types/buy-sell.md#fifo-matching)**.

---

## 💸 Transactions Tab

The **Transactions** tab on the Dashboard displays a complete, paginated list of all operations recorded across the active portfolio scope (buy/sell orders, dividend payouts, cash deposits, transfers, etc.).

For a detailed explanation of the transaction list, filters, and how to read the read-only transaction details, please refer to the dedicated **[Transactions Overview](../transactions/index.md)** page.

# 🏦 Brokers

A **Broker** in LibreFolio represents a brokerage account — the place where your investments live (e.g., Interactive Brokers, Degiro, a bank account).

All transactions, reports, and import data are tied to a broker. You need at least one broker to start tracking your portfolio.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="list" alt="Broker List" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## ➕ Creating a Broker

1. Navigate to the **Brokers** page from the sidebar
2. Click **"New Broker"**
3. Fill in the details: name, base currency, and optionally an icon
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="edit-modal" alt="Broker Edit Form" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

4. The broker appears in your list, ready to receive transactions and reports
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="detail" alt="Broker Edit Form" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>
---

## 🗂️ Broker Detail Layout

Once you select a broker from the list, the interface is split into four primary tabs:

1. **Overview**: Display of net worth, return metrics, growth history, and allocation charts scoped exclusively to this broker account (see **[Dashboard Overview](../dashboard/index.md)**).
2. **Positions**: List of open positions, asset weights, and performance metrics within this broker, with access to the FIFO Lots slide-over (see **[Dashboard Positions](../dashboard/positions.md)**).
3. **Transactions**: The ledger of all financial activities, including manual entries, statement imports, and histories (see **[Importing Transactions](import.md)**).
4. **Info**: Broker metadata, cash overdraft/shorting configurations, AI Export, and inline sharing controls (see **[Configuration & Info](info.md)**).

---

## 📈 Overview Tab

The **Overview** tab acts as a local dashboard for the selected broker. It contains the same elements as the main **[Dashboard Overview](../dashboard/index.md)** but scoped exclusively to this broker account:
- **Local KPI Cards**: Net Worth, Period P&L, and Returns specific to this broker. (See **[Dashboard KPI Cards](../dashboard/kpi-cards.md)** for calculation details).
- **Cash Balances Panel**: Liquid cash held in this broker account, broken down by currency.
- **Growth Chart**: Historical growth of this account value (see **[Portfolio Growth Chart](../dashboard/charts.md#portfolio-growth-chart)**).
- **Allocation Panel**: Portfolio composition (by Type, Sector, and Geography) for holdings held at this specific broker (see **[Allocation Panel](../dashboard/charts.md#allocation-panel)**).

---

## 🔍 Positions Tab

The **Positions** tab lists all active assets currently held under this broker. It is identical in functionality to the main **[Dashboard Positions](../dashboard/positions.md)** view, but scoped only to this broker:

<div class="lf-screenshot-carousel" data-carousel="carousel-broker-positions" data-carousel-interval="6000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
  <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="brokers" data-name="positions-holdings-table" data-title="📋 Holdings (Table)" alt="Broker Holdings Table View">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="positions-holdings-map" data-title="🗺️ Holdings (Map / Treemap)" alt="Broker Holdings Map View">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="positions-performance-table" data-title="📈 Performance (Table)" alt="Broker Performance Table View">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="positions-performance-map" data-title="📊 Performance (Map / Chart)" alt="Broker Performance Map View">
</div>

- **Toggles & Layouts**: You can toggle between **Holdings** (quantities, values, weights) and **Performance** (unrealized P&L, ROI %) metrics, and choose between a **Table** or **Map** (treemap) layout.
- **FIFO Analysis**: Click on any asset row or card to open the **FIFO Lots Analysis** slide-over panel. (See **[FIFO Lots Analysis](../dashboard/positions.md#fifo-lots-analysis)** for detailed matching rules).

---

## 📑 In This Section

- 📥 **[Importing Transactions (BRIM)](import.md)** — How to manually record transactions, run the BRIM CSV/Excel import wizard, and view import logs.
- ⚙️ **[Configuration & Info](info.md)** — Metadata settings (overdrafts, shorting), scoped AI Export prompt generator, and the inline broker sharing panel.
- 🤝 **[Broker Sharing](sharing.md)** — Detailed guide on role permissions (Owner, Editor, Viewer) and asset percentage settings.

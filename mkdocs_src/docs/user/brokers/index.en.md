# 🏦 Brokers

A **broker** is one of your accounts — at a brokerage, a bank or an exchange: the place where your investments and your cash live. Every transaction and every uploaded report belongs to a broker, so you need at least one before you start.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="list" alt="Broker List" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

The **Brokers** page shows one card per broker, with its value (**NAV**) in the currency chosen in **Currency** at the top of the page. Click a card to open the broker.

!!! note "Shared brokers show your share"

    On a broker you co-own, the values on its card and in its **Overview** tab are **scaled by your ownership share**: a 50% Owner sees half of the account. Editors and Viewers always see the full amounts. See [Broker Sharing](sharing.md).

---

## ➕ Create a broker

1. Open **Brokers** from the sidebar and click **Add Broker**.
2. Type a **Name** — the only required field — and set the options you need.
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="edit-modal" alt="Broker Edit Form" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

3. Click **Create**: the broker appears in your list, ready for transactions and reports.
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="detail" alt="Broker Edit Form" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

??? info "⚙️ The optional fields — what each one does"

    - **Description** — your own notes.
    - **Default Import Plugin** — the importer that the [Import Wizard](../transactions/import/index.md) proposes for this broker's files.
    - **Portal URL** — the broker's website, opened from the broker page. Its icon is used when you set no **Custom Icon URL**.
    - **Account Opened** and **Account Active** — when the account was opened, and whether it is still open. A closed broker shows dimmed in the list.
    - **Trading Options** — **Allow Leveraged Buying** and **Allow Short Selling**, explained in [Trading options](info.md#trading-options).
    - **Initial Balances** (only when creating) — your starting cash. LibreFolio records one **Deposit** per currency, **dated today**: if the money was there earlier, change the date of those deposits on the [Transactions](../transactions/index.md) page.

??? warning "🏷️ “A broker named … already exists” — when it appears"

    Broker names are unique on the whole server, across all its users. Choose a different name, or rename the existing broker if it is yours.

    Brokers of other users that you cannot open are listed under **Other Existing Brokers**. Their share button shows who has access, so you know whom to ask: every signed-in user of this LibreFolio can see it, for any broker.

---

## ✏️ Edit or delete a broker

- **Edit** — the pencil on the broker card, or **Edit** in the broker's toolbar. Owners and Editors can edit a broker.
- **Delete** — the bin on the broker card. Only an Owner can delete a broker. If it still holds transactions, LibreFolio says how many and offers **Go to transactions** or **Delete broker and transactions**, which deletes them as well.

---

## 🗂️ Inside a broker

The toolbar at the top applies to every tab:

- the **date range** and the **Currency** of the figures;
- **Edit**, **Share Broker** (it opens the **Info** tab) and **Refresh**;
- **AI Export**, which copies a ready-made prompt about this broker to your clipboard — see [Broker AI Export](../ai-export/broker.md).

Below it, five tabs:

1. **Overview** — how the account is doing (below).
2. **Positions** — what you hold at this broker (below).
3. **Risk** — the Dashboard's risk analysis, limited to this broker (see [Dashboard Risk Tab](../dashboard/index.md#risk-tab)).
4. **Transactions** — the broker's ledger, manual entries, imports and uploaded reports (see [Broker Transactions](import.md)).
5. **Info** — account details, trading options and sharing (see [Configuration & Info](info.md)).

---

## 📈 Overview tab

The **Overview** answers "how is this account doing?" with the same blocks as the [Dashboard Overview](../dashboard/index.md), limited to this broker:

- **KPI cards** — **Period P&L**, **Returns** and **Net Worth** ([KPI Cards](../dashboard/kpi-cards.md)).
- **Cash Balances** — the cash held here, per currency.
- **Growth chart** — the **Abs**, **%** and **P&L** views, with P&L as **Line**, **Candles** or **Income** ([Portfolio Growth Chart](../dashboard/charts.md#portfolio-growth-chart), [P&L mode](../dashboard/charts.md#pnl-mode)). The view you pick is shared with the Dashboard.
- **Allocation** — by type, sector and geography ([Allocation Panel](../dashboard/charts.md#allocation-panel)).

Coming back to a broker you already opened shows its last figures at once, refreshed in the background if something changed ([Coming back and refreshing](../dashboard/index.md#coming-back-and-refreshing)). **Refresh** recalculates on demand, the **Risk** tab and the lots panel included.

---

## 🔍 Positions tab

The **Positions** tab lists what you hold at this broker, in the same panel as the [Dashboard Positions](../dashboard/positions.md):

<div class="lf-screenshot-carousel" data-carousel="carousel-broker-positions" data-carousel-interval="6000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
  <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="brokers" data-name="positions-holdings-table" data-title="📋 Holdings (Table)" alt="Broker Holdings Table View">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="positions-holdings-map" data-title="🗺️ Holdings (Map / Treemap)" alt="Broker Holdings Map View">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="positions-performance-table" data-title="📈 Performance (Table)" alt="Broker Performance Table View">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="positions-performance-map" data-title="📊 Performance (Map / Chart)" alt="Broker Performance Map View">
</div>

- **Portfolio** shows your holdings (quantity, value, weight); **Period** shows each position's gains and losses over the selected dates. Both come as a **Table** or a **Map**.
- The **YOC** column is each holding's [Yield on Cost](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/yield-on-cost.md) at this broker.
- **Analyze Lots** opens the [FIFO Lots Analysis](../dashboard/positions.md#fifo-lots-analysis) panel below the list: find it in a row's **⋮** menu, or right-click the asset in the table or the map.

---

## 📑 In this section

- 📥 **[Broker Transactions](import.md)** — add transactions to this broker, import statements and manage its uploaded reports.
- ⚙️ **[Configuration & Info](info.md)** — account details, trading options and the sharing panel.
- 🧠 **[Broker AI Export](../ai-export/broker.md)** — what a broker export contains, and the analyses you can ask an AI for.
- 🤝 **[Broker Sharing](sharing.md)** — roles (Owner, Editor, Viewer) and ownership shares.

The Brokers page, the **Add Broker** form and the broker page each have a short contextual guide: replay them from [Settings → Preferences → Onboarding and guides](../settings/preferences.md#onboarding-and-guides).

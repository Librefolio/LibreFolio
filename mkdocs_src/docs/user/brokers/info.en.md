# ⚙️ Broker Configuration & Info

The **Info** tab of a broker shows the account's details on the left and who can access it on the right.

<div class="screenshot-container" style="max-width: 700px; margin: 1.5rem auto 2rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="info-tab" alt="Broker Info and Sharing View">
</div>

---

## 📋 Account details

The **Details** card lists:

- **Account Active** — **✓ Active**, or **✗ Closed** for an account you no longer use. A closed broker keeps its history in your charts.
- **Account Opened** — when you opened the account, if you set it.
- **Allow Leveraged Buying** and **Allow Short Selling** — the two trading options, explained below.
- **Created in System** — when the broker was added to LibreFolio.

To change them, click **Edit** in the broker's toolbar (Owners and Editors).

---

## 🛡️ Trading options {: #trading-options }

Both options are off for a new broker, and LibreFolio then guards you against impossible balances:

- with **Allow Leveraged Buying** off, a save is refused if it would leave the cash of a currency below zero;
- with **Allow Short Selling** off, a save is refused if it would leave the quantity of an asset below zero.

Turn an option on for a margin account, or to record short sales.

??? note "📅 How balances are checked — when a save is refused"

    For each currency $c$ and each asset $i$ of the broker, LibreFolio looks at the balance at the **end of every day** $d$, after all of that day's transactions:

    $$
    C_c(d) = \sum_{\text{date}_t \le d} a_t \ge 0 \qquad\qquad Q_i(d) = \sum_{\text{date}_t \le d} q_t \ge 0
    $$

    Here $a_t$ is the cash amount of each transaction $t$ in currency $c$, and $q_t$ the quantity of each transaction of asset $i$. Money in and out on the same day nets out, but a deposit made later does not fix a day that already closed below zero.

    A refused save shows in the workspace under *This configuration causes data inconsistencies*, with the currency or asset, the date, and links to the workspace rows involved.

---

## 🤝 Share the broker

The right column holds the **Share Broker** panel; **Share Broker** in the toolbar brings you here too. Only an Owner can change it: everyone else sees it read-only.

To give someone access:

1. Click **+** (**Add User**) under the ownership chart and find the person **by username**.
2. Choose the **Role** — **Viewer** by default, **Editor** or **Owner** — and, for an Owner, the **Ownership %**. Then click **Add User**.
3. Click **Save Configuration**: nothing changes before you do.

Save before you switch tab: on the Info tab, unsaved changes are dropped without asking.

Under **Your access** you can also **Leave broker**, or **Switch to viewer** if you are an Editor. Roles and ownership shares are explained in [Broker Sharing](sharing.md).

---

## 🔗 Related

- 🧠 **[Broker AI Export](../ai-export/broker.md)** — **AI Export** sits in the broker's toolbar and works from every tab.
- 🏦 **[Brokers](index.md)** — creating a broker and its optional fields.

# 📥 Broker Transactions

The **Transactions** tab is the control center for modifying the broker's ledger. It lists all recorded financial operations (buys, sells, dividends, deposits, withdrawals, transfers, and FX conversions) scoped to this broker.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="transactions-tab" alt="Broker Transactions Tab">
</div>

From this tab, you can record transactions manually or launch bulk statement imports.

---

## ➕ Manual Transactions

Click the **Add Transaction** (`Plus` icon) button to open the single transaction modal wizard. This lets you manually record:

- **Buy / Sell**: Trade assets, specifying date, price, quantity, and currency.
- **Dividend / Income**: Income received from asset holdings.
- **Deposit / Withdrawal**: External cash inflows or outflows to/from the broker cash balance.
- **Transfer**: Transfer of cash or assets between brokers (e.g., funding the account from a bank broker).
- **FX Conversion**: Currency exchanges inside the broker account.

For a detailed explanation of transaction fields and validation rules, see the **[Transaction Form](../transactions/form.md)** guide.

---

## 🧙 Bulk Import (BRIM)

The **Import** (`Upload` icon) button launches the **BRIM** (Broker Report Import Module) wizard, which imports your broker's exported statements in bulk: it parses the files, validates every row, unifies the securities found, checks for duplicates, and lets you review everything before anything is written. Approved rows land in the **bulk editor**, where a final **Save All** commits them to the ledger.

The same wizard is also available from the global **[Transactions](../transactions/index.md)** page. For the full walkthrough see the dedicated guides:

- 📥 **[Import from Broker (BRIM)](../transactions/import/index.md)** — supported brokers, formats, and per-plugin notes.
- 🧙 **[How to Import Transactions](../transactions/import/how-to.md)** — the wizard, step by step.

---

## 🧩 Missing Your Broker?

If your broker has no import plugin yet, you can help:

- **Request a plugin** — open a [plugin request](https://github.com/Librefolio/LibreFolio/issues/new?template=plugin_request.yml) on GitHub, attaching an anonymized sample of the broker's export file so the format can be understood. (The wizard's Corrections step also carries an "open an issue" banner for reporting rows that look wrong.)
- **Write a plugin** — the [BRIM Plugin Guide](../../developer/architecture/patterns/brim_plugin_guide.md) walks developers through the provider contract; see [Contribute](../../community/contribute.md) for the general workflow.

---

## 🗂️ Uploaded Reports

Click the **Uploaded Reports** (`FileText` icon) button to manage the BRIM report files stored for this broker. The modal lets you:

- Review the uploaded reports (name, upload date, size, status), with a quick **preview** of each file's content.
- **Upload** new reports directly — they are auto-assigned to this broker and become available in the wizard's Select Files step.
- **Delete** reports you no longer need.
- Jump to the full **[Files & Uploads](../files/index.md#broker-reports)** page, pre-filtered on this broker.

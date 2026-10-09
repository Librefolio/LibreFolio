# 💸 Transactions

Transactions are every movement in your portfolio: purchases, sales, dividends, fees, transfers, and cash in or out. LibreFolio computes your positions, performance and costs from them, so a complete ledger keeps every figure right.

<div class="screenshot-container">
    <img class="gallery-img" data-category="transactions" data-name="list" alt="Transaction List">
</div>

The **Transactions** page lists the transactions of all the brokers you can access, newest first. Each broker also shows its own in its [Transactions tab](../brokers/import.md).

---

## 🔎 Find and open a transaction

- **Sort** — click a column header.
- **Filter** — open the filter of a column (date, type, asset, broker, tags, description…). Your filters are kept in the page address, so a bookmark reopens the same view.
- **Open** — double-click a row to see it read-only; the pencil switches to editing.

Without filters or sorting, the two rows of a linked pair (a transfer or a currency exchange) stay next to each other, and the link icon jumps to the partner row.

---

## ➕ Add or import transactions

- **Add Transaction** opens the [bulk workspace](#bulk-workspace) on a **New transaction** form: fill it in ([Transaction Form](form.md)), click **Apply**, then **Save All**.
- **Import** opens the workspace with the **Import Wizard**, which reads the files exported by your broker — see [Import from Broker](import/index.md).

---

## ✏️ Edit, clone or delete transactions

- **One row** — right-click it, or use its row actions: **View**, **Edit**, **Clone**, **Split pair** or **Delete**. You only see the actions your role on that broker allows.
- **Several rows** — tick them, then choose **Edit**, **Clone** or **Delete** in the selection bar. **Edit** and **Delete** leave out the rows of brokers where you are only a Viewer.

Each of these opens the bulk workspace, and nothing changes before **Save All**. Editing or deleting one side of a linked pair brings its partner along.

**Clone** keeps the original date: it is how you re-record a historical row, for example under another type.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="transactions" data-name="clone-flow" alt="Bulk workspace with a cloned transaction row">
</div>

---

## 🔗 Link or unlink a pair {: #link-pairs }

Some operations are two linked transactions — see [Paired transactions](form.md#composite-transactions).

- **Link** — tick two single rows that belong together and click **🔗 Promote pair**. Two **Adjustments** become an **Asset Transfer**; a **Withdrawal** and a **Deposit** become a **Currency Exchange** (same broker, two currencies) or a **Cash Transfer** (two brokers, same currency and amount). If the rows disagree on date, description, tags or cost basis, you choose what to keep.
- **Unlink** — **Split pair** on a linked row turns it back into two single rows.

Both ask for confirmation, then save at once, without the workspace.

---

## 🧰 The bulk workspace {: #bulk-workspace }

The workspace is a grid of draft rows — marked **new**, **edit** or **del** — where you prepare changes before writing them:

- **Add Row**, **Import** and **Reset All** sit above the grid. Ticking rows adds **Reset selected**, **Delete selected** and, for a matching pair, **🔗 Promote pair**.
- Rows are checked as you work: problems appear at the top under *Validation errors were found*, and a click takes you to the row. With many rows, automatic checking pauses — press **⚡ Validate now** before saving.
- When two rows look like the two halves of one transfer or exchange, a green banner offers to **Merge** them — two new rows, two saved ones, or one of each.
- When the other half is already saved but not in the workspace — a transfer whose first side you imported last month, say — the 💡 button, above the grid and in the row's menu, offers to add it: once it is in, the banner offers the pair.
- **Save All** writes everything at once. **Cancel** closes the workspace, asking first if you have unsaved changes.

??? warning "🚦 Banners after an import — when they appear"

    After an import, banners above the grid list what to check before **Save All**:

    - **red** — rows the importer did not fully understand: **Save All** stays disabled until you complete them;
    - **amber** — auto-derived fields to verify: **Save All** first asks you to **Review** them or **Save anyway**.

    Click a banner to unfold its list, then an entry: the grid turns to that row's page and highlights it. Balance problems list the rows that cause them (*Workspace rows: …*), and a click opens the first one in the current sort order. If your column filters hide the row, a message tells you so.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="transactions" data-name="bulk-todo-banner" alt="Bulk workspace with the banner of fields to verify unfolded and the clicked entry's row highlighted in the grid">
</div>

After a save, a **Promote pair** or a **Split pair**, the Transactions page clears its selection, since those rows may have changed; closing or cancelling keeps it.

---

## 🧭 Contextual guides

The Transactions page, the **Add Transaction** form, the bulk workspace and the [Import Wizard](import/how-to.md#guided-first-import) each have a short guide. A guide starts only when its screen is ready and never edits a draft or presses a button for you; in the workspace it shows one notice at a time, closed with **Got it**.

Replay any guide from [Settings → Preferences → Onboarding and guides](../settings/preferences.md#onboarding-and-guides).

---

## 🔗 Related

* 📝 **[Transaction Form](form.md)** — fields and transaction types
* 📥 **[Import from Broker](import/index.md)** — the BRIM import workflow
* 📖 **[Transaction Types](../../financial-theory/instruments/transaction-types/index.md)** — the financial theory behind each type

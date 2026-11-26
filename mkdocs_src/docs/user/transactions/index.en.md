# 💸 Transactions

Transactions are every movement in your portfolio: purchases, sales, dividends, fees, transfers, and cash in or out. LibreFolio computes your positions, performance and costs from them, so a complete ledger keeps every figure right.

<div class="screenshot-container">
    <img class="gallery-img" data-category="transactions" data-name="list" alt="Transaction List">
</div>

The **Transactions** page lists the transactions of all the brokers you can access, newest first. Each broker also shows its own in its [Transactions tab](../brokers/import.md).

---

## 🔎 Find and open a transaction

- **Sort** — click a column header.
- **Filter** — open the filter of a column (date, type, asset, broker, tags, description…). In the date filter, type a date in **From** only to see the transactions from that day on, or in **To** only for those up to that day; the two ends of a range must be different days. Your filters are kept in the page address, so a bookmark reopens the same view.
- **Open** — double-click a row to see it read-only; the pencil switches to editing.
- **Unit price** — a column next to the amount shows the price per unit a trade implies (the amount divided by the quantity, per the asset's quote base); it is read-only and empty for a row without a quantity and an amount, and for the legs of a linked pair. Hide it from the column menu if you do not need it. The bulk editor has the same column.

Without filters or sorting, the two rows of a linked pair (a transfer or a currency exchange) stay next to each other, and the link icon jumps to the partner row.

---

## ➕ Add or import transactions

- **Add Transaction** opens the [bulk workspace](#bulk-workspace) on a **New transaction** form: fill it in ([Transaction Form](form.md)), click **Apply**, then **Save All**.
- **Import** opens the workspace with the **Import Wizard**, which reads the files exported by your broker — see [Import from Broker](import/index.md).

---

## ✏️ Edit, clone or delete transactions

- **One row** — right-click it, or use its row actions: **View**, **Edit**, **Clone**, **Split pair** or **Delete**. You only see the actions your role on that broker allows.
- **Several rows** — tick them, then choose **Edit**, **Clone** or **Delete** in the selection bar above the table. Each action shows how many rows it acts on: **Edit** and **Delete** leave out the rows of brokers where you are only a Viewer. When you scroll the list down, the same actions move into the bar at the bottom, above the pages.

Each of these opens the bulk workspace, and nothing changes before **Save All**. Editing or deleting one side of a linked pair brings its partner along. Deleting a transaction that has linked charges first asks what to do with them — see [Linked charges](#linked-charges).

**Clone** keeps the original date: it is how you re-record a historical row, for example under another type. Cloning a transaction with linked charges copies its charges too, linked to the copy; cloning a charge gives a copy linked to the same transaction. If you remove the copy of a transaction from the batch, the copies of its charges you have not changed go with it. While the copy and its charges are all new, they share broker and asset: correct the asset of the copy, or of one of its charges, and the others follow, each keeping its own date.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="transactions" data-name="clone-flow" alt="Bulk workspace with a cloned transaction row">
</div>

---

## 🔗 Link or unlink a pair {: #link-pairs }

Some operations are two linked transactions — see [Paired transactions](form.md#composite-transactions).

- **Link** — tick two single rows that belong together and click **🔗 Promote pair**. Two **Adjustments** become an **Asset Transfer**; a **Withdrawal** and a **Deposit** become a **Currency Exchange** (same broker, two currencies) or a **Cash Transfer** (two brokers, same currency and amount). If the rows have a different description or different tags, you choose what to keep; each row keeps its own date. A description holds at most 500 characters: the dialog counts them and keeps **Confirm promotion** disabled until the description fits.
- **Unlink** — **Split pair** on a linked row turns it back into two single rows. An **Asset Transfer** becomes two **Adjustments**: the receiving one keeps its cost, and the sending one takes the units out without a value: on its broker they only leave the quantity, and their cost counts as a realized loss (see [Outgoing Adjustments](../../financial-theory/instruments/transaction-types/adjustment.md#outgoing-adjustments)).

Both ask for confirmation, then save at once, without the workspace.

---

## 📎 Linked charges {: #linked-charges }

A **Fee** or a **Tax** can be linked to the transaction it was paid for, and stays a transaction of its own. What can be linked to what, and how the form shows it, is in [Linked charges](form.md#linked-charges).

- **In the list** — while the table is not sorted and not filtered on the type, a transaction's charges fold under it. The badge **N charges** (or the 🔗 next to it) opens and closes them; each charge shows `↳`, and its 🔗 takes you to its transaction. Sort the table, or filter it on the type, and every charge is a row of its own again, still marked `↳`.
- **Link** — tick one transaction and the charges that belong to it, then click **Link** in the selection bar. A window shows the rows and what they become; **Link** saves at once. When the selection cannot be linked — another broker, another asset, half of a pair, a charge already linked elsewhere, two transactions — **Link** is greyed out: tap it, or reach it with the keyboard, to read why.
- **Unlink** — tick the charges to separate, on this page or on a broker's **Transactions** tab, and click **Unlink** in the selection bar: its number says how many of the ticked rows are linked charges, and a ticked transaction does not bring its charges along. A window shows each charge and the transaction it is linked to; **Unlink** saves at once, and each charge stays as a transaction of its own.
- **Delete** — when you delete a transaction whose charges are not all in your selection, from this page or from a broker's **Transactions** tab, a window asks first:
    - **Keep the charges** — they stay, as transactions of their own, no longer linked;
    - **Delete all (N)** — the charges go with it.

    Either way the bulk workspace opens with the rows marked, and nothing changes before **Save All**. **Cancel** opens nothing.

---

## 🔁 Relink events {: #relink-events }

A dividend, an interest payment or an adjustment can be linked to the asset's **event** (the dividend the provider announced, a split…). The link is lost when [changing an asset's currency](../assets/create-edit.md#changing-the-currency) deletes the events it pointed to, and a dividend you booked before its event was downloaded never had one. **Relink events**, in the toolbar above the table, finds those transactions and proposes the event to link.

The window lists your **dividends, interest and adjustments** that have an asset and no event, on the brokers where you are at least an Editor, newest first. They are split into three groups, one table each; a group with no transaction is not shown. Each row shows the asset and its broker, the date, the transaction's movement and the event:

| Group | Meaning | What you can do |
|-------|---------|-----------------|
| **With one event** | Exactly one event of the same asset, on the same day, of the matching type: the row shows its value | **Link** the row, or **Link all** the rows of the group |
| **Without an event** | The asset has no such event on that day | **Create event** (or **Create all**): enter its value, and the event is created and the row linked to it in one step; or, when the event is on another day, link it in the transaction (below) |
| **Several events** | More than one candidate | **Choose event**: a small window lists them, each with its value and whether it is automatic or entered by hand; nothing is chosen until you pick one, then **Link** |

Each row's action is also in the menu you open with a right-click on the row. **Link all** and **Create all** act on the rows the group's filters leave, and say how many; **Link all** links them in a single save: if any is refused, none is linked. Nothing is linked unless you click. After **Create event**, only the rows you asked to create are linked, and only when the day now has exactly one event for them; a row that ends up with several events waits for **Choose event**. If the link is refused, the events stay created and the rows appear under **With one event**, ready for **Link**.

To act on some rows only, tick them in the first two groups: the bar above the tables shows **Link** and **Create event**, each with the number of rows it takes, and each acts only on the rows it fits. An action none of the selected rows can take is not shown. The linked rows leave the list and the selection; the other ticked rows stay ticked, so after **Link** the bar still offers **Create event** for the rest. When you scroll the window down, the bar moves into the bar at the bottom; **Esc** there clears the selection and leaves the window open.

!!! info "The event must be on the same date"

    A candidate is proposed only if it is **on the same day** as the transaction. It must be the same asset too, and of the matching type: a dividend with a dividend, an interest payment with an interest event, an adjustment with a price adjustment or a split.

    For example, you booked a dividend on **12 March**. An event of the same asset dated **12 March** is proposed. An event dated **10 March** is **not**, even though it is the only one nearby: the row shows *No event that day*.

    This is what happens when your broker credited the dividend a few days after the event. Open the transaction and pick the event yourself in **Linked Event** ([Transaction Form](form.md)).

---

## 🧰 The bulk workspace {: #bulk-workspace }

The workspace is a grid of draft rows — marked **new**, **edit** or **del** — where you prepare changes before writing them:

- **Add Row**, **Import** and **Reset All** sit above the grid. Ticking rows shows the selection bar at the top of the table — it moves into the bar at the bottom when you scroll — with **Reset selected**, **Link the charges**, **Unlink the charges**, **Delete selected** and, for a matching pair, **🔗 Promote pair**, each with the number of rows it takes. An action that does not apply to the ticked rows is not shown; one that applies but is blocked is shown off, and says why — **Promote pair**, for instance, when one of the two still has linked charges.
- Rows are checked as you work: problems appear at the top under *Validation errors were found*, and a click takes you to the row. With many rows, automatic checking pauses — press **⚡ Validate now** before saving.
- When two rows look like the two halves of one transfer or exchange, a green banner offers to **Merge** them — two new rows, two saved ones, or one of each. When it proposes more than one pair, **Merge all (N)** merges them in one go. Where the two rows of a pair have a different description or different tags, one choice applies to every pair: **All left** keeps the description and tags of the first row, as the banner lists it; **All right**, those of the second row; **Combine**, the default, keeps both descriptions and the tags of both rows. A description holds at most 500 characters, as on any transaction: with **Combine**, a pair whose two descriptions together would go past it is not merged, and a message says how many pairs were left — merge them one by one with **Merge**, where you can shorten the description.
- When the other half is already saved but not in the workspace — a transfer whose first side you imported last month, say — the 💡 button, above the grid and in the row's menu, offers to add it: once it is in, the banner offers the pair.
- **Save All** writes everything at once. If there are merge suggestions you have not looked at — the 💡 never opened, the green banner never clicked — it asks first (*Suggestions you have not looked at*): **Show the suggestions** opens the 💡 list, or brings the banner into view; **Save anyway** goes on. Once you have looked, it does not ask again until you close the workspace. **Cancel** closes the workspace, asking first if you have unsaved changes.

??? warning "🚦 Banners after an import — when they appear"

    After an import, banners above the grid list what to check before **Save All**:

    - **red** — rows the importer did not fully understand: **Save All** stays disabled until you complete them;
    - **amber** — auto-derived fields to verify: **Save All** first asks you to **Review** them or **Save anyway**;
    - **amber, dates** — rows dated before 1 January 1900, listed one by one (click a line to go to the row): **Save All** asks once for all of them (*Yes, the dates are right*). A date that early is usually a typo; once confirmed it is saved like any other.
    - **amber** — rows that may be stock splits (Revolut and Trading212 imports): link a Split event to each, or create it from the banner; see [Revolut](import/revolut.md#stock-splits).

    Click a banner to unfold its list, then an entry: the grid turns to that row's page and highlights it. Balance problems list the rows that cause them (*Workspace rows: …*), and a click opens the first one in the current sort order. If your column filters hide the row, a message tells you so.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="transactions" data-name="bulk-todo-banner" alt="Bulk workspace with the banner of fields to verify unfolded and the clicked entry's row highlighted in the grid">
</div>

After a save, a **Promote pair** or a **Split pair**, the Transactions page clears its selection, since those rows may have changed; closing or cancelling keeps it. If a **Promote pair** or a **Split pair** is refused, nothing changes: an error message says why, and the confirmation stays open.

### 📎 Linked charges in the workspace {: #bulk-linked-charges }

- **Grouped rows** — a transaction's charges sit under it in the grid: the chip **N charges** opens and closes the group, and each charge shows `↳`. They are saved with it, in the same **Save All**. The form's [Linked charges](form.md#linked-charges) section adds, links, unlinks and deletes them.
- **Unlink** — each charge under a transaction has its own checkbox; ticking the transaction does not tick its charges. Tick the charges you want to separate and click **Unlink** in the selection bar: it says how many of the ticked rows it takes, and each becomes a row of its own, as **Unlink** in its form does. Nothing is saved before **Save All**. Until then **Reset selected** puts a charge already saved under that transaction back there; a new charge, or one linked only in this workspace, is joined again with **Link**.
- **Link** — tick one transaction and the charges that belong to it, then click **Link** above the grid. Rows not saved yet can be linked too: the window and the messages name a new row by its number, such as *row 3*. The link is written by **Save All**. A greyed-out **Link** says why on tap or with the keyboard; besides the reasons of the list, a row marked for deletion must be restored first.
- **Delete** — **Mark for deletion** on a transaction with linked charges, or **Delete selected** with such a transaction among the rows, asks the same question as the list: **Keep the charges** or **Delete all**. **Restore** on the transaction brings back the charges that choice changed, also when the question was asked on the Transactions page or a broker's tab; a charge you deleted or unlinked yourself stays as you left it.
- **Merging into a transfer or an exchange** — a transaction that still has linked charges cannot become half of a pair, so the workspace offers no merge for it: not in the suggestions or the 💡 search, and the selection toolbar's merge button is off — tap or hover it to see which transaction has charges. The Transactions page does the same with its **Promote pair** action. **Unlink** its charges first, or mark them for deletion; the offer comes back, and **Save All** saves both together. After the merge such a charge is a row of its own, and **Reset row** or **Restore** on it keeps it unlinked, saying why. A reset that touches a row of a merge not saved yet — **Reset row**, **Reset selected** or **Reset all** — undoes that merge too: a saved transaction comes back as saved, and a new one as a new row of its own. The same goes for a **Split pair** not saved yet: resetting either half brings the pair back as one row, nothing is split on save, and a charge you linked to a half in the meantime comes back as it was before you linked it, with a message saying why. **Undo split** does the same. Unlinking a charge you linked in the workspace only undoes that link: a charge that had no parent comes back with none, and nothing is sent for it.
- **A transaction that leaves the workspace** (a new one deleted, or **Remove from batch**) takes along the new charges you added in its form, unless you opened and applied one on its own. A charge you joined to it with **Link** stays, as a row of its own.

---

## 🧭 Contextual guides

The Transactions page, the **Add Transaction** form, the bulk workspace and the [Import Wizard](import/how-to.md#guided-first-import) each have a short guide. A guide starts only when its screen is ready and never edits a draft or presses a button for you; in the workspace it shows one notice at a time, closed with **Got it**.

Replay any guide from [Settings → Preferences → Onboarding and guides](../settings/preferences.md#onboarding-and-guides).

---

## 🔗 Related

* 📝 **[Transaction Form](form.md)** — fields and transaction types
* 📥 **[Import from Broker](import/index.md)** — the BRIM import workflow
* 📖 **[Transaction Types](../../financial-theory/instruments/transaction-types/index.md)** — the financial theory behind each type

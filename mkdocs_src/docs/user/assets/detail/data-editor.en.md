# ✏️ Data Editor

The Data Editor lets you fix and complete an asset's data by hand: its daily prices and its events, such as dividends. Use it to correct a wrong price from a provider, add the history of an asset without one, fill a gap, or record an event the provider missed.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-editor" alt="Asset Data Editor" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🛠️ Edit prices and events

1. In **Prices** mode, click **✏️ Edit Prices & Events** at the top right of the chart. The editor opens below the chart, with a **Prices** and an **Events** tab.
2. Change what you need:
    - **Add Row** adds a row on a free date: change the date if needed, then fill in the values.
    - Click a cell to edit it.
    - **Delete**, in a row's **⋮** menu, marks the row for deletion, and **Undo** brings it back. Tick several rows to delete them together.
    - **Import CSV** loads many rows at once ([below](#import-from-csv)).
3. Click **Save (n)**, where *n* counts your changes, or **Cancel** to drop them. Both close the editor and bring the other panels back; so does ✕, without saving.

Until you save, new and changed prices show on the chart as a purple line. A price saved outside the dates on screen widens them to include it.

---

## 💰 Prices tab

- **Close** is required and must be a positive number; **Open**, **High**, **Low** and **Volume** are optional, and the eraser in a cell clears its value.
- Prices are in the asset's currency, shown beside the tabs (*Prices in USD*).
- **Stale rows** are days without a price of their own, filled with the last known one. When there are some, a ⚠️ count and a switch appear: turn it on to hide them.

---

## 📅 Events tab

Each row has a **Type** (Dividend, Interest, Split, Price Adjustment or Maturity), an **Amount** in the asset's currency (per share for a dividend, the ratio for a split) and optional **Notes**. See [Asset Events](events.md) for what each type does.

- **Events from a provider are read-only**: an edit would be overwritten at its next sync. You can delete one, but the provider adds it back at its next sync; to remove it for good, change the asset's provider settings.
- **Editing one of your events changes that event**, its **Type** included: no second event is added. A transaction linked to it stays linked and is read according to the new type: an **Adjustment** linked to a split, for example, no longer counts as a split once the event is a Price Adjustment.
- **Changing an event's Type to the one another of your events has on that date** is refused when you save; swapping the types of two events in one save works. If you are deleting that other event, save the deletion first. A refused save keeps your changes in the editor for you to fix, while price changes from the same save are already stored.
- **An event a transaction is linked to** cannot be deleted: the save warns you instead.

---

## 📥 Import from CSV {: #import-from-csv }

**Import CSV** opens a window where you drop a file or paste its text, and each row is checked before you import it. The first line must name the columns, in any order.

=== "Prices"

    ```text
    date;currency;close;open;high;low;volume
    2024-01-15;USD;145.50;144.00;146.20;143.80;1500000
    2024-01-16;USD;146.10;;;;
    ```

    `date`, `currency` and `close` are required: write the asset's currency.

=== "Events"

    ```text
    date;currency;type;amount;notes
    2024-03-15;USD;DIVIDEND;1.25;Q1 payout
    2024-06-01;;SPLIT;2;2:1 split
    ```

    `date`, `type` and `amount` are required. `type` is one of `DIVIDEND`, `INTEREST`, `SPLIT`, `PRICE_ADJUSTMENT` and `MATURITY_SETTLEMENT`.

    `value` is accepted in place of `amount`, so an events file exported by LibreFolio (the backup offered when you [change an asset's currency](../create-edit.md#editing-an-asset)) imports back, its other columns ignored. Mind two limits:

    - **One event per date**: rows sharing a date are all left out as duplicates, so import such events from separate files.
    - **Every row becomes your own event**, a provider's included: leave out the rows whose `source` is `PROVIDER` if the provider will send them again, or they will show twice.

- Dates are `YYYY-MM-DD`, and decimals can use `.` or `,`.
- Columns are separated by `;` or `,`; with `,`, write decimals with `.`.
- Other columns are ignored, so a price file exported by LibreFolio imports as it is.
- The `currency` column is neither checked nor converted: amounts are stored in the asset's currency as they are, so convert those of a backup taken before a currency change first.
- A price line updates the price of its date; an event line updates your event with the same date and type. A line that matches only a provider's event is left out, since an import never changes those; the others are added. Nothing is stored until you click **Save**.

---

## 🖱️ Jump from the chart

With the editor open, double-click a point of the chart (or long-press it on a phone) to jump to that date: to the **Events** tab when the date has an event, to **Prices** otherwise.

---

## 🔗 Related

- 📈 **[Interactive Chart](chart.md)** — Chart visualization with event markers
- 📅 **[Asset Events](events.md)** — Event types and their sources
- 📚 **[Asset Events (Financial Theory)](../../../financial-theory/instruments/asset-events/index.md)** — Detailed impact analysis for each event type
- 🔌 **[Providers](../providers/index.md)** — Automatic price fetching
- 🛠️ **[Datapoint Editor Components](../../../developer/frontend/components/core-ui/data-editor.md)** — For developers: how the editor checks, merges and saves rows

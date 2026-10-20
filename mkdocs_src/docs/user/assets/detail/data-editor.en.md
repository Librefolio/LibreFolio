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

- **Close** is required and must be above 0; **Open**, **High**, **Low** and **Volume** are optional, 0 or more, and the eraser in a cell clears its value. LibreFolio keeps no negative price: a row with one, which only an imported file can bring, is not saved and counts as skipped.
- Prices are in the asset's currency, shown beside the tabs (*Prices in USD*).
- **Stale rows** are days without a price of their own, filled with the last known one. When there are some, a ⚠️ count and a switch appear: turn it on to hide them.
- **A price the server refuses is named.** If it refuses some of your prices, such as a close above the row's **High** or below its **Low**, it saves the others. A warning then names up to five refused dates, each with its reason, and counts the rest; it stays for 20 seconds, so you can note them and enter them again. If it refuses the whole save, for example because a date is after tomorrow, nothing is saved: the message says why, and the editor stays open with your changes.

---

## 📅 Events tab

Each row has a **Type** (Dividend, Interest, Split, Price Adjustment or Maturity), an **Amount** in the asset's currency (per share for a dividend, the ratio for a split) and optional **Notes**. See [Asset Events](events.md) for what each type does.

- **Events from a provider are read-only**: an edit would be overwritten at its next sync. You can delete one, but the provider adds it back at its next sync; to remove it for good, change the asset's provider settings.
- **Editing one of your events changes that event**, its **Type** included: no second event is added. A transaction linked to it stays linked and is read according to the new type: an **Adjustment** linked to a split, for example, no longer counts as a split once the event is a Price Adjustment.
- **Your event changes are saved all together, or not at all.** Deletions, edits and new rows go in one step, deletions first. If anything is refused, no event change is stored, deletions included: *Failed to save: …* tells you why, in your language, and your changes stay in the editor for you to fix. Price changes from the same save are stored all the same, since prices are saved first.

A save is refused, with a message that names the event at fault, when:

- **an event is in another currency than the asset's**: this comes from a CSV line, which keeps the currency it was written in ([below](#import-from-csv));
- **an event's new Type is the one another of your events has on that date**: swapping the types of two events in one save works, and so does deleting that other event in the same save;
- **you delete an event a transaction is linked to**: the message names the event and how many transactions use it. Remove the link from those transactions first. Before LibreFolio 1.3, the rest of the save went through and that deletion was skipped with a warning;
- **you change the Type of a split whose linked adjustments have no purchase cost**: without the split, those units would count as bought at an unknown price. The message counts those adjustments, including any at a broker you cannot see; give them a purchase cost first, then change the Type;
- **a Type is not one of the five**: this too comes from a CSV line.

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

    `date`, `type` and `amount` are required. `type` is one of `DIVIDEND`, `INTEREST`, `SPLIT`, `PRICE_ADJUSTMENT` and `MATURITY_SETTLEMENT`: any other value is refused when you save.

    `value` is accepted in place of `amount`, so an events file exported by LibreFolio (the backup offered when you [change an asset's currency](../create-edit.md#editing-an-asset)) imports back, its other columns ignored. Mind two limits:

    - **One event per date and type**: rows sharing both a date and a type are all left out as duplicates; a dividend and a split on the same day import together.
    - **Every row becomes your own event**, a provider's included: leave out the rows whose `source` is `PROVIDER` if the provider will send them again, or they will show twice.

    In that file, a note that starts with `=`, `+`, `-` or `@` has an apostrophe in front of it, so that a spreadsheet shows it as text instead of running it as a formula: the import removes that apostrophe, and the note comes back as it was.

- Dates are `YYYY-MM-DD`, and decimals can use `.` or `,`.
- Columns are separated by `;` or `,`; with `,`, write decimals with `.`.
- Other columns are ignored, so a price file exported by LibreFolio imports as it is.
- The `currency` column is never converted. On a price line it is not checked either: the price is stored in the asset's currency as it is. An event line keeps its currency, and one in another currency than the asset's is refused when you save; an empty one takes the asset's. So before importing a backup taken before a currency change, convert its amounts and write the asset's new currency.
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

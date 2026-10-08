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

- Dates are `YYYY-MM-DD`, and decimals can use `.` or `,`.
- Columns are separated by `;` or `,`; with `,`, write decimals with `.`.
- Other columns are ignored, so a price file exported by LibreFolio imports as it is.
- A row whose date is already in the table updates it; the others are added. Nothing is stored until you click **Save**.

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

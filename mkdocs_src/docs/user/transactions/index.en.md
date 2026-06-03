# 💸 Transactions

Transactions are the **core of LibreFolio** — every purchase, sale, dividend, fee, transfer, and cash movement you record lives here. Each broker has its own transaction list, accessible from the broker's detail page.

## 📋 Transaction Table

The transaction table displays all movements for a broker in reverse chronological order. Each row shows:

| Column | Description |
|--------|-------------|
| **Date** | Execution date of the transaction |
| **Type** | Icon + label: BUY, SELL, DIVIDEND, FEE, TRANSFER, etc. |
| **Asset** | Linked asset name (blank for cash operations) |
| **Quantity** | Number of units bought/sold/transferred |
| **Price** | Unit price at execution |
| **Amount** | Total value (quantity × price ± fees) |
| **Currency** | Transaction currency |
| **Notes** | Optional user note |

### Sorting & Filtering

- Click any **column header** to sort ascending/descending.
- Use the **search bar** to filter by asset name, type, or notes.
- Use the **type filter** buttons to show only specific transaction types.

---

## ➕ Adding Transactions

Click **+ New Transaction** to open the [Transaction Form](form.md). You can:

- Create a **single transaction** (one form per operation)
- Create a **bulk transaction** via the bulk import modal — paste or upload a table of rows

---

## ✏️ Editing & Deleting

- Click any row to **open the form** pre-filled with that transaction's data.
- Click the **trash icon** (:material-delete:) to delete a transaction.
- Select multiple rows with the **checkbox** column, then use the toolbar to **bulk delete**.

!!! warning "Deletions are permanent"

    There is no undo for deleted transactions. Export a backup first if you are unsure.

---

## ✂️ Split & Promote

Two special operations are available on **composite transactions** (TRANSFER and FX_CONVERSION):

### Split

A **split** breaks a composite transaction into its two constituent legs. Use this when a single imported row actually represents two separate events (e.g., a broker CSV that records a cross-currency transfer as one line).

1. Select the composite transaction row.
2. Click **Split** in the action toolbar.
3. LibreFolio separates it into two independent transactions.

### Promote

**Promote** upgrades a pair of individually-recorded transactions (e.g., a WITHDRAWAL from broker A and a DEPOSIT into broker B) into a linked **TRANSFER** composite. This is the standard way to record an asset move between your own brokers.

1. Select **exactly two transactions** of compatible types.
2. Click **Promote** in the toolbar.
3. LibreFolio validates compatibility (same asset, opposite directions, matching quantity) and links them.

---

## 📊 WAC — Weighted Average Cost

The transaction table integrates **WAC (Weighted Average Cost)** inline. When you add or edit a BUY/SELL:

- A **WAC preview** appears in the form showing the projected cost basis before saving.
- After saving, rows that affect the cost basis are marked with a **⚡ indicator**.
- The WAC is computed at runtime using FIFO/WAC rules — no separate step needed.

See [Financial Theory → Weighted Average Cost](../../financial-theory/portfolio-theory/weighted-average-cost.md) for the underlying methodology.

---

## 📥 Importing from Broker (BRIM)

Instead of entering transactions manually, you can import directly from your broker's export file. See **[Import from Broker](import/index.md)** for the step-by-step guide.

---

## 🔗 Related

- 📝 **[Transaction Form](form.md)** — Fields, validation, and type-specific options
- 📥 **[Import from Broker](import/index.md)** — BRIM import workflow
- 📖 **[Transaction Types](../../financial-theory/instruments/transaction-types/index.md)** — Financial theory behind each type

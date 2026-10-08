# <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="currentColor" d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6m1.8 18H14v-2h1.8v2m0-3H14v-2h1.8v2m0-3H14V9.8h1.8v4.2M13 9V3.5L18.5 9H13M6 20V4h5v7h7v9H6z"/></svg> Generic CSV

The **Generic CSV** importer reads a CSV file you prepare yourself. Name its columns as in the
[column reference](#column-reference) — `date` and `type` at least — and LibreFolio recognises
them by their names: there is nothing to map by hand.

## 🎯 When to Use

- Your broker is not in the [supported list](index.md).
- Your broker changed its export and its importer does not read it yet.
- You keep your own spreadsheet, or a script writes the CSV for you.

## ⚙️ How to Import It

1. **Prepare the file.** Save it as `.csv` (from Excel, save a copy as CSV). Its first row names the
   columns, as in the [column reference](#column-reference); other columns are ignored.
2. **Upload it** in the **[Import Wizard](how-to.md)** and assign it to its broker.
3. **Check the plugin** in **Select Files**: if **Generic CSV** is not already chosen, pick it in
   the file's **Plugin** column.
4. **Parse and review.** Each row becomes a transaction.

!!! tip "One file per broker — not one file per currency"

    Every row of a file is imported into the broker you assign to that file, so never mix two
    brokers in one CSV. Rows in different currencies can share the same file, as each row carries
    its own `currency`; you can also split a broker's history into several files, one per year
    for example, and import them together.

### 🧯 If Something Goes Wrong

- **"required column 'date' not found"** (or `type`): the first row lacks that column, or names it
  differently. Add it, or rename the column to an accepted name, and upload the file again.
- **A row is missing**: rows LibreFolio cannot read — an unknown type, a date in an unknown format,
  an empty `currency` — are skipped and listed among the warnings of the **Parse** step; rows with
  a wrong sign appear as validation issues. Fix them in the file and upload it again.
- **The bulk workspace asks for a cost on an `ADJUSTMENT` row**: enter the cost of **one** unit,
  not the total value of the position.

---

## 🔄 Converting a Custom Report

If your data comes from another tool, a short script can turn it into a Generic CSV. The
**[Generic CSV technical specification](../../../developer/backend/brim/generic_csv.md)** describes
the format in full — signs, which type to use when, worked examples. You can paste it into an AI
assistant (ChatGPT, Claude, Gemini…) with a few sample rows of your file and ask for the script.

---

## 📋 Column Reference {: #column-reference }

These are the columns LibreFolio recognises in a Generic CSV file. Column names are case-insensitive, and spaces around them are ignored.

| Column | Required? | Accepted aliases | Description |
|--------|-----------|-----------------|-------------|
| **`date`** | ✅ Always | `data`, `settlement_date`, `value_date`, `trade_date`, `fecha`, `datum`, `transaction_date`, `exec_date` | Transaction date |
| **`type`** | ✅ Always | `tipo`, `transaction_type`, `operation`, `operazione`, `action`, `azione`, `trans_type`, `op_type` | Transaction type — see values below |
| **`quantity`** | Required for BUY/SELL/ADJUSTMENT | `quantità`, `qty`, `shares`, `azioni`, `units`, `unità`, `amount_shares`, `num_shares` | Number of units. **Negative for SELL, positive for BUY.** |
| **`amount`** | Required for most types | `importo`, `value`, `cash`, `cash_amount`, `total`, `totale`, `net_amount`, `gross_amount`, `price` | Cash impact. **Negative when cash leaves, positive when cash enters.** Empty for ADJUSTMENT. |
| **`currency`** | Optional (defaults to EUR) | `valuta`, `ccy`, `curr`, `currency_code`, `divisa`, `währung` | ISO 4217 currency code. EUR applies only when the file has no currency column: if it has one, fill it on every row with an `amount`, or that row is skipped. |
| **`asset`** | Required for BUY/SELL/DIVIDEND/ADJUSTMENT | `symbol`, `ticker`, `isin`, `asset_id`, `instrument`, `strumento`, `security`, `titolo`, `name`, `nome` | Ticker, ISIN, or a consistent name string for unlisted assets |
| **`description`** | Optional | `descrizione`, `notes`, `memo`, `note`, `details`, `dettagli`, `comment`, `commento` | Free text notes |

### 🏷️ Valid `type` values

`BUY` · `SELL` · `DIVIDEND` · `INTEREST` · `DEPOSIT` · `WITHDRAWAL` · `FEE` · `TAX` · `ADJUSTMENT`

!!! warning "Not supported: TRANSFER, FX_CONVERSION, CASH_TRANSFER"

    These need two linked rows, which a CSV cannot express: such rows are skipped with a warning.
    Enter them by hand from the Transactions page, or use your broker's own importer.

---

## 🔗 Related

- 🧙 **[How to Import](how-to.md)** — the Import Wizard, step by step
- 🏦 **[Supported Brokers](index.md)** — check first whether your broker has its own importer
- 🛠️ **[Generic CSV technical specification](../../../developer/backend/brim/generic_csv.md)** — the full format, for scripts and developers

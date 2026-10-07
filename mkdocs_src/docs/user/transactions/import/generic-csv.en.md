# <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="currentColor" d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6m1.8 18H14v-2h1.8v2m0-3H14v-2h1.8v2m0-3H14V9.8h1.8v4.2M13 9V3.5L18.5 9H13M6 20V4h5v7h7v9H6z"/></svg> Generic CSV

The **Generic CSV** provider is a flexible fallback for brokers that are not directly supported. It recognises your columns automatically from their header names, so a CSV whose first row names its columns as listed in the [column reference](#column-reference) — `date` and `type` at least — can be imported with no mapping step.

## 🎯 When to Use

- Your broker is not in the supported list.
- A supported broker changed its export format and the plugin hasn't been updated yet.
- You have a custom spreadsheet or script-generated CSV you want to import.

LibreFolio offers the Generic CSV for a file only when the file's first row names both required columns, **`date`** and **`type`** — in English or with one of the aliases in the column reference below. If no plugin recognises your file the wizard lists every plugin, but picking the Generic CSV for a file without those two columns stops the analysis with an error that tells you what is missing — for example *Plugin 'broker_generic_csv' cannot parse file '…': required column 'date' not found in the CSV header* — and the file is marked as failed. To fix it, add the missing column to the file's first row (or rename the column that already holds those values to one of the accepted names) and upload the corrected file.

## ⚙️ How It Works

There are no columns to map by hand: LibreFolio reads the first row of the file and recognises each column by its name.

1. **Name your columns.** The first row must use the names in the [column reference](#column-reference) or one of their aliases — English names, plus a few Italian, Spanish and German ones — in upper or lower case alike. Columns with any other name are ignored, and when two columns match the same field, the leftmost one is used. The file must be a `.csv`: save an Excel workbook as CSV first.
2. **Upload it** in the **[Import Wizard](how-to.md)** and assign it to its broker.
3. **Select it.** In **Select Files**, the Generic CSV is chosen for the file automatically when it is the only plugin that recognises it, or when it is the broker's default import plugin; otherwise pick it in the file's **Plugin** column.
4. **Parse and review.** Each row becomes a transaction. A row that cannot be read — an unknown type, a date in an unknown format — is skipped instead, and listed among the warnings of the analysis, so you can fix it in the file and upload it again.

!!! tip "One file per broker — not one file per currency"

    Each file you upload is assigned to exactly **one broker**, and every row of the file is imported into that broker: keep one CSV per broker and never mix the rows of two brokers in the same file. Within one broker, rows in different currencies can share the **same file** — each row carries its own `currency` — so there is no need to split the file by currency. You can still split a broker's history across several files — one per year, for example — and import them together.

---

## 🔄 Converting a Custom Report

If your data source is not natively supported, you can write a conversion script to transform it into the Generic CSV format.

!!! info "Technical specifications for developers and LLMs"

    The complete format specification — including sign conventions, when to use each transaction type, P2P patterns, storno/reversal handling, and worked examples — is in the developer documentation:

    **[Generic CSV Provider — Technical Specification](../../../developer/backend/brim/generic_csv.md)**

    You can paste that page directly into an LLM (ChatGPT, Claude, Gemini…) along with your source file's sample rows and ask it to write a Python conversion script.

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

    These types require **paired legs** (two linked transactions), which a generic
    CSV cannot express — rows with these types are rejected during parsing. Enter
    them manually from the Transactions page, or use a broker-specific plugin that
    generates the pairs.

---

## 🔗 Related

- **[Generic CSV — Technical Specification](../../../developer/backend/brim/generic_csv.md)** — Sign conventions, P2P patterns, storno handling, LLM tip
- **[BRIM Architecture](../../../developer/backend/brim/architecture.md)** — How the import wizard works


# <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="currentColor" d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6m1.8 18H14v-2h1.8v2m0-3H14v-2h1.8v2m0-3H14V9.8h1.8v4.2M13 9V3.5L18.5 9H13M6 20V4h5v7h7v9H6z"/></svg> Generic CSV

The **Generic CSV** provider is a flexible fallback for brokers that are not directly supported. It allows manual column mapping so you can import from any CSV-based export.

## When to Use

- Your broker is not in the supported list.
- A supported broker changed its export format and the plugin hasn't been updated yet.
- You have a custom spreadsheet or script-generated CSV you want to import.

## How It Works

1. Upload your CSV file.
2. LibreFolio shows the raw columns detected.
3. Map each column to the corresponding LibreFolio field (date, type, asset, quantity, amount, currency, description).
4. Preview the parsed rows and confirm import.

---

## 🔄 Converting a Custom Report

If your data source is not natively supported, you can write a conversion script to transform it into the Generic CSV format.

!!! info "Technical specifications for developers and LLMs"

    The complete format specification — including sign conventions, when to use each transaction type, P2P patterns, storno/reversal handling, and worked examples — is in the developer documentation:

    **[Generic CSV Provider — Technical Specification](../../../developer/backend/brim/generic_csv.md)**

    You can paste that page directly into an LLM (ChatGPT, Claude, Gemini…) along with your source file's sample rows and ask it to write a Python conversion script.

---

## 📋 Column Reference

These are the columns LibreFolio recognises in a Generic CSV file. Column names are case-insensitive.

| Column | Required? | Accepted aliases | Description |
|--------|-----------|-----------------|-------------|
| **`date`** | ✅ Always | `data`, `settlement_date`, `value_date`, `trade_date`, `fecha`, `datum`, `transaction_date`, `exec_date` | Transaction date |
| **`type`** | ✅ Always | `tipo`, `transaction_type`, `operation`, `operazione`, `action`, `azione`, `trans_type`, `op_type` | Transaction type — see values below |
| **`quantity`** | Required for BUY/SELL/TRANSFER/ADJUSTMENT | `quantità`, `qty`, `shares`, `azioni`, `units`, `unità`, `amount_shares`, `num_shares` | Number of units. **Negative for SELL, positive for BUY.** |
| **`amount`** | Required for most types | `importo`, `value`, `cash`, `cash_amount`, `total`, `totale`, `net_amount`, `gross_amount`, `price` | Cash impact. **Negative when cash leaves, positive when cash enters.** Empty for TRANSFER and ADJUSTMENT. |
| **`currency`** | Optional (defaults to EUR) | `valuta`, `ccy`, `curr`, `currency_code`, `divisa`, `währung` | ISO 4217 currency code |
| **`asset`** | Required for BUY/SELL/DIVIDEND/TRANSFER/ADJUSTMENT | `symbol`, `ticker`, `isin`, `asset_id`, `instrument`, `strumento`, `security`, `titolo`, `name`, `nome` | Ticker, ISIN, or a consistent name string for unlisted assets |
| **`description`** | Optional | `descrizione`, `notes`, `memo`, `note`, `details`, `dettagli`, `comment`, `commento` | Free text notes |

### Valid `type` values

`BUY` · `SELL` · `DIVIDEND` · `INTEREST` · `DEPOSIT` · `WITHDRAWAL` · `FEE` · `TAX` · `TRANSFER` · `ADJUSTMENT` · `FX_CONVERSION` · `CASH_TRANSFER`

---

## 🔗 Related

- **[Generic CSV — Technical Specification](../../../developer/backend/brim/generic_csv.md)** — Sign conventions, P2P patterns, storno handling, LLM tip
- **[BRIM Architecture](../../../developer/backend/brim/architecture.md)** — How the import wizard works


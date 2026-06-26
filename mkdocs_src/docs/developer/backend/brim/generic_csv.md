# 🔧 Generic CSV Provider

The **Generic CSV Provider** (`broker_generic_csv`) is the fallback import plugin for BRIM. It accepts any CSV file that follows the column conventions below — even if it does not come from a specifically supported broker.

---

## 🤖 Tip: Use an LLM to write your conversion script

The fastest way to import data from an unsupported source is to **paste this entire page into an LLM** and ask it to write a Python script that transforms your data into the Generic CSV format.

!!! tip "Suggested prompt"

    ```
    Here is the LibreFolio Generic CSV format specification:
     
    [paste this page]

    I have data in this format: 
    
    [paste your file's header row and 2–3 sample rows]

    Write a Python script that reads my file and produces a valid LibreFolio Generic CSV.
    ```

    The LLM will produce a working script. Import the output CSV directly via BRIM.

    **Watch for sign convention errors** — this is the most common mistake. See [Sign Conventions](#sign-conventions) below.

---

## ⭐ Key Features

- **Header Auto-Detection**: Does not rely on fixed column names — maintains a dictionary of common synonyms per field.
- **Flexible Date Parsing**: Tries `YYYY-MM-DD`, `DD/MM/YYYY`, `MM/DD/YYYY`, and others automatically.
- **Flexible Number Parsing**: Handles both US (`1,234.56`) and European (`1.234,56`) formats.
- **Transaction Type Mapping**: Maps keywords (`buy`, `acquisto`, `compra`, …) to the `TransactionType` enum.
- **Low Priority**: `detection_priority = 0`, so specific high-confidence plugins are always tried first.

---

## 📋 Column Mapping Reference

| Column | Required | Description |
|--------|----------|-------------|
| **`date`** | ✅ Always | Transaction date. Accepts `2023-12-31`, `31/12/2023`, etc. |
| **`type`** | ✅ Always | One of: `BUY`, `SELL`, `DIVIDEND`, `INTEREST`, `DEPOSIT`, `WITHDRAWAL`, `FEE`, `TAX`, `TRANSFER`, `ADJUSTMENT`, `FX_CONVERSION`, `CASH_TRANSFER` |
| **`quantity`** | Depends on type | Number of units. See [Sign Conventions](#sign-conventions). |
| **`amount`** | Depends on type | Net cash impact. See [Sign Conventions](#sign-conventions). |
| **`currency`** | Optional | ISO 4217 code (`EUR`, `USD`). Defaults to `EUR`. |
| **`asset`** | Depends on type | Asset identifier. See [Asset Identifier](#asset-identifier). |
| **`description`** | Optional | Free text. Used as fallback for asset name resolution when no identifier is available. |

---

## 🔢 Sign Conventions

!!! danger "This is the most common mistake when writing conversion scripts"

    LibreFolio uses an **investor perspective** for signs:

    - **`quantity`**: positive when you **receive** units, negative when you **deliver** units
    - **`amount`**: positive when cash **enters** your account, negative when cash **leaves** your account

### Per-type quick reference

| Type | `quantity` sign | `amount` sign | Notes |
|------|----------------|--------------|-------|
| `BUY` | `+` (receive units) | `−` (pay cash) | e.g. `quantity=10`, `amount=-1500.00` |
| `SELL` | `−` (deliver units) | `+` (receive cash) | e.g. `quantity=-1`, `amount=+62.36` |
| `DIVIDEND` | none (0 or empty) | `+` | Cash distribution received |
| `INTEREST` | none | `+` | Interest income received |
| `DEPOSIT` | none | `+` | Cash entering the broker account |
| `WITHDRAWAL` | none | `−` | Cash leaving the broker account |
| `FEE` | none | `−` | Commission or fee paid |
| `TAX` | none | `−` | Tax or withholding paid |
| `TRANSFER` | `+` or `−` depending on direction | none (must be empty) | Asset movement between brokers |
| `ADJUSTMENT` | `+` or `−` | **must be empty** | Quantity-only correction (splits, gifts). **No cash movement.** |
| `FX_CONVERSION` | none | `+` or `−` | Paired with another leg via `related_transaction_id` |
| `CASH_TRANSFER` | none | `+` or `−` | Cash wire between brokers |

---

## 🏷️ Asset Identifier

The `asset` column accepts:

- **Ticker** (e.g. `AAPL`, `VWCE`) — for exchange-listed securities
- **ISIN** (e.g. `US0378331005`) — preferred when available; unambiguous across exchanges
- **Name / description** (e.g. `VIA SILONE`, `MARINA DI SCARLINO`) — for non-listed assets such as P2P loans, real estate, or anything without a market code

!!! tip "Non-listed assets (P2P loans, crowdfunding, real estate)"

    Use a consistent name string as the identifier (e.g. the project name). During BRIM import review you will be asked to map it — choose asset type **OTHER** since these are not exchange-traded instruments.

    If the BUY transaction has no obvious identifier in a dedicated column, extract the project name from the `description` field in your conversion script.

---

## 🔀 When to Use Each Transaction Type

### P2P lending / crowdfunding patterns

P2P platforms often issue a single report row that bundles capital repayment and interest. You need to **split this into two transactions** for LibreFolio:

| Platform event | LibreFolio transactions |
|----------------|------------------------|
| Principal repayment only | `SELL` (quantity=−fraction, amount=+principal) |
| Interest only | `INTEREST` (amount=+interest) |
| Principal + interest on same row | Two rows: `SELL` at exact cost basis + `INTEREST` for the earnings |
| Tax on interest | `TAX` (amount=−tax, same date as interest) |

!!! example "Example: P2P project repayment"

    Project "VIA SILONE": bought 1 unit at €3,005. Partial repayment of €300.50 capital + €15.00 interest.

    ```csv
    date,type,quantity,amount,currency,asset,description
    2024-06-01,SELL,-0.100000,300.50,EUR,VIA SILONE,Rimborso parziale capitali
    2024-06-01,INTEREST,,15.00,EUR,VIA SILONE,Interessi progetto VIA SILONE
    ```

    The SELL quantity is `−300.50 / 3005 = −0.100000` — the fraction of the 1-unit position being returned.

### Storno / reversal of a broker error

When a broker incorrectly credits an amount and then reverses it, you have two options:

**Option A — Clean history (recommended when the error and reversal are close in time)**

Delete both the erroneous credit and the reversal from your CSV. If they were on the same day, just net the amounts: record only the true net value as a single transaction.

> This keeps your portfolio charts clean with no artificial spikes.

**Option B — Exact ledger (when the two events are weeks or months apart)**

Record the reversal as the **opposite transaction** of the original:
- If the error was a `SELL` (cash in), the reversal is a `WITHDRAWAL` (cash out, same amount negative)
- If the error was a `DEPOSIT`, the reversal is a `WITHDRAWAL`

!!! warning "Do NOT use ADJUSTMENT for cash reversals"

    `ADJUSTMENT` must have an **empty amount** — it is strictly for quantity-only corrections (stock splits, share gifts). Using ADJUSTMENT for a cash reversal will leave the cash balance wrong.

### Fees and taxes

`FEE` and `TAX` are cash-only transactions (no quantity, no asset required):

```csv
date,type,amount,currency,description
2024-06-01,TAX,-28.31,EUR,Ritenuta d'acconto su interessi
2024-06-01,FEE,-1.50,EUR,Commissione operativa
```

---

## 🔍 How It Works: A Deeper Look

### 1️⃣ Column Detection (`_detect_columns`)

Maps the CSV's header row to LibreFolio's standard fields using a synonym dictionary:

```python
HEADER_MAPPINGS = {
    "date": ["date", "data", "settlement_date", ...],
    "type": ["type", "tipo", "operation", ...],
    "asset": ["asset", "symbol", "ticker", "isin", ...],
    # ...
}
```

### 2️⃣ Row Parsing (`_parse_row`)

1. **Extract Values** via `column_map`
2. **Parse Date** — tries multiple `strptime` formats
3. **Parse Type** — looks up lowercase string in `TYPE_MAPPINGS`
4. **Parse Numbers** — handles US and European decimal formats
5. **Handle Assets** — classifies identifier as ticker/ISIN/name; assigns consistent fake asset IDs for batch mapping in BRIM review

### 📐 3. The "Gold Standard" Example

The Generic CSV Provider is the perfect starting point for a new broker plugin. Copy its structure and:

1. Increase `detection_priority` to `100`
2. Add a `can_parse()` method to reliably detect your broker's file
3. Customize `HEADER_MAPPINGS` and `TYPE_MAPPINGS`
4. Refine parsing for any broker-specific quirks

---

## 📌 Complete Example Row by Row

This example shows a P2P portfolio lifecycle on a single platform (adapted from a real Recrowd import):

```csv
date,type,quantity,amount,currency,asset,description
2022-11-03,DEPOSIT,,6015.00,EUR,,Bonifico iniziale
2022-11-03,BUY,1,-3005.00,EUR,VIA SILONE,Investimento progetto VIA SILONE
2022-11-05,BUY,1,-2005.00,EUR,MARINA DI SCARLINO,Investimento progetto MARINA DI SCARLINO
2023-08-01,SELL,-0.031102,62.36,EUR,MARINA DI SCARLINO,Rimborso parziale capitali
2023-08-01,INTEREST,,15.20,EUR,MARINA DI SCARLINO,Interessi parziali
2023-08-01,TAX,,-3.95,EUR,,Ritenuta acconto interessi
2023-12-18,SELL,-1.000000,1005.00,EUR,EX ALBERGO VELA,Restituzione capitali completi
2023-12-18,INTEREST,,108.87,EUR,EX ALBERGO VELA,Interessi finali
2023-12-18,TAX,,-28.31,EUR,,Ritenuta 26% su interessi
2024-06-30,WITHDRAWAL,,-360.87,EUR,,Prelievo verso conto personale
```

Key points demonstrated:

- `DEPOSIT`: positive amount, no asset, no quantity
- `BUY`: positive quantity (receive units), negative amount (pay cash)
- `SELL`: negative quantity (deliver units), positive amount (receive cash)
- `INTEREST`: positive amount, asset optional, no quantity
- `TAX`: negative amount, no quantity, no asset required
- `WITHDRAWAL`: negative amount, no quantity, no asset

